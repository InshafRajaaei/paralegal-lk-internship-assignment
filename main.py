"""Main orchestration script for judge extraction from court decision PDFs."""

import os
import sys
from pathlib import Path
from extractor import extract_text_from_pdf
from parser import extract_bench_judges, extract_author_judges
from output_handler import generate_json_output


def process_pdfs(data_dir: str = "data", output_dir: str = "output") -> None:
    """Process all PDFs in the data folder and extract judges."""
    data_path = Path(data_dir)
    pdf_files = sorted(data_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {data_dir}/")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF file(s) to process.\n")
    
    results = []
    
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        
        # Extract text from PDF
        text = extract_text_from_pdf(str(pdf_file))
        if not text:
            print(f"  [ERROR] Failed to extract text")
            continue
        
        # Extract judges
        bench = extract_bench_judges(text)
        author_judge = extract_author_judges(text)
        
        print(f"  Bench: {bench}")
        print(f"  Author: {author_judge}")
        
        # Generate output
        output_path = generate_json_output(
            pdf_file.name,
            bench,
            author_judge,
            output_dir
        )
        
        if output_path:
            results.append({
                "source": pdf_file.name,
                "output": output_path,
                "bench_count": len(bench),
                "author_count": len(author_judge)
            })
        
        print()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Processing Summary: {len(results)}/{len(pdf_files)} files processed successfully")
    print(f"Output files written to: {output_dir}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    process_pdfs()
