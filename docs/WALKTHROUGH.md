# 3-minute walkthrough

This is written for you, the person evaluating HydraLoop. Follow it in a browser and you will
have seen the whole system in three minutes. There is nothing to install.

Two things worth knowing first. Every transaction you see is synthetic, produced by the
simulator in this repository, so there is no real cardholder data anywhere in it. And the Lab
is live rather than a recording: when you type a description, the system really does map it to
an attack family, clamp a genome, run the payment twin, train a detector, and score the
traffic.

## Minute 1: make it run your attack

You land on the **Lab**, and a demo run starts on its own, so there will already be results on
screen. Ignore those and give it your own input, which is the part actually worth testing.

In **Threat description**, describe a payment fraud behaviour in your own words: cadence,
devices, amounts, how the money moves. Describe behaviour, not a method. For example:

> Someone hands a shopping agent a spending limit, and it starts buying at machine speed just
> under that limit, with no human pause between orders.

Press **Run Identify → Detect** and watch the five steps on the left. Identify names a family
and the signals it matched. Generate clamps your sentence into a schema-valid genome, which you
can read in the panel on the right. Simulate emits transactions from the twin. Detect scores
them, and the counters show how many attack transactions were caught against how many escaped.

Now click any row in **Scored traffic**. The Investigation pane gives you SHAP reason codes for
that one decision, each feature's contribution signed and ranked. Where a counterfactual
applies you also get a plain sentence naming one feature, the value it would have needed, and
the risk score before and after.

The point of this minute: free text becomes a constrained genome rather than free-form attack
content, and every individual decision is explainable.

## Minute 2: watch the defence fail, then fix itself

Stay on the same screen and scroll to the panel headed **Let it escape, then harden**. Press it.

Five stages run. An incumbent model goes on duty trained only on other families, so your attack
is genuinely novel to it. The attack escapes in wave one. Immune memory takes those escapes and
retrains. The **regression gauntlet** then checks the candidate, and the attack re-runs as wave
two.

The gauntlet is the part to scrutinise. A retrained model is promoted only if it has not
regressed on attacks the old model already handled. If it has, the candidate is rejected and
the incumbent stays live, which you will see stated on screen. Note also that wave two runs on
rows the model has never seen, so the improvement is not being measured on its own training
data.

## Minute 3: check whether to believe any of it

Open **Audit** in the sidebar. The run history is a hash chain, where each entry commits to the
hash of the one before it. Press **Verify chain**. Any edit to a past result, including one we
made ourselves, breaks verification on the next check.

Then open **Metrics** for escape rate and archive recall by generation, which is the trend the
whole loop exists to produce. **Arena** replays a full multi-generation run if you want the
narrated version, via the **Caption walkthrough** button.

That is the three minutes. Three screens remain if you have longer: **Threats** holds the
catalog of 28 scenarios across 7 families, and any card runs in the Lab; **Lineage** shows the
genome mutation trail with a plain-English brief per node; **Cases** collects the SHAP
investigations from the most recent episode.

## Ways to try to catch us out

These are the questions we would ask, so the answers are all reachable from the UI.

- Type deliberate nonsense, or an actual how-to. The output space is a domain-specific language,
  not text, so it clamps to a schema-valid genome or refuses. It will not write you an attack.
- Check the arithmetic. **Caught** plus **Escaped** should equal **Attack txns** exactly, and
  the split is the risk score against a stated 0.45 threshold, which you can check row by row
  in the scored traffic table.
- Compare the two waves in the harden panel and confirm the second runs on unseen rows.
- Verify the chain, run another pipeline so fresh entries are appended, then verify again.
- Run the same description twice. Seeds are fixed, so the run reproduces.

## Is this real data?

No, and deliberately so. It is fully synthetic, which is why anyone can run it with no PII, no
credentials, and no NDA. Fidelity is measured rather than asserted: `python -m hydraloop bench`
reports discriminator AUC along with TSTR and TRTS against a shifted reference, and
`python -m hydraloop bench --csv path/to/real.csv` benchmarks against a real dataset and reports
how well the detector transfers.

## If the Lab will not run

A deployment with no backend attached says so directly, and the read-only screens fall back to
a recorded snapshot. To run everything live, clone the repository and follow the Quickstart in
the [README](../README.md); the whole system runs offline on one machine.
