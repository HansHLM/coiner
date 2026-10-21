from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from app.catalog import load_price_records
from app.lefranc import LEFRANC_URL, import_lefranc_prices, parse_lefranc_prices
from app.models import PriceRecord

PAGE_HTML = """
<h1>1 Franc MORLON</h1>
<table id="table_franc">
  <tr class="entete"><td>N° de FRANC</td><td>Date</td><td>Atelier</td>
    <td colspan="6">Prix en Euros Dollars</td><td>Grade</td></tr>
  <tr class="entete"><td>B 10 (€)</td><td>TB 25 (€)</td><td>TTB 45 (€)</td>
    <td>SUP 58 (€)</td><td>SPL 63 (€)</td><td>FDC 65 (€)</td></tr>
  <tr><td>F.219/1</td><td>1931</td><td><i>essai</i></td>
    <td><div class="euro">10,00</div><div class="dollar">11,20</div></td>
    <td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>66</td></tr>
  <tr><td>F.219/2</td><td>1931</td><td></td>
    <td>-</td><td>-</td><td><div class="euro">45,00</div></td>
    <td><div class="euro">90,00</div></td>
    <td><div class="euro">100,00</div></td><td>-</td><td>67</td></tr>
</table>
"""


def test_parse_lefranc_prices_uses_euro_values_and_skips_trial() -> None:
    records = parse_lefranc_prices(PAGE_HTML, date(2026, 10, 21))

    assert [(record.year, record.condition, record.price) for record in records] == [
        (1931, "TTB", 45),
        (1931, "SUP", 90),
        (1931, "SPL", 100),
    ]
    assert all(record.source == "lefranc" for record in records)
    assert all(record.currency == "EUR" for record in records)
    assert all(str(record.source_url) == LEFRANC_URL for record in records)


def test_import_is_idempotent_and_preserves_other_catalog_records(
    monkeypatch, tmp_path: Path
) -> None:
    catalog_path = tmp_path / "catalog.jsonl"
    other_record = PriceRecord(
        country="France",
        denomination="2 francs",
        year=1931,
        source="numista",
        price=Decimal("2.50"),
        currency="EUR",
        condition="VF",
        source_url="https://example.invalid/coin",
        retrieved_at=date(2026, 10, 21),
    )
    catalog_path.write_text(other_record.model_dump_json() + "\n", encoding="utf-8")
    response = SimpleNamespace(text=PAGE_HTML, raise_for_status=lambda: None)
    monkeypatch.setattr("app.lefranc.httpx.get", lambda *args, **kwargs: response)

    first_count = import_lefranc_prices(catalog_path, date(2026, 10, 21))
    first_content = catalog_path.read_text(encoding="utf-8")
    second_count = import_lefranc_prices(catalog_path, date(2026, 10, 21))

    assert first_count == 3
    assert second_count == 3
    assert catalog_path.read_text(encoding="utf-8") == first_content
    records = load_price_records(catalog_path)
    assert other_record in records
