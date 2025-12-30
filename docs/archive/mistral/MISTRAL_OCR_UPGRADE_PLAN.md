# Mistral OCR Upgrade - Integration Plan (Dec 30, 2025)

This plan replaces or augments the local PDF/Image processors with the Mistral OCR API while keeping a stable, Shortcut-friendly JSON output.

## 1) Verified API Facts (Official)

- Endpoint: POST https://api.mistral.ai/v1/ocr
- Model: mistral-ocr-latest
- Auth: Authorization: Bearer ${MISTRAL_API_KEY}
- Content-Type: application/json
- Limits: 50 MB per document; up to 1,000 pages per document
- Request format: JSON with document object (image_url or document_url). Accepts URL or base64 data URI.
- Response: pages[] with markdown, tables, images, hyperlinks, dimensions; optional document_annotation; usage_info

References used:
- https://github.com/mistralai/platform-docs-public/blob/main/docs/capabilities/OCR/basic_ocr.md
- https://github.com/mistralai/platform-docs-public/blob/main/src/app/(docs)/capabilities/document_ai/basic_ocr/page.mdx
- https://github.com/mistralai/platform-docs-public/blob/main/docs/capabilities/document_ai/annotations.md
- https://docs.mistral.ai/deployment/ai-studio/tier

## 2) Goals and First Principles

- Stable downstream schema: output must not change even if upstream OCR model evolves.
- Defensive by default: retries, timeouts, and graceful fallback to local processors.
- Cost-aware: only use OCR when needed; allow explicit force_ai and page selection.
- Verifiable: store raw OCR response for audit and regression checks.

## 3) New Component: processors/mistral_ocr.py

Purpose: Single entry point for OCR across PDFs and images.

Responsibilities:
- Detect input type (pdf or image).
- Optional preflight scan to choose local vs Mistral OCR.
- Call Mistral OCR API and normalize output to SDJ (Standardized Document JSON).
- Persist output to data/generated/.

Proposed signature:
- process_document(input_path, output_dir, use_ai=False, ocr_mode="auto",
  language="en", pages=None, table_format="markdown",
  extract_header=False, extract_footer=False,
  include_image_base64=False, schema_version="1.0")

## 4) API Client Wrapper

Implementation: httpx with timeouts and exponential backoff.

Retry policy:
- Retry on 429, 503, 504, and network timeouts.
- Honor Retry-After when present.
- Max retry window: 30 to 60 seconds.

Timeouts:
- connect: 5s
- read: 60s (PDFs can be slow)

Pseudo-code:

```python
payload = {
    "model": "mistral-ocr-latest",
    "document": {"type": "document_url", "document_url": "data:application/pdf;base64,..."},
    "pages": [0, 1, 2],
    "table_format": "markdown",
    "extract_header": False,
    "extract_footer": False,
    "include_image_base64": False
}

resp = httpx.post(
    "https://api.mistral.ai/v1/ocr",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json=payload,
    timeout=httpx.Timeout(connect=5, read=60, write=30, pool=30),
)
```

## 5) Standardized Document JSON (SDJ) Schema

This schema is optimized for Shortcut AI and Excel workflows.

```json
{
  "schema_version": "1.0",
  "source_file": "invoice_001.pdf",
  "source_type": "pdf|image",
  "processor": "mistral_ocr|pdfplumber|tesseract",
  "pages": [
    {
      "page_number": 1,
      "width": 1000,
      "height": 1500,
      "text": "plain text version",
      "markdown": "# Title\n...",
      "blocks": [],
      "tables": [
        {
          "table_id": "t1",
          "format": "markdown",
          "content": "| H1 | H2 |\n|---|---|\n| A | B |",
          "bbox": [0, 0, 0, 0]
        }
      ],
      "images": [],
      "hyperlinks": []
    }
  ],
  "metadata": {
    "page_count": 1,
    "language": "en",
    "created_at": "2025-12-30T12:00:00Z",
    "ocr_runtime_ms": 1234,
    "model": "mistral-ocr-latest",
    "usage_info": {},
    "warnings": []
  },
  "raw": {
    "provider": "mistral",
    "response": {}
  }
}
```

Mapping rules:
- pages[].markdown mirrors Mistral response.
- pages[].text is a markdown-stripped plain-text variant.
- pages[].tables map from Mistral table objects (format + content).
- raw.response contains the full original Mistral payload.

## 6) Fallback Logic (Local vs OCR)

- PDF:
  - Use pdfplumber when text density is high and images are sparse.
  - Use Mistral OCR for scanned/low-text PDFs or when use_ai=true.
- Image:
  - Use pytesseract by default; Mistral OCR when use_ai=true.
- Override mode: ocr_mode = force_ai | force_local | auto.

Heuristic inputs:
- page.extract_text() length per page
- embedded image area ratio
- file extension

## 7) Server Updates (/api/process)

Add optional parameters to POST body:
- use_ai: boolean
- ocr_mode: "auto" | "force_ai" | "force_local"
- pages: array of 0-based page indices
- table_format: "markdown" | "html"
- extract_header: boolean
- extract_footer: boolean
- include_image_base64: boolean

Routing:
- If use_ai=true, route pdf/image to processors.mistral_ocr.process_document().
- If use_ai=false, keep current behavior.

API key enforcement:
- If use_ai=true and MISTRAL_API_KEY is missing, return 400 with guidance.

Default behavior (current):
- /api/process defaults to use_ai=true and ocr_mode=force_ai for PDFs/images.

## 8) Validation & Testing

Functional:
- PDF with embedded text -> local path in auto mode
- Scanned PDF -> Mistral OCR path in auto mode
- Image -> Mistral OCR when use_ai=true
- Schema validation: SDJ required fields exist and page_count matches pages length

Accuracy checks:
- Golden set of 5-10 documents with known ground truth
- Compare WER (text) and table extraction consistency

Performance:
- Log OCR runtime per page and usage_info
- Track OCR usage to estimate cost

## 9) Pricing and Benchmark Notes (Provisional)

- Pricing and benchmarks were only found in third-party sources.
- Treat any $/1,000 pages and win-rate claims as provisional until Mistral publishes official numbers.
- Rate limits are workspace tier-based; check AI Studio for exact limits.

## 10) Open Gaps

- Official latency benchmarks and official table extraction metrics are not published.
- Versioned model IDs (beyond mistral-ocr-latest alias) are not documented.
- Defaults for image_limit and image_min_size are not documented.
