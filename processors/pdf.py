"""
PDF Processor
=============
Extracts text and tables from PDF files.

Dependencies: pdfplumber, PyMuPDF (fitz)
"""

import json
from pathlib import Path
from typing import Union


def process_pdf(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    output_format: str = "json"
) -> str:
    """
    Extract content from PDF and save to output directory.
    
    Args:
        input_path: Path to input PDF file
        output_dir: Directory to save output
        output_format: "json" or "csv"
    
    Returns:
        Output filename
    """
    import pdfplumber
    
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    
    result = {
        "source_file": input_path.name,
        "pages": [],
        "tables": [],
        "metadata": {}
    }
    
    with pdfplumber.open(input_path) as pdf:
        result["metadata"] = {
            "page_count": len(pdf.pages),
        }
        
        for i, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text() or ""
            result["pages"].append({
                "page_number": i + 1,
                "text": text,
                "width": page.width,
                "height": page.height
            })
            
            # Extract tables
            tables = page.extract_tables()
            for j, table in enumerate(tables):
                if table and len(table) > 0:
                    # Use first row as headers if it looks like headers
                    headers = table[0] if table else []
                    rows = table[1:] if len(table) > 1 else []
                    
                    result["tables"].append({
                        "page": i + 1,
                        "table_index": j,
                        "headers": headers,
                        "rows": rows,
                        "row_count": len(rows)
                    })
    
    # Save output
    output_name = input_path.stem + ".json"
    output_path = output_dir / output_name
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return output_name

