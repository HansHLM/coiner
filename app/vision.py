import base64
import json

from openai import OpenAI

from app.models import CoinObservation

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def identify_coin(
    image_bytes: bytes, content_type: str, api_key: str, model: str
) -> CoinObservation:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Upload a JPEG, PNG, or WebP image.")

    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Identify visible coin details conservatively. Do not estimate a price. "
                    "Use null for uncertain country, denomination, year, or mint mark. "
                    "Set needs_review true if the image or identification is uncertain. "
                    "Return JSON with country, denomination, year, mint_mark, "
                    "identifying_features (array of strings), confidence (0 to 1), "
                    "and needs_review (boolean)."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Identify the coin shown in this photo."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{content_type};base64,{encoded_image}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("The vision model returned an empty identification.")
    try:
        return CoinObservation.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(f"The vision model returned invalid identification data: {error}") from error
