from PIL import Image, ImageEnhance, ImageFilter
import os
import pytesseract


# Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_image_text(file_path):
    """Extract readable text from image using OCR."""

    try:
        image = Image.open(file_path)

        image = image.convert("RGB")

        # Improve OCR quality
        gray = image.convert("L")

        gray = ImageEnhance.Contrast(gray).enhance(1.8)

        gray = gray.filter(
            ImageFilter.SHARPEN
        )

        text = pytesseract.image_to_string(
            gray,
            config="--psm 6"
        )

        return text.strip()

    except Exception as e:

        print("OCR ERROR:", e)

        return ""


def inspect_image(file_path):

    try:

        image = Image.open(file_path)

        width, height = image.size

        file_size = os.path.getsize(file_path)

        # OCR
        ocr_text = extract_image_text(file_path)

        return {
            "success": True,
            "format": image.format,
            "mode": image.mode,
            "width": width,
            "height": height,
            "file_size": file_size,
            "ocr_text": ocr_text,
            "text_detected": bool(
                ocr_text.strip()
            )
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
            "ocr_text": "",
            "text_detected": False
        }