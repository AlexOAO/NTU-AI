import asyncio
import tempfile
import os
import edge_tts

VOICE_MAP = {
    "SCENARIO_MEDICAL": "zh-TW-HsiaoChenNeural",
    "SCENARIO_TOMB":    "zh-TW-HsiaoChenNeural",
    "SCENARIO_ROMANCE": "zh-TW-YunJheNeural",
}


def synthesize(text: str, scenario_id: str) -> str:
    """
    Synthesize text to speech using edge-tts.
    Returns path to a temporary MP3 file.
    """
    voice = VOICE_MAP.get(scenario_id, "zh-TW-HsiaoChenNeural")
    return asyncio.run(_synthesize_async(text, voice))


async def _synthesize_async(text: str, voice: str) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(tmp.name)
    return tmp.name


def synthesize_in_loop(text: str, scenario_id: str) -> str:
    """
    Synthesize using the current event loop if one exists (Gradio compatibility).
    Falls back to asyncio.run() if no loop is running.
    """
    voice = VOICE_MAP.get(scenario_id, "zh-TW-HsiaoChenNeural")
    try:
        loop = asyncio.get_running_loop()
        # We are inside a running loop (e.g. Gradio async handler)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _synthesize_async(text, voice))
            return future.result()
    except RuntimeError:
        return asyncio.run(_synthesize_async(text, voice))
