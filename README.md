# EKDI Atlas — Ecological Knowledge Decay Index

*Identifying where GBIF mediated botanical records may have become ecologically outdated*

[![Live Demo](https://img.shields.io/badge/Live%20Demo-open-blue)](https://GabrielaMoralesS.github.io/EKDI-atlas/app/)
![GBIF Challenge 2026](https://img.shields.io/badge/GBIF%20Challenge-2026-2c7a7b)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Case Study](https://img.shields.io/badge/Case%20Study-Atlantic%20Forest-2f855a)
[![GBIF DOI](https://img.shields.io/badge/GBIF%20DOI-10.15468%2Fdl.evgrnx-orange)](https://doi.org/10.15468/dl.evgrnx)

![Atlas overview](docs/images/01_intro.gif)

## The Problem

GBIF holds over 2 billion occurrence records. Many were collected decades before the deforestation events that followed. In the Atlantic Forest of Brazil alone, **2.22 million hectares of forest were lost after the botanical records describing those areas were collected** — yet those records are still reused today as if the landscape they describe were unchanged.

**EKDI makes that gap visible and turns it into a field-verification priority layer.**

## What EKDI Found

Running the EKDI pipeline against GBIF occurrence data for the Atlantic Forest identified:

- **2,090 Critical Gap cells** (5 km grid) Where old botanical evidence overlaps with significant post-record forest loss
- **4 Knowledge Ghost species** Endemic plants whose only GBIF record sits in a cell plants represented in the current EKDI build by very limited GBIF-mediated evidence:

| Species | Last GBIF record | Forest lost since |
| --- | --- | --- |
| *Varronia neowediana* | — | — |
| *Adenocalymma fistulosum* | — | — |
| *Bromus commutatus* | — | — |
| *Bothriochloa longipaniculata* | — | — |

A Knowledge Ghost is not a claim of extinction or absence — it is a signal that field or herbarium review is overdue.

## What EKDI Adds to GBIF

| GBIF occurrence maps | EKDI Atlas |
| --- | --- |
| Show **where** records were documented | Prioritize **where old evidence needs review** |
| Treat all occurrence records as current | Add habitat-change context and knowledge-decay scoring |
| Species points are the output | Critical Gaps, Knowledge Ghosts, and exportable field checklists are the output |
| One static download | Live atlas + GBIF download readiness checker for your own data |

## Try It With Your Own GBIF Data

EKDI isn't only a finished map , it's a tool you can use today. Inside the live app, **Data Readiness Check** Lets you upload a GBIF/Darwin Core-like occurrence table and check whether it contains the minimum fields required for EKDI-style analysis: scientific names, coordinates, dates and occurrence evidence.

## How It Works

```text
GBIF records → 5 km grid → sampling antiquity → habitat-change context
→ richness deficit → Critical Gaps → Knowledge Ghosts → Field Outputs
```

![Workflow](docs/images/Workflow.png)

EKDI score = weighted combination of **sampling antiquity** (how old is the evidence), **post-record forest loss** (how much habitat changed since), and **richness deficit** (how undersampled the area is relative to expectation). Full formula and weights are documented in [Methodology](docs/methodology.md) and visible live in the app's Scientific Report.

## Atlas Views

![Critical Gaps map](docs/images/03_layers.png)
*2,090 Critical Gap cells across the Atlantic Forest, ranked by EKDI score.*

![Priority Cell Review](docs/images/04_selected_cell.png)
*Per-cell evidence: last GBIF record, years of silence, forest loss, and linked plant candidates — with community observation and expert review*

![Field Outputs](docs/images/07_expedition_planner.png)
*Exportable, citation-ready field-verification checklists for botanists and herbaria.*

## Live Demo

**[Open the EKDI Atlas →](https://GabrielaMoralesS.github.io/EKDI-atlas/app/)**

No installation required. Built with MapLibre GL JS, runs entirely client-side from processed open data.

## Reproducibility — Three Honest Levels

This repository documents exactly what can and cannot be reproduced from the public clone alone — no overstated claims:

| Level | What it does | Status |
| --- | --- | --- |
| **1 — Run the atlas** | Loads the final Atlantic Forest atlas from processed outputs already bundled in `app/data/` | ✅ Supported from clean clone |
| **2 — Run the configurable pipeline** | Regenerates EKDI-style outputs from intermediate inputs via `python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json` | ✅ Supported when local inputs exist |
| **3 — Full recomputation from raw GBIF data** | Re-derives the analytical grid and habitat-change layers from scratch | ⚠️ Requires external/local intermediate inputs — see [Data Sources](docs/data_sources.md) |

Want to test the pipeline right now without any setup?

```bash
python scripts/run_ekdi_pipeline.py --sample-demo
```

This runs a real GBIF/Darwin Core-style occurrence readiness check against a bundled sample CSV — no external data needed.

GBIF source data DOI: **[10.15468/dl.evgrnx](https://doi.org/10.15468/dl.evgrnx)**

- [Methodology](docs/methodology.md) — The EKDI formula, weights, and scoring logic
- [Reproducibility](docs/reproducibility.md) — Full breakdown of the three levels above
- [Data Sources](docs/data_sources.md) — Every input file, its provenance, and whether it's bundled
- [Limitations](docs/limitations.md) — What EKDI does *not* claim

## Beyond the Atlantic Forest

The Atlantic Forest is the demonstration case study, not the ceiling of the approach. EKDI is built as a configurable workflow (`configs/*.json`) intended for adaptation to other threatened biomes — Candidate next pilots could include other threatened, data-rich biomes such as the Cerrado or Sundaland, provided that occurrence data, grid layers, habitat-change data and expert calibration are available.

## Limitations

- EKDI is a decision-support atlas, not a claim of species presence, absence, extinction, or rediscovery.
- The browser app visualizes processed outputs and does not recompute EKDI client side.
- EKDI does not auto-update when new GBIF occurrence releases are published , updating requires re-running the pipeline (Level 2/3 above) against a new download.
- Atlantic Forest weights are a case-study preset and should be recalibrated before use in another biome.

Full list: [Limitations](docs/limitations.md)

## Citation

If you use EKDI or its outputs, please cite:

> Morales Soto, G. (2026). *EKDI Atlas — Ecological Knowledge Decay Index.* GBIF Ebbe Nielsen Challenge 2026. Instituto de Computação, Universidade Estadual de Campinas (UNICAMP). https://doi.org/[pending]

Machine-readable citation: [CITATION.cff](CITATION.cff)

## License

Code is released under the MIT License. Data files retain the licenses of their original sources (GBIF, MapBiomas, FloraBR — see [Data Sources](docs/data_sources.md)).
