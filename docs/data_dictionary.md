# Data Dictionary

## Priority Cell Fields

| Field | Meaning |
|---|---|
| `cell_id` | Unique grid cell identifier. |
| `state` | State abbreviation or state code when available. |
| `stateName` | Human-readable state name when available. |
| `latitude` | Cell representative latitude in WGS84. |
| `longitude` | Cell representative longitude in WGS84. |
| `cls` | Normalized dashboard priority class. |
| `categoria_final` | Original or scientific priority class from source data. |
| `ekdi` | Normalized dashboard EKDI priority score, if available. |
| `indice` | Original EKDI index field, if available. |
| `ultimo_registro` | Last known record year for the cell, when applicable. |
| `n_registros` | Number of occurrence records linked to the cell. |
| `forest_cover_pct` | Forest-cover estimate for the cell. |
| `perdida_ha` | Post-record forest loss in hectares, when available. |
| `deficit_riqueza` | Richness deficit signal. |
| `evidence_completeness` | Evidence availability/completeness for interpretation. |
| `recommended_action` | Recommended review or field action. |
| `action_source` | Whether the action came from source data or EKDI evidence classification. |

## Priority Classes

| Normalized | Source Alias | Meaning |
|---|---|---|
| `critical` | `critico` | Critical Gap. |
| `unsurveyed` | `bosque_sin_explorar` | Unsurveyed Forest. |
| `deficient` | `alto` | Deficient Coverage. |
| `lost` | `sin_datos_abierto` | Historical Review / Lost context. |
| `adequate` | `adecuado` | Adequate Coverage, available in the full grid export. |

## Notes

Missing values should be interpreted cautiously. The dashboard displays user-friendly labels such as `Not Available`, `Not Applicable` or `Requires Validation` instead of raw null values.
