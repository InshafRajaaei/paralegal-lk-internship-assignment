"""PDF text extraction with automatic OCR fallback."""

import pdfplumber
import os

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import io
    OCR_AVAILABLE = True
    
    # Windows: auto-detect Tesseract path
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
    """Extract text from PDF, fallback to OCR if needed."""
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
    
    # If not enough text, try OCR
    if len(extracted_text.strip()) < 100:
        if extraction_error:
            print(f"  [Trying OCR...]")
        elif len(extracted_text.strip()) < 30:
            print(f"  [Minimal text, checking OCR...]")
        
        if OCR_AVAILABLE:
            ocr_text = _extract_text_with_ocr(pdf_path)
            if ocr_text and len(ocr_text) > len(extracted_text):
                extracted_text = ocr_text
        else:
            if len(extracted_text.strip()) == 0:
                print(f"  [OCR not available - install with: pip install pymupdf pytesseract pillow]")
    
    return extracted_text


def _extract_text_with_ocr(pdf_path: str) -> str:
    """Extract text via OCR from PDF pages."""
    if not OCR_AVAILABLE:
        print("  [OCR not available - install with: pip install pymupdf pytesseract pillow]")
        print("  [Also requires system Tesseract installation: https://github.com/UB-Mannheim/tesseract/wiki]")
        return ""
    
    try:
        text_content = []
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        
        # Process first page and last 2-3 pages (judges usually at start/end)
        pages_to_process = []
        if total_pages > 0:
            pages_to_process.append(0)
        if total_pages > 1:
            pages_to_process.extend(range(max(1, total_pages - 2), total_pages))
        pages_to_process = sorted(set(pages_to_process))
        
        for page_num in pages_to_process:
            page = pdf_document[page_num]
            
            # Convert page to image with higher zoom
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))  # 3x zoom for sharper text
            image_data = pix.tobytes("ppm")
            
            img = Image.open(io.BytesIO(image_data))
            
            # Preprocess for better OCR
            if img.mode != 'L':
                img = img.convert('L')
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(3.0)
            
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.2)
            
            img = img.filter(ImageFilter.SHARPEN)
            img = img.filter(ImageFilter.SHARPEN)
            
            threshold = 127
            img = img.point(lambda x: 0 if x < threshold else 255, '1')
            
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
