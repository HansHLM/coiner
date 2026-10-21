import json
from pathlib import Path

from app.models import CoinObservation, PriceRecord


def load_price_records(path: Path) -> list[PriceRecord]:
    records: list[PriceRecord] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(f"Could not read price catalogue at {path}: {error}") from error

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            records.append(PriceRecord.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError) as error:
            raise RuntimeError(
                f"Invalid catalogue record at {path}:{line_number}: {error}"
            ) from error
    return records


def find_matching_prices(
    observation: CoinObservation, records: list[PriceRecord]
) -> list[PriceRecord]:
    if (
        observation.country is None
        or observation.denomination is None
        or observation.year is None
    ):
        return []

    country = observation.country.strip().casefold()
    denomination = observation.denomination.strip().casefold()
    return [
        record
        for record in records
        if record.country.strip().casefold() == country
        and record.denomination.strip().casefold() == denomination
        and record.year == observation.year
        and (
            observation.mint_mark is None
            or (record.mint_mark or "").strip().casefold()
            == observation.mint_mark.strip().casefold()
        )
    ]
