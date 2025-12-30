"""
Temporary test script for PDF processor evaluation.
Tests the current processor with a simple PDF if available.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from processors.pdf import process_pdf

def test_processor():
    """Test the PDF processor if a test PDF exists."""
    inbox_dir = Path("inbox")
    generated_dir = Path("data/generated")
    generated_dir.mkdir(parents=True, exist_ok=True)
    
    # Look for any PDF in inbox
    pdf_files = list(inbox_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("[WARNING] No PDF files found in /inbox/")
        print("   To test: Place a PDF file in the inbox directory")
        return False
    
    test_pdf = pdf_files[0]
    print(f"[TEST] Testing with: {test_pdf.name}")
    print(f"   Size: {test_pdf.stat().st_size / 1024:.1f} KB")
    
    try:
        output_file = process_pdf(test_pdf, generated_dir)
        output_path = generated_dir / output_file
        
        print(f"[SUCCESS] Output: {output_file}")
        print(f"   Output size: {output_path.stat().st_size / 1024:.1f} KB")
        
        # Quick peek at output
        import json
        with open(output_path) as f:
            result = json.load(f)
        
        print(f"\n[RESULTS]")
        print(f"   Pages: {result['metadata']['page_count']}")
        print(f"   Tables found: {len(result['tables'])}")
        print(f"   Total text length: {sum(len(p['text']) for p in result['pages'])} chars")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_processor()

