import json
import os
import openai
from engine.prompts import build_system_prompt

_client = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client


def chat(user_message: str, session: dict) -> dict:
    """
    Call OpenAI GPT-4o with current session state. Returns parsed JSON response dict.
    Falls back to a safe default dict on error.
    """
    scenario_id = session["scenario_id"]
    current_state = session["current_state"]
    turn_count = session["turn_count"]
    history = session["conversation_history"]

    system_prompt = build_system_prompt(scenario_id, current_state, turn_count)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=256,
    )

    raw_text = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # Attempt to extract JSON object from the text
        import re
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = {
                "reply": raw_text[:200],
                "nextState": current_state,
                "detectedTactics": [],
                "escapeDetected": False,
                "pressureLevel": session["pressure_level"],
            }

    # Append to conversation history (update session externally)
    session["conversation_history"].append({"role": "user", "content": user_message})
    session["conversation_history"].append({"role": "assistant", "content": result.get("reply", "")})

    return result
