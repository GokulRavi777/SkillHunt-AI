# VANI 2.0 Repository Audit & Compatibility Report

## Date: 2026-11-18
## Target Environment: `examples/vani_interview/`

### 1. Environment & Runtime
- **Python Version**: Python 3.12.16 (managed via `agents/.venv` and uv)
- **Host OS**: Windows (PowerShell)
- **Dependency Manager**: `uv` 0.13.7

### 2. LiveKit Agents SDK
- **Package**: `livekit-agents` 1.8.12
- **Agent Server / Session API**: `livekit.agents.AgentServer`, `AgentSession`, `JobContext`, `cli.run_app`
- **Voice Pipeline**:
  - `AgentSession(stt=..., vad=..., llm=..., tts=...)`
  - Streaming audio & endpointing support with Silero VAD
  - Preemptive generation and interruption handling supported natively

### 3. Voice Providers (Gnani AI & Silero)
- **Gnani STT**: `livekit.plugins.gnani.STT`
  - Default base URL: `https://api.vachana.ai`
  - Language: `en-IN`
  - Credentials: `GNANI_API_KEY` loaded from environment
  - Status: Initialized and verified
- **Gnani TTS**: `livekit.plugins.gnani.TTS`
  - Model: `timbre-v2.5`
  - Voice: `Nalini`
  - Synthesize method: REST / SSE
  - Status: Verified live synthesis (19 audio event packets received)
- **Silero VAD**: `livekit.plugins.silero.VAD.load()`
  - ONNX runtime CPU inference
  - Status: Verified and operational

### 4. LLM & Orchestration (Gemini, LangChain, LangGraph)
- **Google Gemini**: `langchain-google-genai` 4.5.0
  - Model: `gemini-3.5-flash-lite` (also supports `gemini-2.5-flash`)
  - Status: Verified live prompt and inference
- **LangChain Core**: 1.8.1
- **LangGraph**: 1.2.19
  - StateGraph with typed `InterviewState`
  - In-memory state tracking per session
  - Authoritative deterministic transitions and limit enforcement
- **LangChain-LiveKit Integration**: `livekit.plugins.langchain.LLMAdapter` and custom Agent turn integration

### 5. MCP (Model Context Protocol)
- **MCP Core**: `mcp` 1.30.0, `FastMCP`
- **Adapters**: `langchain-mcp-adapters` 0.3.2
- In-memory session-isolated tool execution for the 5 essential interview tools:
  1. `list_available_skills`
  2. `get_skill_details`
  3. `select_interview_skill`
  4. `get_next_question`
  5. `save_interview_response`

### 6. Architectural Decisions
- Session memory remains strictly in-memory per active LiveKit connection (no DB / Redis / SQLite).
- Strict adherence to 3 primary questions and max 1 follow-up per question.
- All 30 use cases and 25 guardrails implemented deterministically with LLM intent parsing and prompt engine.
