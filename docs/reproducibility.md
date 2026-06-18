# Reproducibility

This public repository supports three honest repeatability levels.

## Level 1 - Run the final atlas from processed outputs

Supported from a clean clone.

The official public app entry point is `app/index.html`. The repository root `index.html` redirects to `./app/`.

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/app/
```

At this level, the browser app runs from processed Atlantic Forest outputs already bundled in `app/data/`.

## Level 2 - Run the configurable pipeline from intermediate inputs

Supported when the required local inputs exist.

```bash
python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json
```

Optional input check:

```bash
python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json --check-inputs
```

This level validates configuration, checks local inputs, and can regenerate EKDI-style outputs into `outputs/ekdi_runs/` without overwriting the shipped app build.

## Beyond the Atlantic Forest case study

The Atlantic Forest is the public case-study demonstration included in this repository, not the claimed limit of the EKDI approach.

EKDI is designed as an adaptable, configurable workflow built around:

- `scripts/run_ekdi_pipeline.py`
- `configs/atlantic_forest.json`
- additional `configs/*.json` files for other target regions

In practice, adapting EKDI to another biome requires users to provide:

- GBIF occurrence data or an equivalent occurrence table
- a target analytical grid
- land-cover or habitat-change layers
- richness-deficit support or equivalent analytical inputs
- biome-appropriate parameters, thresholds, and expert review choices

This repository does not claim that EKDI is already validated globally or that it can be transferred to any biome without recalibration. The intended framing is a configurable methodology and reusable workflow whose Atlantic Forest implementation can guide additional case-study builds when the required data and assumptions are documented explicitly.

## Run a sample GBIF occurrence readiness demo

Supported from the public clone as an input-readiness demo only.

```bash
python scripts/run_ekdi_pipeline.py --sample-demo
```

This demo reads the bundled sample GBIF/Darwin Core-like occurrence CSV in `app/test_data/`, checks required occurrence fields, summarizes coordinate/date/species coverage, and writes a run report.

It does not recompute the Atlantic Forest EKDI atlas. Full EKDI recalculation still requires a target grid, habitat-change layers, and calibrated weights.

## Level 3 - Full EKDI recomputation from raw or external sources

Not fully bundled in the public clone.

Full scientific recomputation still depends on external or locally generated intermediate inputs such as occurrence joins, analytical grids, habitat-change inputs, richness-deficit support, and enrichment tables. Those requirements are documented in [data_sources.md](data_sources.md).

## Browser-app boundary

The browser app visualizes processed EKDI outputs and does not recompute the full EKDI index client-side.

## Provenance and exports

- Processed metadata in `app/data/metadata/` document the current Atlantic Forest build.
- Exports preserve provenance fields instead of implying fresh computation in the browser.
- The in-app Scientific Report and Data Integrity views summarize the shipped case-study outputs, sources, and limitations.
