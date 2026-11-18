"""SkillHunt AI - Minimal LiveKit Conversational Interview Agent with LangChain & FastMCP.

Connects to LiveKit Cloud, accepts candidate sessions, greets the candidate automatically,
transcribes candidate speech using Gnani STT (en-IN), conducts an interview using Google
Gemini (gemini-3.5-flash-lite) through LangChain and official FastMCP tools, and speaks
responses using Gnani TTS (Nalini).
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    ModelSettings,
    TurnHandlingOptions,
    cli,
    llm,
    room_io,
)
from livekit.agents.voice.events import ErrorEvent, UserInputTranscribedEvent
from livekit.plugins import gnani, google, silero

try:
    from .orchestration.conversation import ConversationManager
    from .orchestration.prompts import ORCHESTRATION_SYSTEM_PROMPT
    from .prompts import DEFAULT_GREETING, VANI_SYSTEM_PROMPT
except ImportError:
    from orchestration.conversation import ConversationManager
    from orchestration.prompts import ORCHESTRATION_SYSTEM_PROMPT
    from prompts import DEFAULT_GREETING, VANI_SYSTEM_PROMPT

logger = logging.getLogger("skillhunt-agent")

# Auto-load environment for top-level worker discovery
_local_env = Path(__file__).parent / ".env"
if _local_env.exists():
    load_dotenv(dotenv_path=_local_env)
else:
    load_dotenv()


# Pre-warm Silero VAD at module load time so ONNX session creation does not block the async event loop during room connection
try:
    _WARMED_VAD: Any = silero.VAD.load()
except Exception as _ex:
    logger.warning(f"Silero VAD pre-warm skipped: {_ex}")
    _WARMED_VAD = None


@dataclass
class VaniConfig:
    """Configuration and credential management for VANI agent."""

    livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None
    gnani_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gnani_stt_language: str = "en-IN"
    gnani_tts_voice: str = "Nalini"
    gnani_tts_model: str = "timbre-v2.5"
    gnani_tts_language: str = "en-IN"
    mcp_transport: str = "stdio"
    mcp_server_url: str = "http://127.0.0.1:8000/sse"
    endpointing_min_delay: float = 0.15
    endpointing_max_delay: float = 0.40
    vad_min_silence_duration: float = 0.25

    @classmethod
    def from_env(
        cls,
        dotenv_path: str | Path | None = None,
        *,
        load_env_file: bool = True,
    ) -> VaniConfig:
        """Load configuration from environment and optional .env file."""
        if load_env_file:
            if dotenv_path is not None:
                load_dotenv(dotenv_path=dotenv_path, override=False)
            else:
                local_env = Path(__file__).parent / ".env"
                if local_env.exists():
                    load_dotenv(dotenv_path=local_env, override=False)
                else:
                    load_dotenv(override=False)

        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        if not gemini_model:
            gemini_model = "gemini-3.5-flash-lite"

        return cls(
            livekit_url=os.environ.get("LIVEKIT_URL"),
            livekit_api_key=os.environ.get("LIVEKIT_API_KEY"),
            livekit_api_secret=os.environ.get("LIVEKIT_API_SECRET"),
            gnani_api_key=os.environ.get("GNANI_API_KEY"),
            gemini_api_key=gemini_key,
            gemini_model=gemini_model,
            gnani_stt_language=os.environ.get("GNANI_STT_LANGUAGE", "en-IN"),
            gnani_tts_voice=os.environ.get("GNANI_TTS_VOICE", "Nalini"),
            gnani_tts_model=os.environ.get("GNANI_TTS_MODEL", "timbre-v2.5"),
            gnani_tts_language=os.environ.get("GNANI_TTS_LANGUAGE", "en-IN"),
            mcp_transport=os.environ.get("MCP_TRANSPORT", "stdio"),
            mcp_server_url=os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000/sse"),
            endpointing_min_delay=float(os.environ.get("ENDPOINTING_MIN_DELAY", "0.15")),
            endpointing_max_delay=float(os.environ.get("ENDPOINTING_MAX_DELAY", "0.40")),
            vad_min_silence_duration=float(os.environ.get("VAD_MIN_SILENCE_DURATION", "0.25")),
        )

    def validate_credentials(self, *, require_livekit: bool = True) -> list[str]:
        """Validate required credentials and return a list of missing variable names."""
        missing: list[str] = []
        if require_livekit:
            if not self.livekit_url:
                missing.append("LIVEKIT_URL")
            if not self.livekit_api_key:
                missing.append("LIVEKIT_API_KEY")
            if not self.livekit_api_secret:
                missing.append("LIVEKIT_API_SECRET")

        if not self.gnani_api_key:
            missing.append("GNANI_API_KEY")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")

        return missing

    def ensure_valid_credentials(self, *, require_livekit: bool = True) -> None:
        """Raise ValueError if any required credential is missing."""
        missing = self.validate_credentials(require_livekit=require_livekit)
        if missing:
            raise ValueError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Please configure them in your .env or environment before starting the agent."
            )


class VaniInterviewAgent(Agent):
    """VANI technical interviewer agent powered by LangChain and FastMCP."""

    def __init__(
        self,
        instructions: str = VANI_SYSTEM_PROMPT,
        *,
        conversation_manager: ConversationManager | None = None,
        config: VaniConfig | None = None,
    ) -> None:
        super().__init__(instructions=instructions)
        cfg = config or VaniConfig.from_env()
        self.conversation_manager = conversation_manager or ConversationManager(
            model=cfg.gemini_model,
            api_key=cfg.gemini_api_key,
            system_prompt=ORCHESTRATION_SYSTEM_PROMPT,
        )
        self._hold_timer: asyncio.Task[None] | None = None

    async def _run_hold_timer(self, delay: float = 20.0) -> None:
        """Wait for hold duration, then gently prompt candidate to resume or reschedule."""
        try:
            logger.info(f"Readiness hold timer started ({delay}s). Waiting for candidate...")
            await asyncio.sleep(delay)
            logger.info(f"Readiness hold timer ({delay}s) expired without candidate resumption.")
            prompt_msg = (
                "We have to continue with the interview now. If you're feeling nervous or need a break, "
                "you can always take the interview after some time. Would you like to proceed, or should we stop here for today?"
            )
            # Add message to conversation memory so LLM is aware
            self.conversation_manager.messages.append(AIMessage(content=prompt_msg))
            session = getattr(self, "_session", None) or getattr(self, "_session_override", None)
            if session is None:
                try:
                    session = self.session
                except Exception:
                    session = None
            if session:
                await session.say(prompt_msg, allow_interruptions=False)
        except asyncio.CancelledError:
            logger.info("Hold timer cancelled due to candidate speech resumption.")
            raise

    async def on_enter(self) -> None:
        """Initialize MCP client/tools, bind session, read participant metadata, and greet candidate."""
        logger.info("Candidate entered room. Initializing VANI LangChain MCP pipeline...")
        greeting = DEFAULT_GREETING
        session = getattr(self, "_session_override", None) or getattr(self, "_session", None)
        if session is None:
            try:
                session = self.session
            except Exception:
                session = None

        try:
            await self.conversation_manager.initialize()
            room = getattr(session, "room", None) if session else None
            room_name = getattr(room, "name", None) or "console-session"

            # Extract metadata from candidate participant if present
            candidate_name = "Candidate"
            selected_skill = "Python"
            proficiency = "Intermediate"

            remote_participants = getattr(room, "remote_participants", {}) if room else {}
            if remote_participants:
                for p in remote_participants.values():
                    raw_meta = getattr(p, "metadata", None)
                    if raw_meta:
                        try:
                            import json
                            meta = json.loads(raw_meta)
                            candidate_name = meta.get("candidateName", getattr(p, "name", None) or candidate_name)
                            selected_skill = meta.get("selectedSkill", selected_skill)
                            proficiency = meta.get("proficiency", proficiency)
                            break
                        except Exception:
                            pass

            # Configure session with parsed skill & selected difficulty
            greeting = self.conversation_manager.configure_candidate_session(
                candidate_name=candidate_name,
                skill=selected_skill,
                difficulty=proficiency,
            )
            self.conversation_manager.bind_session(candidate_id=f"cand_{candidate_name}", room_name=room_name)

            # Synchronize chosen skill into FastMCP server
            if "select_interview_skill" in self.conversation_manager.tool_map:
                try:
                    await self.conversation_manager.tool_map["select_interview_skill"].ainvoke({
                        "skill_name": selected_skill,
                        "difficulty": proficiency,
                    })
                except Exception as tool_ex:
                    logger.warning(f"FastMCP skill sync warning: {tool_ex}")

        except Exception as ex:
            logger.exception(f"Failed to initialize conversation manager: {ex}")
            greeting = DEFAULT_GREETING

        logger.info(f"Initiating spoken greeting: {greeting}")
        if session:
            try:
                await session.say(greeting, allow_interruptions=False)
            except Exception as ex:
                logger.warning(f"say() failed in on_enter: {ex}")
                try:
                    await session.generate_reply(allow_interruptions=False)
                except Exception:
                    pass

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[str]:
        """Process candidate turn through LangChain Gemini and FastMCP tools."""
        try:
            msgs = chat_ctx.messages() if callable(chat_ctx.messages) else chat_ctx.messages
            user_transcript = ""
            for msg in reversed(msgs):
                if getattr(msg, "role", None) == "user" and getattr(msg, "text_content", None):
                    user_transcript = msg.text_content
                    break

            if not user_transcript:
                yield DEFAULT_GREETING
                return

            # Language Enforcement Guardrail (Strictly English Only)
            if self.conversation_manager.is_non_english(user_transcript):
                logger.info(f"Candidate spoke non-English: '{user_transcript}'. Enforcing English guardrail.")
                response_text = await self.conversation_manager.process_turn(user_transcript)
                if response_text:
                    yield response_text
                return

            # Cancel any pending hold timer as candidate has resumed speaking in English
            if self._hold_timer and not self._hold_timer.done():
                self._hold_timer.cancel()
                self._hold_timer = None

            logger.info(f"Processing candidate turn via LangChain + MCP: '{user_transcript}'")
            response_text = await self.conversation_manager.process_turn(user_transcript)
            if response_text:
                yield response_text

            # If candidate requested to hold and readiness is not yet locked, start the 20s hold timer
            if self.conversation_manager.is_hold_request(user_transcript) and not self.conversation_manager.readiness_confirmed:
                hold_seconds = float(os.environ.get("HOLD_TIMEOUT_SECONDS", "20.0"))
                logger.info(f"Candidate asked to hold. Starting {hold_seconds}s automatic resumption timer.")
                self._hold_timer = asyncio.create_task(self._run_hold_timer(hold_seconds))
        except Exception as ex:
            logger.exception(f"Error in LangChain MCP turn processing: {ex}")
            yield "I had a momentary glitch processing that. Could you please share that once more?"


def create_agent_session(
    config: VaniConfig,
    *,
    stt_override: Any = None,
    tts_override: Any = None,
    llm_override: Any = None,
    vad_override: Any = None,
) -> AgentSession:
    """Build and configure the AgentSession pipeline.

    Connects Gnani STT (en-IN), Google Gemini (gemini-3.5-flash-lite),
    Gnani TTS (Nalini timbre-v2.5), and Silero VAD.
    """
    stt_instance = stt_override or gnani.STT(
        language=config.gnani_stt_language,
        sample_rate=16000,
        use_streaming=True,
        api_key=config.gnani_api_key,
    )

    tts_instance = tts_override or gnani.TTS(
        voice=config.gnani_tts_voice,
        model=config.gnani_tts_model,
        language=config.gnani_tts_language,
        sample_rate=16000,
        api_key=config.gnani_api_key,
        synthesize_method="websocket",
    )

    if config.gemini_api_key and "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = config.gemini_api_key

    llm_instance = llm_override or google.LLM(
        model=config.gemini_model,
        api_key=config.gemini_api_key,
    )

    vad_instance = vad_override or _WARMED_VAD or silero.VAD.load(
        min_silence_duration=config.vad_min_silence_duration,
    )
    if hasattr(vad_instance, "update_options"):
        try:
            vad_instance.update_options(min_silence_duration=config.vad_min_silence_duration)
        except Exception:
            pass

    turn_handling = TurnHandlingOptions(
        turn_detection=None,
        endpointing={
            "mode": "fixed",
            "min_delay": config.endpointing_min_delay,
            "max_delay": config.endpointing_max_delay,
        },
        interruption={
            "resume_false_interruption": False,
        },
        preemptive_generation={"enabled": False},
    )

    session = AgentSession(
        stt=stt_instance,
        llm=llm_instance,
        tts=tts_instance,
        vad=vad_instance,
        turn_handling=turn_handling,
        tts_text_transforms=[
            "filter_emoji",
            "filter_markdown",
        ],
    )

    @session.on("user_input_transcribed")
    def _on_transcribed(ev: UserInputTranscribedEvent) -> None:
        if ev.is_final:
            logger.info(f"Candidate transcript: {ev.transcript}")

    @session.on("error")
    def _on_error(ev: ErrorEvent) -> None:
        logger.error(f"Pipeline error from {ev.source}: {ev.error}")

    return session


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """LiveKit agent worker entrypoint called upon room assignment."""
    logger.info(f"SkillHunt AI agent job received. Connecting to room: {ctx.room.name}")
    ctx.log_context_fields = {"room": ctx.room.name}

    config = VaniConfig.from_env()
    from livekit.agents.cli import AgentsConsole

    is_console = AgentsConsole.get_instance().enabled
    config.ensure_valid_credentials(require_livekit=not is_console)

    session = create_agent_session(config)

    logger.info("Starting SkillHunt AI AgentSession in room %s", ctx.room.name)
    await session.start(
        agent=VaniInterviewAgent(config=config),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(sample_rate=16000),
            audio_output=room_io.AudioOutputOptions(sample_rate=16000),
        ),
    )


# Alias for backwards compatibility
SkillHuntInterviewAgent = VaniInterviewAgent


if __name__ == "__main__":
    cli.run_app(server)
