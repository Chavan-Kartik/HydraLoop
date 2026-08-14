"""The discrete-event engine.

Sessions are processed in timestamp order, so an entity's online state is always
point-in-time correct when its features are frozen. Delayed events (settlement,
dispute, chargeback) are scheduled onto the clock and appended when they fire,
which is what gives the twin realistic label delay.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .clock import EventClock
from .decision import (
    AlwaysApprove,
    BudgetState,
    DecisionContext,
    RiskDecisionEngine,
)
from .entities import Cardholder
from .labels import LabelModel
from .lifecycle import TransactionState
from .online import EntityState, snapshot_features
from .population import SECONDS_PER_DAY, Population
from .rng import RngRegistry
from .schema import Action, AuthRequest, Channel, Event, EventType

_CHANNELS = (Channel.A2A, Channel.WALLET, Channel.CARD_NOT_PRESENT)


@dataclass
class SessionSpec:
    """A request to run one session. Unset fields are sampled from priors."""

    ts: float
    cardholder_id: str
    is_fraud: bool = False
    attack_id: str | None = None
    genome_id: str | None = None
    amount_minor: int | None = None
    channel: Channel | None = None
    merchant_id: str | None = None
    payee_id: str | None = None
    device_id: str | None = None
    abandon_prob: float | None = None


@dataclass
class SimulationResult:
    events: list[dict]
    transactions: list[dict]
    horizon_s: float


class TwinEngine:
    def __init__(
        self,
        population: Population,
        registry: RngRegistry,
        label_model: LabelModel,
        horizon_s: float,
        decision_engine: RiskDecisionEngine | None = None,
        settlement_delay_s: float = 12 * 3600.0,
    ) -> None:
        self.pop = population
        self.registry = registry
        self.labels = label_model
        self.horizon_s = horizon_s
        self.decision = decision_engine or AlwaysApprove()
        self.settlement_delay_s = settlement_delay_s

        self._holders = {c.cardholder_id: c for c in population.cardholders}
        self._state: dict[str, EntityState] = {
            c.cardholder_id: EntityState(created_ts=c.created_ts) for c in population.cardholders
        }
        self._events: list[dict] = []
        self._txns: list[dict] = []
        self._event_id = 0
        self._budget_step_ups: dict[int, int] = {}
        self._budget_reviews: dict[int, int] = {}

    # -- event helpers -----------------------------------------------------
    def _emit(
        self,
        txn_id: str,
        session_id: str,
        ts: float,
        etype: EventType,
        cardholder_id: str,
        detail: dict | None = None,
    ) -> None:
        censored = ts > self.horizon_s
        self._events.append(
            Event(
                event_id=self._event_id,
                txn_id=txn_id,
                session_id=session_id,
                ts=ts,
                event_type=etype,
                cardholder_id=cardholder_id,
                detail=detail or {},
                censored=censored,
            ).to_row()
        )
        self._event_id += 1

    def _budget_state(self, ts: float, defender_cfg) -> BudgetState:
        day = int(ts // SECONDS_PER_DAY)
        return BudgetState(
            day_index=day,
            step_ups_today=self._budget_step_ups.get(day, 0),
            step_up_budget=defender_cfg["step_up_budget"],
            reviews_today=self._budget_reviews.get(day, 0),
            review_capacity=defender_cfg["review_capacity"],
        )

    # -- sampling ----------------------------------------------------------
    def _sample_session(self, spec: SessionSpec, gen: np.random.Generator) -> AuthRequest:
        holder = self._holders[spec.cardholder_id]
        if spec.channel is not None:
            channel = spec.channel
        else:
            weights = np.array([holder.channel_weights.get(c.value, 0.0) for c in _CHANNELS])
            weights = weights / weights.sum() if weights.sum() > 0 else np.ones(3) / 3
            channel = _CHANNELS[int(gen.choice(len(_CHANNELS), p=weights))]

        if spec.merchant_id is not None:
            merchant = next(m for m in self.pop.merchants if m.merchant_id == spec.merchant_id)
        else:
            idx = int(gen.choice(len(self.pop.merchants), p=self.pop.merchant_weights))
            merchant = self.pop.merchants[idx]

        if spec.amount_minor is not None:
            amount = max(1, int(spec.amount_minor))
        else:
            amount = max(1, int(gen.lognormal(merchant.amount_mu_minor, merchant.amount_sigma)))

        if spec.device_id is not None:
            device_id = spec.device_id
        elif holder.device_ids and gen.random() < 0.95:
            device_id = holder.device_ids[int(gen.integers(0, len(holder.device_ids)))]
        else:
            device_id = f"{holder.cardholder_id}_newdev_{int(gen.integers(0, 1_000_000))}"

        payee_id: str | None = None
        if channel in (Channel.A2A, Channel.WALLET):
            if spec.payee_id is not None:
                payee_id = spec.payee_id
            elif holder.payee_ids:
                payee_id = holder.payee_ids[int(gen.integers(0, len(holder.payee_ids)))]

        txn_id = f"{spec.cardholder_id}-{ int(spec.ts) }-{self._event_id}"
        return AuthRequest(
            txn_id=txn_id,
            session_id=f"s-{txn_id}",
            ts=spec.ts,
            cardholder_id=spec.cardholder_id,
            device_id=device_id,
            merchant_id=merchant.merchant_id,
            payee_id=payee_id,
            channel=channel,
            amount_minor=amount,
            mcc=merchant.mcc,
        )

    # -- session runner ----------------------------------------------------
    def _run_session(self, spec: SessionSpec, defender_cfg: dict) -> None:
        gen = self.registry.stream(f"session:{spec.cardholder_id}:{int(spec.ts)}:{self._event_id}")
        ar = self._sample_session(spec, gen)
        holder: Cardholder = self._holders[spec.cardholder_id]
        state = self._state[spec.cardholder_id]
        txn, sess = ar.txn_id, ar.session_id

        self._emit(txn, sess, ar.ts, EventType.SESSION_START, ar.cardholder_id)
        self._emit(txn, sess, ar.ts, EventType.DEVICE_FINGERPRINT, ar.cardholder_id,
                   {"device_id": ar.device_id})
        self._emit(txn, sess, ar.ts, EventType.INTENT, ar.cardholder_id,
                   {"channel": ar.channel.value, "amount_minor": ar.amount_minor})
        self._emit(txn, sess, ar.ts, EventType.AUTH_REQUEST, ar.cardholder_id,
                   {"amount_minor": ar.amount_minor, "merchant_id": ar.merchant_id})

        features = snapshot_features(state, holder, ar, ar.ts)
        ctx = DecisionContext(
            as_of=ar.ts,
            auth_request=ar,
            features=features,
            budget_state=self._budget_state(ar.ts, defender_cfg),
        )
        decision = self.decision.decide(ctx)
        day = int(ar.ts // SECONDS_PER_DAY)

        tx = TransactionState(ar.amount_minor)
        self._emit(txn, sess, ar.ts, EventType.RISK_DECISION, ar.cardholder_id,
                   {"action": decision.action.value, "risk_score": decision.risk_score})

        approved = self._resolve_action(decision.action, spec, ar, tx, gen, day)

        settlement_ts = ar.ts + self.settlement_delay_s
        settled = False
        captured_minor = 0
        outcome = None
        if approved and tx.approved:
            tx.capture(ar.amount_minor)
            captured_minor = tx.captured_minor
            self._emit(txn, sess, ar.ts, EventType.CAPTURE, ar.cardholder_id,
                       {"amount_minor": captured_minor})
            self._emit(txn, sess, settlement_ts, EventType.SETTLEMENT, ar.cardholder_id,
                       {"amount_minor": captured_minor})
            settled = settlement_ts <= self.horizon_s
            label_gen = self.registry.stream(f"label:{txn}")
            outcome = self.labels.resolve(spec.is_fraud, captured=True,
                                          settlement_ts=settlement_ts, gen=label_gen)
            if outcome.disputed and outcome.dispute_ts is not None:
                tx.open_dispute()
                self._emit(txn, sess, outcome.dispute_ts, EventType.DISPUTE_OPENED,
                           ar.cardholder_id, {})
                if outcome.charged_back:
                    tx.chargeback()
                    self._emit(txn, sess, outcome.dispute_ts + 3600.0, EventType.CHARGEBACK,
                               ar.cardholder_id, {"amount_minor": captured_minor})

        # Update online state only with the auth that actually happened.
        state.observe(ar.ts, float(ar.amount_minor), ar.device_id, ar.payee_id)

        dispute_ts = outcome.dispute_ts if outcome else None
        self._txns.append(
            {
                "txn_id": txn,
                "session_id": sess,
                "ts": ar.ts,
                "cardholder_id": ar.cardholder_id,
                "device_id": ar.device_id,
                "merchant_id": ar.merchant_id,
                "payee_id": ar.payee_id,
                "channel": ar.channel.value,
                "amount_minor": ar.amount_minor,
                "mcc": ar.mcc,
                "action": decision.action.value,
                "risk_score": decision.risk_score,
                "degraded": decision.degraded,
                "approved": approved,
                "captured_minor": captured_minor,
                "settled": settled,
                "settlement_ts": settlement_ts if approved else None,
                "is_fraud": spec.is_fraud,
                "attack_id": spec.attack_id,
                "genome_id": spec.genome_id,
                "disputed": bool(outcome.disputed) if outcome else False,
                "dispute_ts": dispute_ts,
                "charged_back": bool(outcome.charged_back) if outcome else False,
                "label_observed_at": dispute_ts,
                "censored": ar.ts > self.horizon_s or (approved and settlement_ts > self.horizon_s),
                **features,
            }
        )

    def _resolve_action(
        self,
        action: Action,
        spec: SessionSpec,
        ar: AuthRequest,
        tx: TransactionState,
        gen: np.random.Generator,
        day: int,
    ) -> bool:
        """Return whether the auth is ultimately approved, emitting sub-events."""
        txn, sess = ar.txn_id, ar.session_id
        if action == Action.DECLINE:
            self._emit(txn, sess, ar.ts, EventType.AUTH_RESPONSE, ar.cardholder_id,
                       {"approved": False})
            return False

        if action in (Action.APPROVE, Action.SOFT_WARN, Action.DELAY_HOLD):
            tx.approve()
            self._emit(txn, sess, ar.ts, EventType.AUTH_RESPONSE, ar.cardholder_id,
                       {"approved": True})
            return True

        if action == Action.MANUAL_REVIEW:
            self._budget_reviews[day] = self._budget_reviews.get(day, 0) + 1
            # A reviewer approves legitimate traffic and blocks fraud most of the time.
            block = spec.is_fraud and gen.random() < 0.8
            if not block:
                tx.approve()
            self._emit(txn, sess, ar.ts, EventType.AUTH_RESPONSE, ar.cardholder_id,
                       {"approved": not block, "manual_review": True})
            return not block

        if action == Action.STEP_UP_3DS:
            self._budget_step_ups[day] = self._budget_step_ups.get(day, 0) + 1
            self._emit(txn, sess, ar.ts, EventType.THREE_DS_CHALLENGE, ar.cardholder_id, {})
            abandon = spec.abandon_prob if spec.abandon_prob is not None else (
                0.5 if spec.is_fraud else 0.04
            )
            passed = gen.random() >= abandon
            self._emit(txn, sess, ar.ts + 30.0, EventType.CHALLENGE_RESULT, ar.cardholder_id,
                       {"passed": passed})
            if passed:
                tx.approve()
                self._emit(txn, sess, ar.ts + 31.0, EventType.AUTH_RESPONSE, ar.cardholder_id,
                           {"approved": True})
                return True
            self._emit(txn, sess, ar.ts + 31.0, EventType.AUTH_RESPONSE, ar.cardholder_id,
                       {"approved": False})
            return False

        raise ValueError(f"unhandled action {action}")

    # -- public API --------------------------------------------------------
    def simulate(self, specs: list[SessionSpec], defender_cfg: dict | None = None) -> SimulationResult:
        defender_cfg = defender_cfg or {"step_up_budget": 10**9, "review_capacity": 10**9}
        clock = EventClock()
        for i, spec in enumerate(specs):
            clock.schedule(spec.ts, (i, spec))
        while clock:
            _, (_, spec) = clock.pop()
            self._run_session(spec, defender_cfg)
        return SimulationResult(
            events=self._events, transactions=self._txns, horizon_s=self.horizon_s
        )
