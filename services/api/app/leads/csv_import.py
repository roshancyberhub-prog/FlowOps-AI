import csv
import io
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.schemas.leads import LeadCreate

MAX_BYTES = 512 * 1024
MAX_ROWS = 2000
MAX_COLUMNS = 30
MAX_CELL = 2048
csv.field_size_limit(MAX_CELL)


class ImportValidation(ValueError):
    pass


@dataclass
class ParsedRow:
    number: int
    raw: dict[str, str]
    data: dict = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    duplicate_in_file: bool = False


def read_records(data: bytes) -> tuple[list[str], list[tuple[int, list[str]]]]:
    if len(data) > MAX_BYTES:
        raise ImportValidation("CSV files must be 512 KiB or smaller.")
    if b"\0" in data:
        raise ImportValidation("Upload a UTF-8 text CSV without binary content.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportValidation("CSV files must use UTF-8 encoding.") from exc
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = [value.strip() for value in next(reader, [])]
        if not 2 <= len(headers) <= MAX_COLUMNS or any(
            not value or len(value) > 100 for value in headers
        ):
            raise ImportValidation("Use 2–30 named columns, with headers up to 100 characters.")
        if len(set(value.casefold() for value in headers)) != len(headers):
            raise ImportValidation("Every CSV column must have a unique name.")
        rows = []
        for number, values in enumerate(reader, start=2):
            if not any(value.strip() for value in values):
                continue
            if len(values) > MAX_COLUMNS:
                raise ImportValidation("CSV records must have at most 30 columns.")
            rows.append((number, values))
            if len(rows) > MAX_ROWS:
                raise ImportValidation("CSV imports support at most 2000 nonempty records.")
    except csv.Error as exc:
        raise ImportValidation(
            "CSV contains invalid quoting or a field exceeding 2048 characters."
        ) from exc
    if not rows:
        raise ImportValidation("Add at least one nonempty record below the header.")
    return headers, rows


def inspect_csv(data: bytes) -> dict:
    headers, rows = read_records(data)
    known = set(LeadCreate.model_fields)
    aliases = {"full_name": "name", "work_email": "email", "company_name": "company"}
    suggested: dict[str, str] = {}
    for header in headers:
        key = header.strip().casefold().replace(" ", "_")
        key = aliases.get(key, key)
        if key in known and key not in suggested:
            suggested[key] = header
    return {
        "headers": headers,
        "row_count": len(rows),
        "suggested_mapping": suggested,
        "max_bytes": MAX_BYTES,
        "max_rows": MAX_ROWS,
    }


def parse_csv(data: bytes, mapping: dict[str, str]) -> list[ParsedRow]:
    headers, rows = read_records(data)
    validate_mapping(headers, mapping)
    positions = {key: headers.index(column) for key, column in mapping.items()}
    result = []
    seen = set()
    for number, values in rows:
        raw = {
            key: values[index] if index < len(values) else "" for key, index in positions.items()
        }
        row = ParsedRow(number, raw)
        if len(values) != len(headers):
            row.errors.append(
                {"field": "record", "message": "Column count differs from the header."}
            )
        else:
            inputs = {key: value.strip() or None for key, value in raw.items()}
            try:
                row.data = LeadCreate.model_validate(inputs).model_dump(mode="json")
                row.duplicate_in_file = row.data["email"] in seen
                seen.add(row.data["email"])
            except ValidationError as exc:
                row.errors = [
                    {"field": ".".join(map(str, error["loc"])), "message": error["msg"]}
                    for error in exc.errors()
                ]
        result.append(row)
    return result


def validate_mapping(headers: list[str], mapping: dict[str, str]) -> None:
    if not {"name", "email"}.issubset(mapping):
        raise ImportValidation("Map both name and email before importing.")
    if set(mapping) - set(LeadCreate.model_fields):
        raise ImportValidation("Only supported lead input fields may be mapped.")
    if any(column not in headers for column in mapping.values()):
        raise ImportValidation("Every mapped column must exist in the CSV header.")
    if len(set(mapping.values())) != len(mapping):
        raise ImportValidation("Map each CSV column to only one lead field.")
