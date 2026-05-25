# Scientific Report

The EKDI Scientific Report is a compact, audit-oriented summary generated from the cleaned dashboard data.

It is stored at:

```text
app/data/metadata/scientific_report.json
```

In this repository layout, the public app lives in:

```text
repo/app/data/metadata/scientific_report.json
```

## How It Is Generated

Run:

```text
python scripts/build_scientific_report.py
```

The script reads only dashboard-ready files and writes calculated values to `scientific_report.json`.

## Values Calculated

When fields are available, the report calculates:

- total cells and dashboard web-layer cells
- class counts
- EKDI score minimum, maximum, mean, median and standard deviation
- last-record temporal range
- normalized component statistics
- correlations between EKDI and available normalized components
- state-level critical-cell counts and mean EKDI
- linked plant candidate records
- unique species in the plant candidate table
- plant candidate risk-category distribution
- candidate-type distribution
- top species by years without record
- post-record forest-loss summary
- forest remaining distribution
- weight sensitivity summary when normalized component fields are available

## Values Not Yet Available

The current dashboard export does not provide:

- official GBIF DOI
- MapBiomas version
- Flora e Funga version
- access dates for all source datasets
- basis-of-record distribution
- critical-threshold percentile
- decadal forest-loss timeline
- complete floristic inventory per cell

These values are shown as `Not Provided`, `null` or a short limitation note. They are not invented.

## Weight Sensitivity Analysis

Run:

```text
python scripts/run_weight_sensitivity_analysis.py
```

The script reads normalized EKDI component fields from the cleaned dashboard export. If those fields are missing, it writes a not-calculated report instead of estimating values.

Outputs:

- `audit/WEIGHT_SENSITIVITY_ANALYSIS.md`
- `repo/app/data/metadata/weight_sensitivity_summary.json`

When calculated, the summary is included in `scientific_report.json`.

## Scientific Caveats

The Scientific Report is a decision-support summary. It does not confirm species presence or absence, does not declare extinction and does not replace botanical expert review.

Plant Candidate tables represent botanical evidence signals linked to grid cells. They are not complete floristic inventories and are not confirmed current occurrences.

Additional ecological limitations to review before publication:

- adjacent 5 km cells may not be statistically independent;
- herbarium records may reflect family-level and collector-specific sampling bias;
- DD, NE, Not Assessed, Not Linked and Not Provided are distinct threat-status states;
- forest cover percentage does not capture patch size, isolation or connectivity.
