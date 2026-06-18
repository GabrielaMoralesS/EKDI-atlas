# Reproducibility

This public repository supports three honest repeatability levels.

## Level 1 - Run the final atlas from processed outputs

Supported from a clean clone.

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

## Level 3 - Full EKDI recomputation from raw or external sources

Not fully bundled in the public clone.

Full scientific recomputation still depends on external or locally generated intermediate inputs such as occurrence joins, analytical grids, habitat-change inputs, richness-deficit support, and enrichment tables. Those requirements are documented in [data_sources.md](data_sources.md).

## Browser-app boundary

The browser app visualizes processed EKDI outputs and does not recompute the full EKDI index client-side.

## Provenance and exports

- Processed metadata in `app/data/metadata/` document the current Atlantic Forest build.
- Exports preserve provenance fields instead of implying fresh computation in the browser.
- The in-app Scientific Report and Data Integrity views summarize the shipped case-study outputs, sources, and limitations.
