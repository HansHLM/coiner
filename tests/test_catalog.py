from datetime import date
from decimal import Decimal
from pathlib import Path

from app.catalog import find_matching_prices, load_price_records
from app.models import CoinObservation, PriceRecord


def record(
    *,
    country: str = "France",
    denomination: str = "1 franc",
    year: int = 1900,
    mint_mark: str | None = None,
) -> PriceRecord:
    return PriceRecord(
        country=country,
        denomination=denomination,
        year=year,
        mint_mark=mint_mark,
        source="numista",
        price=Decimal("1.25"),
        currency="EUR",
        condition="VF",
        source_url="https://example.invalid/coin",
        retrieved_at=date(2026, 1, 1),
    )


def observation(**overrides: object) -> CoinObservation:
    data: dict[str, object] = {
        "country": "france",
        "denomination": "1 FRANC",
        "year": 1900,
        "confidence": 0.9,
        "needs_review": False,
    }
    data.update(overrides)
    return CoinObservation.model_validate(data)


def test_matches_case_insensitive_identity_fields() -> None:
    assert find_matching_prices(observation(), [record()]) == [record()]


def test_requires_matching_mint_mark_when_identified() -> None:
    prices = [record(mint_mark="A"), record(mint_mark="B")]

    assert find_matching_prices(observation(mint_mark="B"), prices) == [prices[1]]


def test_returns_no_prices_if_identification_is_incomplete() -> None:
    assert find_matching_prices(observation(year=None), [record()]) == []


def test_catalog_contains_numista_morlon_prices_and_issue_metadata() -> None:
    catalog_path = Path(__file__).parents[1] / "data" / "catalog.jsonl"
    records = load_price_records(catalog_path)
    numista_records = [record for record in records if record.source == "numista"]

    assert len(numista_records) == 68
    prices_1935 = {
        record.condition: record.price
        for record in numista_records
        if record.year == 1935
    }
    assert prices_1935 == {
        "F": Decimal(12),
        "VF": Decimal(15),
        "XF": Decimal(19),
    }

    trial = next(record for record in numista_records if record.variety is not None)
    assert trial.year == 1931
    assert trial.condition == "XF"
    assert trial.price == Decimal(120)
    assert trial.mintage is None
    assert trial.frequency == 0.5
    assert trial.reference == "Franc 2014# 219/1; KM# E-B64"
