# Replication

## Required Core Inputs

- GBIF occurrence records.
- Biome or study-area boundary.
- Land-cover or habitat-change layer.
- Grid resolution.

## Optional Enrichment Inputs

- speciesLink or local herbarium networks.
- Flora e Funga or national flora checklist.
- IUCN or national red list.
- GBIF issue flags.
- Protected areas.
- Accessibility layers.

EKDI Core can run without optional enrichment. Optional sources improve botanical interpretation but are not required.

## Pipeline Steps

1. Prepare occurrence records with coordinates, dates and taxonomic fields.
2. Prepare the biome boundary in a projected or WGS84-compatible spatial format.
3. Prepare land-cover or habitat-change layers for the study period.
4. Generate a grid at the selected resolution.
5. Join occurrence records to grid cells.
6. Calculate sampling antiquity.
7. Estimate post-record habitat change.
8. Estimate richness deficit.
9. Apply EKDI weights.
10. Classify priority cells.
11. Export dashboard-ready GeoJSON, JSON and CSV files.

## Recalibrating Weights

The Mata Atlântica preset is:

```text
0.45 Sampling Antiquity
0.35 Post-Record Forest Loss
0.20 Richness Deficit
```

For another biome, weights should be adjusted through expert consultation, sensitivity analysis and validation against known survey priorities.

## Building Dashboard Data

The public script is:

```bash
python scripts/build_dashboard_data.py
```

Before running, verify that expected input paths and dependencies are available.

## Publishing A Static Demo

The dashboard is static and can be served from `app/`.

```bash
cd app
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```
