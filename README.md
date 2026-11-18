# SkillHunt AI — Technical Interview Intelligence Platform

SkillHunt AI is a state-of-the-art real-time conversational technical interview platform built with Python, React 19, FastAPI, LangChain, and FastMCP. It conducts structured, oral technical assessments using **Gnani STT** (`en-IN`), **Google Gemini** (`gemini-3.5-flash-lite`), and **Gnani TTS** (`Nalini` voice, `timbre-v2.5` model) over real-time WebRTC and Web Audio pipelines.

---

## 🌟 Key Capabilities

1. **Automated Resume Parsing & Skill Extraction**:
   - Parses PDF, DOCX, and TXT resumes with section boundary detection and confidence scoring.
   - 113+ technical skills mapped across languages, backend frameworks, cloud, data, and devops.

2. **Full Lifecycle Conversational Interviewing**:
   - **Opening Greeting & Readiness Gate**: Welcomes the candidate by name and strictly gates Question 1 until readiness is confirmed.
   - **Dynamic Few-Shot Question Generation**: Calibrated across Beginner, Intermediate, and Expert tiers tailored to parsed resume skills.
   - **Single Global Follow-Up**: Maximum 1 deep-dive technical follow-up probe across the entire interview.
   - **Vague Answer Elaboration Quota**: Probes for elaboration maximum 1 time per question if candidate answer lacks depth.
   - **Repetition Limits**: Repeats active question at most twice before moving forward.
   - **20-Second Single-Use Hold Quota**: Strict hold policy allowing candidate to pause for up to 20 seconds once per assessment.
   - **Strict English Enforcement**: Gracefully detects non-English speech and redirects candidate to English.
   - **Zero Solution Leakage**: Strictly refuses hints or answers during assessment.

3. **Audio & Voice Intelligence**:
   - **Studio-Grade Text-to-Speech**: Authentic Indian English pronunciation via Gnani TTS (Nalini).
   - **Ultra-Fast Speech Recognition**: Sub-100ms transcription with Gnani STT and Gemini multimodal fallback.
   - **3D Glowing Orb Visualizer**: Real-time volume RMS animation reacting to speech cadence.

---

## 🏗️ Architecture

```
Candidate Microphone
        │
        ▼ (Web Audio / WebRTC)
  Frontend Client (React 19 + Vite + Tailwind)
        │
        ▼ POST /api/interview/transcribe (Audio Blob)
  FastAPI Backend (backend/app.py)
        ├── Gnani STT (REST API @ api.vachana.ai, en-IN)
        └── Gemini 3.5 Flash Lite Multimodal Audio Fallback
        │
        ▼ Transcribed Text
  LangChain Conversation Orchestrator (orchestration/conversation.py)
        │
        ▼ Dynamic System Prompts & Instructions
  FastMCP Server (mcp_server/server.py)
        ├── get_state_instruction()
        ├── generate_few_shot_question()
        └── InMemorySessionStore (Responses & Metrics)
        │
        ▼ Response Generation
  Gemini 3.5 Flash Lite LLM
        │
        ▼ Synthesized Voice Text
  FastAPI Backend (POST /api/interview/tts)
        └── Gnani TTS (Nalini, timbre-v2.5, en-IN)
        │
        ▼ (WAV Audio Stream)
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

### 2. Backend Startup
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Startup
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 🧪 Testing

Run the full pytest suite (62/62 passing tests):
```bash
pytest tests/
```

---

## 📄 License
MIT License
