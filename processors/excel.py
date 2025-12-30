"""
Excel Processor
===============
Converts Excel files to clean JSON/CSV.

Dependencies: openpyxl, pandas
"""

import json
from pathlib import Path
from typing import Union


def process_excel(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    output_format: str = "json"
) -> str:
    """
    Convert Excel file to JSON or CSV.
    
    Args:
        input_path: Path to input Excel file
        output_dir: Directory to save output
        output_format: "json" or "csv"
    
    Returns:
        Output filename
    """
    import pandas as pd
    
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    
    # Read all sheets
    xlsx = pd.ExcelFile(input_path)
    sheet_names = xlsx.sheet_names
    
    if output_format == "json":
        result = {
            "source_file": input_path.name,
            "sheet_count": len(sheet_names),
            "sheets": {}
        }
        
        for sheet_name in sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            # Convert to records, handling NaN values
            df = df.fillna("")
            result["sheets"][sheet_name] = {
                "columns": list(df.columns),
                "row_count": len(df),
                "data": df.to_dict(orient="records")
            }
        
        output_name = input_path.stem + ".json"
        output_path = output_dir / output_name
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    
    elif output_format == "csv":
        # For CSV, export first sheet only (or all sheets as separate files)
        df = pd.read_excel(xlsx, sheet_name=0)
        output_name = input_path.stem + ".csv"
        output_path = output_dir / output_name
        df.to_csv(output_path, index=False)
    
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    return output_name

