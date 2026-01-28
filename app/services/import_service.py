from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Iterable

from app.utils import normalize


@dataclass
class ParsedProductRow:
    name: str
    price: float
    description: str


@dataclass
class ParseResult:
    rows: list[ParsedProductRow]
    errors: list[str]


REQUIRED_HEADERS = {"name", "price"}
OPTIONAL_HEADERS = {"description"}


def parse_products_csv(content: str) -> ParseResult:
    errors: list[str] = []
    rows: list[ParsedProductRow] = []
    if not content.strip():
        return ParseResult(rows=[], errors=["Файл пустой."])

    sample = content[:1024]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ","

    reader = csv.DictReader(StringIO(content), dialect=dialect)
    if not reader.fieldnames:
        return ParseResult(rows=[], errors=["Не удалось прочитать заголовки CSV."])

    headers = {h.strip().lower() for h in reader.fieldnames if h}
    missing = REQUIRED_HEADERS - headers
    if missing:
        errors.append(f"Не хватает колонок: {', '.join(sorted(missing))}.")
        return ParseResult(rows=[], errors=errors)

    seen_names: set[str] = set()
    for idx, row in enumerate(reader, start=2):
        raw_name = (row.get("name") or "").strip()
        raw_price = (row.get("price") or "").strip()
        raw_desc = (row.get("description") or "").strip()

        if not raw_name and not raw_price and not raw_desc:
            continue

        if not raw_name:
            errors.append(f"Строка {idx}: пустое название.")
            continue

        try:
            price = float(raw_price.replace(",", "."))
        except ValueError:
            errors.append(f"Строка {idx}: цена должна быть числом.")
            continue

        if price < 0:
            errors.append(f"Строка {idx}: цена должна быть >= 0.")
            continue

        norm_name = normalize(raw_name)
        if norm_name in seen_names:
            errors.append(f"Строка {idx}: дубликат названия '{raw_name}'.")
            continue
        seen_names.add(norm_name)

        rows.append(ParsedProductRow(name=raw_name, price=price, description=raw_desc))

    if not rows and not errors:
        errors.append("Нет валидных строк для импорта.")

    return ParseResult(rows=rows, errors=errors)


def preview_rows(rows: Iterable[ParsedProductRow], limit: int = 5) -> list[str]:
    lines = []
    for idx, row in enumerate(rows):
        if idx >= limit:
            break
        desc = f" — {row.description}" if row.description else ""
        lines.append(f"{idx + 1}. {row.name} ({row.price}){desc}")
    return lines
