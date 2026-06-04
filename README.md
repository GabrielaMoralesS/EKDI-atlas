# EKDI Atlas - Ecological Knowledge Decay Index

**Old GBIF-mediated records -> 5 km field-verification priorities.**

GBIF-mediated occurrence records preserve where biodiversity was documented, but many old records are reused without checking whether the landscape has changed since collection. EKDI turns old occurrence evidence into 5 km field-verification priorities for threatened biomes.

EKDI does not confirm current presence, absence, rediscovery or extinction. It identifies candidate evidence for expert review.

Repository: https://github.com/GabrielaMoralesS/EKDI-atlas

## What EKDI Adds To GBIF

GBIF tells us where biodiversity was recorded. EKDI asks where that knowledge may no longer be ecologically current after time, sampling gaps and habitat change.

This repository contains the Atlantic Forest case study dashboard, real-data metadata, export helpers and scripts used to prepare dashboard-ready outputs.

## Impact In 60 Seconds

- Critical Gaps: 5 km cells where old records, knowledge deficit and habitat-change context suggest field verification may be needed.
- Unsurveyed Forest: forested cells with no open GBIF-mediated records in this grid.
- Deficient Coverage: cells with limited or outdated evidence.
- Knowledge Ghosts: expert-review species signals, not extinction claims.
- Prepare GBIF Records: a browser-local readiness check for GBIF or Darwin Core-like occurrence tables.

## Core Workflow

1. Load GBIF-mediated occurrence records.
2. Overlay a spatial grid and biome boundary.
3. Add land-cover or habitat-change context.
4. Calculate sampling antiquity, post-record forest loss and richness deficit.
5. Generate EKDI priority classes.
6. Export dashboard-ready layers and field-planning outputs.

## EKDI Formula

For this Atlantic Forest pilot parametrization:

```text
EKDI = 0.45 x Sampling Antiquity
     + 0.35 x Post-Record Forest Loss
     + 0.20 x Richness Deficit
```

These weights are not universal. EKDI is a transferable prioritization framework, but weights, thresholds, habitat-change layers and validation assumptions must be recalibrated for each biome.

## What EKDI Does Not Claim

EKDI does not:

- declare species extinct;
- confirm species presence or absence;
- confirm rediscovery;
- replace expert taxonomic review;
- judge GBIF data as wrong;
- replace field verification, permits or vouchers.

Outputs are planning aids and candidate evidence for review.

## Data Sources

Core inputs:

- GBIF-mediated occurrence records.
- Biome boundary.
- Land-cover or habitat-change layer.
- Spatial grid resolution.

Optional enrichment:

- Local herbarium networks or speciesLink.
- National flora checklist such as Flora e Funga.
- IUCN or national red lists.
- GBIF issue flags.
- Protected areas and accessibility layers.

GBIF Download DOI: https://doi.org/10.15468/dl.evgrnx

This DOI refers to the source GBIF download. EKDI filters and joins these records to the Atlantic Forest 5 km grid for dashboard outputs; the full source download is not displayed directly as dashboard cells.

GBIF source download metadata:

- Creation date: 2026-05-07 00:18:22.
- Records included: 4,455,560 records from 872 published datasets.
- Compressed data size: 637.3 MB.
- Download format: simple tab-separated values TSV.
- Filters: Country = Brazil; HasCoordinate = true; HasGeospatialIssue = false; TaxonKey = Tracheophyta; Year = 1970-2026.

Additional source metadata are documented in the repository when available.

## How To Run Locally

From the repository root:

```bash
cd app
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

The current contest review work is staged in `app/index_v2.html`. It has not been promoted to `app/index.html`.

## Prepare GBIF Records

The browser workflow can validate a GBIF occurrence download or Darwin Core-like table for:

- total rows;
- records with coordinates;
- records with dates;
- oldest and newest year;
- records older than 20 and 30 years;
- unique species;
- oldest-evidence species;
- missing fields;
- readiness: ready / partial / not ready.

The browser readiness check does not draw uploaded records as Critical Gaps, calculate EKDI scores or update the Atlantic Forest dashboard. Full EKDI recalculation for another biome requires the reproducible pipeline, a target grid, habitat-change layers and recalibrated weights/thresholds.

## Other Biomes

Candidate next pilots include the Cerrado and Sundaland, pending comparable occurrence density, land-cover layers and validation partners.

EKDI is a transferable prioritization framework through the reproducible pipeline. A compact example workflow is planned for the repository.

## Repository Structure

```text
repo/
  app/
    index.html
    index_v2.html
    data/
  docs/
  scripts/
  README.md
  LICENSE
  CITATION.cff
  CHANGELOG.md
```

## Citation

See `CITATION.cff`.

## License

Code is released under the MIT License. Data files retain the licenses of their original sources.
