# HydraLoop Data Card

## Data Type

All data HydraLoop produces is synthetic.

## Source

No real cardholder data, PII, or production payment data is used.

## Generation Method

A discrete-event synthetic payment simulator produces every record. Each emitted
dataset carries a `synthetic: true` header.

## Intended Use

- model training inside the HydraLoop sandbox,
- evaluation of detection policies,
- adversarial co-evolution experiments.

## Prohibited Use

- live targeting,
- real payment system integration,
- operational fraud enablement.

## External Reference Data

If external public datasets are used, they will be listed here with:

- source,
- license,
- access date,
- permitted use,
- comparison purpose.

Currently: no external reference data is assumed.