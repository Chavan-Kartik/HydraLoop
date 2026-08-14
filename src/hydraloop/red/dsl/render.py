"""Render a genome as a one-paragraph plain-English attack brief.

This is the text read aloud on stage during the escape beat, so it favours
readable prose over an exhaustive gene dump.
"""

from __future__ import annotations

from .genome import Genome

_FAMILY_PHRASE = {
    "synthetic_identity": "a synthetic-identity operation",
    "account_takeover": "an account-takeover operation",
    "social_engineering": "an authorised-push-payment scam funnel",
    "merchant_abuse": "a merchant-side abuse scheme",
    "card_testing": "a card-testing and enumeration campaign",
    "money_movement": "a money-movement and layering scheme",
}


def render_brief(genome: Genome) -> str:
    g = genome.genes
    vs = g["victim_selection"]
    amt = g["amount_policy"]
    timing = g["timing_policy"]
    net = g["network_topology"]
    fric = g["friction_response"]
    budget = g["resource_budget"]
    channels = g["channel_mix"]["weights"]
    dominant_channel = max(channels, key=channels.get)

    family_phrase = _FAMILY_PHRASE.get(genome.family, genome.family.replace("_", " "))
    if amt["type"] == "ladder":
        amount_phrase = (
            f"escalates value through a {len(amt['steps'])}-step ladder up to "
            f"{int(amt['max_fraction'] * 100)}% of the target's {amt['base']}"
        )
    else:
        amount_phrase = (
            f"moves {amt['type']} amounts up to {int(amt['max_fraction'] * 100)}% "
            f"of the target's {amt['base']}"
        )

    label = genome.label or genome.attack_id or genome.genome_id
    return (
        f"{label}: {family_phrase} targeting the {vs['age_band'].replace('_', '-')} age band "
        f"in the {int(vs['balance_percentile_lo'] * 100)}-{int(vs['balance_percentile_hi'] * 100)} "
        f"balance percentile. It {amount_phrase}, favouring the {dominant_channel} channel, "
        f"with inter-transaction delays around {timing['inter_txn_delay_mu']:.1f} log-seconds and "
        f"a {timing['dwell_before_cashout_h']:.1f}-hour dwell before cash-out. Funds fan out to "
        f"{net['mule_fanout']} mule account(s) across {net['layering_depth']} layer(s). "
        f"When challenged with a step-up it abandons with probability "
        f"{fric['abandon_prob']:.2f} and retries after {fric['retry_after_h']:.0f} hours. "
        f"Budget: {budget['mule_accounts']} mule account(s), "
        f"{budget['synthetic_identities']} synthetic identity(ies), "
        f"{budget['operator_hours']:.1f} operator hours."
    )
