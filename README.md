# EKDI Atlas — Turning old GBIF occurrence records into field-verification priorities under landscape change

EKDI helps identify where old GBIF-mediated plant occurrence records should be reviewed first by combining time since last evidence, post-record habitat change, richness deficit and species-level fragile memory.

## Live Demo

- Live Atlas: [https://GabrielaMoralesS.github.io/EKDI-atlas/app/](https://GabrielaMoralesS.github.io/EKDI-atlas/app/)
- Competition version: [app/index.html](app/index.html)
- Editable V2 copy: [app/index_v2.html](app/index_v2.html)
- Previous/future-work prototype: [app/index_future_work.html](app/index_future_work.html)

## What problem does EKDI solve?

GBIF provides access to occurrence records and maps where biodiversity has been recorded. However, old records can lose ecological currency when the landscape changes after the last evidence. EKDI asks which old occurrence evidence should be prioritized for field verification.

## What EKDI adds to GBIF

- temporal knowledge decay;
- post-record habitat-change context;
- Critical Gaps as 5 km field-review priority cells;
- Knowledge Ghosts as species-level fragile-memory signals;
- Field Verification Planner and exports;
- Data Readiness Check with optional user GBIF download DOI.

## Critical Gaps vs Knowledge Ghosts

| Signal | Level | Question | Meaning |
| --- | --- | --- | --- |
| Critical Gap | 5 km grid cell | Where should field review start? | Place-level priority |
| Knowledge Ghost | Species evidence | Which species requires expert review? | Fragile species-level evidence |

Not every species in a Critical Gap is a Knowledge Ghost. Knowledge Ghost is not an official threat category and does not confirm presence, absence, rediscovery or extinction.

## Relationship to previous GBIF data-gap tools

Previous GBIF Challenge work has shown the value of mapping biodiversity data gaps and ignorance in space and time. EKDI builds on this tradition but shifts the question from "where are data missing?" to "where has old occurrence evidence become a priority for field verification under landscape change?"

What changes here is the combination of old occurrence evidence, post-record habitat change, field-verification outputs and species-level fragile memory.

## How it works

```text
GBIF-mediated plant occurrences
-> 5 km Atlantic Forest grid
-> sampling antiquity
-> post-record forest loss
-> richness deficit
-> EKDI priority classes
-> Critical Gaps
-> Knowledge Ghosts
-> Field Verification Outputs
```

## Main app workflow for judges

1. Open the live atlas.
2. Start with Critical Gaps.
3. Click a priority cell.
4. Review the species evidence table and Knowledge Ghost signals.
5. Export Field Verification Outputs or check a GBIF download in Data Readiness.

## Outputs

### Critical Gaps

- CSV
- JSON
- GeoJSON
- Markdown summary

### Field Planner

- CSV checklist
- JSON with provenance
- Markdown checklist

### Data Readiness

- CSV readiness summary
- JSON readiness report
- Darwin Core field check for uploaded occurrence records only

Darwin Core applies to occurrence records, not EKDI grid-cell priority outputs.

## Reproducibility and provenance

- GBIF source DOI is documented in app metadata and Sources.
- User-uploaded GBIF DOI can be added in Data Readiness Check.
- Exports preserve provenance fields.
- Scientific Report and Data Integrity are available inside the app.

Core GBIF source metadata already documented in this repository:

- GBIF source DOI: [https://doi.org/10.15468/dl.evgrnx](https://doi.org/10.15468/dl.evgrnx)
- Source download creation date: 2026-05-07 00:18:22
- Records included: 4,455,560
- Published datasets: 872

Supporting documentation:

- [docs/methodology.md](docs/methodology.md)
- [docs/provenance_and_audit.md](docs/provenance_and_audit.md)
- [docs/replication.md](docs/replication.md)
- [docs/gbif_submission_notes.md](docs/gbif_submission_notes.md)

## Why this can matter to GBIF nodes and data publishers

EKDI can help GBIF nodes, herbaria and biodiversity data users identify:

- areas where historical occurrence evidence may need review;
- candidate species requiring expert verification;
- field-checklist outputs for planning;
- readiness of user-provided GBIF downloads for EKDI-style analysis.

## How to run locally

From the repository root:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/app/
```

## Repository structure

```text
app/
  index.html
  index_v2.html
  index_future_work.html
  data/
docs/
scripts/
README.md
CITATION.cff
```

## Submission visuals

Existing repository screenshots:

1. [Landing page](docs/lab_guide_images/01_intro.png)
2. [Critical Gaps atlas view](docs/lab_guide_images/02_atlas.png)
3. [Layers panel](docs/lab_guide_images/03_layers.png)
4. [Priority Cell Review](docs/lab_guide_images/04_selected_cell.png)
5. [Plant candidate view](docs/lab_guide_images/05_plant_candidates.png)
6. [Field Expedition Planner](docs/lab_guide_images/07_expedition_planner.png)
7. [Data Integrity view](docs/lab_guide_images/08_data_integrity.png)

Additional recommended screenshots for submission capture:

1. Data Readiness Check with GBIF DOI field
2. Field Verification Outputs panel
3. Featured Knowledge Ghosts panel

## Limitations

- EKDI does not confirm extinction, rediscovery, presence or absence.
- Knowledge Ghost is not an official threat category.
- Updating to another biome requires rerunning the pipeline with a target grid, GBIF download, habitat-change layers and recalibrated parameters.
- Browser Data Readiness Check does not compute full EKDI scores.

## Citation

Morales Soto, G. (2026). EKDI Atlas — Ecological Knowledge Decay Index: Turning old GBIF occurrence records into field-verification priorities under landscape change. GBIF Ebbe Nielsen Challenge 2026. Instituto de Computacao, UNICAMP.

See [CITATION.cff](CITATION.cff) for repository citation metadata.

## License

Code is released under the MIT License. Data files retain the licenses of their original sources.
