import os
from pypdf import PdfReader


def extract_pdf_text(file_path):
    """
    Extract readable text from a PDF.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError("PDF file not found.")

    reader = PdfReader(file_path)

    pages = []
    page_details = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        text = text.strip()

        if text:
            pages.append(text)

        page_details.append({
            "page": page_number,
            "characters": len(text)
        })

    full_text = "\n\n".join(pages).strip()

    return {
        "text": full_text,
        "page_count": len(reader.pages),
        "pages": page_details,
        "has_text": bool(full_text)
    }


def get_pdf_preview(text, limit=1000):
    if len(text) <= limit:
        return text

    return text[:limit] + "..."