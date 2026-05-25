"""
Build clean EKDI dashboard data files for the MapLibre mockup.

Phase 2 only:
- Reads existing real outputs.
- Writes clean dashboard data under PROYECTO CONCURSO GBIF/data/{geo,points,tables,metadata}.
- Does not edit dashboard HTML.
- Does not overwrite original source data files.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DATA = PROJECT_ROOT / "PROYECTO CONCURSO GBIF" / "data"

SRC_GRID_FINAL = PROJECT_ROOT / "data" / "grid_final.gpkg"
SRC_GRID_ENDEMICAS = PROJECT_ROOT / "data" / "grid_endemicas.gpkg"
SRC_GHOSTS = PROJECT_ROOT / "data" / "ghost_species.csv"
SRC_RISK = PROJECT_ROOT / "data" / "extinction_risk_analysis.csv"
SRC_TOP100 = PROJECT_ROOT / "data" / "critical_gaps_top100.csv"
SRC_CURRENT_PRIORITY = DASHBOARD_DATA / "priority_cells.geojson"
SRC_CURRENT_GBIF = DASHBOARD_DATA / "gbif_memory.geojson"
SRC_CURRENT_FOREST = DASHBOARD_DATA / "forest_mask.geojson"

OUT_GEO = DASHBOARD_DATA / "geo"
OUT_POINTS = DASHBOARD_DATA / "points"
OUT_TABLES = DASHBOARD_DATA / "tables"
OUT_METADATA = DASHBOARD_DATA / "metadata"

OUT_PRIORITY = OUT_GEO / "priority_cells.geojson"
OUT_PRIORITY_FULL = OUT_GEO / "priority_cells_full.geojson"
OUT_PRIORITY_WEB = OUT_GEO / "priority_cells_web.geojson"
OUT_FOREST = OUT_GEO / "forest_mask.geojson"
OUT_BIOME = OUT_GEO / "biome_boundary.geojson"
OUT_GBIF = OUT_POINTS / "gbif_memory.geojson"
OUT_GHOSTS = OUT_TABLES / "knowledge_ghosts.json"
OUT_REDISCOVERY = OUT_TABLES / "rediscovery_candidates.json"
OUT_CELL_PLANT_CANDIDATES = OUT_TABLES / "cell_plant_candidates.json"
OUT_STATE_SUMMARY = OUT_TABLES / "state_summary.json"
OUT_TOP100 = OUT_TABLES / "critical_gaps_top100.csv"
OUT_INTEGRITY = OUT_METADATA / "data_integrity.json"
OUT_SCHEMA = OUT_METADATA / "schema.json"
OUT_SOURCES = OUT_METADATA / "sources.json"
OUT_REPORT = PROJECT_ROOT / "BUILD_DASHBOARD_DATA_REPORT.md"
OUT_REPORT_PHASE_2_5 = PROJECT_ROOT / "BUILD_DASHBOARD_DATA_REPORT_PHASE_2_5.md"

REFERENCE_YEAR = 2025
FOREST_MASK_THRESHOLD_PCT = 30
WEB_PRIORITY_CLASSES = ["critical", "deficient", "unsurveyed", "lost"]

CATEGORY_TO_CLASS = {
    "critico": "critical",
    "alto": "deficient",
    "adecuado": "adequate",
    "bosque_sin_explorar": "unsurveyed",
    "sin_datos_abierto": "lost",
}

STATE_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapa",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceara",
    "DF": "Distrito Federal",
    "ES": "Espirito Santo",
    "GO": "Goias",
    "MA": "Maranhao",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Para",
    "PB": "Paraiba",
    "PR": "Parana",
    "PE": "Pernambuco",
    "PI": "Piaui",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondonia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "Sao Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

RECOMMENDATION_BY_CLASS = {
    "critical": (
        "Field verification recommended; review historic records, coordinates, "
        "and post-record forest loss before survey."
    ),
    "unsurveyed": (
        "Exploratory field verification recommended; forest remains but GBIF "
        "occurrence evidence is missing for this cell."
    ),
    "deficient": (
        "Voucher review recommended; schedule targeted field verification if "
        "endemic or threatened-species evidence supports it."
    ),
    "adequate": (
        "Maintain as reference coverage; revisit only if new evidence changes "
        "confidence or local habitat context."
    ),
    "lost": (
        "Historical review recommended; verify coordinates and habitat context "
        "before interpreting transformed areas."
    ),
}


def require_runtime() -> tuple[Any, Any, Any]:
    try:
        import geopandas as gpd
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise SystemExit(
            "Missing geospatial runtime dependency. Run with the project environment "
            "(.venv_ai) that has geopandas, pandas and numpy installed."
        ) from exc
    return gpd, np, pd


def ensure_dirs() -> None:
    for path in (OUT_GEO, OUT_POINTS, OUT_TABLES, OUT_METADATA):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        import numpy as np
        import pandas as pd

        if value is pd.NA:
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            value = float(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
    except Exception:
        pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def rounded_geometry_mapping(geom: Any, precision: int = 6) -> dict[str, Any] | None:
    if geom is None or geom.is_empty:
        return None
    from shapely.geometry import mapping

    mapped = mapping(geom)

    def round_coords(obj: Any) -> Any:
        if isinstance(obj, (list, tuple)):
            if len(obj) == 2 and all(isinstance(v, (float, int)) for v in obj):
                return [round(float(obj[0]), precision), round(float(obj[1]), precision)]
            return [round_coords(v) for v in obj]
        return obj

    return {"type": mapped["type"], "coordinates": round_coords(mapped["coordinates"])}


def write_geojson(gdf: Any, path: Path, coord_precision: int = 6) -> int:
    features = []
    for idx, row in gdf.iterrows():
        props = {}
        for key, value in row.drop(labels=[gdf.geometry.name]).items():
            props[key] = clean_value(value)
        feature = {
            "type": "Feature",
            "properties": props,
            "geometry": rounded_geometry_mapping(row.geometry, coord_precision),
        }
        feature_id = props.get("id") or props.get("cell_id")
        if feature_id is not None:
            feature["id"] = str(feature_id)
        features.append(feature)
    payload = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(features)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def nullable_float(value: Any) -> float | None:
    value = clean_value(value)
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def nullable_int(value: Any) -> int | None:
    value = nullable_float(value)
    if value is None:
        return None
    return int(value)


def state_code_from_name(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if len(raw) == 2:
        return raw.upper()
    lowered = raw.casefold()
    for code, name in STATE_NAMES.items():
        if lowered == name.casefold():
            return code
    aliases = {
        "sc": "SC",
        "sp": "SP",
        "minas gerais": "MG",
        "bahia": "BA",
        "santa catarina": "SC",
    }
    return aliases.get(lowered)


def fallback_recommendation(cls: str | None) -> str | None:
    if not cls:
        return None
    return RECOMMENDATION_BY_CLASS.get(cls)


def load_current_priority_state_maps(gpd: Any) -> dict[str, dict[str, Any]]:
    if not SRC_CURRENT_PRIORITY.exists():
        return {}
    current = gpd.read_file(SRC_CURRENT_PRIORITY)
    mapping: dict[str, dict[str, Any]] = {}
    for _, row in current.iterrows():
        cell_id = clean_value(row.get("id"))
        if not cell_id:
            continue
        mapping[str(cell_id)] = {
            "state": clean_value(row.get("state")),
            "stateName": clean_value(row.get("stateName")),
            "threat": clean_value(row.get("threat")),
            "endemic": clean_value(row.get("endemic")),
        }
    return mapping


def build_priority_cells(gpd: Any, pd: Any) -> tuple[Any, Any, dict[str, Any], dict[str, Any]]:
    grid = gpd.read_file(SRC_GRID_FINAL)
    original_crs = str(grid.crs) if grid.crs else None
    state_map = load_current_priority_state_maps(gpd)

    centroid_wgs = gpd.GeoSeries(grid.geometry.centroid, crs=grid.crs).to_crs("EPSG:4326")
    grid_wgs = grid.to_crs("EPSG:4326")

    grid_wgs["latitude"] = centroid_wgs.y.round(6)
    grid_wgs["longitude"] = centroid_wgs.x.round(6)
    grid_wgs["id"] = grid_wgs["cell_id"]
    grid_wgs["cls"] = grid_wgs["categoria_final"].map(CATEGORY_TO_CLASS)
    grid_wgs["last"] = grid_wgs["ultimo_registro"]
    grid_wgs["loss"] = grid_wgs["perdida_ha"]
    grid_wgs["forest"] = grid_wgs["forest_cover_pct"]
    grid_wgs["gbif"] = grid_wgs["n_registros"]
    grid_wgs["ekdi"] = grid_wgs["indice"]
    if "antiguedad_norm" in grid_wgs.columns:
        grid_wgs["sampling_antiquity_norm"] = grid_wgs["antiguedad_norm"]
    if "perdida_norm" in grid_wgs.columns:
        grid_wgs["post_record_loss_norm"] = grid_wgs["perdida_norm"]
    if "deficit_norm" in grid_wgs.columns:
        grid_wgs["richness_deficit_norm"] = grid_wgs["deficit_norm"]
    grid_wgs["years"] = grid_wgs["ultimo_registro"].apply(
        lambda value: REFERENCE_YEAR - int(value) if nullable_int(value) is not None else None
    )

    grid_wgs["state"] = grid_wgs["cell_id"].map(
        lambda cid: state_map.get(str(cid), {}).get("state")
    )
    grid_wgs["state"] = grid_wgs["state"].apply(
        lambda value: str(value).strip().upper() if value is not None and str(value).strip() else None
    )
    grid_wgs["stateName"] = grid_wgs["cell_id"].map(
        lambda cid: state_map.get(str(cid), {}).get("stateName")
    )
    grid_wgs["stateName"] = grid_wgs.apply(
        lambda row: STATE_NAMES.get(str(row["state"]).upper())
        if row.get("state")
        else row.get("stateName"),
        axis=1,
    )
    grid_wgs["stateName"] = grid_wgs["stateName"].apply(
        lambda value: str(value).strip() if value is not None and str(value).strip() else None
    )
    grid_wgs["threat"] = grid_wgs["cell_id"].map(
        lambda cid: state_map.get(str(cid), {}).get("threat")
    )
    grid_wgs["endemic"] = grid_wgs["cell_id"].map(
        lambda cid: state_map.get(str(cid), {}).get("endemic")
    )
    grid_wgs["nearest_city"] = None
    grid_wgs["recommended_action"] = grid_wgs["cls"].map(fallback_recommendation)
    grid_wgs["recommended_action_source"] = "class_based_fallback"

    # Use grid_endemicas as an enrichment-only source. It has no cell_id, so keep
    # location-specific joins conservative and aggregate it separately in summaries.
    grid_wgs["critical_enrichment_source"] = None

    full_feature_count = write_geojson(grid_wgs, OUT_PRIORITY_FULL, coord_precision=6)
    web_gdf = grid_wgs[grid_wgs["cls"].isin(WEB_PRIORITY_CLASSES)].copy()
    web_feature_count = write_geojson(web_gdf, OUT_PRIORITY_WEB, coord_precision=6)
    shutil.copy2(OUT_PRIORITY_WEB, OUT_PRIORITY)

    required = [
        "cell_id",
        "state",
        "stateName",
        "latitude",
        "longitude",
        "ultimo_registro",
        "n_registros",
        "riqueza_obs",
        "deficit_riqueza",
        "perdida_ha",
        "forest_cover_pct",
        "indice",
        "categoria_final",
        "confianza",
        "nearest_city",
        "recommended_action",
    ]
    missing_counts = {
        field: int(grid_wgs[field].isna().sum()) if field in grid_wgs.columns else len(grid_wgs)
        for field in required
    }
    stats = {
        "features": web_feature_count,
        "full_features": full_feature_count,
        "web_features": web_feature_count,
        "alias_features": web_feature_count,
        "source_crs": original_crs,
        "output_crs": "EPSG:4326",
        "web_classes_included": WEB_PRIORITY_CLASSES,
        "web_classes_present": sorted(str(v) for v in web_gdf["cls"].dropna().unique()),
        "omitted_classes": sorted(
            str(v)
            for v in set(grid_wgs["cls"].dropna().unique()) - set(web_gdf["cls"].dropna().unique())
        ),
        "category_counts": {
            str(k): int(v) for k, v in grid_wgs["categoria_final"].value_counts(dropna=False).items()
        },
        "class_counts": {
            str(k): int(v) for k, v in grid_wgs["cls"].value_counts(dropna=False).items()
        },
        "web_class_counts": {
            str(k): int(v) for k, v in web_gdf["cls"].value_counts(dropna=False).items()
        },
        "state_known_features": int(grid_wgs["state"].notna().sum()),
        "state_missing_features": int(grid_wgs["state"].isna().sum()),
        "web_state_known_features": int(web_gdf["state"].notna().sum()),
        "web_state_missing_features": int(web_gdf["state"].isna().sum()),
        "missing_required_counts": missing_counts,
    }
    return grid_wgs, web_gdf, stats, missing_counts


def build_biome_boundary(gpd: Any, priority_gdf: Any) -> dict[str, Any]:
    boundary_geom = priority_gdf.geometry.union_all() if hasattr(priority_gdf.geometry, "union_all") else priority_gdf.geometry.unary_union
    boundary = gpd.GeoDataFrame(
        [
            {
                "boundary_type": "analysis_grid_footprint",
                "source": rel(SRC_GRID_FINAL),
                "caveat": (
                    "Derived from the dissolved 5 km analysis grid because the Phase 2 "
                    "input list did not include the original biome boundary file."
                ),
            }
        ],
        geometry=[boundary_geom],
        crs="EPSG:4326",
    )
    count = write_geojson(boundary, OUT_BIOME, coord_precision=6)
    return {"features": count, "source": rel(SRC_GRID_FINAL), "output_crs": "EPSG:4326"}


def build_forest_mask(gpd: Any) -> dict[str, Any]:
    forest = gpd.read_file(SRC_CURRENT_FOREST)
    if forest.crs is None:
        forest = forest.set_crs("EPSG:4326")
    else:
        forest = forest.to_crs("EPSG:4326")
    forest["source"] = rel(SRC_CURRENT_FOREST)
    forest["forest_cover_threshold_pct"] = FOREST_MASK_THRESHOLD_PCT
    forest["threshold_note"] = "Copied from existing MapLibre forest mask; threshold documented from prior exporter."
    count = write_geojson(forest, OUT_FOREST, coord_precision=6)
    return {
        "features": count,
        "geometry_types": sorted({geom.geom_type for geom in forest.geometry}),
        "output_crs": "EPSG:4326",
    }


def build_gbif_memory(gpd: Any) -> dict[str, Any]:
    gbif = gpd.read_file(SRC_CURRENT_GBIF)
    if gbif.crs is None:
        gbif = gbif.set_crs("EPSG:4326")
    else:
        gbif = gbif.to_crs("EPSG:4326")
    if "year" not in gbif.columns and "age" in gbif.columns:
        gbif["year"] = gbif["age"]
    gbif["source"] = rel(SRC_CURRENT_GBIF)
    gbif["sampled_layer"] = True
    count = write_geojson(gbif, OUT_GBIF, coord_precision=6)
    years = [nullable_int(v) for v in gbif["year"]] if "year" in gbif.columns else []
    years = [v for v in years if v is not None]
    return {
        "features": count,
        "output_crs": "EPSG:4326",
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "sampled_layer": True,
    }


def build_knowledge_ghosts(pd: Any, priority_gdf: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ghosts = pd.read_csv(SRC_GHOSTS)
    risk = pd.read_csv(SRC_RISK)
    priority_by_cell = priority_gdf.set_index("cell_id").to_dict("index")
    risk_by_species = risk.set_index("species").to_dict("index")
    records: list[dict[str, Any]] = []
    missing = Counter()

    for _, row in ghosts.iterrows():
        source = {str(k): clean_value(v) for k, v in row.to_dict().items()}
        cell_id = clean_value(row.get("cell_id"))
        cell = priority_by_cell.get(cell_id, {}) if cell_id else {}
        risk_row = risk_by_species.get(clean_value(row.get("species")), {})
        state = state_code_from_name(source.get("stateProvince")) or clean_value(cell.get("state"))
        state_name = STATE_NAMES.get(state) if state else source.get("stateProvince")
        latitude = nullable_float(source.get("decimalLatitude"))
        longitude = nullable_float(source.get("decimalLongitude"))

        rec = dict(source)
        rec.update(
            {
                "latitude": latitude,
                "longitude": longitude,
                "state": state,
                "stateName": state_name,
                "cls": clean_value(cell.get("cls")),
                "indice": clean_value(cell.get("indice")),
                "ekdi": clean_value(cell.get("ekdi")),
                "confianza": clean_value(cell.get("confianza")),
                "n_registros": clean_value(cell.get("n_registros")),
                "riqueza_obs": clean_value(cell.get("riqueza_obs")),
                "deficit_riqueza": clean_value(cell.get("deficit_riqueza")),
                "risk_categoria": clean_value(risk_row.get("categoria")),
                "risk_criterio": clean_value(risk_row.get("criterio")),
                "recommended_action": (
                    "Voucher review recommended; field verification recommended where "
                    "access, permits, and habitat context support survey."
                ),
                "recommended_action_source": "knowledge_ghost_class_based_fallback",
                "scientific_language_note": (
                    "Candidate signal only; this record does not confirm presence, "
                    "absence, or extinction."
                ),
            }
        )
        for key, value in rec.items():
            if value is None or value == "":
                missing[key] += 1
        records.append({k: clean_value(v) for k, v in rec.items()})

    write_json(OUT_GHOSTS, records)
    stats = {
        "rows": len(records),
        "missing_counts": dict(missing),
        "source": rel(SRC_GHOSTS),
        "enriched_from": [rel(SRC_GRID_FINAL), rel(SRC_RISK)],
    }
    return records, stats


def build_rediscovery_candidates(pd: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    risk = pd.read_csv(SRC_RISK)
    candidates = risk.copy()
    candidates["last_year_numeric"] = candidates["last_year"].apply(nullable_int)
    candidates = candidates[candidates["last_year_numeric"].notna()]
    candidates = candidates[candidates["last_year_numeric"] <= 2005].copy()
    candidates = candidates.sort_values(["last_year_numeric", "n_records"], ascending=[True, True])

    records: list[dict[str, Any]] = []
    for _, row in candidates.iterrows():
        rec = {str(k): clean_value(v) for k, v in row.to_dict().items()}
        rec.update(
            {
                "rediscovery_candidate": True,
                "candidate_type": "species_level_hypothesis",
                "candidate_basis": (
                    "Historic species-level evidence only. Spatial forest evidence was "
                    "not sufficient in the available Phase 2 inputs."
                ),
                "confidence": "low",
                "cell_id": None,
                "latitude": None,
                "longitude": None,
                "state": None,
                "stateName": None,
                "forest_cover_pct": None,
                "perdida_ha": None,
                "indice": None,
                "confianza": None,
                "recommended_action": (
                    "Rediscovery hypothesis; voucher review recommended before any "
                    "location-specific field verification."
                ),
                "recommended_action_source": "species_level_conservative_fallback",
                "scientific_language_note": (
                    "Candidate/hypothesis only; location-specific fields are null "
                    "because no safe spatial join was available."
                ),
            }
        )
        records.append({k: clean_value(v) for k, v in rec.items()})

    write_json(OUT_REDISCOVERY, records)
    stats = {
        "rows": len(records),
        "source_rows": int(len(risk)),
        "rule": "last_year <= 2005, species-level only, location fields null",
        "source": rel(SRC_RISK),
    }
    return records, stats


def build_cell_plant_candidates(
    ghost_records: list[dict[str, Any]],
    rediscovery_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build conservative cell-linked plant candidate lists.

    Only records with an explicit cell_id are linked to cells. Rediscovery
    candidates are species-level by default and remain unlinked unless a future
    source provides a real cell_id.
    """
    grouped: dict[str, dict[str, Any]] = {}

    def add_record(record: dict[str, Any], candidate_type: str, source: str) -> None:
        cell_id = clean_value(record.get("cell_id"))
        species = clean_value(
            record.get("species")
            or record.get("scientificName")
            or record.get("taxon")
            or record.get("nome_cientifico")
        )
        if not cell_id or not species:
            return
        cell_key = str(cell_id)
        target = grouped.setdefault(
            cell_key,
            {
                "cell_id": cell_key,
                "state": clean_value(record.get("state")),
                "stateName": clean_value(record.get("stateName") or record.get("stateProvince")),
                "plants": [],
            },
        )
        plant = {
            "species": species,
            "candidate_type": candidate_type,
            "last_record": clean_value(
                record.get("year")
                or record.get("last_year")
                or record.get("ultimo_registro")
                or record.get("last_record")
            ),
            "risk_category": clean_value(
                record.get("risk_categoria")
                or record.get("categoria_risco")
                or record.get("categoria")
            ),
            "risk_criterion": clean_value(
                record.get("risk_criterio")
                or record.get("criterio_risco")
                or record.get("criterio")
            ),
            "endemic": clean_value(record.get("endemic") or record.get("endemism")),
            "recommended_action": clean_value(record.get("recommended_action")),
            "evidence_source": source,
            "notes": (
                "Plant candidate signal only; this does not confirm current "
                "presence, absence, rediscovery or extinction."
            ),
        }
        target["plants"].append({k: clean_value(v) for k, v in plant.items()})

    for record in ghost_records:
        add_record(record, "Knowledge Ghost", rel(OUT_GHOSTS))
    for record in rediscovery_records:
        add_record(record, "Rediscovery hypothesis", rel(OUT_REDISCOVERY))

    records = sorted(grouped.values(), key=lambda row: row["cell_id"])
    for row in records:
        row["plants"].sort(key=lambda plant: str(plant.get("species") or ""))
    write_json(OUT_CELL_PLANT_CANDIDATES, records)
    stats = {
        "rows": len(records),
        "plant_records": sum(len(row["plants"]) for row in records),
        "source": [rel(OUT_GHOSTS), rel(OUT_REDISCOVERY)],
        "rule": "Only records with explicit cell_id are linked to cells.",
        "limitations": [
            "Rediscovery candidates remain species-level unless a real cell_id exists.",
            "grid_endemicas.gpkg p_erisk display strings are not joined because no stable cell_id is present.",
        ],
    }
    return records, stats


def build_top100(pd: Any) -> dict[str, Any]:
    top = pd.read_csv(SRC_TOP100)
    top["latitude"] = top["lat"]
    top["longitude"] = top["lon"]
    top["indice"] = top["obsolescence_index"]
    top["perdida_ha"] = top["deforestation_ha"]
    top["ultimo_registro"] = top["last_gbif_record"]
    top["cell_id"] = None
    top["state"] = None
    top["stateName"] = None
    top["nearest_city"] = None
    top["recommended_action"] = (
        "Field verification candidate; join to priority cell geometry before "
        "using for navigation."
    )
    top["recommended_action_source"] = "top100_class_based_fallback"
    top.to_csv(OUT_TOP100, index=False, quoting=csv.QUOTE_MINIMAL)
    return {"rows": int(len(top)), "source": rel(SRC_TOP100), "columns": list(top.columns)}


def build_state_summary(
    priority_gdf: Any,
    web_priority_gdf: Any,
    ghosts_count: int,
    rediscovery_count: int,
    top100_count: int,
) -> dict[str, Any]:
    total_cells = int(len(priority_gdf))
    class_counts = {str(k): int(v) for k, v in priority_gdf["cls"].value_counts(dropna=False).items()}
    web_class_counts = {
        str(k): int(v) for k, v in web_priority_gdf["cls"].value_counts(dropna=False).items()
    }
    category_counts = {
        str(k): int(v) for k, v in priority_gdf["categoria_final"].value_counts(dropna=False).items()
    }
    cells_with_records = int((priority_gdf["n_registros"].fillna(0) > 0).sum())
    never_sampled = total_cells - cells_with_records
    post_record_loss = nullable_float(priority_gdf["perdida_ha"].fillna(0).sum())
    forest_cover_mean = nullable_float(priority_gdf["forest_cover_pct"].mean())

    states = []
    state_known = priority_gdf[priority_gdf["state"].notna()].copy()
    known_state_values = sorted(str(v) for v in state_known["state"].dropna().unique())
    for state, group in state_known.groupby("state", dropna=True):
        states.append(
            {
                "state": clean_value(state),
                "stateName": clean_value(group["stateName"].dropna().iloc[0])
                if group["stateName"].notna().any()
                else STATE_NAMES.get(str(state)),
                "cells_with_state": int(len(group)),
                "class_counts": {
                    str(k): int(v) for k, v in group["cls"].value_counts(dropna=False).items()
                },
                "critical_gaps": int((group["cls"] == "critical").sum()),
                "unsurveyed_forest": int((group["cls"] == "unsurveyed").sum()),
                "deficient_coverage": int((group["cls"] == "deficient").sum()),
                "post_record_loss_ha": nullable_float(group["perdida_ha"].fillna(0).sum()),
            }
        )
    states.sort(key=lambda row: row["critical_gaps"], reverse=True)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_year": REFERENCE_YEAR,
        "overall": {
            "total_cells": total_cells,
            "cells_with_gbif_records": cells_with_records,
            "gbif_coverage_pct": round(cells_with_records / total_cells * 100, 2) if total_cells else None,
            "never_sampled_cells": never_sampled,
            "never_sampled_pct": round(never_sampled / total_cells * 100, 2) if total_cells else None,
            "forest_cover_mean_pct": round(forest_cover_mean, 2) if forest_cover_mean is not None else None,
            "post_record_loss_ha_sum": round(post_record_loss, 2) if post_record_loss is not None else None,
            "category_counts": category_counts,
            "class_counts": class_counts,
            "class_totals_full_grid": class_counts,
            "class_totals_web_layer": web_class_counts,
            "web_layer_cells": int(len(web_priority_gdf)),
            "web_layer_included_classes": WEB_PRIORITY_CLASSES,
            "web_layer_omitted_classes": sorted(
                str(v)
                for v in set(priority_gdf["cls"].dropna().unique())
                - set(web_priority_gdf["cls"].dropna().unique())
            ),
            "knowledge_ghost_count": ghosts_count,
            "rediscovery_candidate_count": rediscovery_count,
            "top100_count": top100_count,
            "state_known_cells": int(priority_gdf["state"].notna().sum()),
            "state_missing_cells": int(priority_gdf["state"].isna().sum()),
            "states_with_known_state_values": known_state_values,
            "known_state_count": len(known_state_values),
            "known_state_cell_count": int(priority_gdf["state"].notna().sum()),
            "unknown_state_count": int(priority_gdf["state"].isna().sum()),
            "web_state_known_cells": int(web_priority_gdf["state"].notna().sum()),
            "web_unknown_state_count": int(web_priority_gdf["state"].isna().sum()),
        },
        "states": states,
        "caveats": [
            "State fields are inherited from the existing priority_cells.geojson where available; many adequate/lost cells remain null.",
            "Forest cover is summarized as a cell-level mean of forest_cover_pct, not an area-weighted biome statistic.",
        ],
    }
    write_json(OUT_STATE_SUMMARY, summary)
    return summary


def column_schema_from_frame(frame: Any) -> dict[str, dict[str, Any]]:
    schema = {}
    for col in frame.columns:
        if col == frame.geometry.name:
            continue
        schema[col] = {
            "dtype": str(frame[col].dtype),
            "missing": int(frame[col].isna().sum()),
        }
    return schema


def build_sources() -> dict[str, Any]:
    sources = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "grid_final": {
                "path": rel(SRC_GRID_FINAL),
                "role": "Primary EKDI analytical grid.",
            },
            "grid_endemicas": {
                "path": rel(SRC_GRID_ENDEMICAS),
                "role": "Critical-gap enrichment source; no stable cell_id available.",
            },
            "ghost_species": {
                "path": rel(SRC_GHOSTS),
                "role": "Knowledge Ghost source table.",
            },
            "extinction_risk_analysis": {
                "path": rel(SRC_RISK),
                "role": "Species-level risk and rediscovery hypothesis source.",
            },
            "critical_gaps_top100": {
                "path": rel(SRC_TOP100),
                "role": "Top 100 critical gap candidates.",
            },
            "current_priority_cells": {
                "path": rel(SRC_CURRENT_PRIORITY),
                "role": "Existing MapLibre priority layer used for state/threat/endemic aliases.",
            },
            "current_gbif_memory": {
                "path": rel(SRC_CURRENT_GBIF),
                "role": "Existing sampled GBIF memory point layer.",
            },
            "current_forest_mask": {
                "path": rel(SRC_CURRENT_FOREST),
                "role": "Existing dissolved forest mask layer.",
            },
        },
        "external_source_labels": {
            "GBIF": "Occurrence evidence, already processed in project outputs.",
            "MapBiomas": "Land-cover change metrics, already processed in project outputs.",
            "WorldClim": "Richness-deficit covariate source, already processed in project outputs.",
            "Flora e Funga do Brasil": "Endemism/risk context, already processed in project outputs where available.",
        },
    }
    write_json(OUT_SOURCES, sources)
    return sources


def build_schema(
    priority_gdf: Any,
    web_priority_gdf: Any,
    priority_missing: dict[str, int],
    stats: dict[str, Any],
    ghost_stats: dict[str, Any],
    rediscovery_stats: dict[str, Any],
    cell_plant_stats: dict[str, Any],
    top100_stats: dict[str, Any],
) -> dict[str, Any]:
    schema = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "outputs": {
            rel(OUT_PRIORITY_FULL): {
                "type": "GeoJSON FeatureCollection",
                "geometry": "Polygon",
                "crs": "EPSG:4326",
                "features": stats["full_features"],
                "layer_role": "Full analytical priority-cell layer.",
                "fields": column_schema_from_frame(priority_gdf),
                "required_field_missing_counts": priority_missing,
                "field_mappings": {
                    "id": "cell_id",
                    "cls": "categoria_final mapped through CATEGORY_TO_CLASS",
                    "last": "ultimo_registro",
                    "loss": "perdida_ha",
                    "forest": "forest_cover_pct",
                    "gbif": "n_registros",
                    "ekdi": "indice",
                    "years": f"{REFERENCE_YEAR} - ultimo_registro",
                    "recommended_action": "class-based fallback; not a measured scientific field",
                },
                "caveats": [
                    "State fields are null where the existing MapLibre priority layer had no matching cell_id.",
                    "nearest_city is null because no stable cell_id join exists in grid_endemicas.gpkg.",
                    "recommended_action is generated as a documented class-based fallback.",
                ],
            },
            rel(OUT_PRIORITY_WEB): {
                "type": "GeoJSON FeatureCollection",
                "geometry": "Polygon",
                "crs": "EPSG:4326",
                "features": stats["web_features"],
                "layer_role": "Recommended web layer for MapLibre dashboard visualization.",
                "included_classes": stats["web_classes_present"],
                "omitted_classes": stats["omitted_classes"],
                "fields": column_schema_from_frame(web_priority_gdf),
                "caveats": [
                    "Adequate cells are omitted from the default web layer for performance.",
                    "State/stateName are missing where no state value was available in the existing priority source.",
                    "nearest_city is null because no stable cell_id join exists in grid_endemicas.gpkg.",
                    "recommended_action is generated as a documented class-based fallback.",
                ],
            },
            rel(OUT_PRIORITY): {
                "type": "GeoJSON FeatureCollection",
                "geometry": "Polygon",
                "crs": "EPSG:4326",
                "features": stats["alias_features"],
                "layer_role": "Alias copy of priority_cells_web.geojson for dashboard fetch compatibility.",
                "alias_of": rel(OUT_PRIORITY_WEB),
                "included_classes": stats["web_classes_present"],
                "omitted_classes": stats["omitted_classes"],
                "caveats": [
                    "This file intentionally aliases the recommended web layer, not the full grid.",
                    "Use priority_cells_full.geojson for complete analytical coverage.",
                ],
            },
            rel(OUT_FOREST): {
                "type": "GeoJSON FeatureCollection",
                "geometry": "MultiPolygon/Polygon",
                "crs": "EPSG:4326",
                "caveats": [
                    f"Forest threshold documented as >= {FOREST_MASK_THRESHOLD_PCT}% from prior exporter logic.",
                ],
            },
            rel(OUT_BIOME): {
                "type": "GeoJSON FeatureCollection",
                "geometry": "Polygon/MultiPolygon",
                "crs": "EPSG:4326",
                "caveats": [
                    "Derived from dissolved grid_final.gpkg footprint because original biome boundary was not in the Phase 2 input list.",
                ],
            },
            rel(OUT_GBIF): {
                "type": "GeoJSON FeatureCollection",
                "geometry": "Point",
                "crs": "EPSG:4326",
                "caveats": [
                    "Copied from existing sampled GBIF memory layer; species fields are not available in that source.",
                ],
            },
            rel(OUT_GHOSTS): {
                "type": "JSON table",
                "rows": ghost_stats["rows"],
                "missing_counts": ghost_stats["missing_counts"],
                "caveats": [
                    "Knowledge Ghost records are candidate signals and do not imply presence, absence, or extinction.",
                ],
            },
            rel(OUT_REDISCOVERY): {
                "type": "JSON table",
                "rows": rediscovery_stats["rows"],
                "rule": rediscovery_stats["rule"],
                "caveats": [
                    "Conservative species-level hypotheses only.",
                    "Location-specific fields are null because spatial evidence was insufficient in Phase 2 inputs.",
                ],
            },
            rel(OUT_CELL_PLANT_CANDIDATES): {
                "type": "JSON table",
                "rows": cell_plant_stats["rows"],
                "plant_records": cell_plant_stats["plant_records"],
                "rule": cell_plant_stats["rule"],
                "fields": {
                    "cell_id": {"required": True, "description": "Priority-cell identifier."},
                    "state": {"required": False, "description": "State code when available."},
                    "stateName": {"required": False, "description": "State name when available."},
                    "plants": {"required": True, "description": "Cell-linked plant candidate records."},
                },
                "plant_fields": [
                    "species",
                    "candidate_type",
                    "last_record",
                    "risk_category",
                    "risk_criterion",
                    "endemic",
                    "recommended_action",
                    "evidence_source",
                    "notes",
                ],
                "caveats": cell_plant_stats["limitations"],
            },
            rel(OUT_STATE_SUMMARY): {
                "type": "JSON summary",
                "caveats": [
                    "State coverage is partial for all cells; class totals remain complete.",
                ],
            },
            rel(OUT_TOP100): {
                "type": "CSV table",
                "rows": top100_stats["rows"],
                "columns": top100_stats["columns"],
                "caveats": [
                    "cell_id, state, stateName and nearest_city are null until a spatial join is performed.",
                ],
            },
        },
        "safe_language": [
            "candidate",
            "hypothesis",
            "needs verification",
            "voucher review recommended",
            "field verification recommended",
        ],
    }
    write_json(OUT_SCHEMA, schema)
    return schema


def build_data_integrity(
    priority_stats: dict[str, Any],
    biome_stats: dict[str, Any],
    forest_stats: dict[str, Any],
    gbif_stats: dict[str, Any],
    ghost_stats: dict[str, Any],
    rediscovery_stats: dict[str, Any],
    cell_plant_stats: dict[str, Any],
    top100_stats: dict[str, Any],
) -> dict[str, Any]:
    integrity = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "Phase 2.5 clean dashboard data generated with full and web priority layers",
        "crs_checks": {
            rel(OUT_PRIORITY_FULL): "EPSG:4326",
            rel(OUT_PRIORITY_WEB): "EPSG:4326",
            rel(OUT_PRIORITY): "EPSG:4326",
            rel(OUT_FOREST): "EPSG:4326",
            rel(OUT_BIOME): "EPSG:4326",
            rel(OUT_GBIF): "EPSG:4326",
        },
        "row_counts": {
            rel(OUT_PRIORITY_FULL): priority_stats["full_features"],
            rel(OUT_PRIORITY_WEB): priority_stats["web_features"],
            rel(OUT_PRIORITY): priority_stats["alias_features"],
            rel(OUT_BIOME): biome_stats["features"],
            rel(OUT_FOREST): forest_stats["features"],
            rel(OUT_GBIF): gbif_stats["features"],
            rel(OUT_GHOSTS): ghost_stats["rows"],
            rel(OUT_REDISCOVERY): rediscovery_stats["rows"],
            rel(OUT_CELL_PLANT_CANDIDATES): cell_plant_stats["rows"],
            rel(OUT_TOP100): top100_stats["rows"],
        },
        "class_counts": priority_stats["class_counts"],
        "web_class_counts": priority_stats["web_class_counts"],
        "omitted_classes": priority_stats["omitted_classes"],
        "category_counts": priority_stats["category_counts"],
        "missing_required_counts": priority_stats["missing_required_counts"],
        "fallbacks": {
            "recommended_action": "Generated class-based fallback where source field is absent.",
            "rediscovery_candidates": "Generated conservatively as species-level hypotheses with null location fields.",
            "cell_plant_candidates": "Only explicit species + cell_id records are linked to cells.",
            "biome_boundary": "Generated from dissolved analysis grid footprint.",
            "priority_cells_alias": "priority_cells.geojson is copied from priority_cells_web.geojson for dashboard compatibility.",
        },
        "validation_caveats": [
            "No dashboard HTML was edited in Phase 2.5.",
            "No original source data files were overwritten.",
            "State fields are incomplete for cells not present in the existing priority_cells.geojson.",
            "Rediscovery candidates require spatial evidence before being treated as location-specific targets.",
            "Adequate cells are omitted from the default web priority layer but retained in priority_cells_full.geojson.",
        ],
    }
    write_json(OUT_INTEGRITY, integrity)
    return integrity


def write_report(output_stats: dict[str, Any]) -> None:
    lines = [
        "# BUILD_DASHBOARD_DATA_REPORT.md",
        "",
        "Phase 2/2.5 build report. The script generated clean dashboard data files and did not edit the dashboard HTML.",
        "",
        "## Generated Files",
        "",
    ]
    for path, stats in output_stats.items():
        lines.append(f"### `{path}`")
        for key, value in stats.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    lines.extend(
        [
            "## Field Mappings",
            "",
            "- `cell_id` -> `id` dashboard alias.",
            "- `categoria_final` -> `cls` using `critico=critical`, `alto=deficient`, `adecuado=adequate`, `bosque_sin_explorar=unsurveyed`, `sin_datos_abierto=lost`.",
            "- `ultimo_registro` -> `last` dashboard alias.",
            "- `perdida_ha` -> `loss` dashboard alias.",
            "- `forest_cover_pct` -> `forest` dashboard alias.",
            "- `n_registros` -> `gbif` dashboard alias.",
            "- `indice` -> `ekdi` dashboard alias.",
            f"- `years` is derived as `{REFERENCE_YEAR} - ultimo_registro` when `ultimo_registro` is available.",
            "- `recommended_action` is generated only as a documented class-based fallback because it is absent from source data.",
            "",
            "## Caveats",
            "",
            "- `nearest_city` remains null in `priority_cells.geojson`; `grid_endemicas.gpkg` has `p_city` but no stable `cell_id` join.",
            "- State fields are inherited from existing `PROYECTO CONCURSO GBIF/data/priority_cells.geojson` where available, so adequate/lost cells may have null state values.",
            "- `biome_boundary.geojson` is a dissolved analysis-grid footprint, not the original biome polygon.",
            "- `rediscovery_candidates.json` is conservative and species-level only; location-specific fields are null.",
            "- `gbif_memory.geojson` is copied from the existing sampled layer and does not include species names because they are absent in that source.",
            "- `priority_cells_full.geojson` keeps all 48,407 cells and preserved fields.",
            "- `priority_cells_web.geojson` omits adequate cells by default for performance.",
            "- `priority_cells.geojson` is an alias copy of the recommended web layer for dashboard fetch compatibility.",
            "- Safe scientific language is preserved: outputs use candidate/hypothesis/verification language and do not claim extinction, absence, or presence.",
        ]
    )
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_phase_2_5_report(output_stats: dict[str, Any], priority_stats: dict[str, Any]) -> None:
    lines = [
        "# BUILD_DASHBOARD_DATA_REPORT_PHASE_2_5.md",
        "",
        "Phase 2.5 performance and readiness report. The builder now emits a full analytical priority layer and a lighter web layer. Dashboard HTML was not edited.",
        "",
        "## Priority Layer Split",
        "",
        f"- Full layer: `{rel(OUT_PRIORITY_FULL)}`",
        f"- Web layer: `{rel(OUT_PRIORITY_WEB)}`",
        f"- Dashboard alias: `{rel(OUT_PRIORITY)}` copies the web layer.",
        f"- Full row count: `{priority_stats['full_features']}`",
        f"- Web row count: `{priority_stats['web_features']}`",
        f"- Included web classes: `{', '.join(priority_stats['web_classes_present'])}`",
        f"- Omitted classes: `{', '.join(priority_stats['omitted_classes']) or 'none'}`",
        "- Distinct known state values are listed in `tables/state_summary.json`.",
        f"- Unknown state count, full layer: `{priority_stats['state_missing_features']}`",
        f"- Unknown state count, web layer: `{priority_stats['web_state_missing_features']}`",
        "",
        "## Generated Files",
        "",
    ]
    for path, stats in output_stats.items():
        lines.append(f"### `{path}`")
        for key, value in stats.items():
            lines.append(f"- {key}: `{value}`")
        lines.append("")
    lines.extend(
        [
            "## Metadata Updates",
            "",
            "- `metadata/schema.json` now documents `priority_cells_full.geojson`, `priority_cells_web.geojson`, and the `priority_cells.geojson` alias.",
            "- `metadata/schema.json` records full/web row counts, omitted classes, missing state/stateName caveats, the nearest_city null caveat, and recommended_action as a class-based fallback.",
            "- `tables/state_summary.json` now includes full-grid class totals, web-layer class totals, known-state counts, and unknown-state counts.",
            "",
            "## Readiness Notes",
            "",
            "- `priority_cells_web.geojson` excludes adequate cells by default to reduce dashboard payload size.",
            "- Lost cells are included in the web layer because they support historical context and are explicitly useful in the existing layer toggles.",
            "- Scientific values are not invented; missing values remain null and are documented in metadata.",
            "- `recommended_action` remains a documented class-based fallback, not a measured scientific field.",
            "- `nearest_city` remains null because there is no stable cell_id join from `grid_endemicas.gpkg`.",
            "- Safe scientific language is preserved: candidate, hypothesis, needs verification, voucher review recommended, and field verification recommended.",
            "- Dashboard HTML was not edited in Phase 2.5.",
        ]
    )
    OUT_REPORT_PHASE_2_5.write_text("\n".join(lines) + "\n", encoding="utf-8")


def size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 2)


def main() -> None:
    gpd, np, pd = require_runtime()
    ensure_dirs()

    priority_gdf, web_priority_gdf, priority_stats, priority_missing = build_priority_cells(gpd, pd)
    biome_stats = build_biome_boundary(gpd, priority_gdf)
    forest_stats = build_forest_mask(gpd)
    gbif_stats = build_gbif_memory(gpd)
    ghosts, ghost_stats = build_knowledge_ghosts(pd, priority_gdf)
    rediscovery, rediscovery_stats = build_rediscovery_candidates(pd)
    cell_plants, cell_plant_stats = build_cell_plant_candidates(ghosts, rediscovery)
    top100_stats = build_top100(pd)
    state_summary = build_state_summary(
        priority_gdf,
        web_priority_gdf,
        ghosts_count=len(ghosts),
        rediscovery_count=len(rediscovery),
        top100_count=top100_stats["rows"],
    )
    sources = build_sources()
    schema = build_schema(
        priority_gdf,
        web_priority_gdf,
        priority_missing,
        priority_stats,
        ghost_stats,
        rediscovery_stats,
        cell_plant_stats,
        top100_stats,
    )
    integrity = build_data_integrity(
        priority_stats,
        biome_stats,
        forest_stats,
        gbif_stats,
        ghost_stats,
        rediscovery_stats,
        cell_plant_stats,
        top100_stats,
    )

    output_stats = {
        rel(OUT_PRIORITY_FULL): {"features": priority_stats["full_features"], "crs": "EPSG:4326", "size_mb": size_mb(OUT_PRIORITY_FULL)},
        rel(OUT_PRIORITY_WEB): {
            "features": priority_stats["web_features"],
            "crs": "EPSG:4326",
            "size_mb": size_mb(OUT_PRIORITY_WEB),
            "included_classes": ",".join(priority_stats["web_classes_present"]),
            "omitted_classes": ",".join(priority_stats["omitted_classes"]),
        },
        rel(OUT_PRIORITY): {
            "features": priority_stats["alias_features"],
            "crs": "EPSG:4326",
            "size_mb": size_mb(OUT_PRIORITY),
            "alias_of": rel(OUT_PRIORITY_WEB),
        },
        rel(OUT_FOREST): {"features": forest_stats["features"], "crs": "EPSG:4326", "size_mb": size_mb(OUT_FOREST)},
        rel(OUT_BIOME): {"features": biome_stats["features"], "crs": "EPSG:4326", "size_mb": size_mb(OUT_BIOME)},
        rel(OUT_GBIF): {"features": gbif_stats["features"], "crs": "EPSG:4326", "size_mb": size_mb(OUT_GBIF)},
        rel(OUT_GHOSTS): {"rows": ghost_stats["rows"], "size_mb": size_mb(OUT_GHOSTS)},
        rel(OUT_REDISCOVERY): {"rows": rediscovery_stats["rows"], "size_mb": size_mb(OUT_REDISCOVERY)},
        rel(OUT_CELL_PLANT_CANDIDATES): {"rows": cell_plant_stats["rows"], "plant_records": cell_plant_stats["plant_records"], "size_mb": size_mb(OUT_CELL_PLANT_CANDIDATES)},
        rel(OUT_STATE_SUMMARY): {"states": len(state_summary["states"]), "size_mb": size_mb(OUT_STATE_SUMMARY)},
        rel(OUT_TOP100): {"rows": top100_stats["rows"], "size_mb": size_mb(OUT_TOP100)},
        rel(OUT_INTEGRITY): {"sections": len(integrity), "size_mb": size_mb(OUT_INTEGRITY)},
        rel(OUT_SCHEMA): {"outputs": len(schema["outputs"]), "size_mb": size_mb(OUT_SCHEMA)},
        rel(OUT_SOURCES): {"inputs": len(sources["inputs"]), "size_mb": size_mb(OUT_SOURCES)},
    }
    write_report(output_stats)
    write_phase_2_5_report(output_stats, priority_stats)

    print("OK Phase 2.5 dashboard data generated")
    for path, stats in output_stats.items():
        print(f"- {path}: {stats}")
    print(f"- {rel(OUT_REPORT)}")
    print(f"- {rel(OUT_REPORT_PHASE_2_5)}")


if __name__ == "__main__":
    main()
