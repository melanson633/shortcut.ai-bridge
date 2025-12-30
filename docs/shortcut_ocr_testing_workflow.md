# Shortcut Agent OCR Testing Workflow

**Purpose:** Comprehensive testing workflow for Shortcut agents to validate Mistral OCR outputs via the Shortcut Bridge API.

**Last Updated:** 2025-12-30  
**Server Version:** 0.2.0

---

## 1. Gap Analysis

### Missing Testing Components

- **No systematic validation workflow**: Current docs show how to call `/api/process` but don't provide a repeatable validation sequence for Shortcut agents
- **No SDJ schema validation**: No checks for required fields (`schema_version`, `source_file`, `source_type`, `processor`, `pages`, `metadata`, `raw`)
- **No page-level validation**: Missing checks for required page fields (`page_number`, `width`, `height`, `text`, `markdown`, `blocks`, `tables`, `images`, `hyperlinks`)
- **No error handling tests**: No examples for handling API failures, missing API keys, or invalid file paths
- **No test matrix**: No organized approach to testing different PDF types (small/large, scanned/digital, with/without tables)
- **No result polling**: No guidance on handling async OCR processing (waiting for results)
- **No metadata validation**: Missing checks for `metadata.page_count` matching `pages.length`, `ocr_runtime_ms` presence, etc.

### File References

- `server.py:132-256` - `/api/process` endpoint implementation
- `processors/mistral_ocr.py:288-341` - SDJ mapping function showing required structure
- `docs/mistral/OCR_USAGE.md` - Current OCR usage docs (lacks validation steps)
- `docs/integration_testing.md` - Integration tests exist but don't cover OCR validation workflow

---

## 2. Proposed Testing Workflow

### Phase 1: Setup & Discovery

**Step 1: Check server status**
- GET `/api/status` to verify server is running
- Verify `inbox_subdirs` includes `ocr_tests` and `live`
- Verify `MISTRAL_API_KEY` is configured (check for 400 error on process without key)

**Step 2: List available test files**
- GET `/api/status` and inspect `files.inbox` for PDFs
- Filter for files in `ocr_tests/` subdirectory

### Phase 2: File Upload (if needed)

**Step 3: Upload test PDF via base64** (if file doesn't exist in inbox)
- POST `/api/upload-base64` with `{filename: "ocr_tests/test.pdf", content_base64: "..."}`
- Verify response: `{status: "ok", saved_to: "ocr_tests/test.pdf"}`

### Phase 3: Process Request

**Step 4: Submit OCR processing request**
- POST `/api/process` with default parameters (use_ai=true, ocr_mode=force_ai)
- Store `output_file` from response for next step
- Handle errors: 400 (missing file/API key), 500 (processing failure)

**Step 5: Wait for processing** (if async)
- Poll `/api/status` until `files.generated` includes expected `_ocr.json` file
- Or implement timeout (max 60 seconds based on Mistral limits)

### Phase 4: Fetch & Validate Results

**Step 6: Fetch OCR result**
- GET `/data/generated/{output_file}` (e.g., `test_ocr.json`)
- Parse JSON response

**Step 7: Validate SDJ schema (top-level)**
- Check `schema_version` exists and equals "1.0"
- Check `source_file` matches input filename
- Check `source_type` is "pdf" or "image"
- Check `processor` is "mistral_ocr"
- Check `pages` is an array
- Check `metadata` object exists
- Check `raw` object exists with `provider: "mistral"`

**Step 8: Validate metadata**
- Check `metadata.page_count` matches `pages.length`
- Check `metadata.created_at` is valid ISO8601 timestamp
- Check `metadata.ocr_runtime_ms` is a number > 0
- Check `metadata.model` is "mistral-ocr-latest"
- Check `metadata.language` exists

**Step 9: Validate pages array**
- For each page in `pages`:
  - Check `page_number` is a positive integer
  - Check `width` and `height` are positive numbers
  - Check `text` is a string (may be empty)
  - Check `markdown` is a string (may be empty)
  - Check `blocks` is an array
  - Check `tables` is an array
  - Check `images` is an array
  - Check `hyperlinks` is an array

**Step 10: Content validation (optional)**
- For scanned PDFs: verify `text` contains non-empty content
- For PDFs with tables: verify at least one `tables` entry exists
- For PDFs with images: verify `images` array structure

### Phase 5: Error Handling Tests

**Step 11: Test missing file**
- POST `/api/process` with `{file: "nonexistent.pdf"}`
- Expect 404 with `{status: "error", message: "File not found..."}`

**Step 12: Test missing API key** (if possible)
- Temporarily unset `MISTRAL_API_KEY`
- POST `/api/process` with `{file: "test.pdf", use_ai: true}`
- Expect 400 with `{status: "error", message: "Missing MISTRAL_API_KEY..."}`

**Step 13: Test invalid file type**
- POST `/api/process` with `{file: "test.txt"}`
- Expect 400 with `{status: "error", message: "Unsupported file type..."}`

---

## 3. Test Matrix

| Test ID | PDF Type | Size | Pages | Content Type | Expected Tables | Expected Images | Validation Focus |
|---------|----------|------|-------|--------------|-----------------|-----------------|------------------|
| T1 | Digital PDF | Small (<1MB) | 1-3 | Text-heavy | 0 | 0 | Basic SDJ schema, text extraction |
| T2 | Digital PDF | Medium (1-5MB) | 5-10 | Mixed (text + tables) | 1-3 | 0-2 | Table extraction, markdown format |
| T3 | Digital PDF | Large (5-20MB) | 20+ | Complex layout | 5+ | 5+ | Page count accuracy, performance |
| T4 | Scanned PDF | Small (<2MB) | 1-3 | Image-based | 0 | 0 | OCR accuracy, text quality |
| T5 | Scanned PDF | Medium (2-10MB) | 5-10 | Tables in images | 1-3 | 0 | Table OCR accuracy |
| T6 | Mixed PDF | Medium | 5-10 | Digital + scanned pages | 2-5 | 2-5 | Hybrid processing |
| T7 | Image (PNG/JPG) | Small (<5MB) | 1 | Single page | 0-1 | 0-1 | Image OCR, single page handling |
| T8 | Multi-page TIFF | Medium | 5-10 | Scanned document | 0-2 | 0 | Multi-page image handling |

**Test Scenarios:**
- **T1-T3**: Test digital PDFs (text extraction should be fast, high accuracy)
- **T4-T5**: Test scanned PDFs (OCR required, slower, accuracy varies)
- **T6**: Test mixed documents (some pages digital, some scanned)
- **T7-T8**: Test image inputs (different from PDF processing path)

---

## 4. Example Shortcut Fetch Snippets

### Basic OCR Processing Flow

```typescript
// Step 1: Check server status
const status = await (await fetch("http://127.0.0.1:8000/api/status")).json();
console.log("Server status:", status.status); // Should be "ok"
console.log("Available PDFs:", status.files.inbox.filter(f => f.name.endsWith('.pdf')));

// Step 2: Process PDF with default Mistral OCR
const processResponse = await (await fetch("http://127.0.0.1:8000/api/process", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    file: "ocr_tests/sample.pdf",
    // use_ai: true (default),
    // ocr_mode: "force_ai" (default)
  })
})).json();

if (processResponse.status !== "ok") {
  throw new Error(`Processing failed: ${processResponse.message}`);
}

const outputFile = processResponse.output_file; // e.g., "sample_ocr.json"

// Step 3: Fetch OCR result
const ocrResult = await (await fetch(
  `http://127.0.0.1:8000/data/generated/${outputFile}`
)).json();

// Step 4: Validate SDJ schema
function validateSDJ(doc: any): {valid: boolean, errors: string[]} {
  const errors: string[] = [];
  
  // Top-level required fields
  if (!doc.schema_version) errors.push("Missing schema_version");
  if (doc.schema_version !== "1.0") errors.push(`Invalid schema_version: ${doc.schema_version}`);
  if (!doc.source_file) errors.push("Missing source_file");
  if (!doc.source_type) errors.push("Missing source_type");
  if (doc.source_type !== "pdf" && doc.source_type !== "image") {
    errors.push(`Invalid source_type: ${doc.source_type}`);
  }
  if (!doc.processor) errors.push("Missing processor");
  if (doc.processor !== "mistral_ocr") errors.push(`Invalid processor: ${doc.processor}`);
  if (!Array.isArray(doc.pages)) errors.push("Missing or invalid pages array");
  if (!doc.metadata) errors.push("Missing metadata");
  if (!doc.raw) errors.push("Missing raw");
  
  // Metadata validation
  if (doc.metadata) {
    if (doc.metadata.page_count !== doc.pages.length) {
      errors.push(`Page count mismatch: metadata.page_count=${doc.metadata.page_count}, pages.length=${doc.pages.length}`);
    }
    if (!doc.metadata.created_at) errors.push("Missing metadata.created_at");
    if (typeof doc.metadata.ocr_runtime_ms !== "number" || doc.metadata.ocr_runtime_ms <= 0) {
      errors.push("Invalid or missing metadata.ocr_runtime_ms");
    }
    if (doc.metadata.model !== "mistral-ocr-latest") {
      errors.push(`Invalid model: ${doc.metadata.model}`);
    }
  }
  
  // Page validation
  doc.pages.forEach((page: any, idx: number) => {
    if (typeof page.page_number !== "number" || page.page_number < 1) {
      errors.push(`Page ${idx}: Invalid page_number`);
    }
    if (typeof page.width !== "number" || page.width <= 0) {
      errors.push(`Page ${idx}: Invalid width`);
    }
    if (typeof page.height !== "number" || page.height <= 0) {
      errors.push(`Page ${idx}: Invalid height`);
    }
    if (typeof page.text !== "string") errors.push(`Page ${idx}: Missing text`);
    if (typeof page.markdown !== "string") errors.push(`Page ${idx}: Missing markdown`);
    if (!Array.isArray(page.blocks)) errors.push(`Page ${idx}: Missing blocks array`);
    if (!Array.isArray(page.tables)) errors.push(`Page ${idx}: Missing tables array`);
    if (!Array.isArray(page.images)) errors.push(`Page ${idx}: Missing images array`);
    if (!Array.isArray(page.hyperlinks)) errors.push(`Page ${idx}: Missing hyperlinks array`);
  });
  
  return {valid: errors.length === 0, errors};
}

const validation = validateSDJ(ocrResult);
if (!validation.valid) {
  console.error("SDJ validation failed:", validation.errors);
} else {
  console.log("✅ SDJ validation passed");
  console.log(`Processed ${ocrResult.metadata.page_count} pages in ${ocrResult.metadata.ocr_runtime_ms}ms`);
}
```

### Error Handling Example

```typescript
// Test missing file
try {
  const errorResponse = await (await fetch("http://127.0.0.1:8000/api/process", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({file: "nonexistent.pdf"})
  }));
  
  if (errorResponse.status === 404) {
    const error = await errorResponse.json();
    console.log("Expected error:", error.message); // "File not found in inbox: nonexistent.pdf"
  }
} catch (e) {
  console.error("Network error:", e);
}

// Test missing API key (if testing without .env)
try {
  const errorResponse = await (await fetch("http://127.0.0.1:8000/api/process", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      file: "test.pdf",
      use_ai: true
    })
  }));
  
  if (errorResponse.status === 400) {
    const error = await errorResponse.json();
    if (error.message.includes("MISTRAL_API_KEY")) {
      console.log("Expected API key error:", error.message);
    }
  }
} catch (e) {
  console.error("Error:", e);
}
```

### Polling for Results (if async)

```typescript
async function waitForOCRResult(expectedFile: string, maxWaitSeconds: number = 60): Promise<any> {
  const startTime = Date.now();
  const maxWait = maxWaitSeconds * 1000;
  
  while (Date.now() - startTime < maxWait) {
    const status = await (await fetch("http://127.0.0.1:8000/api/status")).json();
    const generatedFiles = status.files.generated || [];
    
    const found = generatedFiles.find((f: any) => f.name === expectedFile);
    if (found) {
      // File exists, fetch it
      return await (await fetch(
        `http://127.0.0.1:8000/data/generated/${expectedFile}`
      )).json();
    }
    
    // Wait 1 second before next poll
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  throw new Error(`Timeout: ${expectedFile} not found after ${maxWaitSeconds}s`);
}

// Usage
const result = await waitForOCRResult("sample_ocr.json", 60);
```

### Complete Test Sequence

```typescript
async function testOCRWorkflow(testPdfPath: string) {
  console.log(`Testing OCR workflow for: ${testPdfPath}`);
  
  // 1. Check server
  const status = await (await fetch("http://127.0.0.1:8000/api/status")).json();
  if (status.status !== "ok") throw new Error("Server not available");
  
  // 2. Process PDF
  const processRes = await (await fetch("http://127.0.0.1:8000/api/process", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({file: testPdfPath})
  })).json();
  
  if (processRes.status !== "ok") {
    throw new Error(`Processing failed: ${processRes.message}`);
  }
  
  // 3. Fetch result (with polling if needed)
  const ocrResult = await waitForOCRResult(processRes.output_file, 60);
  
  // 4. Validate
  const validation = validateSDJ(ocrResult);
  if (!validation.valid) {
    throw new Error(`Validation failed: ${validation.errors.join(", ")}`);
  }
  
  // 5. Content checks
  console.log(`✅ Processed ${ocrResult.metadata.page_count} pages`);
  console.log(`✅ Runtime: ${ocrResult.metadata.ocr_runtime_ms}ms`);
  console.log(`✅ Total tables: ${ocrResult.pages.reduce((sum, p) => sum + p.tables.length, 0)}`);
  console.log(`✅ Total images: ${ocrResult.pages.reduce((sum, p) => sum + p.images.length, 0)}`);
  
  return ocrResult;
}

// Run test
testOCRWorkflow("ocr_tests/sample.pdf").then(result => {
  console.log("Test passed!");
}).catch(err => {
  console.error("Test failed:", err);
});
```

---

## 5. Implementation Notes

### Required SDJ Fields Summary

**Top-level:**
- `schema_version` (string, must be "1.0")
- `source_file` (string, filename)
- `source_type` (string, "pdf" | "image")
- `processor` (string, "mistral_ocr")
- `pages` (array of page objects)
- `metadata` (object)
- `raw` (object with `provider: "mistral"`)

**Metadata:**
- `page_count` (number, must match `pages.length`)
- `created_at` (ISO8601 timestamp)
- `ocr_runtime_ms` (number > 0)
- `model` (string, "mistral-ocr-latest")
- `language` (string)

**Page objects:**
- `page_number` (number >= 1)
- `width` (number > 0)
- `height` (number > 0)
- `text` (string)
- `markdown` (string)
- `blocks` (array)
- `tables` (array)
- `images` (array)
- `hyperlinks` (array)

### Testing Recommendations

1. **Start with T1** (small digital PDF) to validate basic flow
2. **Progress to T4** (scanned PDF) to test OCR accuracy
3. **Test T2/T5** (tables) to validate table extraction
4. **Use T3/T6** for stress testing (large files, complex layouts)
5. **Test error cases** (missing files, invalid types) to ensure graceful failures

### Integration Points

- Validation function can be reused across all test cases
- Polling logic handles async processing (though current implementation is synchronous)
- Error handling examples cover common failure modes
- Test matrix provides systematic coverage of PDF types

---

## References

- **Server Code:** `server.py`
- **OCR Processor:** `processors/mistral_ocr.py`
- **OCR Usage Docs:** `docs/mistral/OCR_USAGE.md`
- **Integration Tests:** `docs/integration_testing.md`
- **Shortcut Context:** `docs/shortcut_context.txt`

