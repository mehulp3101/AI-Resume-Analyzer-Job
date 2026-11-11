"""Extract selectable resume text from a PDF kept in memory."""
from io import BytesIO

MAX_PDF_BYTES = 1_000_000
MAX_PDF_PAGES = 15
MAX_TEXT_LENGTH = 200_000


def extract_pdf_text(data):
    if not data.startswith(b'%PDF-'):
        raise ValueError('This is not a valid PDF file. Choose a PDF or TXT resume.')
    from pypdf import PdfReader
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ValueError('This PDF is password-protected. Choose an unlocked copy.')
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError('Choose a PDF with no more than 15 pages.')
        parts, length = [], 0
        for page in reader.pages:
            part = page.extract_text() or ''
            length += len(part) + bool(parts)
            if length > MAX_TEXT_LENGTH:
                raise ValueError('The extracted text exceeds 200,000 characters.')
            parts.append(part)
    except ValueError as error:
        # Only show deliberate validation errors, not parser internals.
        if str(error) in {
            'This PDF is password-protected. Choose an unlocked copy.',
            'Choose a PDF with no more than 15 pages.',
            'The extracted text exceeds 200,000 characters.',
        }:
            raise
        raise ValueError('Could not read this PDF. Try another copy.') from None
    except Exception:
        raise ValueError('Could not read this PDF. Try another copy.') from None
    text = '\n'.join(parts).strip()
    if not text:
        raise ValueError('No selectable text found. Scanned PDFs need OCR. Paste the resume text instead.')
    return text
