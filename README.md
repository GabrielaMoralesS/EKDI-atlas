# EKDI Atlas

*Atlantic Forest case study for GBIF-mediated botanical field verification under landscape change.*

[![Live Atlas](https://img.shields.io/badge/Live%20Atlas-open-blue)](https://GabrielaMoralesS.github.io/EKDI-atlas/app/)
![GBIF Challenge 2026](https://img.shields.io/badge/GBIF%20Challenge-2026-2c7a7b)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Case Study](https://img.shields.io/badge/Case%20Study-Atlantic%20Forest-2f855a)

> [ADD IMAGE: Atlas overview with Critical Gaps]

EKDI turns old GBIF-mediated plant occurrence records into field-verification priorities under landscape change.

## Why It Matters

The Atlantic Forest is one of the world's most threatened biomes, yet many botanical records still circulate without updated landscape interpretation. EKDI helps botanists decide where historical occurrence evidence may deserve renewed review when habitat change, sampling age, and biodiversity knowledge gaps overlap.

## What EKDI Adds to GBIF

| GBIF occurrence maps | EKDI Atlas |
| --- | --- |
| Shows where records were documented | Prioritizes where old occurrence evidence may need field review |
| Focuses on occurrence availability | Adds habitat-change context and knowledge obsolescence |
| Species points are the main output | Critical Gaps and Knowledge Ghosts support field verification planning |

## Core Concepts

- **Critical Gap:** a 5 km cell where botanical evidence may deserve field verification priority.
- **Knowledge Ghost:** a species-level fragile-evidence signal for expert review.
- **Field Verification Output:** exported checklists and summaries for planning follow-up work.

## Workflow

```text
GBIF records -> 5 km grid -> sampling antiquity -> habitat-change context
-> richness deficit -> Critical Gaps -> Knowledge Ghosts -> Field Outputs
```

## Atlas Views

> [ADD IMAGE: Critical Gaps map]

> [ADD IMAGE: Featured Knowledge Ghosts]

> [ADD IMAGE: Priority Cell Review]

> [ADD IMAGE: Data Readiness DOI]

> [ADD IMAGE: Field Outputs]

## Live Atlas

- Live Atlas: [https://GabrielaMoralesS.github.io/EKDI-atlas/app/](https://GabrielaMoralesS.github.io/EKDI-atlas/app/)
- Official app file: [app/index.html](app/index.html)

## Quick Start

```bash
python -m http.server 8000
```

Open:

```text
http://localhost:8000/app/
```

## Reproducibility

A clean clone can run the final Atlantic Forest atlas from processed outputs already bundled in `app/data/`. Configurable reruns and deeper recomputation depend on intermediate or external inputs that are documented explicitly instead of assumed.

- [Methodology](docs/methodology.md)
- [Reproducibility](docs/reproducibility.md)
- [Data Sources](docs/data_sources.md)
- [Limitations](docs/limitations.md)

Open the **Scientific Report** inside the live app for the current case-study report.

## Limitations

- EKDI is a decision-support atlas, not a claim of presence, absence, extinction, or rediscovery.
- The browser app visualizes processed outputs and does not recompute EKDI client-side.
- Full scientific recomputation requires external or locally generated intermediate inputs not bundled in the public repository.
- Atlantic Forest weights are a case-study preset and should be recalibrated before use in another biome.

## Citation

See [CITATION.cff](CITATION.cff).

## License

Code is released under the MIT License. Data files retain the licenses of their original sources.
