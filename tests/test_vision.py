import base64
import json
from types import SimpleNamespace

from app.models import CoinObservation
from app.vision import identify_coin


def test_sends_front_and_back_images_to_vision_model(monkeypatch) -> None:
    request = {}
    observation_json = json.dumps(
        {
            "country": "France",
            "denomination": "1 franc",
            "year": 1935,
            "mint_mark": None,
            "identifying_features": [],
            "confidence": 0.95,
            "needs_review": False,
        }
    )

    class FakeCompletions:
        def create(self, **kwargs):
            request.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=observation_json))
                ]
            )

    class FakeOpenAI:
        def __init__(self, *, api_key):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("app.vision.OpenAI", FakeOpenAI)

    result = identify_coin([(b"front", "image/png"), (b"back", "image/jpeg")], "key", "model")

    assert isinstance(result, CoinObservation)
    content = request["messages"][1]["content"]
    assert content[0]["text"] == "Coin front (obverse):"
    assert content[1]["image_url"]["url"] == (
        f"data:image/png;base64,{base64.b64encode(b'front').decode('ascii')}"
    )
    assert content[2]["text"] == "Coin back (reverse):"
    assert content[3]["image_url"]["url"] == (
        f"data:image/jpeg;base64,{base64.b64encode(b'back').decode('ascii')}"
    )
