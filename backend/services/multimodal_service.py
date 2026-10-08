import os
import re
import json
import pandas as pd

from PIL import Image
import pytesseract
import cv2

from .text_service import extract_text
from .pdf_service import extract_pdf_text
from .table_service import read_table, table_summary, table_preview
from .image_service import inspect_image
from .audio_service import inspect_audio
from .video_service import inspect_video
from .reasoning_service import build_reasoning_result


# ---------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------

def get_extension(path):
    return os.path.splitext(path)[1].lower()


def get_modality(path):
    ext = get_extension(path)

    if ext in [".txt", ".md"]:
        return "Text"

    if ext == ".pdf":
        return "PDF"

    if ext in [".csv", ".xlsx", ".xls"]:
        return "Table / Excel"

    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        return "Image / Chart"

    if ext in [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"]:
        return "Audio"

    if ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
        return "Video"

    return "Unknown"


# ---------------------------------------------------------
# IMAGE OCR
# ---------------------------------------------------------

def extract_image_ocr(path):
    try:
        image = Image.open(path).convert("RGB")

        text = pytesseract.image_to_string(
            image,
            config="--psm 6"
        )

        return text.strip()

    except Exception as e:
        print("IMAGE OCR ERROR:", e)
        return ""


# ---------------------------------------------------------
# VIDEO FRAME OCR
# ---------------------------------------------------------

def extract_video_ocr(path):
    result = []

    try:
        cap = cv2.VideoCapture(path)

        if not cap.isOpened():
            return ""

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            cap.release()
            return ""

        # Take 5 representative frames
        positions = [
            0,
            int(total_frames * 0.25),
            int(total_frames * 0.50),
            int(total_frames * 0.75),
            max(total_frames - 1, 0)
        ]

        for frame_no in positions:

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)

            success, frame = cap.read()

            if not success:
                continue

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            text = pytesseract.image_to_string(
                gray,
                config="--psm 6"
            ).strip()

            if text:
                result.append(
                    f"Frame {frame_no}:\n{text}"
                )

        cap.release()

    except Exception as e:
        print("VIDEO OCR ERROR:", e)

    return "\n\n".join(result)


# ---------------------------------------------------------
# PROCESS ONE FILE
# ---------------------------------------------------------

def process_file(path):

    filename = os.path.basename(path)
    modality = get_modality(path)
    ext = get_extension(path)

    content = ""
    metadata = {}

    try:

        # ---------------- TEXT ----------------

        if modality == "Text":

            content = extract_text(path)

            if not content:
                content = "No readable text found."

        # ---------------- PDF ----------------

        elif modality == "PDF":

            content = extract_pdf_text(path)

            if not content:
                content = "No readable PDF text found."

        # ---------------- TABLE / EXCEL ----------------

        elif modality == "Table / Excel":

            try:

                df = read_table(path)

                metadata["rows"] = int(len(df))
                metadata["columns"] = int(len(df.columns))

                metadata["columns_list"] = [
                    str(c) for c in df.columns
                ]

                content = table_summary(df)

                preview = table_preview(df)

                if preview:
                    content += "\n\nTABLE PREVIEW:\n"
                    content += str(preview)

                # Include complete table when reasonably small
                if len(df) <= 100:

                    content += "\n\nCOMPLETE TABLE:\n"

                    content += df.to_string(
                        index=False
                    )

            except Exception as e:

                content = (
                    "Unable to read table: "
                    + str(e)
                )

        # ---------------- IMAGE ----------------

        elif modality == "Image / Chart":

            try:

                info = inspect_image(path)

                metadata = info or {}

            except Exception:
                metadata = {}

            ocr = extract_image_ocr(path)

            if ocr:

                content = (
                    "OCR TEXT FROM IMAGE / CHART:\n"
                    + ocr
                )

            else:

                content = (
                    "Image metadata:\n"
                    + json.dumps(
                        metadata,
                        default=str
                    )
                )

        # ---------------- AUDIO ----------------

        elif modality == "Audio":

            try:

                info = inspect_audio(path)

                metadata = info or {}

            except Exception:

                metadata = {}

            # Try common transcript keys
            transcript = ""

            if isinstance(metadata, dict):

                for key in [
                    "transcript",
                    "text",
                    "transcription",
                    "speech_text"
                ]:

                    value = metadata.get(key)

                    if value:
                        transcript = str(value)
                        break

            if transcript:

                content = (
                    "AUDIO TRANSCRIPT:\n"
                    + transcript
                )

            else:

                content = (
                    "Audio metadata:\n"
                    + json.dumps(
                        metadata,
                        default=str
                    )
                    + "\n\n"
                    "No speech transcript is available."
                )

        # ---------------- VIDEO ----------------

        elif modality == "Video":

            try:

                info = inspect_video(path)

                metadata = info or {}

            except Exception:

                metadata = {}

            frame_text = extract_video_ocr(path)

            content = (
                "VIDEO METADATA:\n"
                + json.dumps(
                    metadata,
                    default=str
                )
            )

            if frame_text:

                content += (
                    "\n\nTEXT DETECTED "
                    "IN VIDEO FRAMES:\n"
                    + frame_text
                )

            else:

                content += (
                    "\n\nNo readable text "
                    "was detected in sampled frames."
                )

        else:

            content = "Unsupported source."

    except Exception as e:

        content = (
            "Processing error for "
            + filename
            + ": "
            + str(e)
        )

    return {
        "file": filename,
        "modality": modality,
        "content": content,
        "metadata": metadata
    }


# ---------------------------------------------------------
# FIND NUMERIC ANSWER
# ---------------------------------------------------------

def numeric_reasoning(question, all_sources):

    q = question.lower()

    if not any(
        word in q
        for word in [
            "highest",
            "maximum",
            "max",
            "lowest",
            "minimum",
            "min",
            "total",
            "sum",
            "most",
            "least"
        ]
    ):
        return None

    candidates = []

    for source in all_sources:

        content = source.get(
            "content",
            ""
        )

        lines = content.splitlines()

        for line in lines:

            numbers = re.findall(
                r"[-+]?\d+(?:\.\d+)?",
                line
            )

            if not numbers:
                continue

            for number in numbers:

                try:

                    value = float(number)

                    candidates.append(
                        {
                            "value": value,
                            "line": line.strip(),
                            "file": source["file"]
                        }
                    )

                except Exception:
                    pass

    if not candidates:
        return None

    if "highest" in q or "maximum" in q or "max" in q or "most" in q:

        best = max(
            candidates,
            key=lambda x: x["value"]
        )

        return (
            f"The highest detected value is "
            f"{best['value']} from "
            f"{best['file']}. "
            f"Evidence: {best['line']}"
        )

    if "lowest" in q or "minimum" in q or "min" in q or "least" in q:

        best = min(
            candidates,
            key=lambda x: x["value"]
        )

        return (
            f"The lowest detected value is "
            f"{best['value']} from "
            f"{best['file']}. "
            f"Evidence: {best['line']}"
        )

    if "total" in q or "sum" in q:

        total = sum(
            x["value"]
            for x in candidates
        )

        return (
            f"The detected numeric total is "
            f"{total} across the uploaded sources."
        )

    return None


# ---------------------------------------------------------
# MAIN MULTIMODAL ANALYSIS
# ---------------------------------------------------------

def analyze_multimodal_files(
    file_paths,
    question
):

    processed = []

    # Process EVERY uploaded file
    for path in file_paths:

        item = process_file(path)

        processed.append(item)

    # -----------------------------------------------------
    # BUILD ONE UNIFIED CONTEXT
    # -----------------------------------------------------

    context_parts = []

    for index, item in enumerate(
        processed,
        start=1
    ):

        context_parts.append(
            f"""
==============================
SOURCE {index}
==============================

FILE:
{item['file']}

MODALITY:
{item['modality']}

METADATA:
{json.dumps(
    item['metadata'],
    default=str,
    indent=2
)}

CONTENT / EVIDENCE:
{item['content']}
"""
        )

    unified_context = "\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # RULE-BASED REASONING
    # -----------------------------------------------------

    reasoning_result = build_reasoning_result(
        question=question,
        content=unified_context,
        source="All uploaded multimodal sources"
    )

    if not isinstance(
        reasoning_result,
        dict
    ):
        reasoning_result = {
            "answer": str(
                reasoning_result
            )
        }

    # -----------------------------------------------------
    # NUMERIC CROSS-SOURCE REASONING
    # -----------------------------------------------------

    numeric_answer = numeric_reasoning(
        question,
        processed
    )

    if numeric_answer:

        reasoning_result["answer"] = (
            numeric_answer
        )

    # -----------------------------------------------------
    # EVIDENCE
    # -----------------------------------------------------

    evidence = []

    for item in processed:

        evidence.append(
            {
                "source": item["file"],
                "modality": item["modality"],
                "evidence": item["content"][:3000]
            }
        )

    # -----------------------------------------------------
    # SOURCES
    # -----------------------------------------------------

    sources = [
        item["file"]
        for item in processed
    ]

    modalities = [
        item["modality"]
        for item in processed
    ]

    # -----------------------------------------------------
    # REASONING STEPS
    # -----------------------------------------------------

    reasoning_steps = [
        f"Received {len(processed)} uploaded sources.",
        "Detected the modality of every source.",
        "Extracted available evidence from all sources.",
        "Combined the extracted evidence into one reasoning context.",
        f"Evaluated the evidence against the question: {question}",
        "Generated one combined answer from the available evidence."
    ]

    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    return {

        "success": True,

        "answer": reasoning_result.get(
            "answer",
            "MIRA could not determine a reliable answer from the uploaded evidence."
        ),

        "answerable": reasoning_result.get(
            "answerable",
            True
        ),

        "confidence": reasoning_result.get(
            "confidence",
            "Medium"
        ),

        "evidence": evidence,

        "sources": sources,

        "modalities": modalities,

        "source_count": len(processed),

        "uploaded_files": sources,

        "reasoning": reasoning_result.get(
            "reasoning",
            "Evidence from all uploaded sources was combined before answering."
        ),

        "reasoning_steps": reasoning_steps,

        "modality_details": processed,

        "unified_context": unified_context
    }