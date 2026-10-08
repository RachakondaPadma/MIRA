
import random
import smtplib
import time
from email.message import EmailMessage

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ============================================================
# MIRA SERVICES
# ============================================================

from services.text_service import extract_text
from services.pdf_service import extract_pdf_text
from services.table_service import read_table, table_summary, table_preview
from services.image_service import inspect_image
from services.audio_service import inspect_audio
from services.video_service import inspect_video
from services.reasoning_service import build_reasoning_result
from services.multimodal_service import analyze_multimodal_files


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)
CORS(app)

# Maximum upload size = 100 MB
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# ============================================================
# FOLDERS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    "txt",

    "pdf",

    "csv",
    "xlsx",
    "xls",

    "jpg",
    "jpeg",
    "png",
    "webp",
    "bmp",

    "mp3",
    "wav",
    "m4a",
    "ogg",
    "flac",
    "aac",

    "mp4",
    "avi",
    "mov",
    "mkv",
    "webm"
}


# ============================================================
# OTP STORAGE
# ============================================================

otp_storage = {}

OTP_EXPIRY_SECONDS = 300


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def allowed_file(filename):
    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    filename = secure_filename(file.filename)

    timestamp = str(int(time.time() * 1000))

    safe_filename = f"{timestamp}_{filename}"

    file_path = os.path.join(
        UPLOAD_FOLDER,
        safe_filename
    )

    file.save(file_path)

    return file_path


def get_question():
    return request.form.get("question", "").strip()


def cleanup_files(paths):
    for path in paths:

        try:

            if path and os.path.exists(path):
                os.remove(path)

        except Exception as error:
            print("Cleanup error:", error)


# ============================================================
# HOME / HEALTH CHECK
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "status": "online",
        "project": "MIRA",
        "name": "Multimodal Intelligent Reasoning Assistant",
        "message": "MIRA backend is running."
    })


# ============================================================
# TEXT ANALYSIS
# ============================================================

@app.route("/analyze/text", methods=["POST"])
def analyze_text():

    saved_path = None

    try:

        file = request.files.get("file")

        question = get_question()

        if not file:
            return jsonify({
                "success": False,
                "message": "Please upload a text file."
            }), 400

        if not question:
            return jsonify({
                "success": False,
                "message": "Please enter a question."
            }), 400

        if not allowed_file(file.filename):

            return jsonify({
                "success": False,
                "message": "Unsupported file type."
            }), 400

        saved_path = save_uploaded_file(file)

        data = extract_text(saved_path)

        text_content = data.get("text", "")

        result = build_reasoning_result(
            question=question,
            content=text_content,
            source=file.filename
        )

        return jsonify({
            "success": True,
            "file": file.filename,
            "modality": "text",
            "characters": data.get("characters", 0),
            "lines": data.get("lines", 0),
            "result": result
        })

    except Exception as error:

        print("TEXT ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Text analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files([saved_path])


# ============================================================
# PDF ANALYSIS
# ============================================================

@app.route("/analyze/pdf", methods=["POST"])
def analyze_pdf():

    saved_path = None

    try:

        file = request.files.get("file")

        question = get_question()

        if not file:

            return jsonify({
                "success": False,
                "message": "Please upload a PDF."
            }), 400

        if not question:

            return jsonify({
                "success": False,
                "message": "Please enter a question."
            }), 400

        saved_path = save_uploaded_file(file)

        data = extract_pdf_text(saved_path)

        pdf_text = data.get("text", "")

        if not pdf_text.strip():

            return jsonify({
                "success": False,
                "message": "This PDF does not contain extractable text."
            }), 400

        result = build_reasoning_result(
            question=question,
            content=pdf_text,
            source=file.filename
        )

        return jsonify({
            "success": True,
            "file": file.filename,
            "modality": "pdf",
            "pages": data.get("pages", 0),
            "characters": len(pdf_text),
            "result": result
        })

    except Exception as error:

        print("PDF ERROR:", error)

        return jsonify({
            "success": False,
            "message": "PDF analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files([saved_path])


# ============================================================
# TABLE / CSV / EXCEL ANALYSIS
# ============================================================

@app.route("/analyze/table", methods=["POST"])
def analyze_table():

    saved_path = None

    try:

        file = request.files.get("file")

        question = get_question()

        if not file:

            return jsonify({
                "success": False,
                "message": "Please upload a CSV or Excel file."
            }), 400

        if not question:

            return jsonify({
                "success": False,
                "message": "Please enter a question."
            }), 400

        saved_path = save_uploaded_file(file)

        dataframe = read_table(saved_path)

        summary = table_summary(dataframe)

        preview = table_preview(dataframe)

        table_content = str(preview)

        result = build_reasoning_result(
            question=question,
            content=table_content,
            source=file.filename
        )

        return jsonify({
            "success": True,
            "file": file.filename,
            "modality": "table",
            "rows": len(dataframe),
            "columns": len(dataframe.columns),
            "summary": summary,
            "preview": preview,
            "result": result
        })

    except Exception as error:

        print("TABLE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Table analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files([saved_path])


# ============================================================
# IMAGE ANALYSIS
# ============================================================

@app.route("/analyze/image", methods=["POST"])
def analyze_image():

    saved_path = None

    try:

        file = request.files.get("file")

        question = get_question()

        if not file:

            return jsonify({
                "success": False,
                "message": "Please upload an image."
            }), 400

        saved_path = save_uploaded_file(file)

        image_info = inspect_image(saved_path)

        answer = (
            "Image received successfully. "
            "The current local pipeline extracted image metadata. "
            "Semantic visual reasoning will be connected to the "
            "multimodal AI layer."
        )

        return jsonify({
            "success": True,
            "file": file.filename,
            "modality": "image",
            "question": question,
            "image": image_info,
            "result": {
                "answer": answer,
                "answerable": True,
                "confidence": 0.60,
                "evidence": [
                    "Image file successfully processed."
                ],
                "reasoning": [
                    "Image format inspected.",
                    "Image dimensions extracted.",
                    "Image metadata prepared for AI reasoning."
                ]
            }
        })

    except Exception as error:

        print("IMAGE ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Image analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files([saved_path])


# ============================================================
# CHART ANALYSIS
# ============================================================

@app.route("/analyze/chart", methods=["POST"])
def analyze_chart():

    saved_path = None

    try:

        file = request.files.get("file")

        question = get_question()

        if not file:

            return jsonify({
                "success": False,
                "message": "Please upload a chart image."
            }), 400

        saved_path = save_uploaded_file(file)

        chart_info = inspect_image(saved_path)

        return jsonify({
            "success": True,
            "file": file.filename,
            "modality": "chart",
            "question": question,
            "chart": chart_info,
            "result": {
                "answer": (
                    "Chart received successfully. "
                    "Visual chart reasoning will be handled by "
                    "the multimodal AI layer."
                ),
                "answerable": True,
                "confidence": 0.60,
                "evidence": [
                    "Chart image successfully processed."
                ],
                "reasoning": [
                    "Chart image inspected.",
                    "Image metadata extracted.",
                    "Chart prepared for multimodal reasoning."
                ]
            }
        })

    except Exception as error:

        print("CHART ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Chart analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files([saved_path])


# ============================================================
# AUDIO ANALYSIS
# ============================================================

@app.route("/analyze/audio", methods=["POST"])
def analyze_audio():

    saved_path = None

    try:

        file = request.files.get("file")

        question = get_question()

        if not file:

            return jsonify({
                "success": False,
                "message": "Please upload an audio file."
            }), 400

        saved_path = save_uploaded_file(file)

        audio_info = inspect_audio(saved_path)

        return jsonify({
            "success": True,
            "file": file.filename,
            "modality": "audio",
            "question": question,
            "audio": audio_info,
            "result": {
                "answer": (
                    "Audio received successfully. "
                    "Speech-to-text and semantic audio reasoning "
                    "will be connected to the AI layer."
                ),
                "answerable": True,
                "confidence": 0.55,
                "evidence": [
                    "Audio file successfully processed."
                ],
                "reasoning": [
                    "Audio metadata inspected.",
                    "Audio properties extracted.",
                    "Audio prepared for AI transcription."
                ]
            }
        })

    except Exception as error:

        print("AUDIO ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Audio analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files([saved_path])


# ============================================================
# VIDEO ANALYSIS
# ============================================================

@app.route("/analyze/video", methods=["POST"])
def analyze_video():

    saved_path = None

    try:

        file = request.files.get("file")

        question = get_question()

        if not file:

            return jsonify({
                "success": False,
                "message": "Please upload a video."
            }), 400

        saved_path = save_uploaded_file(file)

        video_info = inspect_video(saved_path)

        return jsonify({
            "success": True,
            "file": file.filename,
            "modality": "video",
            "question": question,
            "video": video_info,
            "result": {
                "answer": (
                    "Video received successfully. "
                    "Representative frames were extracted. "
                    "Full visual reasoning will be connected "
                    "to the multimodal AI layer."
                ),
                "answerable": True,
                "confidence": 0.55,
                "evidence": [
                    "Video file successfully processed."
                ],
                "reasoning": [
                    "Video metadata inspected.",
                    "Frames identified.",
                    "Video prepared for visual AI reasoning."
                ]
            }
        })

    except Exception as error:

        print("VIDEO ERROR:", error)

        return jsonify({
            "success": False,
            "message": "Video analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files([saved_path])


# ============================================================
# MULTIMODAL ANALYSIS
# ============================================================

@app.route("/analyze/multimodal", methods=["POST"])
def analyze_multimodal():

    saved_paths = []

    try:

        # Get ALL uploaded files
        files = request.files.getlist("files")

        # Get user's question
        question = request.form.get(
            "question",
            ""
        ).strip()

        # --------------------------------------------
        # VALIDATE FILES
        # --------------------------------------------

        if not files:

            return jsonify({
                "success": False,
                "message": "Please upload at least one source file."
            }), 400

        # --------------------------------------------
        # VALIDATE QUESTION
        # --------------------------------------------

        if not question:

            return jsonify({
                "success": False,
                "message": "Please enter a question."
            }), 400

        # --------------------------------------------
        # SAVE ALL FILES
        # --------------------------------------------

        uploaded_names = []

        for file in files:

            if not file or not file.filename:
                continue

            if not allowed_file(file.filename):

                return jsonify({
                    "success": False,
                    "message": (
                        f"Unsupported file type: "
                        f"{file.filename}"
                    )
                }), 400

            path = save_uploaded_file(file)

            saved_paths.append(path)

            uploaded_names.append(
                file.filename
            )

        if not saved_paths:

            return jsonify({
                "success": False,
                "message": "No valid files were uploaded."
            }), 400

        # --------------------------------------------
        # MULTIMODAL REASONING PIPELINE
        # --------------------------------------------

        result = analyze_multimodal_files(
            file_paths=saved_paths,
            question=question
        )

        # --------------------------------------------
        # ADD REQUEST INFORMATION
        # --------------------------------------------

        result["question"] = question

        result["uploaded_files"] = uploaded_names

        result["source_count"] = len(
            uploaded_names
        )

        return jsonify(result), 200

    except Exception as error:

        print("")
        print("======================================")
        print("MULTIMODAL ANALYSIS ERROR")
        print("======================================")
        print(
            "ERROR TYPE:",
            type(error).__name__
        )
        print(
            "ERROR:",
            str(error)
        )
        print("======================================")
        print("")

        return jsonify({
            "success": False,
            "message": "Multimodal analysis failed.",
            "error": str(error)
        }), 500

    finally:

        cleanup_files(saved_paths)


# ============================================================
# SEND OTP
# ============================================================

@app.route("/send-otp", methods=["POST"])
def send_otp():

    try:

        data = request.get_json()

        email = data.get(
            "email",
            ""
        ).strip()

        if not email:

            return jsonify({
                "success": False,
                "message": "Email is required."
            }), 400

        # ------------------------------------------------
        # IMPORTANT:
        # Put YOUR Gmail and App Password here.
        # Do NOT use normal Gmail password.
        # ------------------------------------------------

        sender_email = os.getenv(
            "MIRA_GMAIL",
            ""
        )

        sender_password = os.getenv(
            "MIRA_GMAIL_APP_PASSWORD",
            ""
        )

        if not sender_email or not sender_password:

            return jsonify({
                "success": False,
                "message": (
                    "Gmail settings are missing. "
                    "Configure MIRA_GMAIL and "
                    "MIRA_GMAIL_APP_PASSWORD."
                )
            }), 500

        # Generate 6 digit OTP
        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        # Store OTP
        otp_storage[email.lower()] = {
            "otp": otp,
            "created_at": time.time()
        }

        # Email
        message = EmailMessage()

        message["Subject"] = "MIRA Password Reset OTP"

        message["From"] = sender_email

        message["To"] = email

        message.set_content(
            f"""
Hello,

Your MIRA password reset OTP is:

{otp}

This OTP is valid for 5 minutes.

If you did not request this OTP,
please ignore this email.

Regards,
MIRA Team
"""
        )

        # Gmail SMTP
        with smtplib.SMTP(
            "smtp.gmail.com",
            587
        ) as server:

            server.starttls()

            server.login(
                sender_email,
                sender_password
            )

            server.send_message(
                message
            )

        print(
            "OTP sent successfully to:",
            email
        )

        return jsonify({
            "success": True,
            "message": "OTP sent successfully."
        })

    except Exception as error:

        print("")
        print("======================================")
        print("EMAIL SENDING ERROR")
        print("======================================")
        print(
            "ERROR TYPE:",
            type(error).__name__
        )
        print(
            "ERROR:",
            str(error)
        )
        print("======================================")
        print("")

        return jsonify({
            "success": False,
            "message": (
                "Email sending failed. "
                "Check Flask terminal for the exact error."
            )
        }), 500


# ============================================================
# RESET PASSWORD
# ============================================================

@app.route("/reset-password", methods=["POST"])
def reset_password():

    try:

        data = request.get_json()

        email = data.get(
            "email",
            ""
        ).strip().lower()

        otp = data.get(
            "otp",
            ""
        ).strip()

        new_password = data.get(
            "new_password",
            ""
        ).strip()

        if not email or not otp or not new_password:

            return jsonify({
                "success": False,
                "message": (
                    "Email, OTP and new password "
                    "are required."
                )
            }), 400

        record = otp_storage.get(email)

        if not record:

            return jsonify({
                "success": False,
                "message": "OTP not found. Please request a new OTP."
            }), 400

        # Check expiry
        if (
            time.time() -
            record["created_at"]
            > OTP_EXPIRY_SECONDS
        ):

            otp_storage.pop(
                email,
                None
            )

            return jsonify({
                "success": False,
                "message": "OTP expired. Please request a new OTP."
            }), 400

        # Check OTP
        if record["otp"] != otp:

            return jsonify({
                "success": False,
                "message": "Invalid OTP."
            }), 400

        # OTP valid
        otp_storage.pop(
            email,
            None
        )

        return jsonify({
            "success": True,
            "message": (
                "OTP verified successfully. "
                "Password reset can continue."
            )
        })

    except Exception as error:

        print(
            "RESET PASSWORD ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": "Password reset failed.",
            "error": str(error)
        }), 500


# ============================================================
# FILE TOO LARGE
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
        "message": (
            "File too large. Maximum allowed size is 100 MB."
        )
    }), 413


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print("")
    print("==================================================")
    print("MIRA BACKEND")
    print("Multimodal Intelligent Reasoning Assistant")
    print("==================================================")
    print("")
    print("Backend URL:")
    print("http://127.0.0.1:5000")
    print("")
    print("Multimodal API:")
    print("http://127.0.0.1:5000/analyze/multimodal")
    print("")
    print("Server starting...")
    print("==================================================")
    print("")

    app.run(
        host="127.0.0.1",
        port=5000,
