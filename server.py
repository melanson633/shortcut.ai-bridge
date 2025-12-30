"""
Shortcut Bridge - Local HTTP Server
===================================
Bridges local filesystem with Shortcut AI's TypeScript runtime.

Endpoints:
  GET  /                         → Server info
  GET  /data/<path>              → Static files (samples, generated, exports)
  GET  /api/status               → Server status and available files
  POST /api/process              → Process a file from /inbox/
  POST /api/export               → Receive data from Shortcut AI

Start: python server.py
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

# Load environment variables from .env if present
load_dotenv()

# Load config or use defaults
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        CONFIG = json.load(f)
else:
    CONFIG = {"host": "127.0.0.1", "port": 8000, "debug": True, "cors_origins": ["*"]}

# =============================================================================
# Flask App Setup
# =============================================================================

app = Flask(__name__)
CORS(app, origins=CONFIG.get("cors_origins", ["*"]))

# Directory paths
DATA_DIR = BASE_DIR / "data"
SAMPLES_DIR = DATA_DIR / "samples"
GENERATED_DIR = DATA_DIR / "generated"
EXPORTS_DIR = DATA_DIR / "exports"
INBOX_DIR = BASE_DIR / "inbox"
INBOX_LIVE_DIR = INBOX_DIR / "live"

# Ensure directories exist
for d in [SAMPLES_DIR, GENERATED_DIR, EXPORTS_DIR, INBOX_DIR, INBOX_LIVE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Routes: Static Files
# =============================================================================

@app.route("/")
def index():
    """Server info and available endpoints."""
    return jsonify({
        "name": "Shortcut Bridge",
        "version": "0.2.0",
        "status": "running",
        "time": datetime.now().isoformat(),
        "endpoints": {
            "GET /": "This info",
            "GET /data/<path>": "Fetch static files",
            "GET /api/status": "Server status and file listing",
            "POST /api/process": "Process a file from inbox",
            "POST /api/export": "Receive data from Shortcut"
        }
    })


@app.route("/data/<path:filepath>")
def serve_data(filepath):
    """Serve files from /data/ directory."""
    return send_from_directory(DATA_DIR, filepath)


# =============================================================================
# Routes: API Endpoints
# =============================================================================

@app.route("/api/status")
def api_status():
    """Return server status and available files."""
    def list_files(directory: Path) -> list:
        if not directory.exists():
            return []
        return [
            {
                "name": f.name,
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            for f in directory.iterdir() if f.is_file()
        ]

    def list_subdirs(directory: Path) -> list:
        if not directory.exists():
            return []
        return sorted([f.name for f in directory.iterdir() if f.is_dir()])

    return jsonify({
        "status": "ok",
        "server_time": datetime.now().isoformat(),
        "files": {
            "samples": list_files(SAMPLES_DIR),
            "generated": list_files(GENERATED_DIR),
            "exports": list_files(EXPORTS_DIR),
            "inbox": list_files(INBOX_DIR),
            "inbox_subdirs": list_subdirs(INBOX_DIR),
        }
    })


@app.route("/api/process", methods=["POST"])
def api_process():
    """
    Process a file from /inbox/.
    
    Request body:
        {"file": "filename.pdf", "output_format": "json"}
    
    Returns:
        {"status": "ok", "output_file": "filename.json", "output_path": "/data/generated/filename.json"}
    """
    data = request.get_json() or {}
    filename = data.get("file")
    output_format = data.get("output_format", "json")
    use_ai_raw = data.get("use_ai", True)
    ocr_mode = data.get("ocr_mode", "force_ai")
    pages_raw = data.get("pages")
    table_format = data.get("table_format", "markdown")
    extract_header_raw = data.get("extract_header", False)
    extract_footer_raw = data.get("extract_footer", False)
    include_image_base64_raw = data.get("include_image_base64", False)

    def parse_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value)

    use_ai = parse_bool(use_ai_raw)
    extract_header = parse_bool(extract_header_raw)
    extract_footer = parse_bool(extract_footer_raw)
    include_image_base64 = parse_bool(include_image_base64_raw)

    if isinstance(ocr_mode, str) and ocr_mode.lower() == "force_ai":
        use_ai = True
    if isinstance(ocr_mode, str) and ocr_mode.lower() == "force_local":
        use_ai = False

    pages = None
    if isinstance(pages_raw, list):
        try:
            pages = [int(p) for p in pages_raw]
        except (TypeError, ValueError):
            pages = None
    elif isinstance(pages_raw, str):
        raw_parts = [p.strip() for p in pages_raw.split(",") if p.strip()]
        try:
            pages = [int(p) for p in raw_parts]
        except ValueError:
            pages = None

    if not filename:
        return jsonify({"status": "error", "message": "Missing 'file' parameter"}), 400

    if use_ai and not os.environ.get("MISTRAL_API_KEY"):
        return jsonify({
            "status": "error",
            "message": "Missing MISTRAL_API_KEY in environment. Set it before using use_ai."
        }), 400

    try:
        input_path = (INBOX_DIR / filename).resolve()
        inbox_root = INBOX_DIR.resolve()
        if inbox_root not in input_path.parents and input_path != inbox_root:
            return jsonify({"status": "error", "message": "Invalid file path"}), 400
    except (OSError, ValueError):
        return jsonify({"status": "error", "message": "Invalid file path"}), 400

    if not input_path.exists():
        return jsonify({"status": "error", "message": f"File not found in inbox: {filename}"}), 404
    
    # Determine processor based on file extension
    ext = input_path.suffix.lower()
    
    try:
        if ext == ".pdf":
            if use_ai:
                from processors.mistral_ocr import process_document
                output_file = process_document(
                    input_path,
                    GENERATED_DIR,
                    use_ai=use_ai,
                    ocr_mode=ocr_mode,
                    pages=pages,
                    table_format=table_format,
                    extract_header=extract_header,
                    extract_footer=extract_footer,
                    include_image_base64=include_image_base64,
                )
            else:
                from processors.pdf import process_pdf
                output_file = process_pdf(input_path, GENERATED_DIR, output_format)
        elif ext in [".xlsx", ".xls"]:
            from processors.excel import process_excel
            output_file = process_excel(input_path, GENERATED_DIR, output_format)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            if use_ai:
                from processors.mistral_ocr import process_document
                output_file = process_document(
                    input_path,
                    GENERATED_DIR,
                    use_ai=use_ai,
                    ocr_mode=ocr_mode,
                    pages=pages,
                    table_format=table_format,
                    extract_header=extract_header,
                    extract_footer=extract_footer,
                    include_image_base64=include_image_base64,
                )
            else:
                from processors.image import process_image
                output_file = process_image(input_path, GENERATED_DIR)
        else:
            return jsonify({"status": "error", "message": f"Unsupported file type: {ext}"}), 400
        
        return jsonify({
            "status": "ok",
            "input_file": filename,
            "output_file": output_file,
            "output_path": f"/data/generated/{output_file}"
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def api_export():
    """
    Receive data from Shortcut AI and save locally.
    
    Request body:
        {"name": "report_name", "data": [...], "format": "json"}
    
    Returns:
        {"status": "ok", "saved_to": "report_name_2025-12-30.json"}
    """
    data = request.get_json() or {}
    name = data.get("name", "export")
    export_data = data.get("data")
    fmt = data.get("format", "json")
    
    if export_data is None:
        return jsonify({"status": "error", "message": "Missing 'data' parameter"}), 400
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    if fmt == "json":
        filename = f"{name}_{timestamp}.json"
        output_path = EXPORTS_DIR / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    elif fmt == "csv":
        import pandas as pd
        filename = f"{name}_{timestamp}.csv"
        output_path = EXPORTS_DIR / filename
        df = pd.DataFrame(export_data)
        df.to_csv(output_path, index=False)
    else:
        return jsonify({"status": "error", "message": f"Unsupported format: {fmt}"}), 400
    
    return jsonify({
        "status": "ok",
        "saved_to": filename,
        "full_path": str(output_path)
    })


# =============================================================================
# Routes: Test Endpoints (for Shortcut AI integration testing)
# =============================================================================

@app.route("/api/data")
def api_data():
    """
    Test 2: Query parameters handling.
    
    Query params:
        filter: Filter by region (e.g., "North", "South")
        limit: Max rows to return (default: 50)
    
    Returns filtered sample data from sales_transactions.csv
    """
    import pandas as pd
    
    filter_region = request.args.get("filter", "")
    limit = int(request.args.get("limit", 50))
    
    csv_path = SAMPLES_DIR / "sales_transactions.csv"
    if not csv_path.exists():
        return jsonify({"status": "error", "message": "Sample data not found"}), 404
    
    df = pd.read_csv(csv_path)
    
    if filter_region:
        df = df[df["region"].str.contains(filter_region, case=False, na=False)]
    
    df = df.head(limit)
    
    return jsonify({
        "status": "ok",
        "filter_applied": filter_region or None,
        "limit": limit,
        "row_count": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records")
    })


@app.route("/api/echo", methods=["POST"])
def api_echo():
    """
    Test 3: POST with JSON body - echoes back received data.
    
    Request body: Any JSON
    Returns: Same JSON with metadata
    """
    data = request.get_json() or {}
    
    return jsonify({
        "status": "ok",
        "received_at": datetime.now().isoformat(),
        "content_type": request.content_type,
        "data_size_bytes": len(request.data),
        "echo": data
    })


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Test 6: FormData / file upload handling.
    
    Accepts multipart/form-data with a file.
    Saves to /inbox/ and returns file info.
    """
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file in request"}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"status": "error", "message": "Empty filename"}), 400
    
    # Save to inbox
    save_path = INBOX_DIR / file.filename
    file.save(save_path)
    
    return jsonify({
        "status": "ok",
        "filename": file.filename,
        "saved_to": str(save_path),
        "size_bytes": save_path.stat().st_size,
        "content_type": file.content_type
    })


@app.route("/api/error")
def api_error():
    """
    Test 7: Error handling - returns 500 response.
    
    Used to test how Shortcut AI handles server errors.
    """
    return jsonify({
        "status": "error",
        "message": "Intentional server error for testing",
        "error_code": 500,
        "timestamp": datetime.now().isoformat()
    }), 500


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """
    Test 8: Full pipeline - receive data, process with pandas, return results.
    
    Request body:
        {"data": [...], "aggregations": ["sum", "mean", "count", "by_region"]}
    
    If no data provided, uses sample dataset (100 rows).
    Returns aggregated results for validation against Excel.
    """
    import pandas as pd
    import random
    
    request_data = request.get_json() or {}
    input_data = request_data.get("data")
    aggregations = request_data.get("aggregations", ["sum", "mean", "count", "by_region"])
    
    # If no data provided, generate realistic sample
    if not input_data:
        random.seed(42)  # Reproducible for testing
        regions = ["North", "South", "East", "West"]
        products = ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Service Z"]
        
        input_data = []
        base_date = datetime(2024, 1, 1)
        for i in range(100):
            row = {
                "id": i + 1,
                "date": (base_date + pd.Timedelta(days=i % 90)).strftime("%Y-%m-%d"),
                "product": random.choice(products),
                "region": random.choice(regions),
                "quantity": random.randint(1, 50),
                "unit_price": round(random.uniform(10, 500), 2),
            }
            row["revenue"] = round(row["quantity"] * row["unit_price"], 2)
            input_data.append(row)
    
    df = pd.DataFrame(input_data)
    
    results = {
        "status": "ok",
        "input_rows": len(df),
        "input_columns": list(df.columns),
        "aggregations": {}
    }
    
    # Numeric columns for aggregation
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    
    if "sum" in aggregations and numeric_cols:
        results["aggregations"]["sum"] = df[numeric_cols].sum().to_dict()
    
    if "mean" in aggregations and numeric_cols:
        results["aggregations"]["mean"] = df[numeric_cols].mean().round(2).to_dict()
    
    if "count" in aggregations:
        results["aggregations"]["count"] = len(df)
    
    if "by_region" in aggregations and "region" in df.columns and "revenue" in df.columns:
        by_region = df.groupby("region")["revenue"].agg(["sum", "mean", "count"])
        by_region = by_region.round(2)
        results["aggregations"]["by_region"] = by_region.to_dict(orient="index")
    
    if "by_product" in aggregations and "product" in df.columns and "revenue" in df.columns:
        by_product = df.groupby("product")["revenue"].agg(["sum", "mean", "count"])
        by_product = by_product.round(2)
        results["aggregations"]["by_product"] = by_product.to_dict(orient="index")
    
    # Include raw data for verification
    results["sample_data"] = input_data[:10]  # First 10 rows for spot-checking
    
    return jsonify(results)


@app.route("/api/bulk", methods=["POST"])
def api_bulk():
    """
    Test 9: Large payload handling.
    
    Request body:
        {"data": [...], "validate": true}
    
    Returns row count and processing stats for validation.
    """
    import time
    start_time = time.time()
    
    request_data = request.get_json() or {}
    data = request_data.get("data", [])
    validate = request_data.get("validate", True)
    
    row_count = len(data)
    col_count = len(data[0].keys()) if data and isinstance(data[0], dict) else 0
    cell_count = row_count * col_count
    
    # Basic validation if requested
    validation_result = None
    if validate and data:
        validation_result = {
            "first_row_keys": list(data[0].keys()) if data else [],
            "last_row_keys": list(data[-1].keys()) if data else [],
            "keys_consistent": list(data[0].keys()) == list(data[-1].keys()) if len(data) > 1 else True
        }
    
    elapsed = round(time.time() - start_time, 3)
    
    return jsonify({
        "status": "ok",
        "row_count": row_count,
        "column_count": col_count,
        "cell_count": cell_count,
        "processing_time_seconds": elapsed,
        "validation": validation_result,
        "received_at": datetime.now().isoformat()
    })


@app.route("/api/slow")
def api_slow():
    """
    Test 10: Slow response for timeout testing.
    
    Query params:
        seconds: How long to wait (default: 5, max: 60)
    
    Returns timing info for validation.
    """
    import time
    
    seconds = min(int(request.args.get("seconds", 5)), 60)  # Cap at 60s
    
    started_at = datetime.now()
    time.sleep(seconds)
    completed_at = datetime.now()
    
    elapsed = (completed_at - started_at).total_seconds()
    
    return jsonify({
        "status": "ok",
        "requested_delay": seconds,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "elapsed_seconds": round(elapsed, 3)
    })


@app.route("/api/upload-base64", methods=["POST"])
def api_upload_base64():
    """
    Alternative upload endpoint accepting base64-encoded file content.
    
    Request body:
        {"filename": "doc.pdf", "content_base64": "JVBERi0xLjQK..."}
    
    Saves decoded file to /inbox/
    """
    import base64
    
    data = request.get_json() or {}
    filename = data.get("filename")
    content_b64 = data.get("content_base64")
    
    if not filename:
        return jsonify({"status": "error", "message": "Missing 'filename'"}), 400
    if not content_b64:
        return jsonify({"status": "error", "message": "Missing 'content_base64'"}), 400
    
    try:
        content = base64.b64decode(content_b64)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Invalid base64: {e}"}), 400
    
    save_path = INBOX_DIR / filename
    with open(save_path, "wb") as f:
        f.write(content)
    
    return jsonify({
        "status": "ok",
        "filename": filename,
        "saved_to": str(save_path),
        "size_bytes": len(content)
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """
    Operation-based data generation (no pre-existing file needed).
    
    Request body:
        {"operation": "generate_report", "params": {"rows": 100, "columns": [...]}}
    
    Supported operations:
        - generate_report: Creates sample data with specified rows/columns
        - random_dataset: Generates random test data
    """
    import pandas as pd
    import random
    
    data = request.get_json() or {}
    operation = data.get("operation")
    params = data.get("params", {})
    
    if not operation:
        return jsonify({"status": "error", "message": "Missing 'operation'"}), 400
    
    if operation == "generate_report":
        rows = params.get("rows", 100)
        columns = params.get("columns", ["id", "date", "value", "category"])
        
        # Generate data
        random.seed(params.get("seed", 42))
        categories = ["A", "B", "C", "D"]
        base_date = datetime(2024, 1, 1)
        
        records = []
        for i in range(rows):
            record = {}
            for col in columns:
                if col == "id":
                    record[col] = i + 1
                elif col == "date":
                    record[col] = (base_date + pd.Timedelta(days=i % 365)).strftime("%Y-%m-%d")
                elif col in ["value", "amount", "revenue", "price"]:
                    record[col] = round(random.uniform(10, 1000), 2)
                elif col in ["quantity", "count"]:
                    record[col] = random.randint(1, 100)
                elif col in ["category", "type", "region"]:
                    record[col] = random.choice(categories)
                else:
                    record[col] = f"{col}_{i+1}"
            records.append(record)
        
        return jsonify({
            "status": "ok",
            "operation": operation,
            "row_count": len(records),
            "columns": columns,
            "data": records
        })
    
    elif operation == "random_dataset":
        rows = params.get("rows", 50)
        cols = params.get("cols", 5)
        
        records = [
            {f"col_{j}": random.random() for j in range(cols)}
            for _ in range(rows)
        ]
        
        return jsonify({
            "status": "ok",
            "operation": operation,
            "row_count": len(records),
            "data": records
        })
    
    else:
        return jsonify({
            "status": "error",
            "message": f"Unknown operation: {operation}",
            "supported": ["generate_report", "random_dataset"]
        }), 400


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  SHORTCUT BRIDGE SERVER")
    print("=" * 50)
    print(f"\n  URL: http://{CONFIG['host']}:{CONFIG['port']}")
    print(f"  Data: {DATA_DIR}")
    print(f"  Inbox: {INBOX_DIR}")
    print("\n  Endpoints:")
    print("    GET  /              - Server info")
    print("    GET  /data/<path>   - Static files")
    print("    GET  /api/status    - File listing")
    print("    POST /api/process   - Process inbox file")
    print("    POST /api/export    - Receive from Shortcut")
    print("\n" + "=" * 50 + "\n")
    
    app.run(
        host=CONFIG.get("host", "127.0.0.1"),
        port=CONFIG.get("port", 8000),
        debug=CONFIG.get("debug", True)
    )
