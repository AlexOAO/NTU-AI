STATES = ["intro", "s1_trust", "s2_problem", "s3_solution", "s4_pressure", "s5_action", "exit_win", "exit_lose"]

# Minimum turns before allowing progression from each state
MIN_TURNS_IN_STATE = {
    "intro":       1,
    "s1_trust":    2,
    "s2_problem":  1,
    "s3_solution": 1,
    "s4_pressure": 1,
    "s5_action":   1,
}

TERMINAL_STATES = {"exit_win", "exit_lose"}

STATE_SEQUENCE = ["intro", "s1_trust", "s2_problem", "s3_solution", "s4_pressure", "s5_action"]


def get_default_state():
    return {
        "scenario_id": None,
        "current_state": "intro",
        "conversation_history": [],
        "tactic_history": [],
        "pressure_level": 0,
        "turn_count": 0,
        "turns_in_current_state": 0,
        "is_ended": False,
        "outcome": None,
    }


def transition(current_state: str, next_state_from_claude: str, escape_detected: bool) -> str:
    if escape_detected:
        return "exit_win"

    if current_state in TERMINAL_STATES:
        return current_state

    # If Claude requests s5_action and no escape, that means user is going along — eventually exit_lose
    if current_state == "s5_action" and next_state_from_claude == "s5_action":
        # Claude will signal exit_lose once turns in s5 are sufficient
        return "s5_action"

    if next_state_from_claude == "exit_lose":
        return "exit_lose"

    # Validate the requested state is a valid forward progression
    if next_state_from_claude in STATES:
        current_idx = STATES.index(current_state) if current_state in STATES else -1
        next_idx = STATES.index(next_state_from_claude)
        # Allow staying in place or advancing (not going backwards past intro)
        if next_idx >= current_idx:
            return next_state_from_claude

    return current_state


def update_state(session: dict, claude_response: dict) -> dict:
    """Apply a Claude response to session state, returning updated session."""
    import copy
    s = copy.deepcopy(session)

    escape = claude_response.get("escapeDetected", False)
    next_state = claude_response.get("nextState", s["current_state"])
    tactics = claude_response.get("detectedTactics", [])
    pressure = claude_response.get("pressureLevel", s["pressure_level"])
    reply = claude_response.get("reply", "")

    s["turn_count"] += 1
    s["turns_in_current_state"] += 1
    s["pressure_level"] = pressure

    if tactics:
        s["tactic_history"].append({
            "turn": s["turn_count"],
            "tactics": tactics,
            "line": reply,
        })

    new_state = transition(s["current_state"], next_state, escape)
    if new_state != s["current_state"]:
        s["current_state"] = new_state
        s["turns_in_current_state"] = 0

    if new_state in TERMINAL_STATES:
        s["is_ended"] = True
        s["outcome"] = "win" if new_state == "exit_win" else "lose"

    return s
