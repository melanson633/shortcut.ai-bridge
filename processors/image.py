"""
Image Processor (OCR)
=====================
Extracts text from images using OCR.

Dependencies: pytesseract, Pillow

Note: Requires Tesseract OCR to be installed on the system.
      Windows: https://github.com/UB-Mannheim/tesseract/wiki
      Add to PATH or set pytesseract.pytesseract.tesseract_cmd
"""

import json
from pathlib import Path
from typing import Union


def process_image(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    language: str = "eng"
) -> str:
    """
    Extract text from image using OCR.
    
    Args:
        input_path: Path to input image file
        output_dir: Directory to save output
        language: OCR language code (default: "eng")
    
    Returns:
        Output filename
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise ImportError(
            "Image processing requires pytesseract and Pillow. "
            "Install with: pip install pytesseract Pillow"
        ) from e
    
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    
    # Open and process image
    img = Image.open(input_path)
    
    # Extract text
    text = pytesseract.image_to_string(img, lang=language)
    
    # Get image info
    result = {
        "source_file": input_path.name,
        "image_size": {
            "width": img.width,
            "height": img.height
        },
        "format": img.format,
        "mode": img.mode,
        "ocr_language": language,
        "extracted_text": text.strip(),
        "line_count": len(text.strip().split("\n")) if text.strip() else 0
    }
    
    # Save output
    output_name = input_path.stem + "_ocr.json"
    output_path = output_dir / output_name
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return output_name

