# Limitations

## Current Prototype Status

This repository is an advanced prototype for review and demonstration. It is not a final scientific publication.

## Known Data Caveats

- `nearest_city` is not calculated yet.
- Some cells may lack state or `stateName` assignment.
- Adequate Coverage cells may be omitted from the interactive map preview for performance.
- The priority GeoJSON is large for browser loading.

## Interpretation Caveats

- Rediscovery Candidates are hypotheses requiring validation.
- Knowledge Ghosts are evidence signals, not confirmed absences.
- Plant Candidates are not confirmed current occurrences.
- Evidence Completeness is not biological certainty.
- EKDI does not confirm species presence or absence.
- EKDI does not declare extinction.

## Ecological and Statistical Limitations

- Spatial Autocorrelation: the 5 km grid creates spatially adjacent cells that may not be statistically independent. EKDI currently functions as a decision-support atlas, not a spatially explicit inferential model.
- Taxonomic Sampling Bias: herbarium records may be unevenly distributed across plant families and collection traditions. EKDI currently summarizes occurrence evidence but does not fully correct for family-level collection bias.
- Threat Status Categories: Data Deficient, Not Evaluated, Not Assessed, Not Linked and Not Provided must be treated as different categories. EKDI should not collapse these categories.
- Forest Fragmentation: forest cover percentage does not describe patch size, isolation or habitat connectivity. Fragmentation metrics are recommended as future enrichment.

## Experimental Verification Window Caveat

The Knowledge Verification Window is an experimental decision-support concept. It requires annual forest-cover history or a reliable recent loss rate per cell.

The current dashboard export includes current forest-cover context and cumulative post-record loss, but not annual forest-cover history per cell. For that reason, the public app does not calculate or display verification-window classes.

If implemented with future data, the selected low-forest threshold must be treated as a configurable planning parameter. It must not be interpreted as an extinction threshold, absence prediction or rediscovery-failure prediction.

## Validation Caveats

Before publication or operational use, EKDI should undergo:

- expert botanical review;
- voucher and herbarium review;
- coordinate uncertainty checks;
- sensitivity analysis;
- field validation;
- comparison with independent survey data.
