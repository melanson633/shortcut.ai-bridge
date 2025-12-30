# Shortcut Bridge

**Local HTTP server that bridges your filesystem with Shortcut AI's TypeScript runtime.**

Shortcut AI can `fetch()` from localhost. This project provides:
- Static file serving (CSV, JSON, TXT)
- Dynamic API endpoints (status, metrics, processing)
- File processors (PDF -> JSON, Excel -> CSV, Image -> OCR text)
- Bidirectional sync (POST endpoints to receive data from Shortcut)

---

## Quick Start

```powershell
# Navigate to directory
cd C:\Users\mmelanson\.cursor-tutor\projects\shortcut-bridge

# Install dependencies
pip install -r requirements.txt

# Start server
python server.py
```

Server runs at `http://127.0.0.1:8000`

---

## Directory Structure

```
shortcut-bridge/
|-- server.py              # Flask server (start here)
|-- requirements.txt       # Python dependencies
|-- start.ps1              # One-click launcher
|-- config.json            # Server settings
|-- data/                  # FETCHABLE content
|   |-- samples/           # Test/demo datasets
|   |-- generated/         # Output from processors/scripts
|   |-- exports/           # Data received FROM Shortcut
|-- inbox/                 # Drop raw files here for processing
|   |-- (PDFs, images, Excel files)
|-- processors/            # File type converters
|   |-- pdf.py             # PDF -> JSON/CSV
|   |-- image.py           # Image -> OCR text
|   |-- excel.py           # XLSX -> clean JSON/CSV
|-- scripts/               # Standalone Python scripts
|-- docs/                  # Documentation
|   |-- shortcut_context.txt
```

---

## API Reference

### Static Files

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/data/samples/{filename}` | Fetch sample datasets |
| GET | `/data/generated/{filename}` | Fetch processed outputs |
| GET | `/data/exports/{filename}` | Fetch exported data |

### Dynamic Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/status` | Server health, available files, timestamps |
| GET | `/api/data?filter=x&limit=n` | Query sample data with filters and limits |
| GET | `/api/error` | Error handling test (returns 500) |
| GET | `/api/slow?seconds=N` | Timeout testing (simulates slow operations) |
| POST | `/api/echo` | Echo back JSON payload (POST testing) |
| POST | `/api/export` | Receive data from Shortcut AI, save to `/data/exports/` |
| POST | `/api/process` | Process a file from `/inbox/` (PDF, Excel, Image) |
| POST | `/api/upload` | Upload file via FormData (multipart) |
| POST | `/api/upload-base64` | Upload file via base64 encoding (recommended) |
| POST | `/api/generate` | Generate data dynamically (no file needed) |
| POST | `/api/analyze` | Full pandas pipeline: receive data, process, return results |
| POST | `/api/bulk` | Handle large payloads (validates row/cell counts) |

---

## Usage Patterns

### Pattern 1: Fetch Static Data
```
Shortcut: fetch("http://127.0.0.1:8000/data/samples/sales.csv")
```

### Pattern 2: Check What's Available
```
Shortcut: fetch("http://127.0.0.1:8000/api/status")
Returns: {status: "ok", server_time: "...", files: {samples: [...], generated: [...], exports: [...], inbox: [...], inbox_subdirs: [...]}}
```

### Pattern 3: Process a PDF
```
1. Drop "report.pdf" into /inbox/
2. Shortcut: POST to /api/process with {file: "report.pdf", output: "json"}
   Default OCR uses Mistral (use_ai=true, ocr_mode=force_ai).
3. Shortcut: GET /data/generated/report_ocr.json
```

Optional (force local OCR/text extraction):
```
POST /api/process
{
  "file": "report.pdf",
  "use_ai": false,
  "ocr_mode": "force_local"
}
```

OCR test drop zone (subpath under inbox):
```
POST /api/process
{
  "file": "ocr_tests/sample_scan.pdf",
  "use_ai": true
}
```

Live drop zone (subpath under inbox):
```
POST /api/process
{
  "file": "live/invoice_2025_12.pdf",
  "use_ai": true,
  "ocr_mode": "auto"
}
```

### Pattern 4: Export Data from Shortcut
```
Shortcut: POST to /api/export with {name: "monthly_report", data: [...]}
Result: Saved to /data/exports/monthly_report_2025-12-30.json
```

---

## File Processors

### PDF Processor (`processors/pdf.py`)
- Extracts text from PDF pages
- Extracts tables as structured JSON
- Handles multi-page documents
- Dependencies: `pdfplumber`, `PyMuPDF`

### Mistral OCR Processor (`processors/mistral_ocr.py`)
- Unified OCR for PDFs and images
- Standardized Document JSON output
- Dependencies: `httpx`

### Image Processor (`processors/image.py`)
- OCR text extraction
- Supports PNG, JPG, TIFF
- Dependencies: `pytesseract`, `Pillow`

### Excel Processor (`processors/excel.py`)
- Converts XLSX to clean CSV/JSON
- Handles multiple sheets
- Cleans headers and data types
- Dependencies: `openpyxl`, `pandas`

---

## Configuration

`config.json`:
```json
{
  "host": "127.0.0.1",
  "port": 8000,
  "cors_origins": ["*"],
  "max_file_size_mb": 50,
  "processors": {
    "pdf": {"extract_tables": true},
    "image": {"ocr_language": "eng"},
    "excel": {"default_sheet": 0}
  }
}
```
Note: `max_file_size_mb` and the `processors` settings are not enforced in `server.py` yet.

## API Key Setup (Mistral OCR)

The Mistral OCR integration reads the API key from the environment at runtime.
By default, `/api/process` uses Mistral OCR for PDFs/images unless you set `use_ai: false`
or `ocr_mode: "force_local"`.

PowerShell (current session):
```powershell
$env:MISTRAL_API_KEY="your_key_here"
python server.py
```

Optional .env file (auto-loaded on server start):
```
MISTRAL_API_KEY=your_key_here
```

If `/api/process` is called with `"use_ai": true` and the key is missing, the server returns an error.

More details: docs/mistral/OCR_USAGE.md

---

## Security Notes

- **Bind to 127.0.0.1 only** - not accessible from network
- **No authentication** - localhost trust model
- **No PII in sample data** - use synthetic/anonymized data
- **Stop server when idle** - no need to run 24/7

---

## Workflow: Cursor <-> Shortcut Collaboration

1. **Cursor Agent** creates files, builds endpoints, writes processing scripts
2. **User** starts the server (`python server.py`)
3. **Shortcut AI** fetches data, processes it, populates Excel sheets
4. **Shortcut AI** can POST data back to local system
5. **Iterate** until workflow is production-ready

---

## Dependencies

```
flask>=2.3.0
flask-cors>=4.0.0
pandas>=2.0.0
pdfplumber>=0.10.0
PyMuPDF>=1.23.0
pytesseract>=0.3.10
Pillow>=10.0.0
openpyxl>=3.1.0
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2025-12-30 | Initial structure, static serving, basic API |
| 0.2.0 | 2025-12-30 | Integration testing complete (10/10 tests passing), added 8 new endpoints |

**Integration Testing:** See `docs/integration_testing.md` for detailed test results and proven capabilities.

---

## Roadmap

- [ ] Basic Flask server with static file serving
- [ ] `/api/status` endpoint
- [ ] Sample data generation script
- [ ] PDF processor
- [ ] Excel processor
- [ ] Image/OCR processor
- [ ] POST `/api/export` endpoint
- [ ] POST `/api/process` endpoint
- [ ] File watcher for auto-processing
- [ ] Scheduled script execution


