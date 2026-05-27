# 台語 AI 語音防詐模擬 POC

以台語雙向語音 AI 對話，模擬三種真實詐騙情境，讓使用者透過與 AI 詐騙者互動，練習識破詐騙話術。

---

## 技術棧

| 層面 | 技術 |
|------|------|
| UI | Gradio 6.15+ |
| LLM | Anthropic Claude (claude-sonnet-4-6) |
| TTS | edge-tts（zh-TW-HsiaoChenNeural / YunJheNeural） |
| ASR | HuggingFace Inference API（選用，預設 fallback 文字輸入） |
| 套件管理 | uv |

---

## 快速開始

```bash
# 1. 安裝依賴
uv sync

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env，至少填入 ANTHROPIC_API_KEY

# 3. 啟動
uv run python app.py
# 開啟 http://localhost:7860
```

---

## 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `ANTHROPIC_API_KEY` | **必填** | Claude API 金鑰。每回合對話皆呼叫 Claude，用於生成詐騙者台語回應、判斷識詐成功/失敗、推進狀態機。沒有此 key 系統無法運作。 |
| `HF_API_TOKEN` | 選用 | HuggingFace Inference API 金鑰，用於台語語音辨識（ASR）。未設定時系統自動改為純文字輸入，其餘功能不受影響。 |
| `HF_MODEL_ID` | 選用 | ASR 模型 ID，預設 `openai/whisper-large-v3-turbo`。如需使用臺南大學 Tv0.5 台語專屬模型，請至 HuggingFace Hub 查詢並填入。 |

---

## 三大情境

| 情境 | 詐騙類型 | 詐騙者 | 目標用戶 |
|------|----------|--------|----------|
| 醫療神藥詐騙 | 電話推銷保健品 | 徐顧問（自稱衛福部合作）| 王伯伯，65 歲退休教師 |
| 靈骨塔退休金詐騙 | 登門拜訪業務 | 陳禮儀師（謊稱鄰居介紹）| 陳媽媽，62 歲退休主婦 |
| 感情詐騙 | LINE 語音通話 | 王明哲醫師（自稱非洲義工）| 林女士，52 歲獨居喪偶 |

---

## 系統架構

```
用戶輸入（語音/文字）
  → ASR（HF Inference API，可選）
  → Claude API
      ├─ 組裝 System Prompt（角色 + 當前 FSM 狀態 + 話術規則）
      ├─ 生成台語詐騙者回應
      ├─ 偵測用戶是否識詐（escapeDetected）
      ├─ 標記使用的話術類型（detectedTactics）
      └─ 回傳 JSON（reply, nextState, pressureLevel…）
  → FSM 狀態機更新
  → edge-tts 語音合成
  → Gradio UI 更新（場景 / 字幕 / 話術徽章 / 壓力計）
```

### FSM 狀態機

```
intro → s1_trust → s2_problem → s3_solution → s4_pressure → s5_action
                                                                   │
                          任意狀態偵測到識詐語句 ──────────────→ exit_win
                          s5_action 配合 2+ 回合 ──────────────→ exit_lose
```

---

## 檔案結構

```
poc/
├── app.py                     # Gradio 主程式（UI + 事件流）
├── pyproject.toml             # uv 依賴管理
├── .env.example               # 環境變數範本
├── implementation-notes.html  # 實作備忘錄（含已知問題）
├── SPEC.md                    # 原始規格書
├── scenarios/
│   ├── __init__.py            # 匯出 ALL_SCENARIOS, SCENARIO_MAP
│   ├── medical.py             # 醫療神藥情境（角色、State Prompts、話術標記）
│   ├── tomb.py                # 靈骨塔情境
│   └── romance.py             # 感情詐騙情境
├── engine/
│   ├── state_machine.py       # FSM（transition, update_state, get_default_state）
│   └── prompts.py             # Claude system prompt 組裝
└── api/
    ├── claude_client.py       # Anthropic API 呼叫 + JSON 解析
    ├── tts_client.py          # edge-tts 非同步語音合成
    └── asr_client.py          # HF Inference API 語音辨識
```

---

## 話術類型

Claude 每回合會自動標記詐騙者使用的話術，並顯示於 UI：

| 話術 ID | 標籤 | 顏色 |
|---------|------|------|
| `fake_authority` | 偽造官方背景 | 紅 |
| `fake_endorsement` | 虛構名人背書 | 紅 |
| `fear_mongering` | 渲染恐懼/焦慮 | 橙 |
| `artificial_scarcity` | 稀缺性製造 | 橙 |
| `urgency_pressure` | 緊迫感施壓 | 橙 |
| `social_proof_fake` | 偽造社會認同 | 黃 |
| `emotional_manipulate` | 情感操控 | 紫 |
| `isolation_tactic` | 孤立勸阻 | 紫 |
| `piety_exploit` | 孝道情感利用 | 紫 |
| `info_fishing` | 套取個人資訊 | 紅 |
| `transfer_request` | 要求匯款 | 紅 |

---

## 識詐成功條件（EXIT_WIN）

Claude 偵測到以下類型語句時，立即觸發識詐成功：

- **明確拒絕**：「我不要」「掛電話」「不需要」「你走」
- **求助轉介**：「問家人」「打165」「問醫生」「問我孩子」
- **身份質疑**：「你是詐騙」「我不認識你」「我要查詢」
- **強烈懷疑**：「你騙人」「這是詐騙」「我不相信你」

---

## 與 SPEC.md 的差異

| 項目 | SPEC | 本 POC |
|------|------|--------|
| 前端 | React + Vite + TailwindCSS | Gradio 6 |
| 後端 | Node.js Express BFF | 同一 Python 進程 |
| ASR | Whisper Tv0.5（本地） | HF Inference API（遠端，選用） |
| TTS | Azure Neural TTS | edge-tts（免費） |
| Push-to-talk | onPointerDown/Up | gr.Audio click-to-record |
