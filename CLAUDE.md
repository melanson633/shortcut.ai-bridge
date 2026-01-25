# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Shortcut Bridge** is a local HTTP server that bridges the filesystem with Shortcut AI's TypeScript runtime. Shortcut AI can `fetch()` from localhost to import/export data, process files (PDFs, Excel, images), and run bidirectional data pipelines.

**Tech Stack**: Python 3.8+, Flask, pandas, pdfplumber, PyMuPDF, pytesseract, openpyxl, Mistral OCR API

**Deployment**: Local only (127.0.0.1), no external access

## Commands

### Development
```bash
# Start server
python server.py

# Install dependencies
pip install -r requirements.txt

# Run PDF processor test
python test_pdf_processor.py

# Generate sample data
python scripts/generate_sample_data.py

# Check server status
curl http://127.0.0.1:8000/api/status
```

### Testing
The server runs at `http://127.0.0.1:8000`. Test with curl or from Shortcut AI:
```bash
# Health check
curl http://127.0.0.1:8000/api/status

# Fetch static file
curl http://127.0.0.1:8000/data/samples/sales_transactions.csv

# Process a file
curl -X POST http://127.0.0.1:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{"file": "report.pdf", "use_ai": true}'
```

## Architecture

### Core Components

**server.py** (main entry point):
- Flask app with CORS enabled for localhost
- Loads config from `config.json` and `.env` (MISTRAL_API_KEY)
- Routes split into: static files (`/data/`), dynamic API (`/api/`), test endpoints
- All processors are imported on-demand (lazy imports in route handlers)

**Processors** (`/processors/`):
- Each processor follows pattern: `process_{type}(input_path, output_dir, **options) -> output_filename`
- **pdf.py**: Local PDF text/table extraction (pdfplumber)
- **mistral_ocr.py**: Unified AI-based OCR for PDFs and images (Mistral API)
- **image.py**: Local OCR using pytesseract
- **excel.py**: XLSX to clean JSON/CSV with pandas

**Data Flow**:
```
1. Drop file in /inbox/ or /inbox/{subdir}/
2. POST /api/process {"file": "path/to/file.ext", "use_ai": true|false}
3. Processor writes to /data/generated/
4. Shortcut AI fetches from /data/generated/{output_file}
```

### Directory Structure (Critical Paths)

```
/data/
  samples/       - Static test datasets (CSV, JSON, TXT)
  generated/     - Output from processors (PDF->JSON, Excel->CSV)
  exports/       - Data received FROM Shortcut AI (POST /api/export)
/inbox/
  live/          - Production drop zone for real documents
  ocr_tests/     - Testing drop zone for OCR validation
  (files...)     - Default drop zone
/processors/     - File converters (pdf, excel, image, mistral_ocr)
/api/            - Future: complex endpoint modules (currently minimal)
/scripts/        - Standalone Python utilities
/docs/           - Documentation, integration tests, API specs
```

### File Processing Logic

**PDF Processing** (`/api/process` with PDF file):
- If `use_ai: true` (default) → `processors/mistral_ocr.py`
  - Requires `MISTRAL_API_KEY` in environment
  - Returns standardized Document JSON with pages, text, tables
  - Supports `ocr_mode`: "auto", "force_ai", "force_local"
- If `use_ai: false` → `processors/pdf.py`
  - Local extraction with pdfplumber (text + tables)
  - No API key required

**Image Processing** (`/api/process` with image file):
- If `use_ai: true` → `processors/mistral_ocr.py`
- If `use_ai: false` → `processors/image.py` (pytesseract local OCR)

**Excel Processing**:
- Always uses `processors/excel.py` (pandas-based, no AI)

### Key API Endpoints

**Static Files**:
- `GET /data/{path}` - Serve files from /data/ (samples, generated, exports)

**Core API**:
- `GET /api/status` - Server health + file listings from all data directories
- `POST /api/process` - Process file from /inbox/ (see File Processing Logic above)
- `POST /api/export` - Receive data from Shortcut AI, save to /data/exports/

**Test/Integration Endpoints** (used for Shortcut AI integration testing):
- `GET /api/data?filter=x&limit=n` - Query sample data with filters
- `POST /api/echo` - Echo JSON payload (POST testing)
- `POST /api/upload` - FormData file upload (known issue: fails from browser JS)
- `POST /api/upload-base64` - Base64 file upload (recommended workaround)
- `POST /api/analyze` - Full pandas pipeline: receive data → aggregate → return results
- `POST /api/bulk` - Handle large payloads (5000+ rows)
- `POST /api/generate` - Generate data dynamically without pre-existing files
- `GET /api/slow?seconds=N` - Timeout testing (simulates slow operations)
- `GET /api/error` - Returns 500 error (error handling test)

## Development Patterns

### Adding a New Processor

1. Create `/processors/{type}.py` with function signature:
   ```python
   def process_{type}(input_path: Union[str, Path], output_dir: Union[str, Path], **options) -> str:
       """Returns output filename (not full path)"""
   ```

2. Add handler in `server.py` `/api/process` route:
   ```python
   elif ext == ".{new_ext}":
       from processors.{type} import process_{type}
       output_file = process_{type}(input_path, GENERATED_DIR, option1, option2)
   ```

3. Return JSON output to `/data/generated/` for easy fetching

### Adding a New Endpoint

**Simple endpoints**: Add route directly to `server.py`
```python
@app.route("/api/new_endpoint", methods=["GET", "POST"])
def api_new_endpoint():
    # Always return JSON with status field
    return jsonify({"status": "ok", ...})
```

**Complex endpoints**: Create module in `/api/`, import in `server.py`

### Modifying server.py

**WARNING**: When server is running, changes to `server.py` require restart. Always alert user:
1. Tell user to stop server (Ctrl+C)
2. Make changes
3. Ask user to restart with `python server.py`

### Error Handling

All API endpoints follow pattern:
```python
try:
    # Processing logic
    return jsonify({"status": "ok", ...})
except Exception as e:
    return jsonify({"status": "error", "message": str(e)}), 500
```

### Environment Variables

Required for Mistral OCR:
```bash
# PowerShell
$env:MISTRAL_API_KEY="your_key_here"

# Or use .env file (auto-loaded on server start)
MISTRAL_API_KEY=your_key_here
```

## Known Issues & Workarounds

### FormData Upload Fails from Browser
**Issue**: `/api/upload` (FormData multipart) fails when called from browser JavaScript (CORS/security restrictions)

**Workaround**: Use `/api/upload-base64` endpoint instead:
```javascript
// Convert file to base64
const reader = new FileReader();
reader.readAsDataURL(file);
reader.onload = () => {
  const base64 = reader.result.split(',')[1];
  fetch('http://127.0.0.1:8000/api/upload-base64', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filename: file.name, data: base64})
  });
};
```

### Integration Test Results
Proven capabilities (all 10 tests passing as of 2025-12-30):
- Bidirectional communication (read/write)
- Large payloads (5000 rows × 5 columns = 25k cells, 8ms processing)
- Timeout handling (no timeout up to 30+ seconds)
- Query parameters, error handling, pandas pipelines

See `docs/integration_testing.md` for detailed test results.

## Configuration

`config.json` settings:
- `host`, `port`: Server binding (ALWAYS use 127.0.0.1)
- `cors_origins`: CORS policy (default: `["*"]` for localhost)
- `max_file_size_mb`: Documented but not enforced in code yet
- `processors.*`: Settings documented but not fully enforced in code yet

## Security Notes

- **Localhost only**: Server binds to 127.0.0.1 (no network exposure)
- **No authentication**: Trust model assumes localhost is secure
- **No PII in sample data**: Use synthetic/anonymized datasets
- **Stop when idle**: No need to run 24/7

## Agent Learning System

This codebase uses `.cursor-learnings.json` for automated agent knowledge capture. See `.cursorrules` for full protocol details. Key points:

**Auto-log triggers** (mandatory):
- `error_recovery`: You hit an error and fixed it
- `retry_success`: First approach failed, second worked
- `user_correction`: User said "do X instead"
- `time_sink`: Spent >5 tool calls debugging one issue
- `pattern_discovery`: Found a reusable pattern

**Before making changes**:
- Check `.cursor-learnings.json` for `category: "processors"` before modifying `/processors/`
- Check for `category: "endpoints"` before modifying `server.py` or adding routes
- Check for `context.error_type` when debugging

**Rate limits**: Max 5 logs/session, max 2 auto-promotions to `.cursorrules`/session
