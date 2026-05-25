"""Build real cell-level plant candidate tables for the EKDI public app.

The script is intentionally dependency-light. It reads GeoJSON, CSV and
GeoPackage files with the Python standard library, then performs a conservative
point-in-polygon spatial join from plant-bearing critical-gap records to the
dashboard priority-cell polygons.

It never modifies original scientific source files.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
APP_DIR = REPO_ROOT / "app"
DATA_DIR = APP_DIR / "data"

PRIORITY_CELLS = DATA_DIR / "geo" / "priority_cells.geojson"
OUTPUT = DATA_DIR / "tables" / "cell_plant_candidates.json"
STATE_OUTPUT = DATA_DIR / "tables" / "state_plant_context.json"

RAW_DATA = WORKSPACE_ROOT / "data"
GRID_ENDEMICAS = RAW_DATA / "grid_endemicas.gpkg"
EXTINCTION_RISK = RAW_DATA / "extinction_risk_analysis.csv"
GHOST_SPECIES = RAW_DATA / "ghost_species.csv"
GRID_FINAL = RAW_DATA / "grid_final.gpkg"
CRITICAL_TOP100 = RAW_DATA / "critical_gaps_top100.csv"
KNOWLEDGE_GHOSTS = DATA_DIR / "tables" / "knowledge_ghosts.json"
REDISCOVERY = DATA_DIR / "tables" / "rediscovery_candidates.json"

FIELD_DASHES = {"", "-", "—", "–", "nan", "none", "null"}
LINKAGE_RANK = {"direct_cell_id": 3, "spatial_join": 2, "grid_join": 2}


def norm_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in FIELD_DASHES:
        return None
    return text


def norm_cell_id(value: Any) -> str | None:
    return norm_text(value)


def to_number(value: Any) -> float | int | None:
    text = norm_text(value)
    if text is None:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def gpkg_wkb(blob: bytes) -> bytes:
    if blob[:2] != b"GP":
        return blob
    flags = blob[3]
    envelope_indicator = (flags >> 1) & 0b111
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    return blob[8 + envelope_sizes.get(envelope_indicator, 0) :]


def parse_wkb_geometry(wkb: bytes, offset: int = 0) -> tuple[dict[str, Any], int]:
    endian = "<" if wkb[offset] == 1 else ">"
    geom_type = struct.unpack(endian + "I", wkb[offset + 1 : offset + 5])[0]
    base_type = geom_type % 1000
    pos = offset + 5

    if base_type == 1:
        x, y = struct.unpack(endian + "dd", wkb[pos : pos + 16])
        return {"type": "Point", "coordinates": (x, y)}, pos + 16

    if base_type == 3:
        ring_count = struct.unpack(endian + "I", wkb[pos : pos + 4])[0]
        pos += 4
        rings = []
        for _ in range(ring_count):
            point_count = struct.unpack(endian + "I", wkb[pos : pos + 4])[0]
            pos += 4
            ring = []
            for _ in range(point_count):
                x, y = struct.unpack(endian + "dd", wkb[pos : pos + 16])
                pos += 16
                ring.append((x, y))
            rings.append(ring)
        return {"type": "Polygon", "coordinates": rings}, pos

    if base_type == 6:
        polygon_count = struct.unpack(endian + "I", wkb[pos : pos + 4])[0]
        pos += 4
        polygons = []
        for _ in range(polygon_count):
            polygon, pos = parse_wkb_geometry(wkb, pos)
            polygons.append(polygon["coordinates"])
        return {"type": "MultiPolygon", "coordinates": polygons}, pos

    raise ValueError(f"Unsupported WKB geometry type {geom_type}")


def bbox_of_coords(coords: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return min(xs), min(ys), max(xs), max(ys)


def representative_point(geometry: dict[str, Any]) -> tuple[float, float] | None:
    if geometry["type"] == "Point":
        return tuple(geometry["coordinates"])
    if geometry["type"] == "Polygon":
        ring = geometry["coordinates"][0]
    elif geometry["type"] == "MultiPolygon":
        ring = max((poly[0] for poly in geometry["coordinates"] if poly), key=len, default=None)
        if ring is None:
            return None
    else:
        return None

    area = 0.0
    cx = 0.0
    cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(area) > 1e-12:
        area *= 0.5
        return cx / (6 * area), cy / (6 * area)

    minx, miny, maxx, maxy = bbox_of_coords(ring)
    return (minx + maxx) / 2, (miny + maxy) / 2


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersects = (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def point_in_geojson_geometry(lon: float, lat: float, geometry: dict[str, Any]) -> bool:
    if not geometry:
        return False
    if geometry["type"] == "Polygon":
        rings = geometry["coordinates"]
        return bool(rings) and point_in_ring(lon, lat, rings[0]) and not any(point_in_ring(lon, lat, hole) for hole in rings[1:])
    if geometry["type"] == "MultiPolygon":
        return any(point_in_geojson_geometry(lon, lat, {"type": "Polygon", "coordinates": poly}) for poly in geometry["coordinates"])
    return False


def geojson_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    points: list[tuple[float, float]] = []

    def collect(obj: Any) -> None:
        if isinstance(obj, list) and obj and isinstance(obj[0], (int, float)):
            points.append((float(obj[0]), float(obj[1])))
        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    collect(geometry.get("coordinates", []))
    return bbox_of_coords(points)


def load_priority_index() -> tuple[dict[str, dict[str, Any]], dict[tuple[int, int], list[dict[str, Any]]]]:
    data = read_json(PRIORITY_CELLS, {"features": []})
    by_id: dict[str, dict[str, Any]] = {}
    index: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    bin_size = 0.25
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        cell_id = norm_cell_id(props.get("cell_id") or props.get("id"))
        if not cell_id or not feature.get("geometry"):
            continue
        minx, miny, maxx, maxy = geojson_bbox(feature["geometry"])
        record = {"cell_id": cell_id, "props": props, "geometry": feature["geometry"], "bbox": (minx, miny, maxx, maxy)}
        by_id[cell_id] = record
        for ix in range(int(minx / bin_size) - 1, int(maxx / bin_size) + 2):
            for iy in range(int(miny / bin_size) - 1, int(maxy / bin_size) + 2):
                index[(ix, iy)].append(record)
    return by_id, index


def find_cell_for_point(lon: float, lat: float, index: dict[tuple[int, int], list[dict[str, Any]]]) -> dict[str, Any] | None:
    bin_size = 0.25
    key = (int(lon / bin_size), int(lat / bin_size))
    candidates = index.get(key, [])
    for record in candidates:
        minx, miny, maxx, maxy = record["bbox"]
        if minx <= lon <= maxx and miny <= lat <= maxy and point_in_geojson_geometry(lon, lat, record["geometry"]):
            return record
    return None


def parse_species_entries(text: Any) -> list[dict[str, Any]]:
    clean = norm_text(text)
    if clean is None:
        return []
    entries: list[dict[str, Any]] = []
    matches = list(re.finditer(r"([^;|]+?)\s*\(last seen\s*(\d{4})\)", clean, flags=re.I))
    if matches:
        for match in matches:
            species = norm_text(match.group(1))
            if species:
                entries.append({"species": species, "last_record": int(match.group(2))})
        return entries
    for part in re.split(r";|\|", clean):
        species = re.sub(r"\([^)]*\)", "", part).strip()
        if norm_text(species):
            entries.append({"species": species, "last_record": None})
    return entries


def risk_lookup() -> dict[str, dict[str, Any]]:
    rows = read_csv(EXTINCTION_RISK)
    return {row.get("species", "").strip().lower(): row for row in rows if row.get("species")}


def default_action(candidate_type: str) -> str:
    if candidate_type == "Knowledge Ghost":
        return "Voucher review and field verification recommended where access, permits, and habitat context support survey."
    if candidate_type == "Threat Signal":
        return "Voucher review and conservation-status review recommended before field verification."
    return "Voucher review and field verification recommended."


def make_candidate(
    *,
    species: str,
    cell_record: dict[str, Any],
    candidate_type: str,
    evidence_source: str,
    linkage_method: str,
    last_record: Any = None,
    gbif_records: Any = None,
    risk_category: Any = None,
    risk_criterion: Any = None,
    endemic: Any = None,
    threat: Any = None,
    latitude: Any = None,
    longitude: Any = None,
    accepted_name: Any = None,
    recommended_action: Any = None,
    notes: Any = None,
    forest_cover_pct: Any = None,
    perdida_ha: Any = None,
    evidence_completeness: Any = None,
) -> dict[str, Any]:
    props = cell_record.get("props", {})
    return {
        "species": species,
        "accepted_name": norm_text(accepted_name),
        "candidate_type": candidate_type,
        "last_record": to_number(last_record),
        "gbif_records": to_number(gbif_records),
        "risk_category": norm_text(risk_category),
        "risk_criterion": norm_text(risk_criterion),
        "endemic": endemic,
        "threat": norm_text(threat),
        "latitude": to_number(latitude),
        "longitude": to_number(longitude),
        "evidence_source": evidence_source,
        "linkage_method": linkage_method,
        "recommended_action": norm_text(recommended_action) or default_action(candidate_type),
        "notes": norm_text(notes) or "Plant candidate signal only; this does not confirm current presence, absence, rediscovery or extinction.",
        "forest_cover_pct": to_number(forest_cover_pct if forest_cover_pct is not None else props.get("forest_cover_pct")),
        "perdida_ha": to_number(perdida_ha if perdida_ha is not None else props.get("perdida_ha")),
        "evidence_completeness": to_number(evidence_completeness if evidence_completeness is not None else props.get("confianza")),
    }


def merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    existing_rank = LINKAGE_RANK.get(existing.get("linkage_method"), 0)
    incoming_rank = LINKAGE_RANK.get(incoming.get("linkage_method"), 0)
    base, other = (incoming, existing) if incoming_rank > existing_rank else (existing, incoming)
    merged = dict(base)
    for key, value in other.items():
        if merged.get(key) in (None, "", "Not Available") and value not in (None, ""):
            merged[key] = value
    return merged


def main() -> None:
    priority_by_id, priority_index = load_priority_index()
    risk_by_species = risk_lookup()
    by_cell: dict[str, dict[str, Any]] = {}
    excluded = {"species_level_only": 0, "state_level_only": 0, "no_spatial_linkage": 0, "duplicates": 0}
    state_context: dict[str, set[str]] = defaultdict(set)

    def add_to_cell(cell_id: str, candidate: dict[str, Any]) -> None:
        cell_record = priority_by_id[cell_id]
        props = cell_record["props"]
        row = by_cell.setdefault(
            cell_id,
            {
                "cell_id": cell_id,
                "state": props.get("state"),
                "stateName": props.get("stateName"),
                "plant_count": 0,
                "plants": [],
            },
        )
        key = candidate["species"].strip().lower()
        for index, current in enumerate(row["plants"]):
            if current["species"].strip().lower() == key:
                row["plants"][index] = merge_candidate(current, candidate)
                excluded["duplicates"] += 1
                return
        row["plants"].append(candidate)

    # Direct cell-id joins from existing clean Knowledge Ghost data.
    for record in read_json(KNOWLEDGE_GHOSTS, []):
        species = norm_text(record.get("species") or record.get("scientificName") or record.get("taxon"))
        cell_id = norm_cell_id(record.get("cell_id"))
        if not species or not cell_id or cell_id not in priority_by_id:
            excluded["no_spatial_linkage"] += 1
            continue
        risk = risk_by_species.get(species.lower(), {})
        candidate = make_candidate(
            species=species,
            cell_record=priority_by_id[cell_id],
            candidate_type="Knowledge Ghost",
            evidence_source="repo/app/data/tables/knowledge_ghosts.json",
            linkage_method="direct_cell_id",
            last_record=record.get("year") or record.get("ultimo_registro"),
            gbif_records=record.get("n_registros") or risk.get("n_records"),
            risk_category=record.get("risk_categoria") or risk.get("categoria"),
            risk_criterion=record.get("risk_criterio") or risk.get("criterio"),
            latitude=record.get("latitude") or record.get("decimalLatitude"),
            longitude=record.get("longitude") or record.get("decimalLongitude"),
            recommended_action=record.get("recommended_action"),
            notes=record.get("scientific_language_note"),
            forest_cover_pct=record.get("forest_cover_pct"),
            perdida_ha=record.get("perdida_ha"),
            evidence_completeness=record.get("confianza"),
        )
        add_to_cell(cell_id, candidate)

    # Direct cell-id joins from raw ghost_species.csv, if present.
    for record in read_csv(GHOST_SPECIES):
        species = norm_text(record.get("species"))
        cell_id = norm_cell_id(record.get("cell_id"))
        if not species or not cell_id or cell_id not in priority_by_id:
            excluded["no_spatial_linkage"] += 1
            continue
        risk = risk_by_species.get(species.lower(), {})
        candidate = make_candidate(
            species=species,
            cell_record=priority_by_id[cell_id],
            candidate_type="Knowledge Ghost",
            evidence_source="data/ghost_species.csv",
            linkage_method="direct_cell_id",
            last_record=record.get("year") or record.get("ultimo_registro"),
            gbif_records=risk.get("n_records"),
            risk_category=risk.get("categoria"),
            risk_criterion=risk.get("criterio"),
            latitude=record.get("decimalLatitude"),
            longitude=record.get("decimalLongitude"),
            forest_cover_pct=record.get("forest_cover_pct"),
            perdida_ha=record.get("perdida_ha"),
        )
        add_to_cell(cell_id, candidate)

    # Spatial join from grid_endemicas.gpkg plant-bearing records.
    if GRID_ENDEMICAS.exists():
        con = sqlite3.connect(GRID_ENDEMICAS)
        con.row_factory = sqlite3.Row
        rows = con.execute("select * from critical_gaps").fetchall()
        for row in rows:
            entries = parse_species_entries(row["p_erisk"])
            if not entries:
                continue
            try:
                geometry, _ = parse_wkb_geometry(gpkg_wkb(row["geom"]))
                point = representative_point(geometry)
            except Exception:
                point = None
            if point is None:
                excluded["no_spatial_linkage"] += len(entries)
                continue
            lon, lat = point
            cell_record = find_cell_for_point(lon, lat, priority_index)
            if cell_record is None:
                state = norm_text(row["p_estado"])
                if state:
                    for entry in entries:
                        state_context[state].add(entry["species"])
                    excluded["state_level_only"] += len(entries)
                else:
                    excluded["no_spatial_linkage"] += len(entries)
                continue
            cell_id = cell_record["cell_id"]
            for entry in entries:
                species = entry["species"]
                risk = risk_by_species.get(species.lower(), {})
                risk_category = norm_text(risk.get("categoria"))
                candidate_type = "Threat Signal" if risk_category and risk_category.lower() != "not assessed" else "Recorded Plant"
                candidate = make_candidate(
                    species=species,
                    cell_record=cell_record,
                    candidate_type=candidate_type,
                    evidence_source="data/grid_endemicas.gpkg:critical_gaps.p_erisk",
                    linkage_method="spatial_join",
                    last_record=entry.get("last_record") or row["p_ultimo"],
                    gbif_records=risk.get("n_records"),
                    risk_category=risk_category,
                    risk_criterion=risk.get("criterio"),
                    latitude=lat,
                    longitude=lon,
                    forest_cover_pct=row["p_forest"],
                    perdida_ha=row["p_perdida"],
                    evidence_completeness=None,
                    notes="Spatially joined plant evidence from critical-gap geometry; candidate signal only, requiring voucher and taxonomic review.",
                )
                add_to_cell(cell_id, candidate)
        con.close()

    # Species-level-only rediscovery candidates are intentionally excluded from cell tables.
    for record in read_json(REDISCOVERY, []):
        if not norm_cell_id(record.get("cell_id")):
            excluded["species_level_only"] += 1

    output = []
    for cell_id, row in sorted(by_cell.items()):
        row["plants"] = sorted(row["plants"], key=lambda item: (item.get("candidate_type") or "", item["species"]))
        row["plant_count"] = len(row["plants"])
        output.append(row)

    state_output = [
        {"state": state, "species_count": len(species), "species": sorted(species)}
        for state, species in sorted(state_context.items())
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATE_OUTPUT.write_text(json.dumps(state_output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    stats = {
        "cells_with_plant_candidates": len(output),
        "plant_records_linked": sum(row["plant_count"] for row in output),
        "species_deduplicated": excluded["duplicates"],
        "records_excluded": excluded,
        "state_context_records": sum(item["species_count"] for item in state_output),
        "outputs": [str(OUTPUT.relative_to(REPO_ROOT)), str(STATE_OUTPUT.relative_to(REPO_ROOT))],
    }
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
