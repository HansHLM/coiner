import base64
import json

from openai import OpenAI

from app.models import CoinObservation

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def identify_coin(
    images: list[tuple[bytes, str]], api_key: str, model: str
) -> CoinObservation:
    if len(images) != 2:
        raise ValueError("Provide both the front and back images of the coin.")

    encoded_images = []
    for image_bytes, content_type in images:
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError("Upload JPEG, PNG, or WebP images.")
        encoded_images.append(
            (content_type, base64.b64encode(image_bytes).decode("ascii"))
        )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Identify the coin using both its front and back images, and combine "
                    "evidence from both sides. Identify visible coin details conservatively. "
                    "Do not estimate a price. "
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
                    {"type": "text", "text": "Coin front (obverse):"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{encoded_images[0][0]};base64,{encoded_images[0][1]}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": "Coin back (reverse):"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{encoded_images[1][0]};base64,{encoded_images[1][1]}",
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
