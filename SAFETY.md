# HydraLoop Safety Policy

HydraLoop is a synthetic, sandboxed research prototype.

## Scope Containment

The system does not target live payment systems.

It does not access:

- real cardholder data,
- personally identifiable information,
- production payment rails,
- real banking APIs,
- real merchant systems,
- real user accounts.

## Abstraction Policy

HydraLoop simulates behavioral and statistical footprints only.

HydraLoop does not generate:

- phishing messages,
- scam scripts,
- persuasion content,
- deepfake audio,
- deepfake video,
- synthetic identity documents,
- exploit code,
- credential stuffing tools,
- malware,
- operational fraud tooling.

The Red Team output space is a constrained Attack Genome DSL.

## LLM Use Policy

If an LLM Strategist is used, it only proposes schema-constrained genome parameters.

It does not generate free-form attack content.

All LLM proposals are:

- validated,
- logged,
- rejected if invalid.

## Data Policy

All generated data is synthetic.

Any external dataset used for fidelity comparison must be:

- publicly available,
- license-checked,
- documented in ASSUMPTIONS.md,
- used only for permitted evaluation purposes.

## Responsible AI Statement

HydraLoop is designed to improve defensive understanding.

It is not intended to enable, instruct, or assist real-world fraud.

Any deployment in a real payment environment would require:

- authorized data,
- privacy review,
- security review,
- regulatory review,
- model risk governance,
- human oversight,
- operational controls.