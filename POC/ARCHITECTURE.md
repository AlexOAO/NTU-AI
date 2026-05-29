# POC 技術架構說明文件

> 台語 AI 詐騙情境模擬教育系統 — 技術架構參考文件
> 最後更新：2026-05-29

---

## 1. 專案簡介

**台語 AI 詐騙情境模擬教育系統**：以語音對話方式，讓使用者在安全環境中練習識別詐騙話術，模擬真實電話詐騙、到府詐騙與 LINE 愛情詐騙等情境。

**核心目標**
- 使用台語語音互動，貼近高風險族群（65 歲以上長者）的日常語言習慣
- 透過 AI 扮演詐騙者，讓使用者實際演練識詐與拒絕技巧
- 即時分析詐騙話術，提供學習回饋

---

## 2. Tech Stack 技術棧

| 層級 | 技術 | 版本 / 說明 |
|------|------|------------|
| UI 框架 | Gradio | 6.15+ |
| 語言模型 (LLM) | OpenAI GPT-4o | `max_tokens=256` |
| 語音辨識 (ASR) | HuggingFace Gradio Space | `AlexOAO/asr-taiwanese` |
| 語音合成 (TTS) | HuggingFace Gradio Space | `AlexOAO/tts-nan` |
| 音訊處理 | torchaudio + soundfile | 重採樣至 16kHz |
| 套件管理 | uv | Python 3.12+ |

---

## 3. 系統架構（資料流）

```
+--------------------------------------------------+
|              使用者語音輸入 (Gradio Audio)          |
+--------------------------------------------------+
                         |
                         v
+--------------------------------------------------+
|                  ASR Module                       |
|  torchaudio 重採樣至 16kHz                        |
|  --> Gradio Space /transcribe                    |
|  (AlexOAO/asr-taiwanese)                         |
+--------------------------------------------------+
                         |
                    台語轉譯文字
                         |
                         v
+--------------------------------------------------+
|                   GPT-4o                         |
|  system prompt + 對話歷史 (conversation_history)  |
|  --> JSON 回應：reply / nextState /               |
|      detectedTactics / escapeDetected /           |
|      pressureLevel                               |
+--------------------------------------------------+
                         |
                         v
+--------------------------------------------------+
|                  FSM Engine                      |
|  狀態轉移計算 (state_machine.py)                  |
|  MIN_TURNS_IN_STATE 限制                         |
+--------------------------------------------------+
                         |
                      新狀態
                         |
                         v
+--------------------------------------------------+
|                  TTS Module                      |
|  --> Gradio Space /tts (AlexOAO/tts-nan)         |
|  輸出 MP3 音訊                                    |
+--------------------------------------------------+
                         |
                         v
+--------------------------------------------------+
|                  Gradio UI                       |
|  語音播放 + 字幕 + 話術標籤 + 壓力計 + 狀態標籤    |
+--------------------------------------------------+
```

---

## 4. 檔案結構

```
POC/
├── app.py                  # Gradio UI + 主流程 (607 行)
├── api/
│   ├── claude_client.py    # GPT-4o 呼叫、JSON 解析
│   ├── tts_client.py       # TTS Space client + keep-alive
│   └── asr_client.py       # ASR Space client + keep-alive
├── engine/
│   ├── state_machine.py    # FSM 狀態機邏輯
│   └── prompts.py          # System prompt 組裝
└── scenarios/
    ├── medical.py          # 電話保健品詐騙情境
    ├── tomb.py             # 墓地預購到府詐騙情境
    └── romance.py          # LINE 愛情詐騙情境
```

---

## 5. FSM 有限狀態機（狀態轉移圖）

```
                           escapeDetected=true
                     +------------------------------+
                     |                              |
                     v                              |
                [exit_win]                          |
                                                    |
[intro] --> [s1_trust] --> [s2_problem] --> [s3_solution] --> [s4_pressure] --> [s5_action] --> [exit_lose]
               (建立信任)    (製造問題)      (提出方案)        (施加壓力)       (促成行動)
```

**狀態最低停留回合數 (MIN_TURNS_IN_STATE)**

| 狀態 | 最低回合數 |
|------|-----------|
| intro | 1 |
| s1_trust | 2 |
| s2_problem | 1 |
| s3_solution | 1 |
| s4_pressure | 1 |
| s5_action | 1 |

> 規則：`turns_in_current_state >= MIN_TURNS_IN_STATE` 才允許 GPT-4o 建議的 `nextState` 生效；否則維持當前狀態。

---

## 6. 三大詐騙情境

| 情境 ID | 詐騙類型 | UI 介面 | TTS 聲線 | 受害者角色 |
|---------|---------|---------|---------|-----------|
| `SCENARIO_MEDICAL` | 電話保健品詐騙 | 電話介面 (iPhone 風格) | `zh-TW-HsiaoChenNeural` | 65 歲退休教師 |
| `SCENARIO_TOMB` | 墓地預購到府詐騙 | 門口場景介面 | `zh-TW-HsiaoChenNeural` | 62 歲退休主婦 |
| `SCENARIO_ROMANCE` | LINE 愛情詐騙 | LINE 聊天介面 | `zh-TW-YunJheNeural` | 52 歲獨居寡婦 |

---

## 7. 話術分類系統（11 種）

系統即時分析詐騙者每一句話，標記所使用的話術類別，作為學習回饋依據。

| # | 話術 ID | 中文名稱 | 標籤顏色 | 範例話術 |
|---|---------|---------|---------|---------|
| 1 | `fake_authority` | 假冒權威 | 紅色 | 「我是衛福部稽查員...」 |
| 2 | `urgency` | 製造緊迫感 | 橙色 | 「只剩今天，明天就沒了！」 |
| 3 | `fear_threat` | 恐嚇威脅 | 深紅色 | 「不處理會被凍結帳戶」 |
| 4 | `social_proof_fake` | 假造社會認同 | 藍色 | 「隔壁鄰居都買了...」 |
| 5 | `reciprocity` | 互惠綁架 | 紫色 | 「免費送你體驗，你再決定」 |
| 6 | `flattery` | 奉承拍馬 | 粉色 | 「您真的很有智慧，一聽就懂」 |
| 7 | `isolation` | 孤立隔絕 | 棕色 | 「這事不要告訴家人，他們不懂」 |
| 8 | `false_scarcity` | 假造稀缺 | 黃橙色 | 「全台只剩 3 個名額」 |
| 9 | `commitment_trap` | 承諾陷阱 | 深藍色 | 「您剛才說願意試試，對吧？」 |
| 10 | `financial_bait` | 金錢誘惑 | 金色 | 「投資 10 萬，一個月回報 3 萬」 |
| 11 | `sympathy_play` | 博取同情 | 灰藍色 | 「我也是為了您好才打電話來的」 |

> UI 中話術標籤以對應顏色的 badge 顯示在對話氣泡下方，協助使用者即時辨識。

---

## 8. GPT-4o 整合細節

### System Prompt 結構（`engine/prompts.py`）

```
[角色定義]
  詐騙者身份設定（姓名、職稱、組織）
  說話風格（台語腔調、語氣節奏）

[當前狀態指令]
  scenarios/<scenario_id>.state_prompts[current_state]
  對應當前 FSM 狀態的行為目標與話術重點

[話術分類規則]
  11 種 tactic 的定義與觸發條件
  要求在 detectedTactics 欄位標記本句使用的話術

[識詐判斷規則]
  使用者說出識詐關鍵詞（拒絕、不要、掛電話等）
  觸發 escapeDetected=true

[回應格式]
  嚴格要求輸出 JSON，不可有額外文字
  字數限制：reply 25-40 字（台語）
```

### JSON 回應格式

```json
{
  "reply": "詐騙者的台語回應，約 25-40 字",
  "nextState": "s2_problem",
  "detectedTactics": ["fake_authority", "social_proof_fake"],
  "escapeDetected": false,
  "pressureLevel": 30
}
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `reply` | string | 詐騙者台語回應文字，同時送 TTS |
| `nextState` | string | GPT-4o 建議的下一個 FSM 狀態 |
| `detectedTactics` | string[] | 本回合使用的話術 ID 列表 |
| `escapeDetected` | boolean | 使用者是否已識詐並拒絕 |
| `pressureLevel` | integer | 當前壓力值 0-100，驅動 UI 壓力計 |

---

## 9. Session State 資料結構

每一場對話的完整狀態，由 Gradio `gr.State` 持有，不落地儲存。

```python
session_state = {
    # 情境識別
    "scenario_id": "SCENARIO_MEDICAL",      # str

    # FSM 狀態
    "current_state": "s1_trust",            # str
    "turns_in_current_state": 1,            # int，本狀態已停留回合數

    # 對話歷史（直接送 GPT-4o messages）
    "conversation_history": [
        {"role": "user",      "content": "..."},
        {"role": "assistant", "content": "..."},
        # ...
    ],

    # 話術分析歷史
    "tactic_history": [
        {
            "turn": 1,
            "tactics": ["fake_authority"],
            "line": "詐騙者說的話..."
        },
        # ...
    ],

    # 壓力與進度
    "pressure_level": 30,                   # int 0-100
    "turn_count": 3,                        # int，總回合數

    # 結束狀態
    "is_ended": False,                      # bool
    "outcome": None,                        # "win" | "lose" | None
}
```

---

## 10. 效能設計

| 機制 | 說明 |
|------|------|
| **Keep-Alive 心跳** | 每 4 分鐘向 ASR / TTS HuggingFace Space 送靜音音訊或測試文字，防止冷啟動延遲（Space 閒置 >5 分鐘會休眠） |
| **縮短回應長度** | GPT-4o 限制 reply 25-40 字 + `max_tokens=256`，TTS 合成時間從 ~60s 降至 ~15s |
| **音訊重採樣** | torchaudio on-the-fly 重採樣至 16kHz（Whisper 標準輸入格式），避免 ASR 拒絕非標準取樣率音訊 |
| **錯誤降級 (Graceful Degradation)** | GPT-4o 失敗 → 佔位文字繼續；TTS 失敗 → 靜音繼續；ASR 失敗 → 提示使用者改文字輸入 |

---

## 附錄：部署與執行

```bash
# 安裝依賴（使用 uv）
uv sync

# 設定環境變數
export OPENAI_API_KEY="sk-..."
export HF_TOKEN="hf_..."

# 啟動應用
uv run python app.py
```

Gradio UI 預設開啟於 `http://localhost:7860`，支援 share=True 產生公開連結供展示使用。
