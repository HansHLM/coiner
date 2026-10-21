from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class CoinObservation(BaseModel):
    country: str | None = None
    denomination: str | None = None
    year: int | None = None
    mint_mark: str | None = None
    identifying_features: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    needs_review: bool


class PriceRecord(BaseModel):
    country: str
    denomination: str
    year: int
    mint_mark: str | None = None
    variety: str | None = None
    mintage: int | None = Field(default=None, ge=0)
    frequency: float | None = Field(default=None, ge=0, le=100)
    reference: str | None = None
    source: Literal["lefranc", "numista"]
    price: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    condition: str
    source_url: HttpUrl
    retrieved_at: date


class IdentificationResult(BaseModel):
    identification: CoinObservation
    prices: list[PriceRecord]
    price_note: str
