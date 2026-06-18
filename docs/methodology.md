# Methodology

## EKDI question

EKDI asks where botanical occurrence evidence may have become ecologically outdated after landscape change. It does not treat older records as wrong. It highlights where renewed interpretation and field verification may matter most.

## Atlantic Forest case-study preset

For the Atlantic Forest dashboard build:

```text
EKDI = 0.45 x Sampling Antiquity
     + 0.35 x Post-Record Forest Loss
     + 0.20 x Richness Deficit
```

These weights are a case-study preset, not a universal model.

## Core components

- **Sampling Antiquity:** how old the available occurrence evidence is for a cell.
- **Post-Record Forest Loss:** habitat change after the last linked evidence.
- **Richness Deficit:** expected biodiversity knowledge not reflected in observed open records.

## Main outputs

- **Critical Gaps:** 5 km field-review priority cells.
- **Knowledge Ghosts:** species-level fragile-evidence signals for expert review.
- **Field Outputs:** exports for verification planning and documentation.

## Interpretation boundary

EKDI is a decision-support atlas. It does not confirm species presence, absence, extinction, or rediscovery. Plant candidates and ghost signals remain evidence signals requiring voucher review, coordinate checks, taxonomic review, and field interpretation.

## Reproducibility links

For public repeatability levels and rerun scope, see [reproducibility.md](reproducibility.md).

For bundled outputs, GBIF DOI provenance, and missing recomputation inputs, see [data_sources.md](data_sources.md).
