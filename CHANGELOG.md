# Changelog

## Unreleased

Repository simplified for GBIF Challenge review.

Added or clarified:

- Official competition app in `app/index.html`
- Processed app outputs in `app/data/`
- Public documentation set:
  - `docs/methodology.md`
  - `docs/reproducibility.md`
  - `docs/data_sources.md`
  - `docs/limitations.md`
- `scripts/run_ekdi_pipeline.py` configurable pipeline entry point
- Public scripts overview in `scripts/README.md`
- Root `requirements.txt` for reproducibility setup

Notes:

- Root `index.html` remains a redirect to `./app/`.
- The browser app visualizes processed outputs and does not recompute EKDI client-side.
- Data files retain the licenses of their original sources.
