# Data Sources

This manifest is a provenance ledger, not a file listing. For every input EKDI depends on, it states the exact source, version where known, whether it is bundled in this public repository, and why — so a reviewer never has to guess what the analysis actually used.

## External sources, by name and version

| Source | What EKDI uses it for | Version / access date | Status |
| --- | --- | --- | --- |
| **GBIF occurrence download** | Primary occurrence evidence for the Atlantic Forest grid | DOI **[10.15468/dl.evgrnx](https://doi.org/10.15468/dl.evgrnx)** | ✅ DOI documented in shipped metadata |
| **MapBiomas** | Annual land-cover transitions used for Post-Record Forest Loss | Collection version and access date not yet finalized in this public build | ⚠️ Documented gap — see note below |
| **FloraBR** | Endemic species reference list for expected-richness estimation | Access date not yet finalized in this public build | ⚠️ Documented gap — see note below |

**On the two open items above:** EKDI states this gap explicitly rather than fabricating a version number. The exact MapBiomas collection and FloraBR access date used to build the shipped Atlantic Forest atlas will be added here and in the in-app Source Verifiability panel before final archival release. Declaring this as open is preferable to guessing a version that cannot be verified.

## Bundled processed outputs — what ships in this repository

These are the files a clean clone actually runs from. Nothing here is a placeholder.

| File | Produces | Bundled? |
| --- | --- | --- |
| `app/data/geo/priority_cells_light.geojson` | Fast-rendering priority-cell layer used by the live app | ✅ Yes |
| `app/data/geo/priority_cells.geojson` | Full published priority-cell layer (archival, not loaded by default) | ✅ Yes |
| `app/data/tables/state_summary.json` | State-level summary statistics shown in the dashboard | ✅ Yes |
| `app/data/metadata/scientific_report.json` | Populates the in-app Scientific Report | ✅ Yes |
| `app/data/metadata/data_integrity.json` | Populates the in-app Data Integrity view | ✅ Yes |
| `app/data/metadata/sources.json` | Source metadata and GBIF DOI notes for the shipped build | ✅ Yes |

**This is sufficient for Level 1 reproducibility** (see [Reproducibility](reproducibility.md)): a reviewer can clone this repository and see the exact submission artifact with no missing data.

## Intermediate inputs — required for Level 2/3, not bundled

These are real files that exist locally during development but are not included in the public clone, with the specific reason in each case.

| Path | Purpose | Why it's not bundled |
| --- | --- | --- |
| `data/grid_final.gpkg` | Analytical 5 km grid with geometry and EKDI component fields (`cell_id`, sampling antiquity, post-record loss, richness deficit, EKDI score, priority class) | Geometry file exceeds practical Git size for a public submission repository |
| `data/gbif_grid_joined.parquet` | GBIF occurrence table joined to the 5 km grid | Derived directly from the GBIF DOI above via local join; regenerable but not pre-computed here |
| `data/grid_endemicas.gpkg` | Enrichment grid for plant-candidate linkage | Same size constraint as `grid_final.gpkg` |
| `data/ghost_species.csv` | Knowledge Ghost support table | Derived output of the endemism + single-record + forest-loss join; regenerable from the above |
| `data/extinction_risk_analysis.csv` | Threat and rediscovery support table | Requires external threat-assessment cross-reference not redistributable at full resolution |
| `data/perdida_forestal_por_celda.gpkg` | Cell-level forest-loss values (when not already on the analytical grid) | Derived from MapBiomas transition rasters via Google Earth Engine; regeneration requires GEE access |
| Expected-richness reference | Input to Richness Deficit calculation | Built from FloraBR cross-tabulation; access-date pending (see note above) |
| Biome boundary and grid-construction inputs | Raw spatial supports used in earlier preprocessing | Upstream of the analytical grid; regenerable from public IBGE/MapBiomas boundaries |

**None of these are missing by oversight.** Each is either a derived file regenerable from sources already documented above, or a file whose size or licensing makes redistribution in a public Git repository impractical. `scripts/run_ekdi_pipeline.py --check-inputs` checks for each of these by exact expected path and reports precisely which are absent — it does not fail silently or proceed with a partial computation.

## Verifying this manifest yourself

```bash
python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json --check-inputs
```

This prints a pass/fail line for every path listed in the "Intermediate inputs" table above against your local filesystem — the fastest way to confirm this document matches the actual code, not just prose.

See also: [Methodology](methodology.md) · [Reproducibility](reproducibility.md) · [Limitations](limitations.md)
