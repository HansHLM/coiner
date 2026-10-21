from datetime import date
from decimal import Decimal

from app.catalog import find_matching_prices
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
