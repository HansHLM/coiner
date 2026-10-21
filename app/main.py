from io import BytesIO
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.catalog import find_matching_prices, load_price_records
from app.config import settings
from app.models import IdentificationResult
from app.vision import ALLOWED_IMAGE_TYPES, identify_coin

app = FastAPI(title="Coiner", description="Photo-based coin identification and sourced price lookup.")
INDEX_PATH = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(INDEX_PATH)


@app.post("/api/identify", response_model=IdentificationResult)
def identify(
    front_image: Annotated[UploadFile, File()],
    back_image: Annotated[UploadFile, File()],
) -> IdentificationResult:
    uploaded_images = (front_image, back_image)
    if any(image.content_type not in ALLOWED_IMAGE_TYPES for image in uploaded_images):
        raise HTTPException(status_code=415, detail="Upload JPEG, PNG, or WebP images.")
    if settings.openai_api_key is None:
        raise HTTPException(status_code=503, detail="Set COINER_OPENAI_API_KEY to enable identification.")
    if settings.max_image_bytes < 1:
        raise HTTPException(status_code=500, detail="COINER_MAX_IMAGE_BYTES must be greater than zero.")

    images = []
    for image in uploaded_images:
        image_bytes = image.file.read(settings.max_image_bytes + 1)
        if len(image_bytes) > settings.max_image_bytes:
            raise HTTPException(status_code=413, detail="An image exceeds the configured size limit.")
        try:
            with Image.open(BytesIO(image_bytes)) as decoded_image:
                decoded_image.verify()
        except (UnidentifiedImageError, OSError) as error:
            raise HTTPException(
                status_code=400, detail="An uploaded file is not a valid image."
            ) from error
        images.append((image_bytes, image.content_type))

    try:
        observation = identify_coin(
            images, settings.openai_api_key, settings.openai_model
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    try:
        records = load_price_records(settings.catalog_path)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    prices = find_matching_prices(observation, records)
    price_note = (
        "Prices are source records, not a guaranteed sale value."
        if prices
        else "No exact price record was found. No price has been estimated."
    )
    return IdentificationResult(
        identification=observation,
        prices=prices,
        price_note=price_note,
    )
