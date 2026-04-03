"""Output generation for extracted judge information."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any


def generate_json_output(
    source_file: str, 
    bench: List[str], 
    author_judge: List[str],
    output_dir: str = "output"
) -> str:
    """
    Generate JSON output file for extracted judges.
    
    Args:
        source_file: Name of the source PDF file (e.g., "sample-judgment-1.pdf")
        bench: List of judge names on the bench
        author_judge: List of judge names who authored the judgment
        output_dir: Directory to write output files to
        
    Returns:
        Path to the generated JSON file
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    base_name = Path(source_file).stem  # Remove .pdf extension
    output_filename = f"{base_name}.json"
    output_path = os.path.join(output_dir, output_filename)
    
    # Create output data structure
    output_data: Dict[str, Any] = {
        "source_file": source_file,
        "bench": bench,
        "author_judge": author_judge
    }
    
    # Write JSON file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Generated: {output_path}")
    except Exception as e:
        print(f"[ERROR] Error writing {output_path}: {e}")
        return ""
    
    return output_path
