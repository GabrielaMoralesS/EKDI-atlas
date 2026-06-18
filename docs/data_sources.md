# Data Sources

A clean clone can run the final EKDI Atlas from processed outputs in `app/data/`. Full scientific recomputation requires external or locally generated intermediate inputs listed below. This manifest documents those requirements explicitly so the public repository does not overstate repeatability.

## Bundled processed outputs

The public repository already includes the processed Atlantic Forest files needed by the browser atlas, including priority-cell layers, state summaries, and metadata used by the in-app Scientific Report and Data Integrity views.

Known GBIF source DOI documented in shipped metadata:

- [https://doi.org/10.15468/dl.evgrnx](https://doi.org/10.15468/dl.evgrnx)

## Inputs and outputs

| Path or input | Input type | Purpose | Included in repository? | Notes |
| --- | --- | --- | --- | --- |
| `app/data/geo/priority_cells_light.geojson` | Processed dashboard output | Initial priority-cell layer used by the official app for fast map rendering. | Yes | Shipped processed output for the final Atlantic Forest atlas. |
| `app/data/geo/priority_cells.geojson` | Processed dashboard output | Full published priority-cell layer retained as processed atlas output. | Yes | Not required for client-side recomputation; the official app starts from the light layer. |
| `app/data/tables/state_summary.json` | Processed dashboard output | State-level summary used by the browser atlas. | Yes | Shipped processed output. |
| `app/data/metadata/scientific_report.json` | Processed dashboard output | Processed metadata consumed by the in-app Scientific Report. | Yes | Open the Scientific Report inside the app for the current case-study narrative. |
| `app/data/metadata/data_integrity.json` | Processed dashboard output | Processed metadata consumed by the in-app Data Integrity view. | Yes | Documents current build checks and caveats. |
| `app/data/metadata/sources.json` | Processed dashboard output | Source metadata and DOI notes for the shipped atlas build. | Yes | Includes the documented EKDI GBIF DOI. |
| `data/grid_final.gpkg` | Intermediate derived input | Intermediate analytical grid containing geometry and EKDI component fields used to generate dashboard outputs. Expected fields may include `cell_id`, geometry, state, sampling antiquity or last-record fields, post-record loss, richness deficit, EKDI score, or priority class. | No | External/local intermediate input; not bundled in the public repository. Required for full recomputation. |
| `data/gbif_grid_joined.parquet` | Intermediate derived input | Intermediate GBIF occurrence table joined to the 5 km grid. | No | GBIF source DOI is documented in shipped metadata. External/local intermediate input; not bundled in the public repository. Required for full recomputation. |
| `data/grid_endemicas.gpkg` | Intermediate derived input | Enrichment grid used for plant-candidate linkage. | No | External/local intermediate input; not bundled in the public repository. Required for full recomputation. |
| `data/ghost_species.csv` | Intermediate derived input | Knowledge Ghost support table. | No | External/local intermediate input; not bundled in the public repository. Required for full recomputation. |
| `data/extinction_risk_analysis.csv` | Intermediate derived input | Threat and rediscovery support table used in analytical preparation. | No | External/local intermediate input; not bundled in the public repository. Required for full recomputation. |
| `data/perdida_forestal_por_celda.gpkg` | Intermediate derived input | Cell-level post-record habitat-change input when loss values are not already on the analytical grid. | No | External/local intermediate input; not bundled in the public repository. Required for full recomputation. |
| Expected-richness or richness-deficit source input | External/raw source input | Expected-richness or richness-deficit input used to compute cell-level richness deficit. | No | External/local source input; not bundled in the public repository. Required for full recomputation. |
| Boundary and grid-construction inputs | External/raw source input | Biome geometry and raw spatial supports used in earlier preprocessing steps. | No | External/local source input; not bundled in the public repository. Required for full raw-to-final recomputation. |

## Notes

- Level 1 repeatability runs from processed outputs already bundled in `app/data/`.
- `scripts/run_ekdi_pipeline.py` can validate a configuration even when some configured files are missing locally.
- Full recomputation requires the external or local intermediate inputs listed above.
- The browser app visualizes processed EKDI outputs and does not recompute the full EKDI index client-side.
