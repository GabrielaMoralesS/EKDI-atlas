# Methodology

## Ecological Memory

Ecological memory refers to information preserved in biodiversity records, specimens, checklists and field observations. A record documents evidence from a place and time, but the surrounding landscape may change after the record is collected.

EKDI uses this idea to ask where older biodiversity knowledge may need renewed interpretation.

## Why Records Can Become Ecologically Outdated

Occurrence records remain valuable, but habitat loss, fragmentation and uneven sampling can change how those records should be interpreted for field planning.

EKDI does not treat older records as wrong. It identifies where the ecological context around records may have changed enough to justify review.

## EKDI Components

### Sampling Antiquity

Sampling Antiquity represents how old the available occurrence evidence is for a cell.

### Post-Record Forest Loss

Post-Record Forest Loss estimates habitat change after the last known record in a cell.

### Richness Deficit

Richness Deficit represents expected biodiversity knowledge that is not reflected in observed open records.

## Formula

For the Mata Atlântica case-study preset:

```text
EKDI = 0.45 × Sampling Antiquity
     + 0.35 × Post-Record Forest Loss
     + 0.20 × Richness Deficit
```

The weights are a case-study preset. They are not universal and should be recalibrated for other biomes.

## Evidence Completeness

Evidence Completeness describes how much information is available to interpret a cell. It is not biological certainty and does not confirm presence or absence.

## Knowledge Ghosts

Knowledge Ghosts are species-level evidence signals where historical records and current landscape context suggest that botanical review may be useful.

They are candidates for review, not claims of extinction, absence or rediscovery.

## Rediscovery Candidates

Rediscovery Candidates are hypotheses based on available evidence. They require voucher review, coordinate checks, field validation and expert taxonomic interpretation.

## Plant Candidates

Plant Candidates are species signals linked to priority cells when available data support the link. They are not confirmed current occurrences.

## Expedition Planner

The Expedition Planner converts selected cells and species signals into a field-verification checklist. It supports CSV and JSON export for planning, but does not replace permits, land access planning or expert review.
