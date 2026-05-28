import os
from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from scenarios import ALL_SCENARIOS, SCENARIO_MAP
from engine.state_machine import get_default_state, update_state
from api import claude_client, tts_client, asr_client

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TACTIC_LABELS = {
    "fake_authority":      {"label": "偽造官方背景",  "color": "#ef4444", "icon": "🏛️"},
    "fake_endorsement":    {"label": "虛構名人背書",  "color": "#ef4444", "icon": "⭐"},
    "fear_mongering":      {"label": "渲染恐懼/焦慮","color": "#f97316", "icon": "😨"},
    "artificial_scarcity": {"label": "稀缺性製造",   "color": "#f97316", "icon": "⏰"},
    "urgency_pressure":    {"label": "緊迫感施壓",   "color": "#f97316", "icon": "🔥"},
    "social_proof_fake":   {"label": "偽造社會認同", "color": "#eab308", "icon": "👥"},
    "emotional_manipulate":{"label": "情感操控",     "color": "#a855f7", "icon": "💔"},
    "isolation_tactic":    {"label": "孤立勸阻",     "color": "#a855f7", "icon": "🚫"},
    "piety_exploit":       {"label": "孝道情感利用", "color": "#a855f7", "icon": "🙏"},
    "info_fishing":        {"label": "套取個人資訊", "color": "#ef4444", "icon": "🎣"},
    "transfer_request":    {"label": "要求匯款",     "color": "#ef4444", "icon": "💸"},
}

THEME_ICONS = {
    "phone":     "📞",
    "door":      "🚪",
    "line_call": "💬",
}

STATE_LABELS = {
    "intro":       "開場",
    "s1_trust":    "建立信任",
    "s2_problem":  "製造問題",
    "s3_solution": "提出解方",
    "s4_pressure": "施加壓力",
    "s5_action":   "要求行動",
    "exit_win":    "識詐成功",
    "exit_lose":   "受騙",
}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
:root {
    --bg-dark: #0f1923;
    --bg-card: #1a2535;
    --accent: #3b82f6;
    --accent-green: #22c55e;
    --accent-red: #ef4444;
    --text-primary: #f1f5f9;
    --text-muted: #94a3b8;
}

body, .gradio-container { background: var(--bg-dark) !important; color: var(--text-primary) !important; }

.scenario-card {
    background: var(--bg-card);
    border: 1px solid #2d3f55;
    border-radius: 16px;
    padding: 24px;
    cursor: pointer;
    transition: transform 0.2s, border-color 0.2s;
    text-align: center;
}
.scenario-card:hover { transform: translateY(-4px); border-color: var(--accent); }

.phone-ui {
    background: #111;
    border-radius: 40px;
    border: 3px solid #333;
    padding: 32px 20px;
    max-width: 320px;
    margin: 0 auto;
    text-align: center;
    color: white;
    box-shadow: 0 0 40px rgba(59,130,246,0.15);
}
.phone-ui .caller-avatar {
    width: 80px; height: 80px; border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    margin: 0 auto 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 36px;
}
.phone-ui .caller-name { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.phone-ui .call-status { color: #94a3b8; font-size: 14px; }
.phone-ui .pulse-ring {
    width: 100px; height: 100px; border-radius: 50%;
    border: 2px solid rgba(59,130,246,0.4);
    margin: 16px auto;
    animation: pulse-ring 1.5s infinite;
}
@keyframes pulse-ring {
    0% { transform: scale(0.8); opacity: 1; }
    100% { transform: scale(1.4); opacity: 0; }
}

.door-ui {
    background: linear-gradient(180deg, #1e3a5f 0%, #0f1923 100%);
    border-radius: 16px;
    padding: 32px;
    max-width: 320px;
    margin: 0 auto;
    text-align: center;
    border: 2px solid #2d4a6b;
}
.line-ui {
    background: #00b900;
    border-radius: 16px;
    padding: 24px;
    max-width: 320px;
    margin: 0 auto;
    text-align: center;
    color: white;
}
.line-ui .line-avatar {
    width: 70px; height: 70px; border-radius: 50%;
    background: white;
    margin: 0 auto 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px;
}

.subtitle-bar {
    background: rgba(0,0,0,0.7);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 16px;
    min-height: 48px;
    color: #f1f5f9;
    border-left: 3px solid var(--accent);
    margin: 8px 0;
}

.tactic-badges { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.tactic-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 12px; border-radius: 20px;
    font-size: 13px; font-weight: 600; color: white;
    animation: slide-in 0.3s ease-out;
}
@keyframes slide-in {
    from { transform: translateX(40px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

.pressure-container { margin: 8px 0; }
.pressure-label { font-size: 13px; color: var(--text-muted); margin-bottom: 4px; }
.pressure-track {
    background: #1a2535; border-radius: 8px; height: 20px;
    overflow: hidden; border: 1px solid #2d3f55;
}
.pressure-fill {
    height: 100%; border-radius: 8px;
    display: flex; align-items: center; justify-content: flex-end;
    padding-right: 8px; font-size: 12px; font-weight: 700; color: white;
    transition: width 0.5s ease, background 0.5s ease;
}

.state-badge {
    display: inline-block; padding: 4px 10px; border-radius: 12px;
    font-size: 12px; background: #2d3f55; color: #94a3b8; margin: 4px 0;
}

.report-section {
    background: var(--bg-card); border-radius: 16px; padding: 24px;
    border: 1px solid #2d3f55; margin: 8px 0;
}
.report-win  { border-color: var(--accent-green); }
.report-lose { border-color: var(--accent-red); }

.turn-item {
    border-left: 2px solid #2d3f55; padding-left: 12px; margin: 8px 0;
    font-size: 14px;
}
.turn-item .turn-num { color: var(--text-muted); font-size: 12px; }
.turn-item .turn-text { color: var(--text-primary); margin: 2px 0; }
.turn-item .turn-tactics { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.turn-tactic-mini {
    font-size: 11px; padding: 2px 8px; border-radius: 10px; color: white;
}
"""

# ---------------------------------------------------------------------------
# HTML Helpers
# ---------------------------------------------------------------------------

def phone_ui_html(scenario: dict) -> str:
    name = scenario["scammer_role"]["name"]
    theme = scenario["ui_theme"]
    icon = THEME_ICONS.get(theme, "📞")
    if theme == "phone":
        return f"""
<div class="phone-ui">
  <div class="pulse-ring"></div>
  <div class="caller-avatar">{icon}</div>
  <div class="caller-name">{name}</div>
  <div class="call-status">通話中…</div>
</div>"""
    elif theme == "door":
        return f"""
<div class="door-ui">
  <div style="font-size:64px; margin-bottom:16px">{icon}</div>
  <div style="font-size:20px; font-weight:700; color:#f1f5f9">{name}</div>
  <div style="color:#94a3b8; font-size:14px; margin-top:4px">門口拜訪中…</div>
</div>"""
    else:  # line_call
        return f"""
<div class="line-ui">
  <div class="line-avatar">{icon}</div>
  <div style="font-size:20px; font-weight:700">{name}</div>
  <div style="font-size:14px; margin-top:4px; opacity:0.85">LINE 語音通話中…</div>
</div>"""


def subtitle_html(text: str, speaker: str = "AI") -> str:
    color = "#3b82f6" if speaker == "AI" else "#22c55e"
    prefix = "詐騙者：" if speaker == "AI" else "你："
    return f'<div class="subtitle-bar"><span style="color:{color}; font-weight:600">{prefix}</span> {text}</div>'


def tactic_badges_html(tactics: list) -> str:
    if not tactics:
        return '<div class="tactic-badges"></div>'
    badges = ""
    for t in tactics:
        info = TACTIC_LABELS.get(t, {"label": t, "color": "#64748b", "icon": "⚠️"})
        badges += f'<span class="tactic-badge" style="background:{info["color"]}">{info["icon"]} {info["label"]}</span>'
    return f'<div class="tactic-badges">{badges}</div>'


def pressure_html(level: int) -> str:
    if level < 30:
        color = "#22c55e"
    elif level < 60:
        color = "#f97316"
    else:
        color = "#ef4444"
    return f"""<div class="pressure-container">
  <div class="pressure-label">詐騙壓力值</div>
  <div class="pressure-track">
    <div class="pressure-fill" style="width:{level}%; background:{color}">{level}%</div>
  </div>
</div>"""


def state_badge_html(state: str) -> str:
    label = STATE_LABELS.get(state, state)
    return f'<span class="state-badge">階段：{label}</span>'


def report_html(session: dict, scenario: dict) -> str:
    outcome = session.get("outcome")
    is_win = outcome == "win"
    cls = "report-win" if is_win else "report-lose"
    banner_color = "#22c55e" if is_win else "#ef4444"
    banner_text = "識詐成功！你識破了詐騙！" if is_win else "受騙了！下次要更小心！"
    edu = scenario["education_content"]

    # Tactic timeline
    timeline_html = ""
    for item in session.get("tactic_history", []):
        mini_badges = "".join(
            f'<span class="turn-tactic-mini" style="background:{TACTIC_LABELS.get(t, {"color":"#64748b"})["color"]}">'
            f'{TACTIC_LABELS.get(t, {"icon":"⚠️"})["icon"]} {TACTIC_LABELS.get(t, {"label":t})["label"]}</span>'
            for t in item["tactics"]
        )
        timeline_html += f"""
<div class="turn-item">
  <div class="turn-num">第 {item["turn"]} 回合</div>
  <div class="turn-text">「{item["line"][:80]}{"…" if len(item["line"]) > 80 else ""}」</div>
  <div class="turn-tactics">{mini_badges}</div>
</div>"""

    # Education tactics
    tactic_cards = "".join(
        f'<div style="margin:8px 0; padding:12px; background:#0f1923; border-radius:8px">'
        f'<strong style="color:#f97316">{t["name"]}</strong><br>'
        f'<span style="font-size:14px; color:#94a3b8">{t["description"]}</span></div>'
        for t in edu["tactics"]
    )

    return f"""
<div class="report-section {cls}">
  <h2 style="color:{banner_color}; text-align:center; font-size:24px">{banner_text}</h2>
  <p style="text-align:center; color:#94a3b8">共 {session["turn_count"]} 回合</p>
</div>

<div class="report-section">
  <h3 style="color:#f1f5f9; margin-bottom:12px">話術時間軸</h3>
  {timeline_html if timeline_html else '<p style="color:#94a3b8">本次無偵測到話術記錄</p>'}
</div>

<div class="report-section">
  <h3 style="color:#f97316; margin-bottom:12px">{edu["title"]}</h3>
  {tactic_cards}
  <div style="margin-top:12px; padding:12px; background:#0f1923; border-radius:8px; border-left:3px solid #22c55e">
    <strong style="color:#22c55e">正確應對：</strong><br>
    <span style="font-size:14px; color:#f1f5f9">{edu["correct_response"]}</span>
  </div>
</div>

<div style="text-align:center; margin-top:8px; color:#64748b; font-size:13px">
  165 反詐騙專線 | 刑事局防詐達人
</div>"""

# ---------------------------------------------------------------------------
# Core processing logic
# ---------------------------------------------------------------------------

def start_scenario(scenario_id: str, state: dict) -> tuple:
    """Initialize a new scenario session and generate opening TTS."""
    scenario = SCENARIO_MAP[scenario_id]

    new_state = get_default_state()
    new_state["scenario_id"] = scenario_id

    # Generate opening line via Claude
    try:
        intro_prompt = scenario["state_prompts"]["intro"]
        claude_resp = claude_client.chat(intro_prompt, new_state)
        new_state = update_state(new_state, claude_resp)
        reply_text = claude_resp.get("reply", "你好，我是詐騙者。")
        tactics = claude_resp.get("detectedTactics", [])
        pressure = claude_resp.get("pressureLevel", 0)
    except Exception as e:
        reply_text = "（系統初始化中，請稍候…）"
        tactics = []
        pressure = 0
        print(f"Claude error on start: {e}")

    # TTS
    audio_path = None
    try:
        audio_path = tts_client.synthesize_in_loop(reply_text, scenario_id)
    except Exception as e:
        print(f"TTS error: {e}")

    scene_html  = phone_ui_html(scenario)
    sub_html    = subtitle_html(reply_text)
    tactic_html = tactic_badges_html(tactics)
    press_html  = pressure_html(pressure)
    st_html     = state_badge_html(new_state["current_state"])

    return (
        new_state,           # state
        scene_html,          # scene_display
        sub_html,            # subtitle_display
        tactic_html,         # tactic_display
        press_html,          # pressure_display
        st_html,             # state_display
        audio_path,          # audio_output
        gr.update(visible=False),  # report_display
        gr.update(visible=False),  # restart_btn
        gr.update(visible=True),   # input_row
    )


def process_input(audio_data, text_input: str, state: dict) -> tuple:
    """Handle user turn: ASR → Claude → TTS → update UI."""
    if state.get("is_ended"):
        return _no_change(state, "情境已結束，請按「再試一次」重新開始。")

    if not state.get("scenario_id"):
        return _no_change(state, "請先選擇一個情境。")

    scenario_id = state["scenario_id"]
    scenario = SCENARIO_MAP[scenario_id]

    # 1. Transcribe audio or use text
    user_text = None
    if audio_data is not None:
        user_text = asr_client.transcribe(audio_data)

    if not user_text:
        user_text = text_input.strip()

    if not user_text:
        return _no_change(state, "請輸入文字或錄音後送出。")

    # 2. Show user subtitle immediately
    user_sub = subtitle_html(user_text, speaker="user")

    # 3. Claude response
    try:
        claude_resp = claude_client.chat(user_text, state)
        state = update_state(state, claude_resp)
        reply_text = claude_resp.get("reply", "")
        tactics = claude_resp.get("detectedTactics", [])
        pressure = claude_resp.get("pressureLevel", state["pressure_level"])
    except Exception as e:
        print(f"Claude error: {e}")
        return _no_change(state, f"Claude API 錯誤：{e}")

    # 4. TTS
    audio_path = None
    try:
        if reply_text:
            audio_path = tts_client.synthesize_in_loop(reply_text, scenario_id)
    except Exception as e:
        print(f"TTS error: {e}")

    # 5. Build UI updates
    scene_html  = phone_ui_html(scenario)
    sub_html    = subtitle_html(reply_text) if reply_text else user_sub
    tactic_html = tactic_badges_html(tactics)
    press_html  = pressure_html(state["pressure_level"])
    st_html     = state_badge_html(state["current_state"])

    # 6. Check end state
    report_visible = gr.update(visible=False)
    restart_visible = gr.update(visible=False)
    input_visible = gr.update(visible=True)

    if state.get("is_ended"):
        report_html_content = report_html(state, scenario)
        report_visible = gr.update(value=report_html_content, visible=True)
        restart_visible = gr.update(visible=True)
        input_visible = gr.update(visible=False)

    return (
        state,
        scene_html,
        sub_html,
        tactic_html,
        press_html,
        st_html,
        audio_path,
        report_visible,
        restart_visible,
        input_visible,
    )


def _no_change(state: dict, message: str) -> tuple:
    scenario_id = state.get("scenario_id")
    scenario = SCENARIO_MAP.get(scenario_id) if scenario_id else None
    scene_html = phone_ui_html(scenario) if scenario else ""
    return (
        state,
        scene_html,
        f'<div class="subtitle-bar" style="color:#f97316">{message}</div>',
        '<div class="tactic-badges"></div>',
        pressure_html(state.get("pressure_level", 0)),
        state_badge_html(state.get("current_state", "intro")),
        None,
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
    )

# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def build_scenario_selector():
    """Return HTML for the scenario selection landing."""
    cards = ""
    for s in ALL_SCENARIOS:
        icon = THEME_ICONS.get(s["ui_theme"], "🎭")
        cards += f"""
<div class="scenario-card" onclick="void(0)" style="margin-bottom:12px">
  <div style="font-size:48px; margin-bottom:12px">{icon}</div>
  <div style="font-size:20px; font-weight:700; color:#f1f5f9; margin-bottom:4px">{s["title"]}</div>
  <div style="color:#94a3b8; font-size:14px">{s["subtitle"]}</div>
</div>"""
    return f"""
<div style="text-align:center; margin-bottom:24px">
  <h1 style="font-size:28px; font-weight:800; color:#f1f5f9; margin-bottom:8px">
    台語 AI 防詐模擬
  </h1>
  <p style="color:#94a3b8">選擇情境，練習識破詐騙話術</p>
</div>
<div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:16px">
{cards}
</div>"""


with gr.Blocks(title="台語 AI 防詐模擬") as demo:
    state = gr.State(get_default_state())

    # ── Header ──────────────────────────────────────────────────
    gr.HTML("""
    <div style="text-align:center; padding:20px 0 8px">
      <h1 style="font-size:26px; font-weight:800; color:#f1f5f9; margin:0">
        台語 AI 防詐模擬
      </h1>
      <p style="color:#94a3b8; margin:4px 0 0">以台語與 AI 詐騙者對話，練習識破詐騙話術</p>
    </div>
    """)

    # ── Scenario selection ──────────────────────────────────────
    with gr.Row():
        scenario_dropdown = gr.Dropdown(
            choices=[(s["title"], s["id"]) for s in ALL_SCENARIOS],
            label="選擇詐騙情境",
            value=ALL_SCENARIOS[0]["id"],
            scale=3,
        )
        start_btn = gr.Button("開始模擬", variant="primary", scale=1)

    # ── Main simulation area ────────────────────────────────────
    with gr.Row():
        with gr.Column(scale=1):
            scene_display    = gr.HTML(label="場景")
            state_display    = gr.HTML()
            subtitle_display = gr.HTML('<div class="subtitle-bar">選擇情境後按「開始模擬」</div>')
            tactic_display   = gr.HTML('<div class="tactic-badges"></div>')
            pressure_display = gr.HTML(pressure_html(0))

        with gr.Column(scale=1):
            audio_output = gr.Audio(
                label="AI 詐騙者語音",
                autoplay=True,
                interactive=False,
            )

            with gr.Group(visible=True) as input_row:
                audio_input = gr.Audio(
                    sources=["microphone"],
                    type="numpy",
                    label="點擊開始錄音，再點停止",
                )
                text_input = gr.Textbox(
                    placeholder="輸入台語文字（例如：你是哪間公司的？）",
                    label="文字輸入",
                    lines=2,
                )

    # ── Report area ─────────────────────────────────────────────
    report_display = gr.HTML(visible=False)
    restart_btn = gr.Button("再試一次", visible=False, variant="secondary")

    # ── Event handlers ──────────────────────────────────────────

    OUTPUTS = [
        state,
        scene_display,
        subtitle_display,
        tactic_display,
        pressure_display,
        state_display,
        audio_output,
        report_display,
        restart_btn,
        input_row,
    ]

    start_btn.click(
        fn=start_scenario,
        inputs=[scenario_dropdown, state],
        outputs=OUTPUTS,
    )

    audio_input.stop_recording(
        fn=process_input,
        inputs=[audio_input, text_input, state],
        outputs=OUTPUTS,
    )

    text_input.submit(
        fn=process_input,
        inputs=[audio_input, text_input, state],
        outputs=OUTPUTS,
    )

    def restart(state_val):
        fresh = get_default_state()
        return (
            fresh,
            "",
            '<div class="subtitle-bar">選擇情境後按「開始模擬」</div>',
            '<div class="tactic-badges"></div>',
            pressure_html(0),
            "",
            None,
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
        )

    restart_btn.click(fn=restart, inputs=[state], outputs=OUTPUTS)


def main():
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False, css=CUSTOM_CSS)


if __name__ == "__main__":
    main()
