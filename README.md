# EKDI Atlas — Ecological Knowledge Decay Index

**A field-verification atlas for ecological memory under landscape change.**

EKDI is a scientific decision-support interface that connects biodiversity occurrence records with landscape change to identify where ecological knowledge may need field verification.

## What EKDI Is

EKDI helps researchers ask where biodiversity knowledge may have become ecologically outdated after habitat change.

It is not just a gap map. It combines historical sampling, post-record habitat change and richness deficit into an interpretable priority atlas.

## Why It Matters

Biodiversity records preserve evidence from a place and time. Landscapes can change after those records were collected. EKDI helps turn open biodiversity data into field-verification questions for botanists, ecologists and conservation teams.

## Case Study: Mata Atlântica

This repository contains an advanced prototype for the Brazilian Mata Atlântica. The dashboard uses cleaned data layers prepared for public review and demonstration.

## What The Demo Shows

- Critical Gaps for botanical verification.
- Unsurveyed Forest cells with forest cover and no open GBIF records.
- Deficient Coverage cells where evidence may be incomplete or outdated.
- Historical Review cells requiring cautious interpretation.
- Botanical Evidence Summary, Plant Candidates and Expedition Planner outputs.

## Core Workflow

1. Load GBIF-mediated occurrence records.
2. Overlay a spatial grid and biome boundary.
3. Add land-cover or habitat-change context.
4. Calculate sampling antiquity, post-record forest loss and richness deficit.
5. Generate EKDI priority classes.
6. Export dashboard-ready layers and field-planning outputs.

## Data Sources

Core inputs:

- GBIF occurrence records.
- Biome boundary.
- Land-cover or habitat-change layer.
- Spatial grid resolution.

Optional enrichment:

- Local herbarium networks or speciesLink.
- National flora checklist such as Flora e Funga.
- IUCN or national red lists.
- GBIF issue flags.
- Protected areas and accessibility layers.

## EKDI Formula

For this Mata Atlântica case-study preset:

```text
EKDI = 0.45 × Sampling Antiquity
     + 0.35 × Post-Record Forest Loss
     + 0.20 × Richness Deficit
```

These weights are not universal. Other biomes require recalibration and validation.

## What EKDI Does Not Claim

EKDI does not:

- declare species extinct;
- confirm species presence;
- replace expert taxonomic review;
- judge GBIF data as wrong;
- replace field verification.

Outputs are planning aids and hypotheses for review.

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

If `python` is unavailable on Windows, try:

```bash
py -m http.server 8000
```

## How To Adapt To Another Biome

Use the same workflow with local inputs:

- occurrence data;
- biome or study boundary;
- land-cover or habitat-change layer;
- grid resolution;
- recalibrated weights;
- local expert validation.

Optional enrichment can be replaced with equivalent local herbarium, checklist or red-list sources.

## Repository Structure

```text
repo/
  app/
    index.html
    data/
  docs/
  scripts/
  README.md
  LICENSE
  CITATION.cff
  CHANGELOG.md
```

## Current Limitations

- This is an advanced prototype, not a final scientific publication.
- The priority GeoJSON is large for public web hosting.
- Some fields, such as nearest city, are not calculated yet.
- Plant Candidates and Rediscovery Candidates require validation.

## Data Verifiability

EKDI includes an internal audit workflow:

```bash
python scripts/run_internal_audit.py
```

Audit outputs are written to `audit/`.

EKDI source data are publicly verifiable, but exact reproducibility depends on metadata such as the GBIF download DOI, MapBiomas collection version and Flora e Funga source date.

Manual action needed before research or policy use: add the GBIF download DOI from the gbif.org user downloads page, the MapBiomas collection/version, and the flora checklist source date or version to `app/data/metadata/sources.json`.

## Next Steps

Near-term:

- validate plant candidate linkage;
- improve species record comparison;
- connect herbarium or speciesLink data where possible;
- add Flora e Funga validation;
- refine the field checklist;
- collect expert feedback.

Medium-term:

- run sensitivity analysis of EKDI weights;
- validate with known survey sites;
- test GitHub Pages deployment publicly;
- prepare GBIF submission materials.

## Citation

See `CITATION.cff`.

## License

Code is released under the MIT License. Data files retain the licenses of their original sources.
