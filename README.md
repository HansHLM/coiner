# Coiner

Coiner is a small Python web app that identifies a coin from a photo and looks
up matching price records with their source and retrieval date. It does not
invent a price when a source record is unavailable.

## Current scope

- Upload front and back images of a coin together in the browser.
- Ask an OpenAI vision model for a structured coin description.
- Match that description against a local JSONL catalogue of Lefranc and Numista
  records.
- Show each matching source record separately, including condition, currency,
  source URL, and retrieval date.

The supplied RAG repository, [HansHLM/coiner](https://github.com/HansHLM/coiner),
currently contains only a README, so there is no existing RAG code or API
contract to integrate yet. This app uses a narrow local retrieval interface
that can be replaced or connected to that repository once its implementation
and data format are available. No Lefranc or Numista prices are bundled or
fabricated.

## Run locally

1. Create and activate a virtual environment.
2. Install the app and development dependencies:

   ```powershell
   python -m pip install -e ".[dev]"
   ```

3. Copy `.env.example` to `.env` and set `COINER_OPENAI_API_KEY`.
4. Start the development server:

   ```powershell
   uvicorn app.main:app --reload
   ```

5. Open <http://127.0.0.1:8000>.

The API documentation is available at <http://127.0.0.1:8000/docs>.

## Catalogue data

Add one JSON object per line to `data/catalog.jsonl`. Each record must describe
an actual source result; keep the source URL and date when it was retrieved.
Records can also include variety, mintage, frequency, and reference metadata
when supplied by the source.
For example (illustrative schema only, not a real price):

```json
{"country":"France","denomination":"1 franc","year":1900,"mint_mark":null,"source":"numista","price":1.25,"currency":"EUR","condition":"VF","source_url":"https://example.invalid/record","retrieved_at":"2026-01-01"}
```

Only exact matches on country, denomination, and year are returned. When a mint
mark is identified, it must also match. Review visual identification and coin
condition manually: catalogue prices are not guaranteed sale prices, and
condition can materially affect value.

To fetch and refresh the regular-circulation 1 Franc Morlon price records from
LeFranc, run:

```powershell
python -m app.lefranc
```

This imports the available euro values by year and condition grade. Trial
strikes marked `essai` are excluded because they are a separate variety. The
import replaces previous records from this LeFranc page and preserves records
from other sources.

The `/api/identify` endpoint requires both `front_image` and `back_image`
multipart file fields. Each image is sent to the vision model in the same
request, labelled as the obverse or reverse, and each is subject to the
configured `COINER_MAX_IMAGE_BYTES` limit.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `COINER_OPENAI_API_KEY` | unset | API key used for image identification |
| `COINER_OPENAI_MODEL` | `gpt-4o-mini` | Vision-capable OpenAI model |
| `COINER_CATALOG_PATH` | `data/catalog.jsonl` | Local JSONL price catalogue |
| `COINER_MAX_IMAGE_BYTES` | `10485760` | Maximum uploaded image size (10 MiB) |