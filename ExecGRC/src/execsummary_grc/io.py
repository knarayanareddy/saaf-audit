from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .models import Control, Dataset, Risk, SourceRef


SUPPORTED_EXTENSIONS = {".csv", ".json", ".xlsx"}


FIELD_ALIASES = {
    "record_type": ["record_type", "type", "object_type", "category"],
    "id": ["id", "identifier", "reference", "ref"],
    "control_id": ["control_id", "control", "control_code", "control_reference", "control_ref"],
    "risk_id": ["risk_id", "risk", "risk_code", "risk_reference", "risk_ref"],
    "name": ["name", "title", "summary", "description"],
    "effectiveness": [
        "effectiveness",
        "control_effectiveness",
        "control_status",
        "operating_effectiveness",
        "status",
    ],
    "risk_rating": ["risk_rating", "rating", "residual_risk_rating"],
    "residual_score": ["residual_risk_score", "residual_score", "risk_score", "score"],
    "inherent_score": ["inherent_risk_score", "inherent_score"],
    "impact": ["impact", "risk_impact", "residual_impact"],
    "likelihood": ["likelihood", "probability", "chance", "risk_likelihood", "residual_likelihood"],
    "trend": ["trend", "risk_trend", "direction"],
    "department": ["department", "business_unit", "function", "domain"],
    "process": ["process", "process_name", "control_process", "risk_process"],
    "framework": ["framework", "standard", "regulation", "control_framework"],
    "owner": ["owner", "risk_owner", "control_owner", "responsible"],
    "related_control_ids": [
        "related_control_ids",
        "control_ids",
        "linked_controls",
        "mapped_controls",
    ],
    "related_risk_ids": ["related_risk_ids", "risk_ids", "linked_risks", "mapped_risks"],
    "rationale": ["rationale", "reason", "comment", "comments", "notes", "analysis"],
}


RATING_TO_SCORE = {
    "critical": 22.0,
    "very high": 20.0,
    "high": 16.0,
    "medium": 9.0,
    "moderate": 9.0,
    "low": 4.0,
    "minor": 2.0,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(input_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = _discover_files(input_path)
    records: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    for path in files:
        loaded = _load_file(path)
        records.extend(loaded)
        source_files.append(
            {
                "path": _display_path(path),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "records_loaded": len(loaded),
            }
        )
    return records, source_files


def normalize_dataset(records: list[dict[str, Any]], source_files: list[dict[str, Any]]) -> Dataset:
    controls: list[Control] = []
    risks: list[Risk] = []
    skipped_records: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        normalized = {_canonical_column(key): value for key, value in record.items()}
        kind = _infer_record_type(normalized)
        source = SourceRef(
            file=str(record.get("_source_file", "<unknown>")),
            row=str(record.get("_source_row", index)),
        )
        if kind == "control":
            control_id = _first_value(normalized, "control_id") or _first_value(normalized, "id")
            if not control_id:
                control_id = f"CONTROL-{len(controls) + 1:03d}"
            risks_for_control = _split_ids(_first_value(normalized, "related_risk_ids"))
            risk_id_on_row = _first_value(normalized, "risk_id")
            if risk_id_on_row:
                risks_for_control.extend(_split_ids(risk_id_on_row))
            controls.append(
                Control(
                    control_id=control_id,
                    name=_first_value(normalized, "name") or control_id,
                    effectiveness=_first_value(normalized, "effectiveness") or "unknown",
                    owner=_first_value(normalized, "owner"),
                    department=_first_value(normalized, "department"),
                    process=_first_value(normalized, "process"),
                    framework=_first_value(normalized, "framework"),
                    risk_ids=sorted(set(risks_for_control)),
                    rationale=_first_value(normalized, "rationale"),
                    source=source,
                    raw=record,
                )
            )
        elif kind == "risk":
            risk_id = _first_value(normalized, "risk_id") or _first_value(normalized, "id")
            if not risk_id:
                risk_id = f"RISK-{len(risks) + 1:03d}"
            controls_for_risk = _split_ids(_first_value(normalized, "related_control_ids"))
            control_id_on_row = _first_value(normalized, "control_id")
            if control_id_on_row:
                controls_for_risk.extend(_split_ids(control_id_on_row))
            rating = _first_value(normalized, "risk_rating")
            residual_score = _as_float(_first_value(normalized, "residual_score"))
            if residual_score is None and rating:
                residual_score = RATING_TO_SCORE.get(_clean_text(rating), None)
            risks.append(
                Risk(
                    risk_id=risk_id,
                    name=_first_value(normalized, "name") or risk_id,
                    residual_score=residual_score,
                    inherent_score=_as_float(_first_value(normalized, "inherent_score")),
                    impact=_as_float(_first_value(normalized, "impact")),
                    likelihood=_as_float(_first_value(normalized, "likelihood")),
                    rating=rating,
                    owner=_first_value(normalized, "owner"),
                    department=_first_value(normalized, "department"),
                    process=_first_value(normalized, "process"),
                    framework=_first_value(normalized, "framework"),
                    control_ids=sorted(set(controls_for_risk)),
                    trend=_first_value(normalized, "trend"),
                    rationale=_first_value(normalized, "rationale"),
                    source=source,
                    raw=record,
                )
            )
        else:
            skipped_records.append(
                {
                    "source": source.label,
                    "reason": "Record type could not be inferred",
                    "columns": sorted(record.keys()),
                }
            )

    return Dataset(controls=controls, risks=risks, skipped_records=skipped_records, source_files=source_files)


def _discover_files(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(
            path for path in input_path.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input type: {input_path.suffix}")
    return [input_path]


def _load_file(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(path)
    if suffix == ".json":
        return _load_json(path)
    if suffix == ".xlsx":
        return _load_xlsx(path)
    raise ValueError(f"Unsupported file type: {path}")


def _load_csv(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            enriched = {key or "": value for key, value in row.items()}
            enriched["_source_file"] = _display_path(path)
            enriched["_source_row"] = row_number
            rows.append(enriched)
    return rows


def _load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

    def append_many(items: list[Any], record_type: str | None = None) -> None:
        for row_number, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            enriched = dict(item)
            if record_type and not any(_canonical_column(key) == "record_type" for key in enriched):
                enriched["record_type"] = record_type
            enriched["_source_file"] = _display_path(path)
            enriched["_source_row"] = row_number
            rows.append(enriched)

    if isinstance(data, list):
        append_many(data)
    elif isinstance(data, dict):
        matched_collection = False
        for key, record_type in (("controls", "control"), ("risks", "risk"), ("records", None), ("data", None)):
            value = data.get(key)
            if isinstance(value, list):
                append_many(value, record_type)
                matched_collection = True
        if not matched_collection:
            enriched = dict(data)
            enriched["_source_file"] = _display_path(path)
            enriched["_source_row"] = 1
            rows.append(enriched)
    return rows


def _load_xlsx(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as workbook:
        shared_strings = _read_shared_strings(workbook)
        sheets = _workbook_sheets(workbook)
        for sheet_name, sheet_path in sheets:
            if sheet_path not in workbook.namelist():
                continue
            sheet_rows = _read_sheet(workbook, sheet_path, shared_strings)
            if not sheet_rows:
                continue
            headers = [_canonical_header(value) for value in sheet_rows[0][1]]
            for excel_row_number, values in sheet_rows[1:]:
                if not any(str(value).strip() for value in values):
                    continue
                row = {headers[index]: values[index] if index < len(values) else "" for index in range(len(headers))}
                row["_source_file"] = _display_path(path)
                row["_source_row"] = f"{sheet_name}!{excel_row_number}"
                rows.append(row)
    return rows


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    namespace = _namespace(root.tag)
    strings: list[str] = []
    for item in root.findall(f".//{namespace}si"):
        text = "".join(node.text or "" for node in item.findall(f".//{namespace}t"))
        strings.append(text)
    return strings


def _workbook_sheets(workbook: zipfile.ZipFile) -> list[tuple[str, str]]:
    root = ET.fromstring(workbook.read("xl/workbook.xml"))
    namespace = _namespace(root.tag)
    rels_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rels = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_root
        if "Id" in rel.attrib and "Target" in rel.attrib
    }
    sheets: list[tuple[str, str]] = []
    rel_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    for sheet in root.findall(f".//{namespace}sheet"):
        name = sheet.attrib.get("name", "Sheet")
        rel_id = sheet.attrib.get(rel_key, "")
        target = rels.get(rel_id)
        if not target:
            continue
        if target.startswith("/"):
            path = target.lstrip("/")
        elif target.startswith("xl/"):
            path = target
        else:
            path = f"xl/{target}"
        sheets.append((name, path))
    return sheets


def _read_sheet(
    workbook: zipfile.ZipFile, sheet_path: str, shared_strings: list[str]
) -> list[tuple[int, list[str]]]:
    root = ET.fromstring(workbook.read(sheet_path))
    namespace = _namespace(root.tag)
    output: list[tuple[int, list[str]]] = []
    for row in root.findall(f".//{namespace}row"):
        row_number = int(row.attrib.get("r", len(output) + 1))
        cells: dict[int, str] = {}
        for index, cell in enumerate(row.findall(f"{namespace}c"), start=1):
            reference = cell.attrib.get("r", "")
            column_index = _excel_column_index(reference) or index
            cells[column_index] = _cell_value(cell, namespace, shared_strings)
        if cells:
            max_column = max(cells)
            output.append((row_number, [cells.get(column, "") for column in range(1, max_column + 1)]))
    return output


def _cell_value(cell: ET.Element, namespace: str, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{namespace}t"))
    value_node = cell.find(f"{namespace}v")
    if value_node is None or value_node.text is None:
        return ""
    raw_value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, ValueError):
            return raw_value
    return raw_value


def _namespace(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[0] + "}"
    return ""


def _excel_column_index(reference: str) -> int | None:
    letters = "".join(char for char in reference if char.isalpha())
    if not letters:
        return None
    total = 0
    for char in letters.upper():
        total = total * 26 + (ord(char) - ord("A") + 1)
    return total


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _canonical_header(value: Any) -> str:
    header = str(value).strip()
    return header or "unnamed"


def _canonical_column(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _first_value(row: dict[str, Any], field: str) -> str:
    for alias in FIELD_ALIASES[field]:
        value = row.get(_canonical_column(alias))
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return ""


def _clean_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _infer_record_type(row: dict[str, Any]) -> str | None:
    record_type = _clean_text(_first_value(row, "record_type"))
    if "control" in record_type:
        return "control"
    if "risk" in record_type:
        return "risk"
    if _first_value(row, "effectiveness"):
        return "control"
    if _first_value(row, "residual_score") or _first_value(row, "risk_rating"):
        return "risk"
    has_control = bool(_first_value(row, "control_id"))
    has_risk = bool(_first_value(row, "risk_id"))
    if has_control and not has_risk:
        return "control"
    if has_risk and not has_control:
        return "risk"
    return None


def _split_ids(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[;,|]", value) if item.strip()]


def _as_float(value: str) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    cleaned = str(value).replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
