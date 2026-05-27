# 台語 AI 語音防詐模擬情境互動網頁 POC
## Claude Code 開發規格書 (SPEC.md)

> **版本**：v1.0 | **技術棧**：React + Vite + TailwindCSS  
> **ASR**：Whisper-Taiwanese Tv0.5（臺南大學 × 國科會）  
> **TTS**：Microsoft Azure Neural TTS（台語）  
> **LLM**：Anthropic Claude API（claude-sonnet-4-20250514）

---

## 目錄

1. [專案概述](#1-專案概述)
2. [技術棧與環境設定](#2-技術棧與環境設定)
3. [目錄結構](#3-目錄結構)
4. [核心功能模組](#4-核心功能模組)
5. [三大情境腳本與狀態機](#5-三大情境腳本與狀態機)
6. [API 串接規格](#6-api-串接規格)
7. [UI 元件規格](#7-ui-元件規格)
8. [環境變數](#8-環境變數)
9. [開發優先順序](#9-開發優先順序)
10. [驗收標準](#10-驗收標準)

---

## 1. 專案概述

### 目標
以「台語雙向語音 AI 對話」模擬三種真實詐騙情境，讓使用者透過說台語與 AI 詐騙者互動，在沉浸式體驗中習得識詐能力。

### 三大情境
| ID | 情境名稱 | 詐騙類型 | 場景 |
|----|----------|----------|------|
| `SCENARIO_MEDICAL` | 醫療神藥詐騙 | 電話詐騙 | 詐騙者自稱健康顧問，推銷神藥 |
| `SCENARIO_TOMB` | 靈骨塔退休金詐騙 | 登門詐騙 | 詐騙者登門推銷預售塔位 |
| `SCENARIO_ROMANCE` | 感情詐騙 | LINE 語音通話詐騙 | 網路交友後情感操控索錢 |

### 核心流程
```
使用者說台語
  → Tv0.5 ASR（語音轉文字）
  → Claude API（意圖分析 + 話術生成）
  → Azure TTS 台語（文字轉台語語音）
  → 播放 AI 詐騙者語音
  → 即時話術標記（UI 顯示警示）
  → 重複直到識詐成功或受騙
```

---

## 2. 技術棧與環境設定

### 前端
```bash
npm create vite@latest tw-antiscam -- --template react
cd tw-antiscam
npm install tailwindcss @tailwindcss/vite
npm install @anthropic-ai/sdk
npm install framer-motion        # 動畫
npm install lucide-react         # 圖示
```

### 後端（輕量 BFF）
```bash
mkdir server && cd server
npm init -y
npm install express cors dotenv
npm install @anthropic-ai/sdk
npm install microsoft-cognitiveservices-speech-sdk   # Azure TTS
npm install openai                                    # Whisper Tv0.5 相容介面
npm install multer                                    # 音訊檔案上傳
```

### 啟動指令
```bash
# 開發
npm run dev          # Vite 前端 :5173
node server/index.js # BFF 後端 :3001

# 建置
npm run build
```

---

## 3. 目錄結構

```
tw-antiscam/
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── index.css
│   │
│   ├── pages/
│   │   ├── HomePage.jsx          # 情境選擇首頁
│   │   ├── ScenarioPage.jsx      # 情境模擬主頁（含語音對話）
│   │   └── ReportPage.jsx        # 識詐分析報告頁
│   │
│   ├── components/
│   │   ├── ScenarioCard.jsx      # 首頁情境卡片
│   │   ├── PhoneUI.jsx           # 電話撥入 UI（情境一、二）
│   │   ├── LineUI.jsx            # LINE 通話 UI（情境三）
│   │   ├── VoiceButton.jsx       # 「按住說話」麥克風按鈕
│   │   ├── AudioWaveform.jsx     # AI 說話時的聲波動畫
│   │   ├── TacticBadge.jsx       # 即時話術標記 badge
│   │   ├── TacticSidebar.jsx     # 話術標記側邊欄
│   │   ├── SubtitleBar.jsx       # 語音字幕列
│   │   ├── PressureGauge.jsx     # 詐騙壓力計量表
│   │   └── ReportCard.jsx        # 報告頁話術解析卡片
│   │
│   ├── hooks/
│   │   ├── useVoiceRecorder.js   # 麥克風錄音 hook
│   │   ├── useAudioPlayer.js     # TTS 音訊播放 hook
│   │   └── useScenarioEngine.js  # 情境狀態機管理 hook
│   │
│   ├── engine/
│   │   ├── scenarioStateMachine.js   # FSM 狀態機邏輯
│   │   ├── tacticDetector.js         # 話術類型分類
│   │   └── escapeEvaluator.js        # 識詐成功判斷邏輯
│   │
│   ├── scenarios/
│   │   ├── medical.js            # 醫療情境腳本與 prompt
│   │   ├── tomb.js               # 靈骨塔情境腳本與 prompt
│   │   └── romance.js            # 感情詐騙情境腳本與 prompt
│   │
│   └── utils/
│       ├── api.js                # 後端 API 呼叫工具
│       └── constants.js          # 話術類型常數、狀態常數
│
└── server/
    ├── index.js                  # Express 主程式
    ├── routes/
    │   ├── asr.js                # POST /api/asr（Tv0.5 語音辨識）
    │   ├── chat.js               # POST /api/chat（Claude 話術生成）
    │   ├── tts.js                # POST /api/tts（Azure 台語語音合成）
    │   └── analyze.js            # POST /api/analyze（話術分類）
    └── middleware/
        └── rateLimit.js          # 速率限制
```

---

## 4. 核心功能模組

### 4.1 語音錄音 Hook — `useVoiceRecorder.js`

```javascript
// 使用 Web Audio API + MediaRecorder
// 回傳：{ isRecording, startRecording, stopRecording, audioBlob }

const useVoiceRecorder = () => {
  // 按住錄音（push-to-talk）
  // 放開後自動呼叫 /api/asr
  // 音訊格式：audio/webm;codecs=opus（瀏覽器原生）
  // 取樣率：16000Hz（Whisper 最佳）
  // 最長錄音：30秒，超過自動停止
}
```

### 4.2 情境狀態機 — `scenarioStateMachine.js`

```javascript
// 狀態定義（每個情境共用此結構）
const STATES = {
  INTRO:      'intro',       // 情境說明
  S1_TRUST:   's1_trust',    // 建立信任
  S2_PROBLEM: 's2_problem',  // 描述問題/渲染焦慮
  S3_SOLUTION:'s3_solution', // 提出解方
  S4_PRESSURE:'s4_pressure', // 製造緊迫
  S5_ACTION:  's5_action',   // 要求行動（索錢/個資）
  EXIT_WIN:   'exit_win',    // 識詐成功
  EXIT_LOSE:  'exit_lose',   // 受騙
}

// 狀態轉換規則
// - 每個狀態有最少/最多對話回合限制
// - Claude 回傳 nextState 決定推進時機
// - 使用者說出識詐語句 → 強制跳 EXIT_WIN
```

### 4.3 話術類型常數 — `constants.js`

```javascript
export const TACTIC_TYPES = {
  FAKE_AUTHORITY:    { id: 'fake_authority',    label: '偽造官方背景',   color: 'red',    icon: '🏛️' },
  FAKE_ENDORSEMENT:  { id: 'fake_endorsement',  label: '虛構名人背書',   color: 'red',    icon: '⭐' },
  FEAR_MONGERING:    { id: 'fear_mongering',    label: '渲染恐懼/焦慮', color: 'orange', icon: '😨' },
  ARTIFICIAL_SCARCITY:{ id: 'artificial_scarcity', label: '稀缺性製造', color: 'orange', icon: '⏰' },
  URGENCY_PRESSURE:  { id: 'urgency_pressure',  label: '緊迫感施壓',    color: 'orange', icon: '🔥' },
  SOCIAL_PROOF_FAKE: { id: 'social_proof_fake', label: '偽造社會認同',  color: 'yellow', icon: '👥' },
  EMOTIONAL_MANIPULATE:{ id: 'emotional_manipulate', label: '情感操控', color: 'purple', icon: '💔' },
  ISOLATION_TACTIC:  { id: 'isolation_tactic',  label: '孤立勸阻',      color: 'purple', icon: '🚫' },
  PIETY_EXPLOIT:     { id: 'piety_exploit',     label: '孝道情感利用',  color: 'purple', icon: '🙏' },
  INFO_FISHING:      { id: 'info_fishing',      label: '套取個人資訊',  color: 'red',    icon: '🎣' },
  TRANSFER_REQUEST:  { id: 'transfer_request',  label: '要求匯款',      color: 'red',    icon: '💸' },
}
```

### 4.4 識詐成功判斷 — `escapeEvaluator.js`

```javascript
// 透過 Claude API 判斷使用者回應是否達到識詐條件
// 觸發 EXIT_WIN 的範例台語語句（供 Claude prompt 參考）：
// - 「我要掛電話」「我不要買」「你是詐騙」
// - 「我要問我的家人/子女/醫生」
// - 「我要打 165 查詢」
// - 「我不認識你」「你是誰」（第一回合強烈拒絕）
// 
// 判斷維度：
// 1. 明確拒絕（直接說不、掛電話意圖）→ 高信心 EXIT_WIN
// 2. 轉介求助（告知家人、打165）→ EXIT_WIN
// 3. 質疑身份（不認識你、要查詢）→ 依情境決定
// 4. 猶豫（要想想）→ 繼續 S4 施壓
```

---

## 5. 三大情境腳本與狀態機

### 5.1 情境一：醫療神藥詐騙 — `scenarios/medical.js`

```javascript
export const MEDICAL_SCENARIO = {
  id: 'SCENARIO_MEDICAL',
  title: '醫療神藥詐騙',
  subtitle: '保健品電話推銷',
  uiTheme: 'phone',           // 使用 PhoneUI 元件
  soundEffect: 'phone_ring',  // 電話來電音效
  bgAmbience: 'phone_static', // 電話雜音背景
  
  userRole: {
    name: '王伯伯',
    age: 65,
    background: '退休教師，輕微高血壓，住台南，台語為主要語言',
  },
  
  scammerRole: {
    name: '徐顧問',
    persona: '自稱「台灣銀髮健康推廣中心」業務，宣稱前衛福部合作廠商',
    voiceStyle: '親切台語，帶濃厚台南腔，說話節奏快',
    azureTtsVoice: 'zh-TW-HsiaoChenNeural', // 暫代；正式版換台語音色
  },

  // 每個 state 的 System Prompt 補充（注入 Claude API system）
  statePrompts: {
    s1_trust: `
你是「徐顧問」，正在打電話給王伯伯。
【目標】建立信任，讓他相信你是正規機構。
【話術重點】
- 假裝認識他，說上次有做健康評估
- 強調「政府認證」「衛福部合作」
- 用台語親切問候，聊天氣、身體狀況
【台語示範】「王伯伯你好，我是徐顧問啦，上次幫你做健康評估的，你還記得嗎？」
【限制】此狀態不提產品，只建立關係，2-3 回合後轉 s2_problem。
`,
    s2_problem: `
【目標】渲染健康焦慮，讓王伯伯感到擔心。
【話術重點】
- 說他的血壓/血糖有潛在風險
- 提到「老年病」嚴重性，暗示後果
- 表現「很擔心他」的關懷語氣
【限制】還不要提具體產品，只製造問題感。
`,
    s3_solution: `
【目標】提出「御元金」神藥作為解決方案。
【話術重點】
- 強調日本進口、院長研發
- 引用虛假名人（前衛福部長）背書
- 說很多人吃了都有效，引入社會認同
- 提供「免費試用」降低防備
`,
    s4_pressure: `
【目標】製造緊迫感，逼迫今天決定。
【話術重點】
- 強調「只剩最後幾盒」
- 說「今天不決定就沒有了」
- 提高語速，情緒稍顯急切
- 如果對方猶豫，提出「小額試用」降低門檻
`,
    s5_action: `
【目標】索取信用卡號或要求匯款。
【話術重點】
- 說可以幫他「先保留」，只需要信用卡號
- 或說「先匯訂金，剩下貨到付款」
- 若對方拒絕，改口說「好啦，LINE 帳號給我，我傳資料給你」
`,
  },

  // 每個 state 的識別話術類型（用於 TacticBadge）
  stateTactics: {
    s1_trust:    ['fake_authority', 'social_proof_fake'],
    s2_problem:  ['fear_mongering'],
    s3_solution: ['fake_endorsement', 'social_proof_fake', 'fake_authority'],
    s4_pressure: ['artificial_scarcity', 'urgency_pressure'],
    s5_action:   ['info_fishing', 'transfer_request'],
  },

  // 識詐成功後的教育內容
  educationContent: {
    title: '你識破了！這是醫療詐騙常見手法',
    tactics: [
      { name: '偽造官方背景', description: '「衛福部合作」「政府認證」是常見謊言，可至衛福部官網查詢合法廠商' },
      { name: '稀缺性製造', description: '「只剩最後幾盒」是標準話術，目的是讓你來不及思考' },
      { name: '渲染恐懼', description: '誇大病情嚴重性，讓你焦慮而降低判斷力' },
    ],
    correctResponse: '遇到此類電話，直接說「我不需要，我要掛電話了」，不需要解釋理由。',
    resources: [
      { label: '165 反詐騙專線', action: 'tel:165' },
      { label: '食藥署廠商查詢', url: 'https://www.fda.gov.tw' },
    ],
  },
}
```

---

### 5.2 情境二：靈骨塔退休金詐騙 — `scenarios/tomb.js`

```javascript
export const TOMB_SCENARIO = {
  id: 'SCENARIO_TOMB',
  title: '靈骨塔退休金詐騙',
  subtitle: '登門拜訪業務員',
  uiTheme: 'door',            // 門鈴 → 客廳場景
  soundEffect: 'doorbell',
  bgAmbience: 'living_room',

  userRole: {
    name: '陳媽媽',
    age: 62,
    background: '剛退休的家庭主婦，存款約200萬，台語為主要語言，住在台中',
  },

  scammerRole: {
    name: '陳禮儀師',
    persona: '自稱禮儀規劃師，謊稱是鄰居王太太介紹來的靈骨塔業務',
    voiceStyle: '語氣熱情，夾雜孝道話術，說話帶台中腔',
    azureTtsVoice: 'zh-TW-HsiaoChenNeural',
  },

  statePrompts: {
    s1_trust: `
你是「陳禮儀師」，剛按門鈴，陳媽媽開門。
【目標】進入屋內，建立信任。
【話術重點】
- 謊稱是「鄰居王太太介紹的」
- 帶小禮物（水果/餅乾），表現誠意
- 聊家常，問她退休後的生活
【台語示範】「陳媽媽你好，我是王太太介紹的，我有帶一點水果，可以讓我進去坐一下嗎？」
`,
    s2_problem: `
【目標】引入「預先規劃的重要性」，連結孝道情感。
【話術重點】
- 說「長輩最怕子女麻煩」
- 提到「現在規劃，子女以後不用操心」
- 暗示身後事如果沒安排好很麻煩
`,
    s3_solution: `
【目標】介紹塔位產品，包裝成「投資 + 孝順」。
【話術重點】
- 強調「現在買便宜，以後會漲」
- 說有很多人買了，包含知名人士
- 把退休金低利率焦慮轉移到「投資塔位」
`,
    s4_pressure: `
【目標】製造緊迫感，催促今天決定。
【話術重點】
- 「月底漲價，今天簽最划算」
- 「我老闆說只剩這幾個好位置了」
- 提出帶她去「實地參觀」（帶看陷阱）
`,
    s5_action: `
【目標】逼簽合約或索取存摺影本。
【話術重點】
- 拿出合約說「先簽個意向書，不算正式合約」
- 說需要存摺影本「確認財力，才能保留名額」
- 若她拒絕，改說「帶現金就好，今天先付訂金」
`,
  },

  stateTactics: {
    s1_trust:    ['social_proof_fake'],
    s2_problem:  ['piety_exploit', 'fear_mongering'],
    s3_solution: ['fake_endorsement', 'piety_exploit'],
    s4_pressure: ['urgency_pressure', 'artificial_scarcity'],
    s5_action:   ['info_fishing', 'transfer_request'],
  },

  educationContent: {
    title: '你識破了！靈骨塔詐騙三大警訊',
    tactics: [
      { name: '孝道情感操控', description: '利用台灣人重視孝順的文化，讓你在情感壓力下做出財務決定' },
      { name: '偽造熟人引薦', description: '謊稱「鄰居介紹」是建立假信任的常見手法，應先電話向引薦人確認' },
      { name: '逼簽合約', description: '合法業者不會在第一次見面就要求當場簽約。任何需要「今天決定」的投資都要小心' },
    ],
    correctResponse: '陌生業務員登門，不讓進屋。任何塔位購買都要等家人陪同確認，並查詢內政部合法業者名單。',
    resources: [
      { label: '165 反詐騙專線', action: 'tel:165' },
      { label: '內政部殯葬資訊', url: 'https://mort.moi.gov.tw' },
      { label: '消費者保護委員會', url: 'https://www.cpc.ey.gov.tw' },
    ],
  },
}
```

---

### 5.3 情境三：感情詐騙 — `scenarios/romance.js`

```javascript
export const ROMANCE_SCENARIO = {
  id: 'SCENARIO_ROMANCE',
  title: '感情詐騙',
  subtitle: 'LINE 語音通話 — 情緒價值騙局',
  uiTheme: 'line_call',       // LINE 通話介面
  soundEffect: 'line_ringtone',
  bgAmbience: 'overseas_call_noise', // 模擬海外通話雜音

  userRole: {
    name: '林女士',
    age: 52,
    background: '獨居，喪偶三年，透過 LINE 認識「王醫師」已三週，對他有好感',
  },

  scammerRole: {
    name: '王明哲醫師',
    persona: '自稱在非洲執行 UN 醫療任務的外科醫師，溫柔體貼，三週來每天傳訊',
    voiceStyle: '語氣溫柔深情，略帶海外腔，偶有通話雜音',
    azureTtsVoice: 'zh-TW-YunJheNeural', // 男聲
  },

  statePrompts: {
    s1_trust: `
你是「王明哲醫師」，已和林女士認識三週，感情漸進。
【目標】確認感情基礎，讓她感受到你的關心與思念。
【話術重點】
- 說很思念她，詢問她今天過得如何
- 分享「在非洲工作」的孤單感
- 強調「你是我唯一能說話的人」
- 語氣溫柔，製造「只有妳最懂我」的感覺
`,
    s2_problem: `
【目標】製造危機事件，但先不說錢。
【話術重點】
- 說護照在海關被「莫名扣押」
- 說很擔心，語氣略顯慌亂
- 說「只是想跟妳說，我沒事的，妳不用擔心」（反向操作讓她主動關心）
`,
    s3_solution: `
【目標】讓她提出幫助，或接受你開口求助。
【話術重點】
- 表現為難，說「不想麻煩妳」
- 說「只要 15 萬就能取回護照，我在台灣的帳戶結凍了」
- 強調「借我，我回台灣馬上還你，我們還要見面的」
`,
    s4_pressure: `
【目標】情感勒索，讓她覺得不幫就是不愛。
【話術重點】
- 「妳不相信我嗎？我們說好要在一起的」
- 「如果我回不來，我們就沒辦法見面了」
- 說時間緊迫（「今晚必須繳清」）
`,
    s5_action: `
【目標】索取具體匯款資訊。
【話術重點】
- 請她匯款到指定帳號（說是朋友帳戶）
- 若她猶豫，說「用超商繳款就好，很方便」
- 請她不要告訴家人（「他們不了解我們的關係」）
`,
  },

  stateTactics: {
    s1_trust:    ['emotional_manipulate', 'isolation_tactic'],
    s2_problem:  ['emotional_manipulate'],
    s3_solution: ['emotional_manipulate', 'transfer_request'],
    s4_pressure: ['emotional_manipulate', 'urgency_pressure', 'isolation_tactic'],
    s5_action:   ['transfer_request', 'isolation_tactic', 'info_fishing'],
  },

  educationContent: {
    title: '你識破了！感情詐騙六個警訊',
    tactics: [
      { name: '長期情感投資', description: '詐騙者通常先花數週建立感情，再在你最信任的時刻開口要錢' },
      { name: '「只有你能幫我」', description: '刻意讓你覺得自己是唯一，是孤立你、阻止你尋求他人意見的手法' },
      { name: '要求不告訴家人', description: '這是最重要的警訊。任何人要求你「別讓家人知道」，必定是詐騙' },
    ],
    correctResponse: '任何網路認識的朋友開口要錢，第一步就是告知家人。掛電話後撥打 165，查詢對方帳號是否為詐騙帳戶。',
    resources: [
      { label: '165 反詐騙專線', action: 'tel:165' },
      { label: '以圖搜圖（查詐騙照片）', url: 'https://images.google.com' },
      { label: '刑事局防詐達人', url: 'https://www.cib.gov.tw' },
    ],
  },
}
```

---

## 6. API 串接規格

### 6.1 後端路由：`POST /api/asr`

Whisper-Taiwanese Tv0.5 語音辨識

```javascript
// Request
// Content-Type: multipart/form-data
// Body: { audio: File (audio/webm), scenarioId: string }

// Response
{
  "transcript": "我要掛電話了，你是詐騙",
  "confidence": 0.92,
  "language": "taiwanese",
  "fallbackToText": false  // true 表示信心值低，前端切換文字輸入
}

// Server 實作重點
// - Tv0.5 透過 HuggingFace Inference API 或自架 FastAPI 服務呼叫
// - 防詐詞彙 prompt prefix：
//   "以下是台語對話，包含：靈骨塔、退休金、護照、衛福部、165、匯款"
// - 若 confidence < 0.7，回傳 fallbackToText: true
```

### 6.2 後端路由：`POST /api/chat`

Claude API 話術生成

```javascript
// Request
{
  "scenarioId": "SCENARIO_MEDICAL",
  "currentState": "s3_solution",
  "conversationHistory": [
    { "role": "assistant", "content": "王伯伯你好..." },
    { "role": "user", "content": "你是哪間公司的？" }
  ],
  "userMessage": "你是哪間公司的？",
  "turnCount": 3
}

// Response
{
  "scammerReply": "我們是配合衛福部的台灣銀髮健康推廣中心啦...",
  "nextState": "s3_solution",        // 維持或推進
  "detectedTactics": ["fake_authority", "social_proof_fake"],
  "escapeDetected": false,
  "escapeProbability": 0.12,
  "pressureLevel": 45               // 0-100，用於 PressureGauge
}

// System Prompt 結構（server 端組裝）
// = BASE_SYSTEM + scenario.statePrompts[currentState] + ESCAPE_DETECTION_INSTRUCTIONS
```

**Claude System Prompt 基礎模板（`server/routes/chat.js` 中組裝）：**

```
你是一個台語防詐教育模擬系統中的 AI 詐騙者角色。

【角色】{scammerRole.name}，{scammerRole.persona}
【語言】全程使用台語（以繁體中文漢字書寫台語），夾雜少量國語。
【目標使用者】{userRole.name}，{userRole.background}

【情境專屬指令】
{statePrompts[currentState]}

【回應格式】請以 JSON 回應，結構如下：
{
  "reply": "詐騙者的台語回應（50-100字）",
  "nextState": "維持或推進的下一個狀態代碼",
  "detectedTactics": ["使用的話術類型陣列"],
  "escapeDetected": false,
  "escapeProbability": 0.0,
  "pressureLevel": 30
}

【識詐判斷規則】
如果使用者說出以下類型語句，escapeDetected 設為 true：
- 明確拒絕：「我不要」「掛電話」「不需要」
- 求助轉介：「問家人」「打165」「問醫生」
- 身份質疑：「你是詐騙」「我不認識你」「我要查詢」

【限制】
- 不得直接教使用者如何詐騙他人
- 話術強度隨 turnCount 遞增
- 遇到 EXIT 狀態，回傳「情境結束」訊號
```

### 6.3 後端路由：`POST /api/tts`

Azure Neural TTS 台語語音合成

```javascript
// Request
{
  "text": "王伯伯你好，我是徐顧問啦...",
  "voiceName": "zh-TW-HsiaoChenNeural",
  "rate": "0%",         // 語速調整：-20% 到 +20%
  "pitch": "0%",
  "style": "cheerful"   // Azure 語音風格
}

// Response
// Content-Type: audio/mpeg
// Body: 音訊二進位串流（streaming）

// 實作重點
// - 使用 Azure SDK streaming 模式，邊生成邊傳送
// - 前端 AudioContext 接收串流，達到更低延遲
// - 目標：TTS 首字延遲 < 1.5s
```

### 6.4 後端路由：`POST /api/analyze`

情境結束後的完整話術分析報告

```javascript
// Request
{
  "scenarioId": "SCENARIO_MEDICAL",
  "fullConversation": [...],  // 完整對話記錄
  "outcome": "win" | "lose",
  "turnCount": 8
}

// Response
{
  "summary": "你在第 5 回合識破了「稀缺性製造」話術...",
  "tacticTimeline": [
    { "turn": 1, "tactic": "fake_authority", "scammerLine": "我們是配合衛福部的..." },
    { "turn": 3, "tactic": "fear_mongering", "scammerLine": "你的血壓狀況..." }
  ],
  "correctResponseSuggestions": ["你可以這樣回應：「我要掛電話了」"],
  "score": 78,          // 識詐分數 0-100
  "badge": "防詐小英雄" // 或 "識詐學徒" / "下次更厲害"
}
```

---

## 7. UI 元件規格

### 7.1 首頁 `HomePage.jsx`

```
Layout:
- 全螢幕深色背景（#0F1923）
- 頂部 Logo + 標語「台語 AI 防詐模擬」
- 三張情境卡片（水平排列，行動版垂直堆疊）

ScenarioCard 規格：
- 點擊後進入對應 ScenarioPage
- 顯示：情境圖示、標題（台語漢字）、難度（🔴🟠🟡）、預計時間
- Hover 效果：卡片略微放大 + 背景色變化
```

### 7.2 情境頁 `ScenarioPage.jsx`

```
Layout（手機優先）：
┌─────────────────────────┐
│  [情境模擬中] [暫停按鈕] │  ← 頂部狀態列
├─────────────────────────┤
│                          │
│   PhoneUI / LineUI       │  ← 主視覺（電話 or LINE UI）
│   （AI 說話時顯示聲波）   │
│                          │
├─────────────────────────┤
│  字幕列（台語文字）       │  ← SubtitleBar
├─────────────────────────┤
│  [話術標記 badges]        │  ← TacticBadge（右側滑入）
├─────────────────────────┤
│  詐騙壓力計 ████░░░ 65%  │  ← PressureGauge
├─────────────────────────┤
│                          │
│    🎙 按住說台語          │  ← VoiceButton（大型，底部置中）
│                          │
└─────────────────────────┘
```

### 7.3 VoiceButton 元件

```
狀態：
- idle：灰色麥克風圖示，「按住說台語」文字
- recording：紅色脈動動畫，「放開送出」文字
- processing：旋轉 loading，「辨識中...」文字
- ai_speaking：禁用（AI 說話時無法按下）

行為：
- onPointerDown → startRecording()
- onPointerUp → stopRecording() → 自動呼叫 /api/asr
- 長按超過 30s → 自動停止錄音
- 觸覺回饋：使用 navigator.vibrate([10]) on mobile
```

### 7.4 TacticBadge 元件

```
觸發：每次 Claude 回應包含 detectedTactics 時，從右側滑入
顯示：話術 icon + 話術名稱 + 顏色分級
動畫：slide-in from right，停留 4 秒後淡出
堆疊：最多顯示 3 個，超過則 FIFO 替換
```

### 7.5 報告頁 `ReportPage.jsx`

```
內容（由上至下）：
1. 結果 Banner（WIN / LOSE + 識詐分數）
2. 話術時間軸（每回合詐騙者說什麼 + 使用什麼話術）
3. 話術解析卡片（TacticType → 解說 + 實際例句）
4. 正確應對示範（台語文字 + 語音播放按鈕）
5. 資源連結（165、相關網站）
6. 分享按鈕 + 「再試一次」按鈕
```

---

## 8. 環境變數

```bash
# .env（根目錄）
VITE_API_BASE_URL=http://localhost:3001

# server/.env
PORT=3001

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Azure TTS
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastasia

# Whisper Tv0.5（擇一）
# 方案A：HuggingFace Inference API
HUGGINGFACE_API_TOKEN=hf_...
TV05_MODEL_ID=openai/whisper-large-v3-turbo  # 替換為臺南大學發布的 model ID

# 方案B：自架 FastAPI 服務
TV05_API_URL=http://localhost:8000/transcribe

# 速率限制
MAX_REQUESTS_PER_MIN=60
MAX_CONCURRENT_SESSIONS=50
```

---

## 9. 開發優先順序

### Phase 1（Week 1–2）：語音核心 MVP
**目標：端到端語音流程可跑通**

```
[P0] 後端 /api/asr 串接 Tv0.5（先用 HF Inference API，後換自架）
[P0] 後端 /api/tts 串接 Azure TTS，支援 streaming
[P0] 後端 /api/chat 串接 Claude API，情境一基本 prompt
[P0] VoiceButton 元件（錄音 → 上傳 → 播放回應）
[P1] SubtitleBar（同步顯示字幕）
[P1] 情境一（醫療）基本對話流程 E2E 可跑
```

### Phase 2（Week 3–4）：情境完整化
```
[P0] 情境狀態機（FSM）完整實作
[P0] TacticBadge 即時話術標記
[P0] 識詐成功 / 失敗判斷邏輯
[P1] PressureGauge 元件
[P1] 情境二（靈骨塔）完整流程
[P1] 情境三（感情詐騙）完整流程
[P2] 音效整合（電話聲、門鈴、LINE 音效）
```

### Phase 3（Week 5–6）：報告 + 首頁 + 優化
```
[P0] ReportPage（話術解析報告）
[P0] HomePage（情境選擇）
[P1] 延遲優化（目標 E2E ≤ 5s）
[P1] Fallback 文字輸入模式
[P2] 動畫 + 音效打磨
[P2] 行動裝置適配
[P2] 分享功能
```

---

## 10. 驗收標準

### 功能驗收
- [ ] 三大情境均可從頭到尾完整執行（語音輸入 → AI 語音回應）
- [ ] 識詐成功路徑（使用者說「我要掛電話」等語句）→ 正確觸發 EXIT_WIN
- [ ] 受騙路徑（使用者配合到 S5 提供帳號）→ 觸發 EXIT_LOSE + 顯示說明
- [ ] 每個回合的話術類型標記正確出現（至少準確率 80%）
- [ ] Fallback 文字輸入在 ASR 信心值低時正常觸發
- [ ] 報告頁正確顯示本次對話的話術時間軸

### 效能驗收
- [ ] E2E 延遲（說完話 → AI 開始播音）≤ 5 秒（正常網路環境）
- [ ] TTS 首字延遲 ≤ 2 秒
- [ ] 行動裝置（iOS Safari / Android Chrome）正常運作

### 語言品質驗收（需台語顧問評估）
- [ ] TTS 台語語音自然度 MOS ≥ 3.5
- [ ] 詐騙話術台語文本符合自然口語
- [ ] 字幕與語音同步誤差 ≤ 0.5 秒

---

## 附錄：話術類型 Prompt 分類 Instruction

以下加入 Claude system prompt，確保 `detectedTactics` 準確分類：

```
【話術類型分類規則】
分析你生成的回應，從以下類型中標記使用到的話術（可複選）：

fake_authority      → 偽稱政府機關、醫療機構、知名品牌
fake_endorsement    → 虛構名人、醫生、官員背書
fear_mongering      → 誇大健康風險、死亡、身後事
artificial_scarcity → 「只剩幾個」「限量」「搶購中」
urgency_pressure    → 「今天不決定就沒了」「月底漲價」
social_proof_fake   → 「你鄰居/朋友也買了」「很多人都說有效」
emotional_manipulate→ 「你不相信我嗎」「我們說好要在一起」
isolation_tactic    → 「不要告訴家人」「他們不懂我們」
piety_exploit       → 「這是孝順」「子女不用操心」
info_fishing        → 索取信用卡號、帳號、身分證
transfer_request    → 要求匯款、超商繳款、加密貨幣

若本回合未使用明顯話術，回傳空陣列 []。
```

---

*本 SPEC 由 Claude 生成，供 Claude Code 開發使用。*  
*最後更新：2026-05-27*
