import os

_client = None


def _get_client():
    global _client
    if _client is None:
        from gradio_client import Client
        space_id = os.environ.get("ASR_SPACE_ID", "AlexOAO/asr-taiwanese")
        _client = Client(space_id)
    return _client


def transcribe(audio_data: tuple | None) -> str | None:
    """
    Transcribe audio via HuggingFace Space (AlexOAO/asr-taiwanese).

    audio_data: (sample_rate, numpy_array) from gr.Audio type="numpy"
    Returns transcript string, or None if audio is empty/unavailable.
    """
    if audio_data is None:
        return None

    import tempfile, soundfile as sf, numpy as np

    sr, array = audio_data

    if array.ndim > 1:
        array = array.mean(axis=1)

    array = array.astype(np.float32)
    max_val = np.abs(array).max()
    if max_val > 0:
        array = array / max_val

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    sf.write(tmp.name, array, sr)

    try:
        from gradio_client import handle_file
        result = _get_client().predict(handle_file(tmp.name), api_name="/transcribe")
        return result.strip() if result else None
    except Exception:
        import traceback
        traceback.print_exc()
        return None
