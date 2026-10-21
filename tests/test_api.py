from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models import CoinObservation, PriceRecord


def test_rejects_unsupported_image_type() -> None:
    response = TestClient(app).post(
        "/api/identify",
        files={"image": ("coin.gif", b"not an image", "image/gif")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Upload a JPEG, PNG, or WebP image."


def test_requires_api_key_before_processing_image(monkeypatch) -> None:
    monkeypatch.setattr("app.main.settings.openai_api_key", None)
    response = TestClient(app).post(
        "/api/identify",
        files={"image": ("coin.png", b"not decoded without an API key", "image/png")},
    )

    assert response.status_code == 503


def test_rejects_invalid_image(monkeypatch) -> None:
    monkeypatch.setattr("app.main.settings.openai_api_key", "test-key")
    response = TestClient(app).post(
        "/api/identify",
        files={"image": ("coin.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is not a valid image."


def test_rejects_oversized_image(monkeypatch) -> None:
    monkeypatch.setattr("app.main.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.main.settings.max_image_bytes", 4)
    response = TestClient(app).post(
        "/api/identify",
        files={"image": ("coin.png", b"12345", "image/png")},
    )

    assert response.status_code == 413


def test_returns_source_price_records(monkeypatch) -> None:
    image_bytes = BytesIO()
    Image.new("RGB", (8, 8), color="silver").save(image_bytes, format="PNG")
    observation = CoinObservation(
        country="France",
        denomination="1 franc",
        year=1900,
        confidence=0.95,
        needs_review=False,
    )
    price = PriceRecord(
        country="France",
        denomination="1 franc",
        year=1900,
        source="numista",
        price=Decimal("1.25"),
        currency="EUR",
        condition="VF",
        source_url="https://example.invalid/record",
        retrieved_at=date(2026, 1, 1),
    )
    monkeypatch.setattr("app.main.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.main.identify_coin", lambda *_: observation)
    monkeypatch.setattr("app.main.load_price_records", lambda *_: [price])

    response = TestClient(app).post(
        "/api/identify",
        files={"image": ("coin.png", image_bytes.getvalue(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["identification"]["country"] == "France"
    assert response.json()["prices"][0]["source"] == "numista"
    assert response.json()["prices"][0]["price"] == "1.25"
