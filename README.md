# VANI 2.0 — Conversational AI Technical Interviewer

VANI 2.0 is a real-time conversational AI technical interviewer built on **LiveKit Agents**, **Google Gemini**, **LangChain**, **LangGraph**, **FastMCP**, **Gnani AI STT/TTS**, and **Silero VAD**.

## Key Highlights

- **Real-time Voice Pipeline**: LiveKit WebRTC audio + Gnani STT (Indian English) + Silero VAD + Gnani TTS (`Nalini`, `timbre-v2.5`).
- **Dynamic Few-Shot Question Engine**: Questions and follow-ups are dynamically synthesized from candidate answers using curated few-shot exemplars (never static templates).
- **LangGraph Stateful Orchestration**: Authoritative StateGraph controls transitions, answer processing, and session recovery.
- **Strict Limit Enforcement**: Deterministically enforces **maximum 3 primary technical questions** and **maximum 1 follow-up per question**.
- **MCP Tool Integration**: 5 essential tools for skills discovery, topic metadata, and in-memory session answers.
- **In-Memory Session Isolation**: Session-scoped conversational memory with zero external database dependencies, strictly cleaned up on disconnect.
- **30 Use Cases & 25 Guardrails**: Full coverage of onboarding, adaptive questioning, conversation controls, prompt injection, and pause/resume integrity.

---

## Architecture

```text
vani_interview/
├── agent.py                      # LiveKit Agent worker entry point
├── config/
│   └── settings.py               # Central environment configuration
├── vani/
│   ├── llm/
│   │   ├── model.py              # Gemini LangChain model service
│   │   ├── prompts.py            # System instructions & intent analysis prompt
│   │   ├── prompt_builder.py     # Dynamic few-shot prompt assembler
│   │   ├── example_bank.py       # Curated 7-category few-shot example bank
│   │   ├── question_generator.py # Question synthesis & validation engine
│   │   └── livekit_adapter.py    # Bridge between LiveKit audio turns & LangGraph
│   ├── graph/
│   │   ├── state.py              # Typed InterviewState schema
│   │   ├── nodes.py              # LangGraph workflow nodes
│   │   └── workflow.py           # Compiled StateGraph & turn driver
│   ├── mcp/
│   │   ├── server.py             # FastMCP server & 5 essential tools
│   │   └── client.py             # MCP client & LangChain tool bindings
│   ├── guardrails/
│   │   └── engine.py             # Deterministic 25-guardrail engine
│   ├── schemas/
│   │   └── models.py             # Pydantic data schemas & enums
│   └── session/
│       └── manager.py            # In-memory session state manager
├── tests/
│   └── test_vani_integration.py  # Integration & smoke test suite
└── docs/
    ├── ARCHITECTURE.md           # Architecture diagrams & state machine
    ├── LIVEKIT_CONSOLE_GUIDE.md  # LiveKit Cloud console demo guide
    ├── REPOSITORY_AUDIT.md       # SDK compatibility & setup decisions
    └── EXECUTION_REPORT.md       # Full completion & verification report
```

---

## Quickstart & Execution

### 1. Configure Credentials
Copy `.env.example` to `.env` and fill in credentials:
```bash
cp .env.example .env
```
Ensure the following variables are defined:
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `GNANI_API_KEY`
- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-3.5-flash-lite`
- `AGENT_NAME=vani-interviewer`

### 2. Run Integration Smoke Tests
Run the comprehensive integration test suite to verify Gemini, MCP, LangGraph, dynamic prompting, and guardrails:
```powershell
python -m unittest tests/test_vani_integration.py
```

### 3. Launch LiveKit Voice Worker
Start the VANI agent worker:
```powershell
python agent.py dev
```

Connect via the [LiveKit Cloud Agent Console](https://cloud.livekit.io/) or your LiveKit client application and start interviewing!
See [LIVEKIT_CONSOLE_GUIDE.md](docs/LIVEKIT_CONSOLE_GUIDE.md) for step-by-step spoken walkthrough instructions.
