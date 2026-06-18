# Scripts

This folder contains public preparation scripts used for parts of the EKDI data workflow.

## Scripts currently included

### build_dashboard_data.py

- Builds dashboard-ready layers, tables and metadata from intermediate analytical files and older dashboard outputs.
- Not runnable from a clean public clone as-is, because it references intermediate inputs and an older dashboard path that are not bundled here.

### build_cell_plant_candidates.py

- Links plant candidate evidence to published priority cells and writes app tables.
- Not runnable from a clean public clone as-is, because it expects intermediate files in a workspace-level `data/` folder outside the repository.

### build_cell_species_records.py

- Builds lightweight species-per-cell summaries for the app from a joined GBIF-plus-grid Parquet file.
- Not runnable from a clean public clone as-is, because the required Parquet input is not bundled and a local Parquet reader dependency is needed.

For public reproducibility guidance, see:

- [../docs/replication.md](../docs/replication.md)
- [../docs/input_manifest.md](../docs/input_manifest.md)
