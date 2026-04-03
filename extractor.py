"""PDF extraction module for court decision documents."""

import pdfplumber
import os

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import io
    OCR_AVAILABLE = True
    
    # Try to configure Tesseract path for Windows
    if os.name == 'nt':
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        for path in common_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.pytesseract_cmd = path
                break
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.
    
    First attempts native text extraction using pdfplumber.
    If extraction yields minimal text and OCR is available, falls back to OCR.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Full text content of the PDF
    """
    text_content = []
    extraction_error = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
    except Exception as e:
        extraction_error = e
    
    extracted_text = "\n".join(text_content)
    
    # If native extraction yielded minimal text or failed, try OCR if available
    if len(extracted_text.strip()) < 100:
        if extraction_error:
            print(f"  [Native extraction returned error, attempting OCR...]")
        elif len(extracted_text.strip()) < 30:
            print(f"  [Native extraction returned minimal text ({len(extracted_text)} chars), attempting OCR...]")
        
        if OCR_AVAILABLE:
            ocr_text = _extract_text_with_ocr(pdf_path)
            if ocr_text and len(ocr_text) > len(extracted_text):
                extracted_text = ocr_text
        else:
            if len(extracted_text.strip()) == 0:
                print(f"  [OCR not available - install with: pip install pymupdf pytesseract pillow]")
    
    return extracted_text


def _extract_text_with_ocr(pdf_path: str) -> str:
    """
    Extract text from PDF using OCR (pytesseract).
    
    Focuses on last pages where judge names & signatures typically appear.
    Applies aggressive preprocessing for scanned documents.
    
    Requires: Tesseract OCR system installation + pytesseract, PIL, PyMuPDF Python packages
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Text extracted via OCR (or empty string if OCR unavailable/fails)
    """
    if not OCR_AVAILABLE:
        print("  [OCR not available - install with: pip install pymupdf pytesseract pillow]")
        print("  [Also requires system Tesseract installation: https://github.com/UB-Mannheim/tesseract/wiki]")
        return ""
    
    try:
        text_content = []
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        
        # Focus on last 3 pages (where judges & signatures typically are)
        # But also check first page for "Before:" sections
        pages_to_process = []
        
        # Always include first page (might have "Before: Judge names")
        if total_pages > 0:
            pages_to_process.append(0)
        
        # Include last 2-3 pages (signatures, judge info)
        if total_pages > 1:
            pages_to_process.extend(range(max(1, total_pages - 2), total_pages))
        
        # Remove duplicates and sort
        pages_to_process = sorted(set(pages_to_process))
        
        for page_num in pages_to_process:
            page = pdf_document[page_num]
            
            # Convert page to image with higher zoom
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))  # 3x zoom for sharper text
            image_data = pix.tobytes("ppm")
            
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            # Apply multiple preprocessing steps for better OCR
            # Step 1: Increase contrast significantly
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(3.0)  # Aggressive contrast increase
            
            # Step 2: Enhance brightness
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.2)
            
            # Step 3: Sharpen
            img = img.filter(ImageFilter.SHARPEN)
            img = img.filter(ImageFilter.SHARPEN)  # Apply twice
            
            # Step 4: Convert to binary (black & white) for cleaner text
            threshold = 127
            img = img.point(lambda x: 0 if x < threshold else 255, '1')
            
            # Tesseract OCR config for better text detection
            # psm=6: Assume a single uniform block of text
            # oem=3: Use both legacy and LSTM OCR engine
            config = r'--psm 6 --oem 3'
            
            page_text = pytesseract.image_to_string(img, lang='eng', config=config)
            if page_text:
                text_content.append(page_text)
        
        pdf_document.close()
        return "\n".join(text_content)
    
    except Exception as e:
        print(f"  [OCR extraction failed: {e}]")
        print(f"  [Note: If Tesseract is installed but not in PATH, see TESSERACT_SETUP.md]")
        return ""
