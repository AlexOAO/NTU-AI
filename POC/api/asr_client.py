import os
import numpy as np
import torch

_pipe = None


def _get_pipe():
    global _pipe
    if _pipe is None:
        from transformers import pipeline
        model_path = os.environ.get("WHISPER_MODEL_PATH", "./model/whisper-taiwanese")
        if torch.cuda.is_available():
            device = 0
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = -1
        _pipe = pipeline("automatic-speech-recognition", model=model_path, device=device)
    return _pipe


def transcribe(audio_data: tuple | None) -> str | None:
    """
    Transcribe audio using local transformers pipeline (Tv0.5 / Whisper).

    audio_data: (sample_rate, numpy_array) from gr.Audio type="numpy"
    Returns transcript string, or None if audio is empty/unavailable.
    """
    if audio_data is None:
        return None

    sr, array = audio_data

    # Ensure mono
    if array.ndim > 1:
        array = array.mean(axis=1)

    # Normalize to float32
    array = array.astype(np.float32)
    max_val = np.abs(array).max()
    if max_val > 0:
        array = array / max_val

    try:
        result = _get_pipe()(
            {"sampling_rate": sr, "array": array},
            generate_kwargs={"language": "zh", "task": "transcribe"},
        )
        text = result["text"].strip()
        return text if text else None
    except Exception as e:
        print(f"ASR error: {e}")
        return None
