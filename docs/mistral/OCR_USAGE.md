# Mistral OCR Usage Notes

This document captures the current OCR behavior and recommended usage patterns.

## Defaults

- /api/process defaults to Mistral OCR for PDFs and images.
- Default parameters:
  - use_ai: true
  - ocr_mode: force_ai
  - table_format: markdown

To use local processing (pdfplumber or pytesseract):

```
POST /api/process
{
  "file": "report.pdf",
  "use_ai": false,
  "ocr_mode": "force_local"
}
```

## Drop Zones

- Test OCR files: inbox/ocr_tests/
- Live OCR files: inbox/live/

Subpaths are allowed in the file field:

```
POST /api/process
{
  "file": "ocr_tests/sample_scan.pdf",
  "use_ai": true
}
```

## Output Location

- OCR outputs are written to data/generated/
- Mistral OCR outputs use the suffix _ocr.json

## Key Parameters

- use_ai: boolean (default true)
- ocr_mode: force_ai | force_local | auto
- pages: list of 0-based page indices
- table_format: markdown | html
- extract_header: boolean
- extract_footer: boolean
- include_image_base64: boolean

## Logging

OCR logs are emitted to the server console:

- Selection logs indicate whether Mistral or local processing was chosen.
- Request logs include document type, pages, and table format.
- Response logs show page count, table count, and image count.

Example:

```
INFO processors.mistral_ocr: OCR selected Mistral for report.pdf (mode=force_ai)
INFO processors.mistral_ocr: Mistral OCR request for report.pdf (type=pdf, pages=all, table_format=markdown)
INFO processors.mistral_ocr: Mistral OCR response for report.pdf: pages=4 tables=2 images=0
```

## Troubleshooting

- Missing API key: set MISTRAL_API_KEY in .env or the shell environment.
- If you hit rate limits, retry with a smaller pages list or switch to local processing.

## Archive

- Historical upgrade plan: `docs/archive/mistral/MISTRAL_OCR_UPGRADE_PLAN.md` (implementation completed on 2025-12-30)
