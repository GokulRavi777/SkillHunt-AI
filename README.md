# SkillHunt AI — Autonomous Voice Technical Interviewer

SkillHunt AI is a cloud-native, real-time conversational technical interview platform built with LiveKit Agents, LangChain, FastMCP, and Gnani Speech AI. It conducts hands-free, oral technical assessments directly inside the **LiveKit Cloud Console / Playground** or via direct WebRTC room connections using **Gnani STT** (`en-IN`), **Google Gemini** (`gemini-3.5-flash-lite`), and **Gnani TTS** (`Nalini` voice, `timbre-v2.5` model).

---

## 🌟 Key Capabilities

1. **Direct LiveKit Cloud Console Integration**:
   - Zero custom frontend dependencies; the candidate connects directly via the LiveKit Cloud Playground or LiveKit Meet.
   - Real-time bidirectional WebRTC audio streaming with Silero VAD turn detection.

2. **Full Lifecycle Conversational Interviewing**:
   - **Opening Greeting & Readiness Gate**: Welcomes the candidate and strictly gates Question 1 until readiness is confirmed.
   - **Dynamic Few-Shot Question Generation**: Calibrated across Beginner, Intermediate, and Expert tiers tailored to technical skills.
   - **Single Global Follow-Up**: Maximum 1 deep-dive technical follow-up probe across the entire interview.
   - **Vague Answer Elaboration Quota**: Probes for elaboration maximum 1 time per question if candidate answer lacks depth.
   - **Repetition Limits**: Repeats active question at most twice before moving forward.
   - **20-Second Single-Use Hold Quota**: Strict hold policy allowing candidate to pause for up to 20 seconds once per assessment.
   - **Strict English Enforcement**: Gracefully detects non-English speech and redirects candidate to English.
   - **Zero Solution Leakage**: Strictly refuses hints or answers during assessment.

3. **Audio & Voice Intelligence**:
   - **Studio-Grade Text-to-Speech**: Authentic Indian English pronunciation via Gnani TTS (Nalini).
   - **Ultra-Fast Speech Recognition**: Sub-100ms streaming transcription with Gnani STT.
   - **Silero VAD**: Low-latency voice activity detection with fixed endpointing.

---

## 🏗️ Architecture

```
Candidate Microphone
        │
        ▼ (WebRTC Audio Stream)
  LiveKit Cloud Console / Playground
        │
        ▼ (LiveKit RTC Room)
  SkillHunt AI Agent Worker (agent.py)
        ├── Silero VAD (Voice Activity Detection & Endpointing)
        ├── Gnani STT (Streaming Speech-to-Text, en-IN)
        ├── LangChain Conversation Orchestrator (orchestration/conversation.py)
        │      ├── Dynamic FastMCP Tool Suite (mcp_server/server.py)
        │      └── Google Gemini 3.5 Flash Lite LLM
        └── Gnani TTS (WebRTC Audio Synthesis, Nalini, timbre-v2.5)
        │
        ▼ (WebRTC Audio Track)
Candidate Speaker / Headphones
```

---

## 🚀 Getting Started

### 1. Environment Configuration
Create `.env` in the root directory:
```env
LIVEKIT_URL=wss://vani-2-0-1khnawsy.livekit.cloud
LIVEKIT_API_KEY=your_livekit_key
LIVEKIT_API_SECRET=your_livekit_secret

GNANI_API_KEY=your_gnani_key
GNANI_STT_LANGUAGE=en-IN
GNANI_TTS_VOICE=Nalini
GNANI_TTS_MODEL=timbre-v2.5
GNANI_TTS_LANGUAGE=en-IN

GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

### 2. Start the LiveKit Agent Worker
Run the agent in development mode (auto-reload on changes):
```bash
python agent.py dev
```
Or run in production mode:
```bash
python agent.py start
```

### 3. Conduct Interview in LiveKit Cloud Console
1. Log into your LiveKit Cloud dashboard: [https://cloud.livekit.io](https://cloud.livekit.io)
2. Open your project (`vani-2-0-1khnawsy`).
3. Navigate to **Playground** or **Agents**.
4. Click **Connect** with your microphone enabled.
5. SkillHunt AI will automatically greet you and begin the conversational interview!

Alternatively, generate a 1-click shareable test link for candidates:
```bash
python share_with_friends.py --name "Candidate Name"
```

---

## 🧪 Testing

Execute the comprehensive 62-case test suite:
```bash
pytest tests/
```

Run the full pytest suite (62/62 passing tests):
```bash
pytest tests/
```

---

## 📄 License
MIT License
