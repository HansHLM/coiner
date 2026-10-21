import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path

import httpx

from app.catalog import load_price_records
from app.config import settings
from app.models import PriceRecord

LEFRANC_URL = "https://www.lefranc.net/monnaie,1-franc-morlon,219.html"
_GRADE_PATTERN = re.compile(r"^(TTB|TB|B|SUP|SPL|FDC)\b")
_ISSUE_PATTERN = re.compile(r"^F\.219/\d+$")


class _TableCell:
    def __init__(self, classes: set[str]) -> None:
        self.classes = classes
        self.text: list[str] = []
        self.euro_text: list[str] = []


class _LeFrancTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[_TableCell]] = []
        self.header_rows: list[list[_TableCell]] = []
        self._in_table = False
        self._row: list[_TableCell] | None = None
        self._is_header_row = False
        self._cell: _TableCell | None = None
        self._in_euros = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == "table_franc":
            self._in_table = True
        if not self._in_table:
            return
        if tag == "tr":
            self._row = []
            self._is_header_row = "entete" in set((attributes.get("class") or "").split())
        elif tag in {"td", "th"} and self._row is not None:
            classes = set((attributes.get("class") or "").split())
            self._cell = _TableCell(classes)
        elif tag == "div" and self._cell is not None:
            self._in_euros = "euro" in set((attributes.get("class") or "").split())

    def handle_endtag(self, tag: str) -> None:
        if not self._in_table:
            return
        if tag == "div":
            self._in_euros = False
        elif tag in {"td", "th"} and self._cell is not None:
            if self._row is not None:
                self._row.append(self._cell)
            self._cell = None
            self._in_euros = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            if self._is_header_row:
                self.header_rows.append(self._row)
            self._row = None
            self._is_header_row = False
        elif tag == "table":
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._cell is None:
            return
        self._cell.text.append(data)
        if self._in_euros:
            self._cell.euro_text.append(data)


def parse_lefranc_prices(html: str, retrieved_at: date) -> list[PriceRecord]:
    parser = _LeFrancTableParser()
    parser.feed(html)
    if len(parser.header_rows) < 2:
        raise ValueError("The LeFranc price table headers could not be found.")

    grades = [
        match.group(1)
        for cell in parser.header_rows[1]
        if (match := _GRADE_PATTERN.match(" ".join("".join(cell.text).split())))
    ]
    if len(grades) != 6:
        raise ValueError("The LeFranc price table did not contain six recognized condition grades.")

    records: list[PriceRecord] = []
    for row in parser.rows:
        if len(row) < 9:
            continue
        issue_number = " ".join("".join(row[0].text).split())
        if not _ISSUE_PATTERN.fullmatch(issue_number):
            continue
        year_text = " ".join("".join(row[1].text).split())
        atelier = " ".join("".join(row[2].text).split())
        if "essai" in atelier.casefold():
            continue
        if not year_text.isdigit():
            raise ValueError(f"Invalid year in LeFranc issue {issue_number}: {year_text!r}")

        for grade, cell in zip(grades, row[3:9], strict=True):
            euro_value = " ".join("".join(cell.euro_text).split())
            if not euro_value:
                continue
            try:
                price = Decimal(euro_value.replace(",", "."))
            except InvalidOperation as error:
                raise ValueError(
                    f"Invalid euro price in LeFranc issue {issue_number}: {euro_value!r}"
                ) from error
            records.append(
                PriceRecord(
                    country="France",
                    denomination="1 franc",
                    year=int(year_text),
                    source="lefranc",
                    price=price,
                    currency="EUR",
                    condition=grade,
                    source_url=LEFRANC_URL,
                    retrieved_at=retrieved_at,
                )
            )
    if not records:
        raise ValueError("No LeFranc prices were parsed from the page.")
    return records


def import_lefranc_prices(
    catalog_path: Path, retrieved_at: date | None = None
) -> int:
    try:
        response = httpx.get(LEFRANC_URL, follow_redirects=True, timeout=20)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise RuntimeError(f"Could not download LeFranc prices from {LEFRANC_URL}: {error}") from error

    return import_lefranc_html(catalog_path, response.text, retrieved_at)


def import_lefranc_html(
    catalog_path: Path, html: str, retrieved_at: date | None = None
) -> int:
    imported = parse_lefranc_prices(html, retrieved_at or date.today())
    existing = (
        [
            record
            for record in load_price_records(catalog_path)
            if str(record.source_url) != LEFRANC_URL
        ]
        if catalog_path.exists()
        else []
    )
    all_records = existing + imported
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        "".join(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False) + "\n"
            for record in all_records
        ),
        encoding="utf-8",
    )
    return len(imported)


if __name__ == "__main__":
    count = import_lefranc_prices(settings.catalog_path)
    print(f"Imported {count} LeFranc price records into {settings.catalog_path}.")
