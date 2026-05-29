import os

_client = None


def _get_client():
    global _client
    if _client is None:
        from gradio_client import Client
        space_id = os.environ.get("ASR_SPACE_ID", "AlexOAO/asr-taiwanese")
        _client = Client(space_id)
    return _client


def warmup():
    _get_client()


def _keep_alive_loop():
    import time, tempfile, numpy as np, soundfile as sf
    from gradio_client import handle_file
    silent = np.zeros(1600, dtype=np.float32)  # 0.1s @ 16kHz
    while True:
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            sf.write(tmp.name, silent, 16000)
            _get_client().predict(handle_file(tmp.name), api_name="/transcribe")
        except Exception:
            pass
        time.sleep(4 * 60)


def transcribe(audio_data: tuple | None) -> str | None:
    if audio_data is None:
        return None

    import tempfile, soundfile as sf, numpy as np
    import torch, torchaudio.functional as F

    sr, array = audio_data

    if array.ndim > 1:
        array = array.mean(axis=1)

    array = array.astype(np.float32)
    max_val = np.abs(array).max()
    if max_val > 0:
        array = array / max_val

    # 降採樣到 16kHz（Whisper 標準，減少上傳大小）
    if sr != 16000:
        t = torch.from_numpy(array).unsqueeze(0)
        t = F.resample(t, sr, 16000)
        array = t.squeeze(0).numpy()
        sr = 16000

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
