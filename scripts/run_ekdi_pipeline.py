"""Configurable EKDI pipeline entry point.

This public entry point is configuration-driven and intentionally honest about
what can and cannot be reproduced from the public repository alone.

Usage:
    python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json
    python scripts/run_ekdi_pipeline.py --config configs/atlantic_forest.json --check-inputs

The script prefers existing analytical component columns when they already
exist in the configured grid. It does not invent missing values and does not
overwrite shipped app outputs unless the configuration explicitly allows it.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_INPUT_MANIFEST = "docs/data_sources.md"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "ekdi_runs"
CURRENT_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"

WEIGHT_KEYS = (
    "sampling_antiquity",
    "post_record_forest_loss",
    "richness_deficit",
)
CONFIG_REQUIRED_KEYS = (
    "project_name",
    "biome_name",
    "grid_resolution_km",
    "current_year",
    "weights",
    "thresholds",
    "inputs",
    "outputs",
    "overwrite_existing_outputs",
)
CONFIG_REQUIRED_INPUT_KEYS = (
    "grid",
    "gbif_joined",
    "endemism_grid",
    "ghost_species",
    "extinction_risk_analysis",
)
CONFIG_REQUIRED_OUTPUT_KEYS = (
    "priority_cells",
    "state_summary",
    "scientific_report",
)
CONFIG_OPTIONAL_INPUT_KEYS = (
    "forest_loss_grid",
    "richness_deficit_grid",
)

CELL_ID_ALIASES = ("cell_id", "id", "grid_id", "cell", "id_cell")
STATE_ALIASES = ("stateName", "state_name", "state", "estado", "uf")
LAST_RECORD_ALIASES = (
    "ultimo_registro",
    "last_record",
    "last_record_year",
    "last_year",
    "year_last_record",
    "last",
)
YEARS_SILENT_ALIASES = (
    "years_since_last_record",
    "years_silent",
    "years_since_record",
    "years",
)
FOREST_REMAINING_ALIASES = (
    "forest_cover_pct",
    "forest_remaining_pct",
    "forest_remaining",
    "forest",
)
SAMPLING_NORM_ALIASES = (
    "sampling_antiquity_norm",
    "antiguedad_norm",
    "sampling_norm",
)
POST_LOSS_NORM_ALIASES = (
    "post_record_loss_norm",
    "perdida_norm",
    "forest_loss_norm",
)
RICHNESS_NORM_ALIASES = (
    "richness_deficit_norm",
    "deficit_norm",
)
POST_LOSS_RAW_ALIASES = (
    "perdida_ha",
    "post_record_forest_loss_ha",
    "post_record_loss_ha",
    "forest_loss_ha",
    "loss",
)
RICHNESS_RAW_ALIASES = (
    "deficit_riqueza",
    "richness_deficit",
    "richness_gap",
    "deficit",
)


class ConfigError(ValueError):
    """Raised when the config file is invalid."""


class PipelineBlockedError(RuntimeError):
    """Raised when configured inputs are insufficient for a requested run."""


@dataclass
class ComponentResult:
    values: Any
    used_existing_columns: list[str]
    caveats: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configurable EKDI pipeline")
    parser.add_argument("--config", required=True, help="Path to a JSON config file.")
    parser.add_argument(
        "--check-inputs",
        action="store_true",
        help="Validate config and inputs without computing outputs.",
    )
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_slug() -> str:
    return utc_now().strftime(CURRENT_TIMESTAMP_FORMAT)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "ekdi_run"


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def make_relative_display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_config(path: str) -> dict[str, Any]:
    config_path = repo_path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON config: {exc}") from exc
    if not isinstance(config, dict):
        raise ConfigError("Config root must be a JSON object.")
    config["_config_path"] = str(config_path)
    return config


def validate_config(config: dict[str, Any]) -> None:
    errors: list[str] = []

    for key in CONFIG_REQUIRED_KEYS:
        if key not in config:
            errors.append(f"Missing required config key: {key}")

    weights = config.get("weights")
    if not isinstance(weights, dict):
        errors.append("weights must be an object.")
    else:
        for key in WEIGHT_KEYS:
            value = weights.get(key)
            if not isinstance(value, (int, float)):
                errors.append(f"weights.{key} must be numeric.")

    thresholds = config.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("thresholds must be an object.")
    else:
        critical_percentile = thresholds.get("critical_percentile")
        if not isinstance(critical_percentile, (int, float)):
            errors.append("thresholds.critical_percentile must be numeric.")
        elif not 0 < float(critical_percentile) < 1:
            errors.append("thresholds.critical_percentile must be between 0 and 1.")

    inputs = config.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("inputs must be an object.")
    else:
        for key in CONFIG_REQUIRED_INPUT_KEYS:
            if not isinstance(inputs.get(key), str) or not inputs.get(key).strip():
                errors.append(f"inputs.{key} must be a non-empty string path.")
        for key in CONFIG_OPTIONAL_INPUT_KEYS:
            value = inputs.get(key)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                errors.append(f"inputs.{key} must be a non-empty string path when provided.")

    outputs = config.get("outputs")
    if not isinstance(outputs, dict):
        errors.append("outputs must be an object.")
    else:
        for key in CONFIG_REQUIRED_OUTPUT_KEYS:
            if not isinstance(outputs.get(key), str) or not outputs.get(key).strip():
                errors.append(f"outputs.{key} must be a non-empty string path.")

    if not isinstance(config.get("project_name"), str) or not config.get("project_name", "").strip():
        errors.append("project_name must be a non-empty string.")
    if not isinstance(config.get("biome_name"), str) or not config.get("biome_name", "").strip():
        errors.append("biome_name must be a non-empty string.")
    if not isinstance(config.get("grid_resolution_km"), (int, float)) or float(config["grid_resolution_km"]) <= 0:
        errors.append("grid_resolution_km must be a positive number.")
    if not isinstance(config.get("current_year"), int):
        errors.append("current_year must be an integer.")
    if not isinstance(config.get("overwrite_existing_outputs"), bool):
        errors.append("overwrite_existing_outputs must be true or false.")

    if errors:
        raise ConfigError("\n".join(errors))


def check_inputs(config: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, str] = {}
    missing: dict[str, str] = {}
    for key, raw_path in config["inputs"].items():
        if raw_path in (None, ""):
            continue
        resolved = repo_path(raw_path)
        display_path = make_relative_display(resolved)
        if resolved.exists():
            found[key] = display_path
        else:
            missing[key] = display_path
    return {
        "found": found,
        "missing": missing,
        "all": {
            key: {
                "configured_path": raw_path,
                "resolved_path": make_relative_display(repo_path(raw_path)),
                "exists": repo_path(raw_path).exists(),
            }
            for key, raw_path in config["inputs"].items()
            if raw_path not in (None, "")
        },
    }


def import_runtime() -> tuple[Any, Any]:
    try:
        import geopandas as gpd  # type: ignore
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise PipelineBlockedError(
            "Full EKDI computation requires geopandas and pandas in the local environment."
        ) from exc
    return gpd, pd


def find_column(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    lookup = {column.lower(): column for column in columns}
    for alias in aliases:
        found = lookup.get(alias.lower())
        if found:
            return found
    return None


def clean_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def normalize_components(values: Any) -> tuple[Any, list[str]]:
    non_null = values.dropna()
    caveats: list[str] = []
    if non_null.empty:
        raise PipelineBlockedError("Component normalization failed because all component values are null.")
    minimum = float(non_null.min())
    maximum = float(non_null.max())
    if math.isclose(minimum, maximum):
        caveats.append("Component values were constant; normalized values were set to 0.0.")
        return values.apply(lambda value: 0.0 if clean_number(value) is not None else None), caveats
    normalized = values.apply(
        lambda value: None
        if clean_number(value) is None
        else (float(clean_number(value)) - minimum) / (maximum - minimum)
    )
    return normalized, caveats


def read_gbif_last_record_by_cell(parquet_path: Path) -> dict[str, int]:
    _, pd = import_runtime()
    frame = pd.read_parquet(parquet_path)
    columns = [str(column) for column in frame.columns]
    cell_column = find_column(columns, CELL_ID_ALIASES)
    year_column = find_column(columns, ("year", "eventDate", "event_year"))
    if not cell_column or not year_column:
        raise PipelineBlockedError(
            "gbif_joined exists but is missing a cell_id or year/eventDate column needed for sampling antiquity."
        )
    frame = frame[[cell_column, year_column]].copy()
    if year_column != "year":
        frame["year"] = frame[year_column].astype(str).str.extract(r"(1[6-9]\d{2}|20\d{2}|21\d{2})")[0]
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    else:
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame[cell_column] = frame[cell_column].astype(str).str.strip()
    frame = frame.dropna(subset=[cell_column, "year"])
    if frame.empty:
        return {}
    latest = frame.groupby(cell_column)["year"].max().dropna()
    return {str(cell_id): int(year) for cell_id, year in latest.items()}


def load_auxiliary_mapping(path: Path, value_aliases: tuple[str, ...]) -> tuple[dict[str, float], str]:
    gpd, pd = import_runtime()
    suffix = path.suffix.lower()
    if suffix in {".gpkg", ".geojson", ".json"}:
        frame = gpd.read_file(path)
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix == ".parquet":
        frame = pd.read_parquet(path)
    else:
        raise PipelineBlockedError(f"Unsupported auxiliary input format: {path.name}")

    columns = [str(column) for column in frame.columns]
    cell_column = find_column(columns, CELL_ID_ALIASES)
    value_column = find_column(columns, value_aliases)
    if not cell_column or not value_column:
        raise PipelineBlockedError(
            f"{path.name} exists but does not expose both a cell identifier and a component column."
        )
    mapping: dict[str, float] = {}
    for _, row in frame.iterrows():
        cell_id = str(row[cell_column]).strip()
        value = clean_number(row[value_column])
        if cell_id and value is not None:
            mapping[cell_id] = value
    return mapping, value_column


def compute_sampling_antiquity(grid: Any, current_year: int, inputs: dict[str, Any]) -> ComponentResult:
    columns = [str(column) for column in grid.columns]
    existing_column = find_column(columns, SAMPLING_NORM_ALIASES)
    if existing_column:
        return ComponentResult(
            values=grid[existing_column],
            used_existing_columns=[existing_column],
            caveats=["Sampling Antiquity used an existing normalized grid column."],
        )

    years_column = find_column(columns, YEARS_SILENT_ALIASES)
    if years_column:
        normalized, caveats = normalize_components(grid[years_column].apply(clean_number))
        return ComponentResult(values=normalized, used_existing_columns=[years_column], caveats=caveats)

    last_record_column = find_column(columns, LAST_RECORD_ALIASES)
    if last_record_column:
        years_silent = grid[last_record_column].apply(
            lambda value: None if clean_number(value) is None else current_year - int(clean_number(value))
        )
        normalized, caveats = normalize_components(years_silent)
        return ComponentResult(values=normalized, used_existing_columns=[last_record_column], caveats=caveats)

    gbif_path_text = inputs.get("gbif_joined")
    if not gbif_path_text:
        raise PipelineBlockedError(
            "Sampling Antiquity could not be computed because the grid has no usable last-record fields and no gbif_joined input was configured."
        )
    gbif_path = repo_path(gbif_path_text)
    if not gbif_path.exists():
        raise PipelineBlockedError(
            "Sampling Antiquity could not be computed because the grid has no usable last-record fields and the configured gbif_joined file is missing."
        )

    cell_column = find_column(columns, CELL_ID_ALIASES)
    if not cell_column:
        raise PipelineBlockedError("Grid file is missing a cell identifier column required for Sampling Antiquity.")
    last_record_by_cell = read_gbif_last_record_by_cell(gbif_path)
    years_silent = grid[cell_column].apply(
        lambda value: None
        if last_record_by_cell.get(str(value).strip()) is None
        else current_year - int(last_record_by_cell[str(value).strip()])
    )
    normalized, caveats = normalize_components(years_silent)
    caveats.append("Sampling Antiquity was derived from the configured gbif_joined table.")
    return ComponentResult(values=normalized, used_existing_columns=[], caveats=caveats)


def compute_post_record_loss(grid: Any, inputs: dict[str, Any]) -> ComponentResult:
    columns = [str(column) for column in grid.columns]
    existing_column = find_column(columns, POST_LOSS_NORM_ALIASES)
    if existing_column:
        return ComponentResult(
            values=grid[existing_column],
            used_existing_columns=[existing_column],
            caveats=["Post-Record Forest Loss used an existing normalized grid column."],
        )

    raw_column = find_column(columns, POST_LOSS_RAW_ALIASES)
    if raw_column:
        normalized, caveats = normalize_components(grid[raw_column].apply(clean_number))
        return ComponentResult(values=normalized, used_existing_columns=[raw_column], caveats=caveats)

    aux_path_text = inputs.get("forest_loss_grid")
    if not aux_path_text:
        raise PipelineBlockedError(
            "Post-Record Forest Loss could not be computed because neither grid columns nor a forest_loss_grid input were available."
        )
    aux_path = repo_path(aux_path_text)
    if not aux_path.exists():
        raise PipelineBlockedError(
            "Post-Record Forest Loss could not be computed because the configured forest_loss_grid file is missing."
        )

    cell_column = find_column(columns, CELL_ID_ALIASES)
    if not cell_column:
        raise PipelineBlockedError("Grid file is missing a cell identifier column required for Post-Record Forest Loss.")
    loss_by_cell, source_column = load_auxiliary_mapping(aux_path, POST_LOSS_RAW_ALIASES + POST_LOSS_NORM_ALIASES)
    raw_values = grid[cell_column].apply(lambda value: loss_by_cell.get(str(value).strip()))
    normalized, caveats = normalize_components(raw_values)
    caveats.append(
        f"Post-Record Forest Loss was joined from {make_relative_display(aux_path)} using column {source_column}."
    )
    return ComponentResult(values=normalized, used_existing_columns=[], caveats=caveats)


def compute_richness_deficit(grid: Any, inputs: dict[str, Any]) -> ComponentResult:
    columns = [str(column) for column in grid.columns]
    existing_column = find_column(columns, RICHNESS_NORM_ALIASES)
    if existing_column:
        return ComponentResult(
            values=grid[existing_column],
            used_existing_columns=[existing_column],
            caveats=["Richness Deficit used an existing normalized grid column."],
        )

    raw_column = find_column(columns, RICHNESS_RAW_ALIASES)
    if raw_column:
        normalized, caveats = normalize_components(grid[raw_column].apply(clean_number))
        return ComponentResult(values=normalized, used_existing_columns=[raw_column], caveats=caveats)

    aux_path_text = inputs.get("richness_deficit_grid")
    if not aux_path_text:
        raise PipelineBlockedError(
            "Richness Deficit could not be computed because neither grid columns nor a richness_deficit_grid input were available."
        )
    aux_path = repo_path(aux_path_text)
    if not aux_path.exists():
        raise PipelineBlockedError(
            "Richness Deficit could not be computed because the configured richness_deficit_grid file is missing."
        )

    cell_column = find_column(columns, CELL_ID_ALIASES)
    if not cell_column:
        raise PipelineBlockedError("Grid file is missing a cell identifier column required for Richness Deficit.")
    deficit_by_cell, source_column = load_auxiliary_mapping(aux_path, RICHNESS_RAW_ALIASES + RICHNESS_NORM_ALIASES)
    raw_values = grid[cell_column].apply(lambda value: deficit_by_cell.get(str(value).strip()))
    normalized, caveats = normalize_components(raw_values)
    caveats.append(
        f"Richness Deficit was joined from {make_relative_display(aux_path)} using column {source_column}."
    )
    return ComponentResult(values=normalized, used_existing_columns=[], caveats=caveats)


def compute_ekdi_score(
    sampling_antiquity: Any,
    post_record_forest_loss: Any,
    richness_deficit: Any,
    weights: dict[str, float],
) -> Any:
    return (
        sampling_antiquity.fillna(0) * float(weights["sampling_antiquity"])
        + post_record_forest_loss.fillna(0) * float(weights["post_record_forest_loss"])
        + richness_deficit.fillna(0) * float(weights["richness_deficit"])
    )


def classify_priority_cells(scores: Any, critical_percentile: float) -> tuple[Any, float]:
    valid_scores = scores.dropna()
    if valid_scores.empty:
        raise PipelineBlockedError("Priority classification failed because EKDI scores are all null.")
    threshold = float(valid_scores.quantile(float(critical_percentile)))
    classes = scores.apply(
        lambda value: None
        if clean_number(value) is None
        else ("Critical Gap" if float(value) >= threshold else "Review Priority")
    )
    return classes, threshold


def summarize_state_counts(grid: Any, state_column: str | None) -> list[dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    if state_column is None:
        return []
    for _, row in grid.iterrows():
        state_value = str(row[state_column]).strip() if row[state_column] is not None else "Unknown"
        summary = summaries.setdefault(
            state_value,
            {
                "state_name": state_value,
                "total_cells": 0,
                "critical_gaps": 0,
                "mean_ekdi_score": [],
            },
        )
        summary["total_cells"] += 1
        if row.get("priority_class") == "Critical Gap":
            summary["critical_gaps"] += 1
        if clean_number(row.get("ekdi_score")) is not None:
            summary["mean_ekdi_score"].append(float(row["ekdi_score"]))
    output: list[dict[str, Any]] = []
    for value in summaries.values():
        output.append(
            {
                "state_name": value["state_name"],
                "total_cells": value["total_cells"],
                "critical_gaps": value["critical_gaps"],
                "mean_ekdi_score": round(mean(value["mean_ekdi_score"]), 6)
                if value["mean_ekdi_score"]
                else None,
            }
        )
    output.sort(key=lambda row: (-row["critical_gaps"], row["state_name"]))
    return output


def scientific_report_payload(
    config: dict[str, Any],
    grid: Any,
    threshold_value: float,
    existing_component_columns_used: list[str],
    caveats: list[str],
) -> dict[str, Any]:
    critical_count = int((grid["priority_class"] == "Critical Gap").sum())
    state_column = find_column([str(column) for column in grid.columns], STATE_ALIASES)
    return {
        "generated_at": utc_now().isoformat(),
        "project_name": config["project_name"],
        "biome_name": config["biome_name"],
        "grid_resolution_km": config["grid_resolution_km"],
        "current_year": config["current_year"],
        "weights": config["weights"],
        "critical_percentile": config["thresholds"]["critical_percentile"],
        "critical_threshold_score": threshold_value,
        "total_cells": int(len(grid)),
        "critical_gap_cells": critical_count,
        "review_priority_cells": int((grid["priority_class"] == "Review Priority").sum()),
        "ekdi_score_summary": {
            "min": round(float(grid["ekdi_score"].min()), 6),
            "max": round(float(grid["ekdi_score"].max()), 6),
            "mean": round(float(grid["ekdi_score"].mean()), 6),
        },
        "existing_component_columns_used": existing_component_columns_used,
        "state_summary_rows": len(summarize_state_counts(grid, state_column)),
        "provenance": config.get("provenance", {}),
        "caveats": caveats,
    }


def clean_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    text = str(value)
    return text


def geojson_from_grid(grid: Any, columns: list[str]) -> dict[str, Any]:
    from shapely.geometry import mapping  # type: ignore

    features = []
    for _, row in grid.iterrows():
        properties = {column: clean_json_value(row[column]) for column in columns if column in grid.columns}
        geometry = None if row.geometry is None or row.geometry.is_empty else mapping(row.geometry)
        feature = {"type": "Feature", "properties": properties, "geometry": geometry}
        cell_id = properties.get("cell_id")
        if cell_id:
            feature["id"] = cell_id
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def determine_run_directory(config: dict[str, Any], run_id: str) -> Path:
    if bool(config["overwrite_existing_outputs"]):
        return repo_path("outputs") / "latest_overwrite_run"
    return DEFAULT_OUTPUT_ROOT / run_id


def resolve_output_targets(config: dict[str, Any], run_dir: Path) -> dict[str, Path]:
    targets: dict[str, Path] = {}
    overwrite = bool(config["overwrite_existing_outputs"])
    for key, relative_path in config["outputs"].items():
        resolved = repo_path(relative_path)
        if overwrite:
            targets[key] = resolved
        else:
            targets[key] = run_dir / Path(relative_path)
    return targets


def write_outputs(
    grid: Any,
    config: dict[str, Any],
    run_dir: Path,
    threshold_value: float,
    existing_component_columns_used: list[str],
    caveats: list[str],
) -> list[str]:
    state_column = find_column([str(column) for column in grid.columns], STATE_ALIASES)
    targets = resolve_output_targets(config, run_dir)
    priority_columns = [
        column
        for column in [
            find_column([str(col) for col in grid.columns], CELL_ID_ALIASES),
            state_column,
            find_column([str(col) for col in grid.columns], FOREST_REMAINING_ALIASES),
            find_column([str(col) for col in grid.columns], LAST_RECORD_ALIASES),
            "sampling_antiquity_norm",
            "post_record_forest_loss_norm",
            "richness_deficit_norm",
            "ekdi_score",
            "priority_class",
        ]
        if column
    ]
    priority_geojson = geojson_from_grid(grid, priority_columns)
    write_json(targets["priority_cells"], priority_geojson)

    state_summary = summarize_state_counts(grid, state_column)
    write_json(
        targets["state_summary"],
        {
            "generated_at": utc_now().isoformat(),
            "project_name": config["project_name"],
            "biome_name": config["biome_name"],
            "states": state_summary,
        },
    )

    scientific_report = scientific_report_payload(
        config=config,
        grid=grid,
        threshold_value=threshold_value,
        existing_component_columns_used=existing_component_columns_used,
        caveats=caveats,
    )
    write_json(targets["scientific_report"], scientific_report)

    created = [make_relative_display(path) for path in targets.values()]
    return created


def write_run_report(run_dir: Path, report: dict[str, Any]) -> None:
    write_json(run_dir / "run_report.json", report)
    markdown_lines = [
        "# EKDI Pipeline Run Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Project: `{report['project_name']}`",
        f"- Biome: `{report['biome_name']}`",
        f"- Config: `{report['config_path']}`",
        f"- Check inputs only: `{report['check_inputs_only']}`",
        f"- Full recomputation ran: `{report['full_recomputation_ran']}`",
        f"- Existing component columns used: `{', '.join(report['existing_component_columns_used']) or 'none'}`",
        "",
        "## Weights",
        "",
    ]
    for key, value in report["weights"].items():
        markdown_lines.append(f"- `{key}`: `{value}`")
    markdown_lines.extend(["", "## Input files found", ""])
    found = report["input_files_found"] or []
    for item in found:
        markdown_lines.append(f"- `{item}`")
    if not found:
        markdown_lines.append("- none")
    markdown_lines.extend(["", "## Input files missing", ""])
    missing = report["input_files_missing"] or []
    for item in missing:
        markdown_lines.append(f"- `{item}`")
    if not missing:
        markdown_lines.append("- none")
    markdown_lines.extend(["", "## Output files created", ""])
    created = report["output_files_created"] or []
    for item in created:
        markdown_lines.append(f"- `{item}`")
    if not created:
        markdown_lines.append("- none")
    markdown_lines.extend(["", "## Caveats", ""])
    for item in report["caveats"]:
        markdown_lines.append(f"- {item}")
    write_markdown(run_dir / "run_report.md", "\n".join(markdown_lines) + "\n")


def prepare_run_report_base(
    config: dict[str, Any],
    check_result: dict[str, Any],
    check_inputs_only: bool,
) -> dict[str, Any]:
    return {
        "generated_at": utc_now().isoformat(),
        "project_name": config["project_name"],
        "biome_name": config["biome_name"],
        "config_path": make_relative_display(Path(config["_config_path"])),
        "check_inputs_only": check_inputs_only,
        "grid_resolution_km": config["grid_resolution_km"],
        "weights": deepcopy(config["weights"]),
        "input_files_found": sorted(check_result["found"].values()),
        "input_files_missing": sorted(check_result["missing"].values()),
        "full_recomputation_ran": False,
        "existing_component_columns_used": [],
        "output_files_created": [],
        "caveats": [],
        "config_used": {
            key: value
            for key, value in config.items()
            if not key.startswith("_")
        },
    }


def load_grid(config: dict[str, Any]) -> Any:
    gpd, _ = import_runtime()
    grid_path = repo_path(config["inputs"]["grid"])
    if not grid_path.exists():
        raise PipelineBlockedError(
            "EKDI pipeline cannot run full recomputation because the configured grid file is missing."
        )
    return gpd.read_file(grid_path)


def enrich_grid_for_outputs(grid: Any, config: dict[str, Any]) -> Any:
    columns = [str(column) for column in grid.columns]
    cell_column = find_column(columns, CELL_ID_ALIASES)
    if not cell_column:
        raise PipelineBlockedError("Grid file is missing a usable cell identifier column.")
    if cell_column != "cell_id":
        grid["cell_id"] = grid[cell_column].astype(str)
    state_column = find_column(columns + ["cell_id"], STATE_ALIASES)
    if state_column and state_column != "state_name":
        grid["state_name"] = grid[state_column]
    last_record_column = find_column(columns + ["cell_id"], LAST_RECORD_ALIASES)
    if last_record_column and last_record_column != "last_record_year":
        grid["last_record_year"] = grid[last_record_column]
    forest_column = find_column(columns + ["cell_id"], FOREST_REMAINING_ALIASES)
    if forest_column and forest_column != "forest_remaining_pct":
        grid["forest_remaining_pct"] = grid[forest_column]
    return grid


def write_failure_console(check_result: dict[str, Any]) -> None:
    print("EKDI pipeline cannot run full recomputation.")
    print("Missing configured inputs:")
    for path in sorted(check_result["missing"].values()):
        print(f"- {path}")
    print(f"See {DOCS_INPUT_MANIFEST} for required inputs.")


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
        validate_config(config)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    run_id = f"{slugify(config['project_name'])}_{timestamp_slug()}"
    run_dir = determine_run_directory(config, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    check_result = check_inputs(config)
    report = prepare_run_report_base(config, check_result, args.check_inputs)

    if args.check_inputs:
        report["caveats"].append("No computation executed because --check-inputs was used.")
        if check_result["missing"]:
            report["caveats"].append(
                "Some configured inputs are missing. Full recomputation remains blocked until those files are provided."
            )
        write_run_report(run_dir, report)
        print(f"Config: {make_relative_display(Path(config['_config_path']))}")
        print("Input validation only. No computation executed.")
        print("Found inputs:")
        for path in sorted(check_result["found"].values()):
            print(f"- {path}")
        if not check_result["found"]:
            print("- none")
        print("Missing inputs:")
        for path in sorted(check_result["missing"].values()):
            print(f"- {path}")
        if not check_result["missing"]:
            print("- none")
        print(f"Run report written to {make_relative_display(run_dir / 'run_report.json')}")
        return 0

    try:
        grid = enrich_grid_for_outputs(load_grid(config), config)
        sampling = compute_sampling_antiquity(grid, config["current_year"], config["inputs"])
        post_loss = compute_post_record_loss(grid, config["inputs"])
        richness = compute_richness_deficit(grid, config["inputs"])

        grid["sampling_antiquity_norm"] = sampling.values
        grid["post_record_forest_loss_norm"] = post_loss.values
        grid["richness_deficit_norm"] = richness.values
        grid["ekdi_score"] = compute_ekdi_score(
            sampling_antiquity=grid["sampling_antiquity_norm"],
            post_record_forest_loss=grid["post_record_forest_loss_norm"],
            richness_deficit=grid["richness_deficit_norm"],
            weights=config["weights"],
        )
        grid["priority_class"], threshold_value = classify_priority_cells(
            grid["ekdi_score"], config["thresholds"]["critical_percentile"]
        )

        component_columns_used = (
            sampling.used_existing_columns
            + post_loss.used_existing_columns
            + richness.used_existing_columns
        )
        caveats = sampling.caveats + post_loss.caveats + richness.caveats
        created_outputs = write_outputs(
            grid=grid,
            config=config,
            run_dir=run_dir,
            threshold_value=threshold_value,
            existing_component_columns_used=component_columns_used,
            caveats=caveats,
        )
        report["full_recomputation_ran"] = True
        report["existing_component_columns_used"] = component_columns_used
        report["output_files_created"] = created_outputs
        report["caveats"].extend(caveats)
        if not config["overwrite_existing_outputs"]:
            report["caveats"].append(
                "overwrite_existing_outputs is false, so outputs were written under outputs/ekdi_runs/."
            )
        write_run_report(run_dir, report)
        print("EKDI pipeline run completed.")
        for output in created_outputs:
            print(f"- {output}")
        print(f"Run report written to {make_relative_display(run_dir / 'run_report.json')}")
        return 0
    except PipelineBlockedError as exc:
        report["caveats"].append(str(exc))
        report["caveats"].append(f"See {DOCS_INPUT_MANIFEST} for required inputs.")
        write_run_report(run_dir, report)
        write_failure_console(check_result)
        print(str(exc))
        print(f"Run report written to {make_relative_display(run_dir / 'run_report.json')}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
