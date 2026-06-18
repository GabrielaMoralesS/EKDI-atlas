# Scripts

This folder contains public preparation scripts used for parts of the EKDI data workflow.

For reproducibility scope, see:

- [../docs/reproducibility.md](../docs/reproducibility.md)
- [../docs/data_sources.md](../docs/data_sources.md)

## Suggested execution order

1. `run_ekdi_pipeline.py`  
   Validate configuration, check required local inputs, and run the reproducible pipeline structure when intermediate inputs are available.

2. `build_dashboard_data.py`  
   Build processed dashboard layers, tables, and metadata from intermediate analytical files and existing project outputs.

3. `build_cell_plant_candidates.py`  
   Build cell-linked plant candidate tables from plant-bearing enrichment inputs and published priority cells.

4. `build_cell_species_records.py`  
   Build cell-level GBIF plant evidence summaries from the joined occurrence-grid table and published candidate outputs.

## Scripts currently included

### run_ekdi_pipeline.py

- Role: config/input checks and reproducible run structure for EKDI reruns.
- Expected inputs: `configs/atlantic_forest.json`, plus local intermediate files such as `data/grid_final.gpkg`, `data/gbif_grid_joined.parquet`, `data/grid_endemicas.gpkg`, `data/ghost_species.csv`, and `data/extinction_risk_analysis.csv`.
- Expected outputs: run reports and regenerated outputs under `outputs/ekdi_runs/` unless the config points elsewhere.

### build_dashboard_data.py

- Role: build dashboard-ready layers, tables, and metadata from intermediate analytical inputs and existing project outputs.
- Expected inputs: local `data/grid_final.gpkg`, `data/grid_endemicas.gpkg`, `data/ghost_species.csv`, `data/extinction_risk_analysis.csv`, `data/critical_gaps_top100.csv`, plus existing dashboard spatial layers.
- Expected outputs: processed `geo/`, `points/`, `tables/`, and `metadata/` dashboard products.

### build_cell_plant_candidates.py

- Role: link plant candidate evidence to published priority cells and write app tables.
- Expected inputs: `app/data/geo/priority_cells.geojson`, local `data/grid_endemicas.gpkg`, `data/extinction_risk_analysis.csv`, `data/ghost_species.csv`, `data/grid_final.gpkg`, and `data/critical_gaps_top100.csv`.
- Expected outputs: `app/data/tables/cell_plant_candidates.json` and `app/data/tables/state_plant_context.json`.

### build_cell_species_records.py

- Role: build lightweight species-per-cell summaries for the app from the joined GBIF-plus-grid table.
- Expected inputs: local `data/gbif_grid_joined.parquet`, `app/data/tables/cell_plant_candidates.json`, and `app/data/geo/priority_cells.geojson`.
- Expected outputs: `app/data/tables/cell_species_records.json`, `cell_species_top10_by_cell.json`, `cell_species_top5_priority_cells.json`, `cell_species_top3_critical_gaps.json`, and `app/data/metadata/cell_species_records_columns.json`.
