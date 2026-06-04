"""Build real GBIF species-per-cell summaries for the EKDI app.

This script reads the GBIF occurrence table already joined to the 5 km EKDI
grid, summarizes records by cell and species, then merges existing
priority-linked plant evidence. It never invents species, threat categories,
endemism, DOI values or occurrence records.

If no Parquet reader is installed, install one locally:

    pip install pandas pyarrow
    python repo/scripts/build_cell_species_records.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
APP_DATA = REPO_ROOT / "app" / "data"

GBIF_JOINED = WORKSPACE_ROOT / "data" / "gbif_grid_joined.parquet"
PRIORITY_PLANTS = APP_DATA / "tables" / "cell_priority_plants.json"
PLANT_CANDIDATES = APP_DATA / "tables" / "cell_plant_candidates.json"
OUTPUT = APP_DATA / "tables" / "cell_species_records.json"
TOP10_OUTPUT = APP_DATA / "tables" / "cell_species_top10_by_cell.json"
TOP5_PRIORITY_OUTPUT = APP_DATA / "tables" / "cell_species_top5_priority_cells.json"
TOP3_CRITICAL_OUTPUT = APP_DATA / "tables" / "cell_species_top3_critical_gaps.json"
COLUMN_REPORT = APP_DATA / "metadata" / "cell_species_records_columns.json"
PRIORITY_CELLS = APP_DATA / "geo" / "priority_cells.geojson"

CURRENT_YEAR = 2026
THREAT_CATEGORIES = {"CR", "EN", "VU"}
EMPTY_VALUES = {"", "none", "null", "nan", "na", "n/a", "not available"}


FIELD_ALIASES = {
    "species": [
        "scientificName",
        "species",
        "acceptedScientificName",
        "canonicalName",
    ],
    "cell_id": ["cell_id", "grid_id", "id_cell", "cell"],
    "year": ["year", "eventDate", "event_year"],
    "latitude": ["decimalLatitude", "latitude", "lat"],
    "longitude": ["decimalLongitude", "longitude", "lon", "lng"],
    "basis": ["basisOfRecord"],
    "occurrence_id": ["occurrenceID", "occurrenceId"],
    "gbif_id": ["gbifID", "gbifId"],
    "family": ["family", "familia", "taxon_family", "familyName"],
    "genus": ["genus", "genero", "taxon_genus", "genusName"],
    "accepted": [
        "acceptedScientificName",
        "acceptedName",
        "accepted_scientific_name",
        "accepted_name",
    ],
    "kingdom": ["kingdom", "reino"],
    "taxon_rank": ["taxonRank", "rank", "taxon_rank"],
    "coordinate_uncertainty": [
        "coordinateUncertaintyInMeters",
        "coordinate_uncertainty",
        "coordinate_uncertainty_m",
    ],
}


def norm_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in EMPTY_VALUES:
        return None
    return text


def norm_cell_id(value: Any) -> str | None:
    return norm_text(value)


def normalize_species_key(value: Any) -> str | None:
    text = norm_text(value)
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text or None


def derive_genus(scientific_name: str | None) -> str | None:
    text = norm_text(scientific_name)
    if not text:
        return None
    return text.split()[0] if text.split() else None


def parse_year(value: Any) -> int | None:
    text = norm_text(value)
    if not text:
        return None
    match = re.search(r"(1[6-9]\d{2}|20\d{2}|21\d{2})", text)
    if not match:
        return None
    year = int(match.group(1))
    if 1500 < year <= CURRENT_YEAR:
        return year
    return None


def column_lookup(columns: list[str]) -> dict[str, str]:
    return {column.lower(): column for column in columns}


def detect_column(columns: list[str], aliases: list[str]) -> str | None:
    lookup = column_lookup(columns)
    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]
    return None


def row_value(row: dict[str, Any], column: str | None) -> Any:
    if not column:
        return None
    return row.get(column)


def rows_from_dataframe(frame: Any) -> tuple[list[dict[str, Any]], list[str], str]:
    columns = [str(column) for column in list(frame.columns)]
    records = frame.to_dict(orient="records")
    return records, columns, "dataframe"


def read_parquet(path: Path) -> tuple[list[dict[str, Any]], list[str], str]:
    errors: list[str] = []

    try:
        import pandas as pd  # type: ignore

        try:
            frame = pd.read_parquet(path, engine="pyarrow")
            records, columns, _ = rows_from_dataframe(frame)
            return records, columns, "pandas+pyarrow"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"pandas+pyarrow: {exc}")

        try:
            frame = pd.read_parquet(path, engine="fastparquet")
            records, columns, _ = rows_from_dataframe(frame)
            return records, columns, "pandas+fastparquet"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"pandas+fastparquet: {exc}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pandas import: {exc}")

    try:
        import geopandas as gpd  # type: ignore

        frame = gpd.read_parquet(path)
        records, columns, _ = rows_from_dataframe(frame)
        return records, columns, "geopandas"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"geopandas: {exc}")

    try:
        import duckdb  # type: ignore

        frame = duckdb.sql(f"SELECT * FROM read_parquet('{path.as_posix()}')").df()
        records, columns, _ = rows_from_dataframe(frame)
        return records, columns, "duckdb"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"duckdb: {exc}")

    try:
        import polars as pl  # type: ignore

        frame = pl.read_parquet(path)
        records = frame.to_dicts()
        columns = [str(column) for column in frame.columns]
        return records, columns, "polars"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"polars: {exc}")

    message = "\n".join(
        [
            "No usable Parquet reader is available.",
            "Install a reader and rerun:",
            "  pip install pandas pyarrow",
            "  python repo/scripts/build_cell_species_records.py",
            "",
            "Reader attempts:",
            *[f"  - {error}" for error in errors],
        ]
    )
    raise RuntimeError(message)


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_priority_plants(data: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return output
    for row in data:
        if not isinstance(row, dict):
            continue
        plants = row.get("plants") if isinstance(row.get("plants"), list) else [row]
        for plant in plants:
            if not isinstance(plant, dict):
                continue
            merged = dict(plant)
            merged.setdefault("cell_id", row.get("cell_id"))
            merged.setdefault("state", row.get("state"))
            merged.setdefault("stateName", row.get("stateName"))
            output.append(merged)
    return output


def priority_endemic_flag(plant: dict[str, Any]) -> bool | None:
    for key in [
        "endemic",
        "endemism",
        "endemic_signal",
        "endemica",
        "endemismo",
        "is_endemic",
        "florabr_endemic",
        "endemic_to_brazil",
        "endemica_br",
    ]:
        value = norm_text(plant.get(key))
        if not value:
            continue
        lowered = value.lower()
        if lowered in {"true", "yes", "sim", "endemic", "endemica", "endemic signal"}:
            return True
        if lowered in {"false", "no", "nao", "não"}:
            return False
        return True
    source = str(plant.get("evidence_source") or "").lower()
    if "grid_endemicas" in source or "endemic" in source or "endem" in source:
        return True
    return None


def priority_official_status(plant: dict[str, Any]) -> str | None:
    for key in [
        "official_red_list_status",
        "red_list_status",
        "red_list_category",
        "iucn_category",
        "iucn",
        "category",
        "categoria",
        "categoria_risco",
        "risk_category",
        "conservation_status",
        "threat_status",
        "status_ameaca",
        "cncflora_category",
        "lista_vermelha",
    ]:
        value = norm_text(plant.get(key))
        if value:
            return value
    return None


def priority_flags(plant: dict[str, Any]) -> dict[str, Any]:
    candidate_type = str(plant.get("candidate_type") or "").lower()
    evidence_source = str(plant.get("evidence_source") or plant.get("source") or "")
    return {
        "is_priority_linked": True,
        "is_endemic": priority_endemic_flag(plant),
        "is_knowledge_ghost": "knowledge ghost" in candidate_type
        or "knowledge_ghost" in evidence_source.lower(),
        "is_rediscovery_hypothesis": "rediscovery" in candidate_type
        or "rediscovery" in evidence_source.lower(),
        "official_status": priority_official_status(plant),
        "priority_evidence_source": evidence_source or None,
        "priority_candidate_type": plant.get("candidate_type"),
    }


def summarize_basis(values: list[str]) -> str | None:
    cleaned = [value for value in values if norm_text(value)]
    if not cleaned:
        return None
    counts = Counter(cleaned)
    return "; ".join(f"{key}: {value}" for key, value in counts.most_common(5))


def sample_values(values: list[str], limit: int = 5) -> list[str]:
    seen: list[str] = []
    for value in values:
        text = norm_text(value)
        if text and text not in seen:
            seen.append(text)
        if len(seen) >= limit:
            break
    return seen


def review_need(row: dict[str, Any]) -> str:
    official = str(row.get("official_status") or "").upper()
    if official in THREAT_CATEGORIES:
        return "Threat-linked review"
    if row.get("is_priority_linked"):
        return "Priority-linked review"
    if row.get("record_count") == 1:
        return "Single-record verification"
    years_silent = row.get("years_silent")
    if isinstance(years_silent, int) and years_silent >= 30:
        return "Historical evidence review"
    if isinstance(years_silent, int) and years_silent >= 20:
        return "Old-record review"
    if row.get("coordinate_review_needed"):
        return "Coordinate review"
    return "Occurrence review"


def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    official = str(row.get("official_status") or "").upper()
    return (
        not bool(row.get("is_priority_linked")),
        not bool(row.get("is_knowledge_ghost")),
        official not in THREAT_CATEGORIES,
        -(row.get("years_silent") or 0),
        0 if row.get("record_count") == 1 else 1,
        row.get("record_count") or 999999,
        str(row.get("scientificName") or "").lower(),
    )


def write_column_report(
    columns: list[str],
    detected: dict[str, str | None],
    reader: str,
    raw_rows: int,
) -> None:
    COLUMN_REPORT.parent.mkdir(parents=True, exist_ok=True)
    COLUMN_REPORT.write_text(
        json.dumps(
            {
                "source": str(GBIF_JOINED.as_posix()),
                "reader": reader,
                "raw_rows": raw_rows,
                "detected_columns": columns,
                "detected_fields": detected,
                "created": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_failure_report(error: str) -> None:
    COLUMN_REPORT.parent.mkdir(parents=True, exist_ok=True)
    COLUMN_REPORT.write_text(
        json.dumps(
            {
                "source": str(GBIF_JOINED.as_posix()),
                "created": datetime.now(timezone.utc).isoformat(),
                "status": "not_built",
                "error": error,
                "install_instructions": [
                    "pip install pandas pyarrow",
                    "python repo/scripts/build_cell_species_records.py",
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def build_records(raw_rows: list[dict[str, Any]], columns: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    detected = {key: detect_column(columns, aliases) for key, aliases in FIELD_ALIASES.items()}
    missing = [key for key in ["species", "cell_id", "year"] if not detected[key]]
    if missing:
        raise RuntimeError(f"Missing required field(s): {', '.join(missing)}. Detected: {detected}")

    has_kingdom = detected.get("kingdom") is not None
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    skipped_invalid_year = 0
    skipped_missing_required = 0
    skipped_non_plants = 0

    for row in raw_rows:
        if has_kingdom:
            kingdom = str(row_value(row, detected["kingdom"]) or "").strip().lower()
            if kingdom and kingdom not in {"plantae", "plant", "plants"}:
                skipped_non_plants += 1
                continue

        cell_id = norm_cell_id(row_value(row, detected["cell_id"]))
        scientific_name = norm_text(row_value(row, detected["species"]))
        species_key = normalize_species_key(scientific_name)
        year = parse_year(row_value(row, detected["year"]))
        if not cell_id or not scientific_name or not species_key:
            skipped_missing_required += 1
            continue
        if year is None:
            skipped_invalid_year += 1
            continue

        key = (cell_id, species_key)
        entry = grouped.setdefault(
            key,
            {
                "cell_id": cell_id,
                "scientificName": scientific_name,
                "acceptedScientificName": norm_text(row_value(row, detected.get("accepted"))),
                "genus": norm_text(row_value(row, detected.get("genus"))) or derive_genus(scientific_name),
                "family": norm_text(row_value(row, detected.get("family"))),
                "years": [],
                "basis": [],
                "gbif_ids": [],
                "occurrence_ids": [],
                "latitudes": [],
                "longitudes": [],
                "coordinate_uncertainties": [],
                "source_type": "GBIF occurrence",
                "evidence_type": "GBIF occurrence",
                "is_priority_linked": False,
                "is_endemic": None,
                "is_knowledge_ghost": False,
                "is_rediscovery_hypothesis": False,
                "official_status": None,
            },
        )
        entry["years"].append(year)
        for target, detected_key in [
            ("basis", "basis"),
            ("gbif_ids", "gbif_id"),
            ("occurrence_ids", "occurrence_id"),
            ("latitudes", "latitude"),
            ("longitudes", "longitude"),
            ("coordinate_uncertainties", "coordinate_uncertainty"),
        ]:
            value = norm_text(row_value(row, detected.get(detected_key)))
            if value:
                entry[target].append(value)

    records: list[dict[str, Any]] = []
    for entry in grouped.values():
        years = entry.pop("years")
        basis = entry.pop("basis")
        gbif_ids = entry.pop("gbif_ids")
        occurrence_ids = entry.pop("occurrence_ids")
        latitudes = entry.pop("latitudes")
        longitudes = entry.pop("longitudes")
        uncertainties = entry.pop("coordinate_uncertainties")
        first_year = min(years)
        last_year = max(years)
        coordinate_review_needed = not (latitudes and longitudes)
        if uncertainties:
            numeric_uncertainties = []
            for value in uncertainties:
                try:
                    numeric_uncertainties.append(float(value))
                except ValueError:
                    pass
            if numeric_uncertainties and max(numeric_uncertainties) > 10000:
                coordinate_review_needed = True

        record = {
            **entry,
            "record_count": len(years),
            "first_year": first_year,
            "last_year": last_year,
            "years_silent": CURRENT_YEAR - last_year,
            "basisOfRecord_summary": summarize_basis(basis),
            "gbif_ids_sample": sample_values(gbif_ids),
            "occurrence_ids_sample": sample_values(occurrence_ids),
            "coordinate_review_needed": coordinate_review_needed,
        }
        records.append(record)

    stats = {
        "detected": detected,
        "raw_rows": len(raw_rows),
        "grouped_rows": len(records),
        "skipped_invalid_year": skipped_invalid_year,
        "skipped_missing_required": skipped_missing_required,
        "skipped_non_plants": skipped_non_plants,
        "kingdom_filter_applied": has_kingdom,
    }
    return records, stats


def merge_priority(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    priority_source = PRIORITY_PLANTS if PRIORITY_PLANTS.exists() else PLANT_CANDIDATES
    priority_rows = flatten_priority_plants(load_json(priority_source, []))
    index = {
        (norm_cell_id(row.get("cell_id")), normalize_species_key(row.get("scientificName") or row.get("species") or row.get("taxon"))): row
        for row in records
    }
    index = {key: value for key, value in index.items() if key[0] and key[1]}

    merged = 0
    appended = 0
    skipped = 0

    for plant in priority_rows:
        cell_id = norm_cell_id(plant.get("cell_id"))
        scientific_name = norm_text(plant.get("scientificName") or plant.get("species") or plant.get("taxon"))
        species_key = normalize_species_key(scientific_name)
        if not cell_id or not scientific_name or not species_key:
            skipped += 1
            continue
        flags = priority_flags(plant)
        key = (cell_id, species_key)
        target = index.get(key)
        if target:
            target.update({key_name: value for key_name, value in flags.items() if value is not None})
            target["evidence_type"] = "GBIF occurrence + Priority-linked"
            if flags.get("official_status") and not target.get("official_status"):
                target["official_status"] = flags["official_status"]
            merged += 1
            continue

        last_year = parse_year(plant.get("last_record") or plant.get("ultimo_registro") or plant.get("year") or plant.get("last_year"))
        first_year = parse_year(plant.get("first_record") or plant.get("primer_registro") or plant.get("primeiro_registro")) or last_year
        if last_year is None:
            skipped += 1
            continue
        record_count = plant.get("record_count") or plant.get("gbif_records") or plant.get("n_registros") or plant.get("n_records")
        try:
            record_count_int = int(float(record_count)) if record_count is not None else 1
        except (TypeError, ValueError):
            record_count_int = 1
        appended_record = {
            "cell_id": cell_id,
            "scientificName": scientific_name,
            "acceptedScientificName": norm_text(plant.get("acceptedScientificName") or plant.get("acceptedName")),
            "genus": norm_text(plant.get("genus")) or derive_genus(scientific_name),
            "family": norm_text(plant.get("family")),
            "record_count": record_count_int,
            "first_year": first_year,
            "last_year": last_year,
            "years_silent": CURRENT_YEAR - last_year,
            "basisOfRecord_summary": None,
            "gbif_ids_sample": [],
            "occurrence_ids_sample": [],
            "source_type": "Priority-linked plant evidence",
            "evidence_type": "Priority-linked",
            "coordinate_review_needed": False,
            **flags,
        }
        records.append(appended_record)
        index[key] = appended_record
        appended += 1

    return records, {"merged_priority_rows": merged, "appended_priority_rows": appended, "skipped_priority_rows": skipped}


def assign_display_ranks(records: list[dict[str, Any]]) -> None:
    by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_cell[row["cell_id"]].append(row)
    for cell_rows in by_cell.values():
        cell_rows.sort(key=sort_key)
        for rank, row in enumerate(cell_rows, start=1):
            row["display_rank"] = rank
            row["review_need"] = review_need(row)


def build_output(records: list[dict[str, Any]], stats: dict[str, Any], merge_stats: dict[str, int], reader: str) -> dict[str, Any]:
    unique_cells = {row["cell_id"] for row in records}
    unique_species = {normalize_species_key(row["scientificName"]) for row in records if normalize_species_key(row["scientificName"])}
    top_cells = Counter(row["cell_id"] for row in records).most_common(10)
    return {
        "metadata": {
            "source": "data/gbif_grid_joined.parquet",
            "reader": reader,
            "created": datetime.now(timezone.utc).isoformat(),
            "current_year": CURRENT_YEAR,
            "raw_gbif_records": stats["raw_rows"],
            "rows": len(records),
            "unique_cells": len(unique_cells),
            "unique_species": len(unique_species),
            "top_cells_by_species_count": [
                {"cell_id": cell_id, "species_rows": count} for cell_id, count in top_cells
            ],
            "merged_priority_rows": merge_stats["merged_priority_rows"],
            "appended_priority_rows": merge_stats["appended_priority_rows"],
            "skipped_priority_rows": merge_stats["skipped_priority_rows"],
            "skipped_invalid_year": stats["skipped_invalid_year"],
            "skipped_missing_required": stats["skipped_missing_required"],
            "skipped_non_plants": stats["skipped_non_plants"],
            "kingdom_filter_applied": stats["kingdom_filter_applied"],
            "note": "Species records summarized from GBIF-mediated occurrence records joined to 5 km EKDI grid.",
            "limitation": (
                "If no kingdom field was available, records were not filtered by kingdom in this script. "
                "No species, red-list category, endemism value or GBIF DOI was invented."
            ),
        },
        "records": records,
    }


def clean_top_species_record(row: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "scientificName",
        "acceptedScientificName",
        "genus",
        "family",
        "record_count",
        "first_year",
        "last_year",
        "years_silent",
        "evidence_type",
        "source_type",
        "is_priority_linked",
        "is_endemic",
        "is_knowledge_ghost",
        "is_rediscovery_hypothesis",
        "official_status",
        "review_need",
        "display_rank",
    ]
    return {field: row.get(field) for field in fields if row.get(field) not in (None, [], "")}


def clean_contest_species_record(row: dict[str, Any]) -> dict[str, Any]:
    output = {
        "scientificName": row.get("scientificName"),
        "record_count": row.get("record_count"),
        "last_year": row.get("last_year"),
        "years_silent": row.get("years_silent"),
        "evidence_type": row.get("evidence_type"),
        "review_need": row.get("review_need"),
        "is_priority_linked": bool(row.get("is_priority_linked")),
    }
    if row.get("is_endemic") is not None:
        output["is_endemic"] = row.get("is_endemic")
    if norm_text(row.get("official_status")):
        output["official_status"] = row.get("official_status")
    return {key: value for key, value in output.items() if value not in (None, [], "")}


def priority_class_from_props(props: dict[str, Any]) -> str | None:
    raw = str(props.get("cls") or props.get("categoria_final") or "").strip().lower()
    aliases = {
        "critico": "critical",
        "critical": "critical",
        "alto": "deficient",
        "deficient": "deficient",
        "bosque_sin_explorar": "unsurveyed",
        "unsurveyed": "unsurveyed",
        "sin_datos_abierto": "lost",
        "lost": "lost",
        "adecuado": "adequate",
        "adequate": "adequate",
    }
    return aliases.get(raw)


def load_priority_cell_classes(path: Path = PRIORITY_CELLS) -> dict[str, str]:
    data = load_json(path, {"features": []})
    classes: dict[str, str] = {}
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        cell_id = norm_cell_id(props.get("cell_id") or props.get("id") or feature.get("id"))
        cls = priority_class_from_props(props)
        if cell_id and cls:
            classes[cell_id] = cls
    return classes


def read_full_metadata(path: Path) -> dict[str, Any]:
    lines: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if '"records"' in line:
                break
            lines.append(line)
    text = "".join(lines).strip()
    text = re.sub(r",\s*$", "", text)
    text += "\n}"
    return json.loads(text).get("metadata", {})


def iter_full_records(path: Path):
    in_records = False
    collecting = False
    buffer: list[str] = []
    depth = 0
    in_string = False
    escaped = False

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not in_records:
                if '"records"' in line and "[" in line:
                    in_records = True
                continue

            for char in line:
                if not collecting:
                    if char == "]":
                        return
                    if char == "{":
                        collecting = True
                        buffer = ["{"]
                        depth = 1
                        in_string = False
                        escaped = False
                    continue

                buffer.append(char)
                if escaped:
                    escaped = False
                    continue
                if char == "\\" and in_string:
                    escaped = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        yield json.loads("".join(buffer))
                        collecting = False
                        buffer = []


def build_top10_by_cell(full_path: Path = OUTPUT, top10_path: Path = TOP10_OUTPUT) -> dict[str, Any]:
    if not full_path.exists():
        raise FileNotFoundError(f"Missing full cell species records file: {full_path}")

    metadata = read_full_metadata(full_path)
    cells: dict[str, dict[str, Any]] = {}
    top_species_names: set[str] = set()
    processed = 0

    for row in iter_full_records(full_path):
        processed += 1
        cell_id = norm_cell_id(row.get("cell_id"))
        if not cell_id:
            continue
        cell = cells.setdefault(
            cell_id,
            {
                "cell_id": cell_id,
                "total_species": 0,
                "total_records": 0,
                "top_species": [],
            },
        )
        cell["total_species"] += 1
        try:
            cell["total_records"] += int(row.get("record_count") or 0)
        except (TypeError, ValueError):
            pass
        current = cell["top_species"]
        candidate = clean_top_species_record(row)
        current.append(candidate)
        current.sort(key=sort_key)
        if len(current) > 10:
            current.pop()

    for cell in cells.values():
        cell["top_species"].sort(key=sort_key)
        for rank, row in enumerate(cell["top_species"], start=1):
            row["display_rank"] = rank
            name = normalize_species_key(row.get("scientificName"))
            if name:
                top_species_names.add(name)

    output = {
        "metadata": {
            "source": "cell_species_records.json",
            "created": datetime.now(timezone.utc).isoformat(),
            "current_year": CURRENT_YEAR,
            "unique_cells": len(cells),
            "unique_species": len(top_species_names),
            "unique_species_source": metadata.get("unique_species"),
            "total_rows_source": metadata.get("rows", processed),
            "raw_gbif_records": metadata.get("raw_gbif_records"),
            "merged_priority_rows": metadata.get("merged_priority_rows"),
            "kingdom_filter_applied": metadata.get("kingdom_filter_applied"),
            "note": "Top species per cell summarized from GBIF-mediated occurrence records joined to the 5 km EKDI grid.",
            "limitation": metadata.get("limitation"),
        },
        "cells": cells,
    }
    top10_path.parent.mkdir(parents=True, exist_ok=True)
    top10_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return output["metadata"]


def build_lightweight_priority_species(
    full_path: Path = OUTPUT,
    output_path: Path = TOP5_PRIORITY_OUTPUT,
    allowed_classes: set[str] | None = None,
    max_species: int = 5,
) -> dict[str, Any]:
    if not full_path.exists():
        raise FileNotFoundError(f"Missing full cell species records file: {full_path}")
    allowed_classes = allowed_classes or {"critical", "deficient", "unsurveyed"}
    metadata = read_full_metadata(full_path)
    priority_classes = load_priority_cell_classes()
    target_cells = {cell_id: cls for cell_id, cls in priority_classes.items() if cls in allowed_classes}
    cells: dict[str, dict[str, Any]] = {}
    represented_species: set[str] = set()
    source_rows_scanned = 0
    source_rows_in_scope = 0

    for row in iter_full_records(full_path):
        source_rows_scanned += 1
        cell_id = norm_cell_id(row.get("cell_id"))
        if not cell_id or cell_id not in target_cells:
            continue
        source_rows_in_scope += 1
        cell = cells.setdefault(
            cell_id,
            {
                "cell_id": cell_id,
                "priority_class": target_cells[cell_id],
                "total_species": 0,
                "total_records": 0,
                "species": [],
            },
        )
        cell["total_species"] += 1
        try:
            cell["total_records"] += int(row.get("record_count") or 0)
        except (TypeError, ValueError):
            pass
        current = cell["species"]
        current.append(clean_contest_species_record(row))
        current.sort(key=sort_key)
        if len(current) > max_species:
            current.pop()

    class_counts = Counter(cell["priority_class"] for cell in cells.values())
    for cell in cells.values():
        cell["species"].sort(key=sort_key)
        for row in cell["species"]:
            name = normalize_species_key(row.get("scientificName"))
            if name:
                represented_species.add(name)

    output = {
        "metadata": {
            "source": "cell_species_records.json",
            "created": datetime.now(timezone.utc).isoformat(),
            "current_year": CURRENT_YEAR,
            "target": "contest_ui_priority_cells",
            "allowed_classes": sorted(allowed_classes),
            "class_counts": dict(class_counts),
            "cells_covered": len(cells),
            "max_species_per_cell": max_species,
            "unique_species_represented": len(represented_species),
            "total_rows_source": metadata.get("rows", source_rows_scanned),
            "source_rows_in_scope": source_rows_in_scope,
            "raw_gbif_records": metadata.get("raw_gbif_records"),
            "merged_priority_rows": metadata.get("merged_priority_rows"),
            "kingdom_filter_applied": metadata.get("kingdom_filter_applied"),
            "note": "Lightweight contest UI table with prioritized GBIF-mediated species evidence for selected EKDI cells.",
            "limitation": "Prioritized subset for fast display, not the full floristic inventory. Large full tables are local reproducibility artifacts and are not loaded by default.",
        },
        "cells": cells,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return output["metadata"]


def build_lightweight_priority_species_from_top10(
    top10_path: Path = TOP10_OUTPUT,
    output_path: Path = TOP5_PRIORITY_OUTPUT,
    allowed_classes: set[str] | None = None,
    max_species: int = 5,
) -> dict[str, Any]:
    if not top10_path.exists():
        raise FileNotFoundError(f"Missing top10 source file: {top10_path}")
    allowed_classes = allowed_classes or {"critical", "deficient", "unsurveyed"}
    top10 = load_json(top10_path, {})
    source_metadata = top10.get("metadata") or {}
    source_cells = top10.get("cells") or {}
    priority_classes = load_priority_cell_classes()
    cells: dict[str, dict[str, Any]] = {}
    represented_species: set[str] = set()

    for cell_id, cell in source_cells.items():
        cls = priority_classes.get(cell_id)
        if cls not in allowed_classes:
            continue
        species_rows = []
        for row in (cell.get("top_species") or [])[:max_species]:
            cleaned = clean_contest_species_record(row)
            if cleaned:
                species_rows.append(cleaned)
                name = normalize_species_key(cleaned.get("scientificName"))
                if name:
                    represented_species.add(name)
        if not species_rows:
            continue
        cells[cell_id] = {
            "cell_id": cell_id,
            "priority_class": cls,
            "total_species": cell.get("total_species", len(species_rows)),
            "total_records": cell.get("total_records", 0),
            "species": species_rows,
        }

    class_counts = Counter(cell["priority_class"] for cell in cells.values())
    output = {
        "metadata": {
            "source": "cell_species_records.json via cell_species_top10_by_cell.json",
            "created": datetime.now(timezone.utc).isoformat(),
            "current_year": CURRENT_YEAR,
            "target": "contest_ui_priority_cells",
            "allowed_classes": sorted(allowed_classes),
            "class_counts": dict(class_counts),
            "cells_covered": len(cells),
            "max_species_per_cell": max_species,
            "unique_species_represented": len(represented_species),
            "unique_species_source": source_metadata.get("unique_species_source"),
            "total_rows_source": source_metadata.get("total_rows_source"),
            "raw_gbif_records": source_metadata.get("raw_gbif_records"),
            "merged_priority_rows": source_metadata.get("merged_priority_rows"),
            "kingdom_filter_applied": source_metadata.get("kingdom_filter_applied"),
            "note": "Lightweight contest UI table with prioritized GBIF-mediated species evidence for selected EKDI cells.",
            "limitation": "Prioritized subset for fast display, not the full floristic inventory. Large full tables are local reproducibility artifacts and are not loaded by default.",
        },
        "cells": cells,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    return output["metadata"]


def main() -> int:
    if "--top10-only" in sys.argv:
        top10_metadata = build_top10_by_cell(OUTPUT, TOP10_OUTPUT)
        print(json.dumps({"top10": top10_metadata}, indent=2, ensure_ascii=False))
        print(f"Wrote {TOP10_OUTPUT}")
        return 0
    if "--contest-lightweight" in sys.argv:
        metadata = build_lightweight_priority_species_from_top10() if TOP10_OUTPUT.exists() else build_lightweight_priority_species()
        print(json.dumps({"contest_lightweight": metadata}, indent=2, ensure_ascii=False))
        print(f"Wrote {TOP5_PRIORITY_OUTPUT}")
        if TOP5_PRIORITY_OUTPUT.stat().st_size > 15 * 1024 * 1024:
            critical_metadata = build_lightweight_priority_species_from_top10(
                output_path=TOP3_CRITICAL_OUTPUT,
                allowed_classes={"critical"},
                max_species=3,
            ) if TOP10_OUTPUT.exists() else build_lightweight_priority_species(output_path=TOP3_CRITICAL_OUTPUT, allowed_classes={"critical"}, max_species=3)
            print(json.dumps({"contest_lightweight_fallback": critical_metadata}, indent=2, ensure_ascii=False))
            print(f"Wrote {TOP3_CRITICAL_OUTPUT}")
        return 0
    if not GBIF_JOINED.exists():
        raise FileNotFoundError(f"Missing source file: {GBIF_JOINED}")
    raw_rows, columns, reader = read_parquet(GBIF_JOINED)
    records, stats = build_records(raw_rows, columns)
    write_column_report(columns, stats["detected"], reader, len(raw_rows))
    records, merge_stats = merge_priority(records)
    assign_display_ranks(records)
    records.sort(key=lambda row: (row["cell_id"], row.get("display_rank", 999999)))
    output = build_output(records, stats, merge_stats, reader)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    top10_metadata = build_top10_by_cell(OUTPUT, TOP10_OUTPUT)

    print(json.dumps(output["metadata"], indent=2, ensure_ascii=False))
    print(json.dumps({"top10": top10_metadata}, indent=2, ensure_ascii=False))
    print(f"Wrote {OUTPUT}")
    print(f"Wrote {TOP10_OUTPUT}")
    print(f"Wrote {COLUMN_REPORT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        write_failure_report(str(exc))
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
