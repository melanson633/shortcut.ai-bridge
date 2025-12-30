"""
Mistral OCR Processor
=====================
Unified OCR processor for PDFs and images using the Mistral OCR API,
with optional local fallback and a standardized JSON output.
"""

import base64
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx


MISTRAL_OCR_ENDPOINT = "https://api.mistral.ai/v1/ocr"
MISTRAL_OCR_MODEL = "mistral-ocr-latest"

SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp", ".avif"}

logger = logging.getLogger(__name__)


def process_document(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    use_ai: bool = False,
    ocr_mode: str = "auto",
    language: str = "en",
    pages: Optional[List[int]] = None,
    table_format: str = "markdown",
    extract_header: bool = False,
    extract_footer: bool = False,
    include_image_base64: bool = False,
    schema_version: str = "1.0",
) -> str:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_type = _detect_source_type(input_path)
    ocr_mode = (ocr_mode or "auto").lower()

    if ocr_mode == "force_local":
        logger.info("OCR force_local enabled for %s", input_path.name)
        result = _process_local(input_path, source_type, schema_version, language)
    elif ocr_mode == "force_ai":
        logger.info("OCR force_ai enabled for %s", input_path.name)
        result = _process_mistral(
            input_path,
            source_type,
            schema_version,
            language,
            pages,
            table_format,
            extract_header,
            extract_footer,
            include_image_base64,
        )
    else:
        if source_type == "pdf" and use_ai:
            use_mistral = _should_use_mistral_for_pdf(input_path)
        elif source_type == "pdf":
            use_mistral = _should_use_mistral_for_pdf(input_path)
        else:
            use_mistral = use_ai

        if use_mistral:
            logger.info("OCR selected Mistral for %s (mode=%s)", input_path.name, ocr_mode)
            result = _process_mistral(
                input_path,
                source_type,
                schema_version,
                language,
                pages,
                table_format,
                extract_header,
                extract_footer,
                include_image_base64,
            )
        else:
            logger.info("OCR selected local processor for %s (mode=%s)", input_path.name, ocr_mode)
            result = _process_local(input_path, source_type, schema_version, language)

    output_name = f"{input_path.stem}_ocr.json"
    output_path = output_dir / output_name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return output_name


def _detect_source_type(input_path: Path) -> str:
    ext = input_path.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in SUPPORTED_IMAGE_EXTS:
        return "image"
    raise ValueError(f"Unsupported file type for OCR: {ext}")


def _should_use_mistral_for_pdf(input_path: Path) -> bool:
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not available; defaulting to Mistral OCR for %s", input_path.name)
        return True

    with pdfplumber.open(input_path) as pdf:
        if not pdf.pages:
            logger.warning("PDF has no pages; defaulting to Mistral OCR for %s", input_path.name)
            return True

        text_pages = 0
        image_heavy_pages = 0
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if len(text) >= 50:
                text_pages += 1
            if getattr(page, "images", None):
                if len(page.images) > 0 and len(text) < 50:
                    image_heavy_pages += 1

        text_ratio = text_pages / max(len(pdf.pages), 1)
        image_ratio = image_heavy_pages / max(len(pdf.pages), 1)

        if text_ratio < 0.6:
            logger.info(
                "PDF text density low (text_ratio=%.2f) for %s",
                text_ratio,
                input_path.name,
            )
            return True
        if image_ratio >= 0.4:
            logger.info(
                "PDF image density high (image_ratio=%.2f) for %s",
                image_ratio,
                input_path.name,
            )
            return True

    return False


def _process_mistral(
    input_path: Path,
    source_type: str,
    schema_version: str,
    language: str,
    pages: Optional[List[int]],
    table_format: str,
    extract_header: bool,
    extract_footer: bool,
    include_image_base64: bool,
) -> Dict[str, Any]:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("Missing MISTRAL_API_KEY in environment")

    document_type, document_url = _build_document_payload(input_path, source_type)

    payload: Dict[str, Any] = {
        "model": MISTRAL_OCR_MODEL,
        "document": {
            "type": document_type,
            document_type: document_url,
        },
        "table_format": table_format,
        "extract_header": bool(extract_header),
        "extract_footer": bool(extract_footer),
        "include_image_base64": bool(include_image_base64),
    }

    if pages:
        payload["pages"] = pages

    logger.info(
        "Mistral OCR request for %s (type=%s, pages=%s, table_format=%s)",
        input_path.name,
        source_type,
        pages if pages else "all",
        table_format,
    )

    start = time.time()
    response = _mistral_request(payload, api_key)
    elapsed_ms = int((time.time() - start) * 1000)

    return _map_mistral_to_sdj(
        response,
        input_path,
        source_type,
        schema_version,
        language,
        elapsed_ms,
    )


def _mistral_request(payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    timeout = httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=30.0)
    max_attempts = 5
    backoff = 0.5

    for attempt in range(max_attempts):
        try:
            resp = httpx.post(
                MISTRAL_OCR_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except (httpx.TimeoutException, httpx.NetworkError):
            resp = None

        if resp is None:
            _sleep_backoff(attempt, backoff)
            continue

        if resp.status_code in {429, 503, 504}:
            _sleep_backoff(attempt, backoff, retry_after=resp.headers.get("Retry-After"))
            continue

        resp.raise_for_status()
        return resp.json()

    raise RuntimeError("Mistral OCR request failed after retries")


def _sleep_backoff(attempt: int, base: float, retry_after: Optional[str] = None) -> None:
    if retry_after:
        try:
            delay = float(retry_after)
        except ValueError:
            delay = base * (2 ** attempt)
    else:
        delay = base * (2 ** attempt)

    jitter = delay * 0.2
    time.sleep(max(0.0, delay - jitter))


def _build_document_payload(input_path: Path, source_type: str) -> (str, str):
    mime = _guess_mime_type(input_path)
    encoded = _encode_base64(input_path)

    if source_type == "pdf":
        return "document_url", f"data:{mime};base64,{encoded}"
    return "image_url", f"data:{mime};base64,{encoded}"


def _encode_base64(input_path: Path) -> str:
    with open(input_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii")


def _guess_mime_type(input_path: Path) -> str:
    ext = input_path.suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".tiff":
        return "image/tiff"
    if ext == ".bmp":
        return "image/bmp"
    if ext == ".gif":
        return "image/gif"
    if ext == ".webp":
        return "image/webp"
    if ext == ".avif":
        return "image/avif"
    return "application/octet-stream"


def _map_mistral_to_sdj(
    response: Dict[str, Any],
    input_path: Path,
    source_type: str,
    schema_version: str,
    language: str,
    elapsed_ms: int,
) -> Dict[str, Any]:
    pages_out: List[Dict[str, Any]] = []

    for page in response.get("pages", []):
        markdown = page.get("markdown") or ""
        pages_out.append({
            "page_number": int(page.get("index", 0)) + 1,
            "width": page.get("dimensions", {}).get("width"),
            "height": page.get("dimensions", {}).get("height"),
            "text": _markdown_to_text(markdown),
            "markdown": markdown,
            "blocks": [],
            "tables": _map_tables(page.get("tables", [])),
            "images": page.get("images", []),
            "hyperlinks": page.get("hyperlinks", []),
        })

    table_count = sum(len(page.get("tables") or []) for page in response.get("pages", []))
    image_count = sum(len(page.get("images") or []) for page in response.get("pages", []))
    logger.info(
        "Mistral OCR response for %s: pages=%d tables=%d images=%d",
        input_path.name,
        len(pages_out),
        table_count,
        image_count,
    )

    return {
        "schema_version": schema_version,
        "source_file": input_path.name,
        "source_type": source_type,
        "processor": "mistral_ocr",
        "pages": pages_out,
        "metadata": {
            "page_count": len(pages_out),
            "language": language,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ocr_runtime_ms": elapsed_ms,
            "model": response.get("model", MISTRAL_OCR_MODEL),
            "usage_info": response.get("usage_info", {}),
            "warnings": [],
        },
        "raw": {
            "provider": "mistral",
            "response": response,
        },
    }


def _map_tables(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mapped = []
    for table in tables or []:
        mapped.append({
            "table_id": table.get("id"),
            "format": table.get("format"),
            "content": table.get("content"),
            "bbox": table.get("bbox", [0, 0, 0, 0]),
        })
    return mapped


def _markdown_to_text(markdown: str) -> str:
    if not markdown:
        return ""

    text = re.sub(r"^#{1,6}\s*", "", markdown, flags=re.MULTILINE)
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _process_local(
    input_path: Path,
    source_type: str,
    schema_version: str,
    language: str,
) -> Dict[str, Any]:
    if source_type == "pdf":
        return _process_pdf_local(input_path, schema_version, language)
    return _process_image_local(input_path, schema_version, language)


def _process_pdf_local(input_path: Path, schema_version: str, language: str) -> Dict[str, Any]:
    import pdfplumber

    pages_out: List[Dict[str, Any]] = []

    with pdfplumber.open(input_path) as pdf:
        for index, page in enumerate(pdf.pages):
            text = (page.extract_text() or "").strip()
            tables = page.extract_tables()
            mapped_tables = []
            for table in tables or []:
                mapped_tables.append({
                    "table_id": None,
                    "format": "markdown",
                    "content": _table_to_markdown(table),
                    "bbox": [0, 0, 0, 0],
                })

            pages_out.append({
                "page_number": index + 1,
                "width": page.width,
                "height": page.height,
                "text": text,
                "markdown": text,
                "blocks": [],
                "tables": mapped_tables,
                "images": [],
                "hyperlinks": [],
            })

    return {
        "schema_version": schema_version,
        "source_file": input_path.name,
        "source_type": "pdf",
        "processor": "pdfplumber",
        "pages": pages_out,
        "metadata": {
            "page_count": len(pages_out),
            "language": language,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ocr_runtime_ms": None,
            "model": None,
            "usage_info": {},
            "warnings": [],
        },
        "raw": {
            "provider": "local",
            "response": {},
        },
    }


def _process_image_local(input_path: Path, schema_version: str, language: str) -> Dict[str, Any]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Image processing requires pytesseract and Pillow. "
            "Install with: pip install pytesseract Pillow"
        ) from exc

    img = Image.open(input_path)
    text = pytesseract.image_to_string(img, lang=language).strip()

    pages_out = [{
        "page_number": 1,
        "width": img.width,
        "height": img.height,
        "text": text,
        "markdown": text,
        "blocks": [],
        "tables": [],
        "images": [],
        "hyperlinks": [],
    }]

    return {
        "schema_version": schema_version,
        "source_file": input_path.name,
        "source_type": "image",
        "processor": "tesseract",
        "pages": pages_out,
        "metadata": {
            "page_count": 1,
            "language": language,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ocr_runtime_ms": None,
            "model": None,
            "usage_info": {},
            "warnings": [],
        },
        "raw": {
            "provider": "local",
            "response": {},
        },
    }


def _table_to_markdown(table: List[List[Any]]) -> str:
    if not table:
        return ""

    headers = table[0]
    rows = table[1:] if len(table) > 1 else []

    def _row(values: List[Any]) -> str:
        return "| " + " | ".join(str(v or "").strip() for v in values) + " |"

    header_row = _row(headers)
    separator = "| " + " | ".join(["---"] * len(headers)) + " |"
    row_lines = [_row(row) for row in rows]

    return "\n".join([header_row, separator] + row_lines)
