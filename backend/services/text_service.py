import os


def extract_text(file_path):
    """
    Extract text from a TXT file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError("Text file not found.")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        text = file.read()

    text = text.strip()

    if not text:
        raise ValueError("The text file is empty.")

    return {
        "text": text,
        "characters": len(text),
        "lines": len(text.splitlines())
    }


def get_text_preview(text, limit=500):
    """
    Return a short preview for dashboard/debugging.
    """
    if len(text) <= limit:
        return text

    return text[:limit] + "..."