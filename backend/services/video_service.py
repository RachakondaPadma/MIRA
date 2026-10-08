import os
import cv2


SUPPORTED_VIDEO_FORMATS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm"
}


def inspect_video(file_path):
    """
    Inspect video and extract representative frames.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError("Video file not found.")

    extension = os.path.splitext(file_path)[1].lower()

    if extension not in SUPPORTED_VIDEO_FORMATS:
        raise ValueError("Unsupported video format.")

    capture = cv2.VideoCapture(file_path)

    if not capture.isOpened():
        raise ValueError("Unable to open the video.")

    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(
        capture.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    width = int(
        capture.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    duration = (
        frame_count / fps
        if fps and fps > 0
        else 0
    )

    frames = _extract_sample_frames(
        capture,
        frame_count
    )

    capture.release()

    return {
        "format": extension.replace(".", "").upper(),
        "fps": round(fps, 2) if fps else 0,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_seconds": round(duration, 2),
        "sample_frames": frames
    }


def _extract_sample_frames(capture, frame_count):
    """
    Extract basic frame information at:
    0%, 25%, 50%, 75%, 100%.
    """

    if frame_count <= 0:
        return []

    positions = [
        0,
        0.25,
        0.50,
        0.75,
        0.99
    ]

    frames = []

    for position in positions:

        frame_number = int(
            frame_count * position
        )

        capture.set(
            cv2.CAP_PROP_POS_FRAMES,
            frame_number
        )

        success, frame = capture.read()

        if not success:
            continue

        height, width = frame.shape[:2]

        frames.append({
            "frame_number": frame_number,
            "width": width,
            "height": height
        })

    return frames