import os
import wave


SUPPORTED_AUDIO_FORMATS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".flac",
    ".aac"
}


def inspect_audio(file_path):
    """
    Inspect audio file information.

    WAV files can be inspected directly with Python's wave module.
    Other formats are returned with basic file metadata.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError("Audio file not found.")

    extension = os.path.splitext(file_path)[1].lower()

    if extension not in SUPPORTED_AUDIO_FORMATS:
        raise ValueError("Unsupported audio format.")

    result = {
        "format": extension.replace(".", "").upper(),
        "file_size_bytes": os.path.getsize(file_path)
    }

    if extension == ".wav":

        try:
            with wave.open(file_path, "rb") as audio:

                frames = audio.getnframes()
                sample_rate = audio.getframerate()
                channels = audio.getnchannels()

                duration = (
                    frames / float(sample_rate)
                    if sample_rate
                    else 0
                )

                result.update({
                    "duration_seconds": round(duration, 2),
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "frames": frames
                })

        except Exception as error:
            result["inspection_error"] = str(error)

    return result