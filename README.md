# Judge Extraction from Sri Lankan Court Decisions

Deterministic extraction system for identifying bench judges and author judges from court decision PDFs, with automatic text/OCR detection.

## Overview

This project extracts judge information from Sri Lankan Supreme Court decisions in JSON format:

- **bench** – All judges listed as part of the bench (coram/present/before)
- **author_judge** – Judge(s) who authored/delivered the final judgment

The system handles both text-based and image-based PDFs automatically with no manual intervention.

## Table of Contents

- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Output Format](#output-format)
- [Approach](#approach)
- [Assumptions](#assumptions)

## Project Structure

```
paralegal-lk-internship-assignment/
├── README.md                 # This file
├── pyproject.toml            # Project config & dependencies
├── main.py                   # Main orchestration script
├── extractor.py              # PDF text extraction with OCR fallback
├── parser.py                 # Judge identification & parsing rules
├── output_handler.py         # JSON output generation
├── .gitignore                # Git exclusions
├── data/                     # Input PDF files
│   ├── sample-judgment-1.pdf
│   ├── sample-judgment-2.pdf
│   ├── sample-judgment-3.pdf
│   └── sample-judgment-4.pdf
└── output/                   # Generated JSON output (created at runtime)
    ├── sample-judgment-1.json
    ├── sample-judgment-2.json
    ├── sample-judgment-3.json
    └── sample-judgment-4.json
```

## Requirements

### System Requirements

- **Python**: 3.11 or higher
- **uv**: Package manager (v0.11.0+)
- **Tesseract OCR**: Required for processing image-based PDFs (sample-judgment-3.pdf is image-based)

#### Tesseract Installation

**Windows**:
```
Download: https://github.com/UB-Mannheim/tesseract/releases/download/v5.4.0.20240606/tesseract-ocr-w64-setup-v5.4.0.20240606.exe
- Run installer with default settings
- Installs to: C:\Program Files\Tesseract-OCR
- Auto-detected by Python script
```

**macOS**:
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update && sudo apt-get install tesseract-ocr
```

**Verify installation**:
```bash
tesseract --version
```

## Setup & Installation

1. **Clone the repository**:
```bash
git clone git clone https://github.com/InshafRajaaei/paralegal-lk-internship-assignment.git
cd paralegal-lk-internship-assignment
```

2. **Install Tesseract OCR** (see Requirements → Tesseract Installation above)

3. **Install Python dependencies**:
```bash
uv sync
```

4. **Verify setup**:
```bash
uv run python --version
tesseract --version
```

## Usage

Run the extraction pipeline:

```bash
uv run python main.py
```

**Process**:
- Automatically discovers all PDF files in `data/` folder
- For each PDF:
  - Extracts text using pdfplumber (native text extraction)
  - Falls back to Tesseract OCR if < 100 characters extracted
  - Identifies bench judges and author judge(s)
  - Writes JSON to `output/` folder with matching filename
- Displays processing status for each file

**Expected output**: Four JSON files in `output/` folder with format shown below

## Output Format

Each PDF generates a JSON file in `output/` with matching filename:

**Example** (sample-judgment-3.json):
```json
{
  "source_file": "sample-judgment-3.pdf",
  "bench": [
    "G.P.S. de Silva",
    "A.R.B. Amarasinghe",
    "P. Ramanathan"
  ],
  "author_judge": [
    "G.P.S. de Silva"
  ]
}
```

**Output fields**:
- `source_file` – Input PDF filename
- `bench` – Array of bench judge names (in document order)
- `author_judge` – Array of author judge names

## Approach

### 1. Automatic PDF Type Detection
The system first attempts native text extraction using pdfplumber. If fewer than 100 characters are extracted, the PDF is classified as image-based and OCR is triggered. This approach ensures efficient processing of text-based documents while automatically handling scanned/image-based PDFs.

### 2. Text Extraction Strategy
For text-based PDFs, pdfplumber extracts raw text directly from the PDF structure. For image-based PDFs, the system converts pages to high-resolution images (3x zoom), applies aggressive preprocessing (3x contrast enhancement, binary conversion), and feeds them to Tesseract OCR with optimized configuration (PSM 6: single text block, OEM 3: legacy+LSTM). The system intelligently focuses on the last 2-3 pages where judge information typically appears.

### 3. Bench Judge Identification
The parser scans for anchor keywords ("Before:", "Present:", "Coram") that typically precede bench listings. Once found, it extracts judge names appearing immediately after until a section break. Judge names are normalized by removing titles and special characters, then deduplicated while preserving order.

### 4. Author Judge Identification
The system uses a two-tier strategy. Primary: detect judges lacking "I agree" statements (indicating they authored the main judgment rather than concurring). Fallback: search for explicit markers ("Judgment by:", "delivered by:") or default to the first bench judge. This handles documents with multiple concurrent opinions gracefully.

### 5. OCR Artifact Cleaning
Image-based PDFs produce common OCR artifacts (e.g., "A.R.B. Amarasinghe, ''" with quote instead of comma, ": . . " prefixes, "mo " corruption). The parser intelligently detects and removes these patterns using targeted regex and character filtering, ensuring accurate judge name extraction even from degraded images.

### 6. JSON Output Generation
The extracted judges and source metadata are serialized to JSON files matching input filenames. Output files are written to the `output/` folder with UTF-8 encoding, enabling easy integration with downstream systems.

**Technical Stack**:
- **pdfplumber** – Native PDF text extraction (text-based PDFs)
- **pdf2image + PyMuPDF** – PDF to image conversion (image preprocessing)
- **pytesseract + Tesseract v5.4.0** – OCR processing (image-based PDFs)
- **Pillow/PIL** – Image preprocessing (zoom, contrast, binary conversion)
- **regex** – Deterministic judge name pattern matching
- **JSON** – Structured output format

## Assumptions

1. **Standard Format**: All court decisions follow standard Sri Lankan Supreme Court judgment formatting with recognizable judge sections (Before/Present/Coram listing).

2. **Judge Name Conventions**: Judge names follow standard patterns (initials + surname, titles like "Chief Justice" or "J.") consistent with Sri Lankan court documents.

3. **Single Author Default**: When author detection is ambiguous, the first listed bench judge is assumed to be the author.

4. **Complete Coverage**: All 4 provided PDFs represent the complete test set; the system is optimized for these specific documents.

5. **PDF Location**: All input PDFs are located in the `data/` folder and in native PDF format (not encrypted or corrupted).

6. **Tesseract Available**: For reproducible results on image-based PDFs, Tesseract OCR must be installed in the system PATH or at standard platform-specific locations (Windows: C:\Program Files\Tesseract-OCR, macOS/Linux: /usr/bin or /usr/local/bin).

7. **No Manual Intervention**: The extraction pipeline runs deterministically end-to-end with no manual editing of results; the same input always produces identical output.
