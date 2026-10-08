import re
from typing import List, Dict, Any


# =========================================================
# FUTURE / UNANSWERABLE KEYWORDS
# =========================================================

FUTURE_KEYWORDS = [
    "2030",
    "2035",
    "2040",
    "2050",
    "future",
    "tomorrow",
    "next year",
    "next month",
    "will happen",
    "will be",
    "predict",
    "prediction",
    "forecast",
    "forecasting",
]


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# QUESTION KEYWORDS
# =========================================================

def extract_question_keywords(question: str) -> List[str]:

    question = normalize_text(question).lower()

    words = re.findall(r"[a-zA-Z0-9]+", question)

    stop_words = {
        "what", "which", "where", "when", "who", "why", "how",
        "is", "are", "was", "were",
        "the", "a", "an", "of", "to", "from", "in", "on",
        "for", "and", "or", "with",
        "this", "that", "these", "those",
        "can", "could", "does", "do", "did",
        "it", "be", "me", "please",
        "tell", "about", "give", "show",
        "find", "information"
    }

    keywords = []

    for word in words:
        if len(word) >= 2 and word not in stop_words:
            if word not in keywords:
                keywords.append(word)

    return keywords


# =========================================================
# QUESTION TYPE
# =========================================================

def detect_question_type(question: str) -> str:

    q = normalize_text(question).lower()

    if any(word in q for word in [
        "highest",
        "maximum",
        "largest",
        "most",
        "top"
    ]):
        return "highest"

    if any(word in q for word in [
        "lowest",
        "minimum",
        "smallest",
        "least"
    ]):
        return "lowest"

    if any(word in q for word in [
        "how many",
        "count",
        "number of"
    ]):
        return "count"

    if any(word in q for word in [
        "total",
        "sum",
        "overall"
    ]):
        return "total"

    if any(word in q for word in [
        "compare",
        "comparison",
        "difference",
        "higher",
        "lower",
        "more",
        "less"
    ]):
        return "comparison"

    if q.startswith("who"):
        return "person"

    if q.startswith("where"):
        return "location"

    if q.startswith("when"):
        return "time"

    if q.startswith("why"):
        return "explanation"

    if q.startswith("how"):
        return "explanation"

    return "general"


# =========================================================
# FUTURE / UNANSWERABLE DETECTION
# =========================================================

def detect_unanswerable(
    question: str,
    content: str = ""
) -> Dict[str, Any]:

    question = normalize_text(question).lower()
    content = normalize_text(content)

    matched_keywords = []

    for keyword in FUTURE_KEYWORDS:

        if keyword in question:
            matched_keywords.append(keyword)

    if matched_keywords:

        return {
            "answerable": False,
            "reason": (
                "The question asks about a future event or prediction "
                "that cannot be reliably established from the uploaded evidence."
            ),
            "matched_keywords": matched_keywords
        }

    if not content.strip():

        return {
            "answerable": False,
            "reason": "No usable evidence was extracted from the uploaded data.",
            "matched_keywords": []
        }

    return {
        "answerable": True,
        "reason": "",
        "matched_keywords": []
    }


# =========================================================
# SPLIT CONTENT
# =========================================================

def split_content(content: str) -> List[str]:

    content = normalize_text(content)

    if not content:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+|\n+",
        content
    )

    result = []

    for part in parts:

        part = normalize_text(part)

        if part:
            result.append(part)

    return result


# =========================================================
# EVIDENCE SEARCH
# =========================================================

def keyword_evidence(
    question: str,
    content: str,
    max_results: int = 8
) -> List[str]:

    keywords = extract_question_keywords(question)

    sentences = split_content(content)

    if not sentences:
        return []

    scored = []

    for sentence in sentences:

        lower_sentence = sentence.lower()

        score = 0

        for keyword in keywords:

            if keyword in lower_sentence:
                score += 1

        if score > 0:

            scored.append(
                (
                    score,
                    sentence
                )
            )

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    evidence = []

    for _, sentence in scored:

        if sentence not in evidence:

            evidence.append(sentence)

        if len(evidence) >= max_results:
            break

    if not evidence:
        evidence = sentences[:max_results]

    return evidence


# =========================================================
# EXTRACT NUMBERS
# =========================================================

def extract_numbers(text: str) -> List[float]:

    text = normalize_text(text)

    matches = re.findall(
        r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?",
        text
    )

    numbers = []

    for value in matches:

        try:
            numbers.append(float(value))
        except ValueError:
            pass

    return numbers


# =========================================================
# FIND NUMERIC VALUES WITH LABELS
# Example:
# Road A has 120 vehicles
# Road B has 80 vehicles
# =========================================================

def extract_label_value_pairs(content: str):

    pairs = []

    lines = re.split(r"\n|(?<=[.!?])\s+", content)

    for line in lines:

        line = normalize_text(line)

        if not line:
            continue

        numbers = re.findall(
            r"[-+]?\d+(?:\.\d+)?",
            line
        )

        if not numbers:
            continue

        try:
            value = float(numbers[-1])
        except ValueError:
            continue

        # Remove numeric value
        label = re.sub(
            r"[-+]?\d+(?:\.\d+)?",
            "",
            line
        )

        # Remove common words
        label = re.sub(
            r"\b(has|have|is|are|with|vehicles|vehicle|cars|car|"
            r"people|students|marks|score|percentage|percent|"
            r"traffic|count|total)\b",
            " ",
            label,
            flags=re.IGNORECASE
        )

        label = re.sub(r"[^a-zA-Z0-9 ]", " ", label)
        label = re.sub(r"\s+", " ", label).strip()

        if label:
            pairs.append(
                {
                    "label": label,
                    "value": value,
                    "source_line": line
                }
            )

    return pairs


# =========================================================
# HIGHEST / LOWEST
# =========================================================

def find_extreme(
    content: str,
    highest: bool = True
) -> Dict[str, Any]:

    pairs = extract_label_value_pairs(content)

    if not pairs:
        return {
            "found": False,
            "label": "",
            "value": None,
            "source_line": ""
        }

    if highest:
        selected = max(
            pairs,
            key=lambda item: item["value"]
        )
    else:
        selected = min(
            pairs,
            key=lambda item: item["value"]
        )

    return {
        "found": True,
        "label": selected["label"],
        "value": selected["value"],
        "source_line": selected["source_line"]
    }


# =========================================================
# COUNT
# =========================================================

def calculate_count(content: str) -> int:

    lines = split_content(content)

    return len(lines)


# =========================================================
# TOTAL
# =========================================================

def calculate_total(content: str) -> float:

    numbers = extract_numbers(content)

    return sum(numbers)


# =========================================================
# GENERATE ANSWER
# =========================================================

def generate_answer(
    question: str,
    evidence: List[str],
    content: str
) -> str:

    if not evidence:

        return (
            "I could not find enough relevant information "
            "in the uploaded sources to answer this question."
        )

    question_type = detect_question_type(question)

    # -----------------------------------------------------
    # HIGHEST
    # -----------------------------------------------------

    if question_type == "highest":

        result = find_extreme(
            content,
            highest=True
        )

        if result["found"]:

            value = result["value"]

            if float(value).is_integer():
                value = int(value)

            return (
                f"The highest value is **{value}**, "
                f"corresponding to **{result['label']}**."
            )

    # -----------------------------------------------------
    # LOWEST
    # -----------------------------------------------------

    if question_type == "lowest":

        result = find_extreme(
            content,
            highest=False
        )

        if result["found"]:

            value = result["value"]

            if float(value).is_integer():
                value = int(value)

            return (
                f"The lowest value is **{value}**, "
                f"corresponding to **{result['label']}**."
            )

    # -----------------------------------------------------
    # COUNT
    # -----------------------------------------------------

    if question_type == "count":

        return (
            f"The uploaded data contains approximately "
            f"**{calculate_count(content)} relevant line(s)**."
        )

    # -----------------------------------------------------
    # TOTAL
    # -----------------------------------------------------

    if question_type == "total":

        total = calculate_total(content)

        if float(total).is_integer():
            total = int(total)

        return (
            f"The total of the detected numerical values is "
            f"**{total}**."
        )

    # -----------------------------------------------------
    # COMPARISON
    # -----------------------------------------------------

    if question_type == "comparison":

        result_high = find_extreme(
            content,
            highest=True
        )

        result_low = find_extreme(
            content,
            highest=False
        )

        if result_high["found"] and result_low["found"]:

            high_value = result_high["value"]
            low_value = result_low["value"]

            if float(high_value).is_integer():
                high_value = int(high_value)

            if float(low_value).is_integer():
                low_value = int(low_value)

            return (
                f"Comparison result: **{result_high['label']}** "
                f"has the highest value ({high_value}), while "
                f"**{result_low['label']}** has the lowest value "
                f"({low_value})."
            )

        return (
            "Based on the uploaded sources, the relevant "
            "comparison information is: "
            + " ".join(evidence[:3])
        )

    # -----------------------------------------------------
    # GENERAL
    # -----------------------------------------------------

    return " ".join(evidence[:3])


# =========================================================
# BUILD SINGLE-DATA REASONING RESULT
# =========================================================

def build_reasoning_result(
    question: str,
    content: str,
    source: str = "uploaded data"
) -> Dict[str, Any]:

    question = normalize_text(question)
    content = normalize_text(content)

    # -----------------------------------------------------
    # EMPTY QUESTION
    # -----------------------------------------------------

    if not question:

        return {
            "success": False,
            "answer": "Please enter a question.",
            "answerable": False,
            "evidence": [],
            "reasoning": [],
            "confidence": 0,
            "source": source,
            "question_type": "unknown",
            "warning": "Question is empty."
        }

    # -----------------------------------------------------
    # ANSWERABILITY
    # -----------------------------------------------------

    answerability = detect_unanswerable(
        question,
        content
    )

    if not answerability["answerable"]:

        return {
            "success": True,
            "answer": (
                "This question cannot be reliably answered "
                "from the available evidence."
            ),
            "answerable": False,
            "evidence": [],
            "reasoning": [
                "Received the user's question.",
                "Checked the uploaded evidence.",
                answerability["reason"]
            ],
            "confidence": 15,
            "source": source,
            "question_type": detect_question_type(question),
            "warning": answerability["reason"]
        }

    # -----------------------------------------------------
    # EVIDENCE
    # -----------------------------------------------------

    evidence = keyword_evidence(
        question,
        content,
        max_results=8
    )

    # -----------------------------------------------------
    # ANSWER
    # -----------------------------------------------------

    answer = generate_answer(
        question,
        evidence,
        content
    )

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    if len(evidence) >= 4:
        confidence = 92
    elif len(evidence) == 3:
        confidence = 85
    elif len(evidence) == 2:
        confidence = 75
    elif len(evidence) == 1:
        confidence = 65
    else:
        confidence = 30

    # -----------------------------------------------------
    # REASONING
    # -----------------------------------------------------

    question_type = detect_question_type(question)

    reasoning = [
        "Received the user's question.",
        f"Identified the question type as '{question_type}'.",
        f"Analyzed evidence from {source}.",
        f"Found {len(evidence)} relevant evidence item(s).",
        "Applied the appropriate reasoning operation.",
        "Generated the final answer from the available evidence."
    ]

    return {
        "success": True,
        "answer": answer,
        "answerable": True,
        "evidence": evidence,
        "reasoning": reasoning,
        "confidence": confidence,
        "source": source,
        "question_type": question_type,
        "warning": ""
    }


# =========================================================
# MULTIMODAL REASONING
# =========================================================

def build_multimodal_reasoning(
    question: str,
    processed_files: List[Dict[str, Any]]
) -> Dict[str, Any]:

    unified_parts = []

    sources = []

    modalities = []

    # -----------------------------------------------------
    # PROCESS EACH FILE
    # -----------------------------------------------------

    for item in processed_files:

        if not isinstance(item, dict):
            continue

        filename = item.get(
            "filename",
            item.get("name", "Unknown file")
        )

        modality = item.get(
            "modality",
            item.get("type", "unknown")
        )

        content = item.get(
            "content",
            ""
        )

        metadata = item.get(
            "metadata",
            {}
        )

        sources.append(filename)

        if modality not in modalities:
            modalities.append(modality)

        # -------------------------------------------------
        # TEXT / EXTRACTED CONTENT
        # -------------------------------------------------

        if content:

            unified_parts.append(
                f"[SOURCE: {filename}]\n"
                f"[MODALITY: {modality}]\n"
                f"{normalize_text(content)}"
            )

        # -------------------------------------------------
        # METADATA
        # -------------------------------------------------

        if metadata and isinstance(metadata, dict):

            metadata_lines = []

            for key, value in metadata.items():

                if key in {
                    "content",
                    "text",
                    "preview"
                }:
                    continue

                metadata_lines.append(
                    f"{key}: {value}"
                )

            if metadata_lines:

                unified_parts.append(
                    f"[METADATA: {filename}]\n"
                    + "\n".join(metadata_lines)
                )

    # -----------------------------------------------------
    # CREATE UNIFIED CONTEXT
    # -----------------------------------------------------

    unified_context = "\n\n".join(
        unified_parts
    )

    # -----------------------------------------------------
    # NO DATA
    # -----------------------------------------------------

    if not unified_context.strip():

        return {
            "success": False,
            "answer": (
                "I could not extract usable information "
                "from the uploaded files."
            ),
            "answerable": False,
            "evidence": [],
            "reasoning": [
                "Received uploaded files.",
                "Attempted to create a unified multimodal context.",
                "No usable content was available."
            ],
            "confidence": 0,
            "sources": sources,
            "modalities": modalities,
            "source_count": len(sources),
            "unified_context": "",
            "warning": "No usable evidence."
        }

    # -----------------------------------------------------
    # REASON ACROSS ALL SOURCES
    # -----------------------------------------------------

    result = build_reasoning_result(
        question=question,
        content=unified_context,
        source="multiple uploaded sources"
    )

    # -----------------------------------------------------
    # ADD MULTIMODAL INFORMATION
    # -----------------------------------------------------

    result["sources"] = sources

    result["modalities"] = modalities

    result["source_count"] = len(sources)

    result["unified_context"] = unified_context

    # -----------------------------------------------------
    # MULTIMODAL REASONING STEPS
    # -----------------------------------------------------

    result["reasoning"] = [
        f"Received {len(sources)} uploaded source(s).",
        (
            "Detected modalities: "
            + (
                ", ".join(modalities)
                if modalities
                else "unknown"
            )
        ),
        "Created a unified context from all available sources.",
        "Searched the combined context for relevant evidence.",
        "Applied reasoning across the available sources.",
        "Generated the final answer with evidence."
    ]

    return result


# =========================================================
# SINGLE DATA HELPER
# =========================================================

def reason_single(
    question: str,
    content: str,
    source: str = "single uploaded source"
) -> Dict[str, Any]:

    return build_reasoning_result(
        question=question,
        content=content,
        source=source
    )


# =========================================================
# MULTIPLE DATA HELPER
# =========================================================

def reason_multiple(
    question: str,
    processed_files: List[Dict[str, Any]]
) -> Dict[str, Any]:

    return build_multimodal_reasoning(
        question=question,
        processed_files=processed_files
    )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    test_content = """
    Road A has 120 vehicles.
    Road B has 80 vehicles.
    Road C has 45 vehicles.
    """

    questions = [
        "Which road has the highest traffic?",
        "Which road has the lowest traffic?",
        "Compare Road A and Road B.",
        "What is the total?",
        "How many roads are there?",
        "Will Road A have the highest traffic in 2035?"
    ]

    print("\n======================================")
    print("MIRA REASONING ENGINE TEST")
    print("======================================")

    for question in questions:

        result = build_reasoning_result(
            question=question,
            content=test_content,
            source="traffic.txt"
        )

        print("\nQuestion:", question)
        print("Answer:", result["answer"])
        print("Answerable:", result["answerable"])
        print("Confidence:", result["confidence"])
        print("Evidence:", result["evidence"])

    print("\n======================================")
    print("MIRA REASONING TEST COMPLETE")
    print("======================================")