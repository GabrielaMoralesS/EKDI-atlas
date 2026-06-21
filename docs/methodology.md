# Methodology

## The EKDI Question

GBIF-mediated occurrence records describe biodiversity at the moment of collection. They do not describe the landscape today. EKDI asks: **where has the gap between recorded evidence and current habitat condition grown large enough that the evidence should be treated as ecologically outdated, not just old?**

EKDI does not treat older records as incorrect. A record is data about a moment in time; EKDI flags when that moment may no longer represent the present ecological context — and therefore where field or herbarium re-verification is most likely to be informative.

This framing follows the same logic as sample-bias and survey-gap methods used in prior biodiversity-informatics work (e.g. *sampbias*, Meyer et al. 2015; GBIF coverage-assessment approaches), but adds a temporal-decay dimension that those methods do not address: **not just where sampling is sparse, but where existing sampling has become stale relative to landscape change.**

## EKDI Score

For each 5 km grid cell *i*:

```text
EKDI(i) = w_a · A(i) + w_l · L(i) + w_r · R(i)
```

where A, L, and R are each normalized to [0, 1] across the study area, and the weights sum to 1.

### Atlantic Forest case-study preset

```text
EKDI = 0.45 × Sampling Antiquity
     + 0.35 × Post-Record Forest Loss
     + 0.20 × Richness Deficit
```

**Why these weights.** The Atlantic Forest is a biome where the dominant driver of evidence obsolescence is time-since-last-record interacting with land-use change, not undersampling alone — most of the biome has *some* historical GBIF coverage, but very little of it has been revisited after the deforestation waves of the last four decades. Sampling Antiquity is weighted highest (0.45) because age-of-evidence is the strongest available proxy for "this record predates known landscape change" at cell level. Post-Record Forest Loss (0.35) is weighted second because it is the most direct observable confirmation that the landscape actually changed, not just that time passed. Richness Deficit (0.20) is weighted lowest because GBIF richness gaps in the Atlantic Forest are confounded by collector access and protected-area bias, making it a useful but noisier signal than the first two.

**These weights are a documented case-study preset, not a universal model.** Section "Weight Sensitivity" in the in-app Scientific Report shows how Critical Gap classification shifts under ±0.1 perturbations to each weight, so reviewers can assess sensitivity rather than accept the preset on faith. Adapting EKDI to another biome requires re-deriving or re-justifying these weights against that biome's actual drivers of evidence decay — see [Reproducibility](reproducibility.md).

## Core Components

### Sampling Antiquity — A(i)

```text
A(i) = normalize(current_year − last_record_year(i))
```

Years since the most recent GBIF-mediated occurrence record linked to cell *i*, normalized 0–1 across all cells with at least one record. Cells with no record at all are handled separately (see Priority Classes below) rather than assigned an antiquity score, since "never sampled" is a distinct condition from "sampled long ago."

### Post-Record Forest Loss — L(i)

```text
L(i) = normalize(forest_ha_lost_after(last_record_year(i)))
```

Hectares of forest cover lost within cell *i* strictly after its last linked occurrence record's year, derived from MapBiomas annual land-cover transitions. This isolates habitat change that postdates the evidence — loss that occurred *before* the record does not count, since it was already reflected in the landscape the collector observed.

### Richness Deficit — R(i)

```text
R(i) = max(0, expected_richness(i) − observed_richness(i)) / expected_richness(i)
```

Expected richness is estimated from environmental covariates and regional species pools (FloraBR endemic reference list cross-tabulated against the Atlantic Forest); observed richness is the count of distinct species with GBIF-mediated records in the cell. A positive deficit means the cell has fewer documented species than comparable cells with similar habitat — a signal of undersampling independent of age.

## Priority Classes

Cells are assigned to one of four classes based on EKDI score and data availability, not on EKDI score alone:

| Class | Condition | Field meaning |
| --- | --- | --- |
| **Critical Gap** | EKDI(i) ≥ 0.70 **and** has ≥1 occurrence record | Old evidence + significant post-record habitat change; highest field-verification priority |
| **Deficient Coverage** | 0.40 ≤ EKDI(i) < 0.70 | Moderate evidence decay or richness deficit; secondary priority |
| **Unsurveyed Forest** | 0 records **and** forest_cover_pct ≥ threshold | No GBIF-mediated evidence at all in a forested cell; distinct from decay, since there is no record to decay |
| **Adequate Coverage** | EKDI(i) < 0.40 | Evidence is recent relative to observed habitat change |

The 0.70 / 0.40 thresholds are documented case-study cutoffs, calibrated so that Critical Gaps represent roughly the top decile of decay signal in the Atlantic Forest dataset — not a universal statistical boundary. See [Data Sources](data_sources.md) for the exact cell counts each threshold produces.

## Knowledge Ghosts

A **Knowledge Ghost** is a stricter, species-level signal layered on top of the cell-level EKDI score: an endemic species (per FloraBR) whose *only* GBIF-mediated record falls within a Critical Gap cell. It is the conjunction of three conditions — endemism, single-record evidence, and residence in a cell with severe post-record forest loss — not a separate statistical model.

A Knowledge Ghost is **not** a claim of extinction, absence, or confirmed rediscovery candidacy. It is a flag that says: *this species' only evidence on record sits in a place that has changed enough that someone should look again.*

## Main Outputs

- **Critical Gaps** — 5 km field-verification priority cells (see Priority Classes above)
- **Knowledge Ghosts** — species-level fragile-evidence signals for expert and herbarium review
- **Field Outputs** — exportable, citation-ready checklists for verification planning

## Interpretation Boundary

EKDI is a decision-support and prioritization atlas. It does not confirm species presence, absence, extinction, or rediscovery, and it does not replace taxonomic, herbarium, or field expert judgment. Every plant candidate and Knowledge Ghost signal in the dashboard requires voucher review, coordinate verification, taxonomic confirmation, and field interpretation before any biological claim is made from it. See [Limitations](limitations.md) for the full boundary of what EKDI does and does not claim.

## Reproducibility and Sensitivity

- For the three public repeatability levels and rerun scope, see [Reproducibility](reproducibility.md).
- For bundled outputs, GBIF DOI provenance, and the inputs required for full recomputation, see [Data Sources](data_sources.md).
- For how Critical Gap classification responds to weight perturbation, open the **Weight Sensitivity** section of the in-app Scientific Report.

## References

- Meyer, C., Weigelt, P., & Kreft, H. (2015). Multidimensional biases, gaps and uncertainties in global plant occurrence information. *Ecology Letters*.
- GBIF Secretariat. *GBIF Data Quality Requirements and Guidelines.*
- MapBiomas Project — Annual land-use and land-cover maps for Brazil.
