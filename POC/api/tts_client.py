import os

_client = None


def _get_client():
    global _client
    if _client is None:
        from gradio_client import Client
        space_id = os.environ.get("TTS_SPACE_ID", "AlexOAO/tts-nan")
        _client = Client(space_id)
    return _client


def warmup():
    _get_client()


def _keep_alive_loop():
    import time
    while True:
        try:
            _get_client().predict("測", api_name="/tts")
        except Exception:
            pass
        time.sleep(4 * 60)


def synthesize_in_loop(text: str, scenario_id: str) -> str | None:
    try:
        return _get_client().predict(text, api_name="/tts")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None
