# Limitations

EKDI is most useful when its boundaries are explicit. This page groups limitations by type rather than listing them in arbitrary order, so a reviewer can quickly find the category relevant to their concern.

## What EKDI does not claim biologically

- EKDI is a decision-support atlas. It does **not** confirm species presence, absence, extinction, or rediscovery.
- Knowledge Ghosts and rediscovery candidates are evidence signals — a flag that a species' only or oldest record sits in a changed landscape — not a biological determination. Every signal requires voucher review, coordinate verification, taxonomic confirmation, and field interpretation before any claim is made from it.
- Plant candidates and Knowledge Ghosts are not complete floristic inventories, and the absence of a species from the dashboard is not evidence of its absence in the field.
- Forest-remaining and post-record forest-loss values describe habitat context. They do not, by themselves, prove that a species has persisted or disappeared from a cell.

## What the live app does and does not compute

- The public browser app visualizes **processed** Atlantic Forest outputs. It does not recompute the EKDI index client-side, and no interface element — including the in-app **Data Readiness Check** — claims to perform full EKDI computation in the browser.
- Full scientific recomputation depends on external or locally generated intermediate inputs that are not bundled in this public repository. See [Data Sources](data_sources.md) for exactly which inputs and why.

## What is and is not generalizable

- The 0.45 / 0.35 / 0.20 component weights are a documented **Atlantic Forest case-study preset**, justified in [Methodology](methodology.md) for this biome's specific drivers of evidence decay. They are not a universal model and must be re-derived — not reused by default — before applying EKDI to another biome.
- **EKDI does not auto-update when new GBIF occurrence releases are published.** The Atlantic Forest atlas reflects the GBIF download documented by DOI [10.15468/dl.evgrnx](https://doi.org/10.15468/dl.evgrnx) at the time it was built. Incorporating a newer GBIF release requires re-running the Level 2/3 pipeline described in [Reproducibility](reproducibility.md) against the new download — it is not automatic, and this repository does not imply otherwise.
- MapBiomas collection version and FloraBR access date for the shipped build are an open documentation item — see [Data Sources](data_sources.md) — rather than a silently assumed constant.

## Why these limits are stated here, not hidden

A method that states its own boundaries precisely is easier to trust than one that claims none. Every limitation above maps to a corresponding design decision documented in [Methodology](methodology.md), [Reproducibility](reproducibility.md), or [Data Sources](data_sources.md) — this page is the index of what to check, not the full explanation.
