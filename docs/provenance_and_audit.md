# Provenance And Internal Audit

EKDI includes an internal audit workflow for checking public app data files, hashes, counts, source metadata, EKDI recalculation, plant linkage and zero-value issues.

Run:

```text
python scripts/run_internal_audit.py
```

Outputs are written to:

```text
audit/
```

## What The Audit Checks

- file existence, size, modified time and SHA256 hashes
- GeoJSON feature counts, geometry types and bounding boxes
- priority-cell class counts and cell ID uniqueness
- EKDI recalculation from normalized component fields when available
- zero values in forest and post-record loss fields
- plant candidate linkage to priority cells
- source metadata completeness
- GBIF public verification readiness
- MapBiomas verification readiness

## Data Verifiability

EKDI source data are publicly verifiable in principle, but exact reproducibility depends on metadata such as the GBIF download DOI, MapBiomas collection version and Flora e Funga source date.

The current metadata identifies major source families, but it does not yet include all DOI, version, access-date, filter and citation fields needed for full public reproducibility.

Manual action needed: add the GBIF download DOI from gbif.org user downloads, the MapBiomas collection/version, Flora e Funga or FloraBR source date/version, and citation strings to `app/data/metadata/sources.json`.

## UI Policy

The app should not expose direct `Verify GBIF` or `Verify MapBiomas` buttons until exact occurrence IDs, source IDs or validated link templates are available.

Species-name-only data may support search links, but not direct public occurrence verification.
