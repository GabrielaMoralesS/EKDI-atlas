# Reproducibility

Reproducibility claims are only useful if they are falsifiable. This document states exactly what a reviewer can verify from a clean clone of this repository, what requires additional local inputs, and what cannot currently be regenerated from the public repository alone — with no claim left ambiguous.

## Why three levels, not one claim

Most biodiversity-informatics submissions either overstate reproducibility ("fully reproducible") or provide no detail at all. EKDI instead documents three distinct, independently verifiable repeatability levels, following the same principle used by reproducible-pipeline submissions in prior GBIF Ebbe Nielsen cycles (e.g. *bdc*, GridDER, 2022): **state precisely what each level guarantees, so a reviewer can verify the claim rather than trust it.**

| Level | Claim | Verifiable from clean clone? |
| --- | --- | --- |
| 1 — Run the atlas | The shipped Atlantic Forest atlas renders correctly from bundled processed outputs | ✅ Yes |
| 2 — Run the configurable pipeline | The pipeline script runs, validates inputs, and regenerates EKDI-style outputs when local inputs are supplied | ✅ Yes (script behavior); ⚠️ requires local inputs for full output regeneration |
| 3 — Full recomputation from raw GBIF data | The entire grid, habitat-change layers, and richness model can be rebuilt from primary sources | ⚠️ Not bundled — documented explicitly in [Data Sources](data_sources.md), not silently assumed |

## Level 1 — Run the final atlas from processed outputs

**Claim:** A reviewer can clone this repository and see the exact Atlantic Forest atlas referenced in the submission, with no missing data and no placeholder content.

**How to verify it:**

```bash
git clone https://github.com/GabrielaMoralesS/EKDI-atlas.git
cd EKDI-atlas
python -m http.server 8000
```

Open `http://localhost:8000/app/`. Confirm: Critical Gaps layer loads with 2,090 cells, summary cards show real numbers (not "Loading…"), and the Scientific Report opens with populated statistics rather than placeholder text.

The repository root `index.html` redirects to `./app/`; the canonical entry point is `app/index.html`.

**What this proves:** the bundled processed outputs in `app/data/` are complete, internally consistent, and sufficient to reproduce the exact submission artifact — independent of any external service, API key, or live data fetch.

## Level 2 — Run the configurable pipeline from intermediate inputs

**Claim:** The pipeline code is real, executable, and behaves as documented — not a placeholder script.

**Run it with no setup, against bundled sample data:**

```bash
python scripts/run_ekdi_pipeline.py --sample-demo
```

This executes against the bundled GBIF/Darwin Core-style sample CSV in `app/test_data/`, validates required occurrence fields (coordinates, event date, scientific name), summarizes coverage, and writes a run report to `outputs/ekdi_runs/`. **Success criterion:** the command exits without error and the report lists the same field-coverage statistics documented in this file's accompanying test fixture.

**Run it against your own intermediate inputs:**

```bash
python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json --check-inputs
python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json
```

`--check-inputs` validates that the configured grid, occurrence table, and habitat-change layers exist and have the expected schema before any computation runs — it will not generate a false success. Without those local intermediate inputs (see table below), the run reports exactly which file is missing rather than failing silently or fabricating output. Regenerated outputs are written to `outputs/ekdi_runs/` and never overwrite the shipped `app/data/` build.

**What this proves:** the scoring logic, weight application, and priority-class assignment described in [Methodology](methodology.md) are implemented in real, runnable code — not only described in prose.

## Level 3 — Full recomputation from raw GBIF data

**Claim:** full recomputation requires intermediate inputs not bundled in this public repository, and this document says exactly which ones, instead of implying the repository is self-sufficient.

To rebuild the Atlantic Forest atlas entirely from primary sources, a user needs to independently obtain:

- The GBIF occurrence download referenced by DOI **[10.15468/dl.evgrnx](https://doi.org/10.15468/dl.evgrnx)**, joined to a 5 km analytical grid
- MapBiomas annual land-cover transition layers for the same grid and time range
- A FloraBR-derived endemic species reference table for expected-richness estimation
- Biome-appropriate weight calibration (see [Methodology](methodology.md) — the 0.45/0.35/0.20 preset is Atlantic-Forest-specific, not universal)

Every one of these is listed with its exact expected path, format, and bundling status in [Data Sources](data_sources.md) — nothing is assumed or left for the user to guess.

**Why this isn't bundled:** the intermediate grid-join and land-cover-transition files exceed what is practical to version in a public Git repository and require Google Earth Engine access to regenerate from scratch. This is stated here rather than worked around with a partial or misleading bundle.

## Adapting EKDI beyond the Atlantic Forest

The Atlantic Forest is the demonstration case study, not the boundary of the method. EKDI is built as a configurable workflow around `scripts/run_ekdi_pipeline.py` and `configs/*.json` — adapting it to another biome means supplying a new config file plus the four input categories listed under Level 3 (GBIF occurrence data, a target grid, habitat-change layers, and a richness-deficit reference), and **re-deriving or re-justifying the component weights against that biome's actual drivers of evidence decay** — not reusing the Atlantic Forest preset by default.

Candidate next pilots: **Cerrado** and **Sundaland**, both of which combine comparable deforestation pressure with adequate existing GBIF occurrence density.

This repository does not claim EKDI is already validated globally. The claim is narrower and verifiable: the method, weighting logic, and pipeline code work as documented for the Atlantic Forest, and the same code can be pointed at a new config once the required inputs exist.

## Browser-app boundary

The browser app (Level 1) visualizes processed outputs only. It does not recompute the EKDI index client-side, and no button in the interface claims otherwise — including the in-app **Data Readiness Check**, which validates uploaded GBIF/Darwin Core tables for field completeness but does not run Level 2 or Level 3 computation in-browser.

## Provenance in every export

Every file generated by **Field Verification Outputs** in the live app — CSV, JSON, or Markdown — embeds its own provenance: the EKDI weight profile used, the source GBIF DOI, generation timestamp, and a suggested citation. A reviewer who downloads any export can trace it back to this repository and this methodology without relying on external memory of where the file came from.

See also:
- [Methodology](methodology.md) — the scoring formula and weight justification
- [Data Sources](data_sources.md) — every input file, its provenance, and bundling status
- [Limitations](limitations.md) — what EKDI does not claim
