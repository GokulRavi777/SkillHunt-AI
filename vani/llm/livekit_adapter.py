import asyncio
import json
import logging
from typing import Any, Optional
from livekit.agents import llm, utils
from livekit.agents.llm import ToolChoice
from livekit.agents.llm.chat_context import ChatContext
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)
from config.settings import settings
from vani.graph.workflow import interview_engine
from vani.session.manager import session_manager

logger = logging.getLogger("vani.livekit_adapter")

class VaniInterviewerLLM(llm.LLM):
    """Bridges LiveKit Agents audio turns directly to the VANI LangGraph interview engine."""

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id
        self._agent_session: Optional[Any] = None
        self._room: Optional[Any] = None
        self._prep_timer_task: Optional[asyncio.Task] = None
        self._answer_timer_task: Optional[asyncio.Task] = None

    def set_agent_session(self, session: Any, room: Any) -> None:
        """Stores agent session and room references for timer prompts and clean termination."""
        self._agent_session = session
        self._room = room

    def cancel_prep_timer(self) -> None:
        """Safely cancels running preparation timer if candidate speaks or session completes."""
        if self._prep_timer_task and not self._prep_timer_task.done():
            self._prep_timer_task.cancel()
            self._prep_timer_task = None

    def cancel_answer_timer(self) -> None:
        """Safely cancels active 30-second answer timer when candidate begins answering."""
        if self._answer_timer_task and not self._answer_timer_task.done():
            self._answer_timer_task.cancel()
            self._answer_timer_task = None

    def start_answer_timer(self, duration: float = 30.0) -> None:
        """Starts asynchronous 30-second answer timer after question playback completes."""
        self.cancel_answer_timer()
        self._answer_timer_task = asyncio.create_task(self._run_answer_timer(duration))

    async def _run_answer_timer(self, duration: float) -> None:
        """Asynchronous answer timer: waits 30s; if candidate remains silent, moves to next question."""
        try:
            logger.info(f"Starting {duration}s answer timer for session {self.session_id}")
            await asyncio.sleep(duration)
            sess = session_manager.get_or_create(self.session_id)
            if sess.current_state in ["LISTENING", "ASKING_QUESTION"] and not sess.is_terminated():
                timeout_msg = await interview_engine.handle_answer_timeout(self.session_id)
                if timeout_msg and self._agent_session:
                    logger.info(f"Answer timer expired for session {self.session_id}; advancing question")
                    if self._room and hasattr(self._room, "local_participant") and self._room.local_participant:
                        try:
                            import json
                            payload = json.dumps({"type": "transcript", "sender": "Vani", "text": timeout_msg}).encode("utf-8")
                            await self._room.local_participant.publish_data(payload, reliable=True)
                        except Exception as e:
                            logger.warning(f"Error publishing answer timeout transcript: {e}")
                    await self._agent_session.say(timeout_msg)
        except asyncio.CancelledError:
            logger.info(f"Answer timer cancelled early for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error in answer timer task: {e}")

    def start_prep_timer(self) -> None:
        """Starts asynchronous 20-second preparation timer with confirmation fallback."""
        self.cancel_prep_timer()
        self._prep_timer_task = asyncio.create_task(self._run_prep_timer())

    async def _run_prep_timer(self) -> None:
        """Asynchronous timer: waits 20s for candidate; if silent, prompts for readiness confirmation."""
        try:
            logger.info(f"Starting 20s preparation timer for session {self.session_id}")
            await asyncio.sleep(settings.PREPARATION_WAIT_SECONDS)
            sess = session_manager.get_or_create(self.session_id)
            if sess.current_state == "PREPARATION_WAIT" and not sess.is_terminated():
                timeout_msg = await interview_engine.handle_preparation_timeout(self.session_id)
                if timeout_msg and self._agent_session:
                    logger.info(f"Preparation timer expired for {self.session_id}; asking readiness confirmation")
                    if self._room and hasattr(self._room, "local_participant") and self._room.local_participant:
                        try:
                            import json
                            payload = json.dumps({"type": "transcript", "sender": "Vani", "text": timeout_msg}).encode("utf-8")
                            await self._room.local_participant.publish_data(payload, reliable=True)
                        except Exception as e:
                            logger.warning(f"Error publishing prep timeout transcript: {e}")
                    await self._agent_session.say(timeout_msg)
                    
                    # Wait for confirmation timeout
                    await asyncio.sleep(settings.CONFIRMATION_TIMEOUT_SECONDS)
                    if sess.current_state == "READINESS_CONFIRMATION" and not sess.is_terminated():
                        logger.info(f"Confirmation timeout expired for {self.session_id}; terminating politely")
                        term_msg = await interview_engine.handle_confirmation_timeout(self.session_id)
                        if term_msg:
                            if self._room and hasattr(self._room, "local_participant") and self._room.local_participant:
                                try:
                                    import json
                                    payload = json.dumps({"type": "transcript", "sender": "Vani", "text": term_msg}).encode("utf-8")
                                    await self._room.local_participant.publish_data(payload, reliable=True)
                                except Exception as e:
                                    logger.warning(f"Error publishing confirmation timeout transcript: {e}")
                            await self._agent_session.say(term_msg)
                            await asyncio.sleep(5.0)
                            if self._room:
                                await self._room.disconnect()
        except asyncio.CancelledError:
            logger.info(f"Preparation timer cancelled early for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error in preparation timer task: {e}")

    @property
    def model(self) -> str:
        return "vani-langgraph-gemini"

    @property
    def provider(self) -> str:
        return "VANI-LangChain"

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[llm.Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> "VaniInterviewerLLMStream":
        return VaniInterviewerLLMStream(
            self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
            session_id=self.session_id,
        )


class VaniInterviewerLLMStream(llm.LLMStream):
    def __init__(
        self,
        llm: VaniInterviewerLLM,
        *,
        chat_ctx: ChatContext,
        tools: list[llm.Tool],
        conn_options: APIConnectOptions,
        session_id: str,
    ) -> None:
        super().__init__(
            llm,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options,
        )
        self.session_id = session_id
        self.llm = llm

    async def _run(self) -> None:
        try:
            # Inspect messages to see what user said
            messages = list(self._chat_ctx.messages())
            last_user_message = None
            for m in reversed(messages):
                if m.role == "user":
                    # Robust extraction across livekit versions & content formats
                    text = None
                    if getattr(m, "text_content", None):
                        text = m.text_content
                    elif getattr(m, "raw_text_content", None):
                        text = m.raw_text_content
                    elif getattr(m, "content", None):
                        if isinstance(m.content, str):
                            text = m.content
                        elif isinstance(m.content, list):
                            parts = []
                            for c in m.content:
                                if isinstance(c, str):
                                    parts.append(c)
                                elif isinstance(c, dict) and "text" in c:
                                    parts.append(c["text"])
                                elif hasattr(c, "text"):
                                    parts.append(str(c.text))
                            if parts:
                                text = " ".join(parts)
                    if text and text.strip():
                        last_user_message = text.strip()
                        break

            if not last_user_message:
                # Trigger initial greeting
                response_text = await interview_engine.start_interview(self.session_id)
            else:
                # Candidate spoke: cancel running preparation and answer timers immediately
                self.llm.cancel_prep_timer()
                self.llm.cancel_answer_timer()
                
                # Broadcast Candidate transcript to room data channel
                if self.llm._room and hasattr(self.llm._room, "local_participant") and self.llm._room.local_participant:
                    try:
                        import json
                        c_payload = json.dumps({"type": "transcript", "sender": "Candidate", "text": last_user_message}).encode("utf-8")
                        await self.llm._room.local_participant.publish_data(c_payload, reliable=True)
                    except Exception as err:
                        logger.warning(f"Error publishing candidate transcript: {err}")

                # Process candidate turn through LangGraph
                response_text = await interview_engine.handle_candidate_utterance(
                    self.session_id, last_user_message
                )

            # Broadcast Vani transcript to room data channel
            if self.llm._room and hasattr(self.llm._room, "local_participant") and self.llm._room.local_participant and response_text:
                try:
                    import json
                    v_payload = json.dumps({"type": "transcript", "sender": "Vani", "text": response_text}).encode("utf-8")
                    await self.llm._room.local_participant.publish_data(v_payload, reliable=True)
                except Exception as err:
                    logger.warning(f"Error publishing Vani transcript: {err}")

            # Stream words/sentences to LiveKit TTS
            chunk_id = utils.shortuuid("VANI_")
            chunk = llm.ChatChunk(
                id=chunk_id,
                delta=llm.ChoiceDelta(
                    role="assistant",
                    content=response_text,
                ),
            )
            self._event_ch.send_nowait(chunk)

            # State check: trigger timers or scheduled disconnect
            sess = session_manager.get_or_create(self.session_id)
            if sess.current_state == "PREPARATION_WAIT":
                self.llm.start_prep_timer()
            elif sess.current_state in ["LISTENING", "ASKING_QUESTION"] and not sess.is_terminated():
                # Start 30-second answer window after question is delivered
                self.llm.start_answer_timer(duration=sess.answer_timer_duration)
            elif sess.is_terminated() or sess.cleanup_completed:
                self.llm.cancel_prep_timer()
                self.llm.cancel_answer_timer()
                sess.final_response_delivered = True
                if self.llm._room:
                    words = len(response_text.split())
                    delay = max(3.0, min(8.0, (words / 2.5) + 1.0))
                    asyncio.create_task(self._safe_terminal_cleanup(self.llm._room, delay=delay))

        except Exception as e:
            logger.error(f"Error in VaniInterviewerLLMStream: {e}", exc_info=True)
            err_chunk = llm.ChatChunk(
                id=utils.shortuuid("ERR_"),
                delta=llm.ChoiceDelta(
                    role="assistant",
                    content="I experienced a brief connection glitch. Could you please repeat that?",
                ),
            )
            self._event_ch.send_nowait(err_chunk)

    async def _safe_terminal_cleanup(self, room: Any, delay: float = 5.0) -> None:
        try:
            await asyncio.sleep(delay)
            sess = session_manager.get(self.session_id)
            if sess:
                final_assessment = sess.finalize_assessment()
                sess.mark_cleanup_completed()

                # Sync to SQLite database for candidate portal results
                try:
                    import json
                    from datetime import datetime
                    from backend.app.database import SessionLocal
                    from backend.app.models import InterviewSession

                    with SessionLocal() as db:
                        db_sess = db.query(InterviewSession).filter(InterviewSession.id == self.session_id).first()
                        if db_sess:
                            db_sess.session_status = sess.session_status
                            db_sess.terminal_outcome = sess.terminal_outcome
                            db_sess.termination_reason = sess.termination_reason
                            if sess.completed_at:
                                db_sess.completed_at = datetime.fromtimestamp(sess.completed_at)
                                if sess.started_at:
                                    db_sess.duration_seconds = round(sess.completed_at - sess.started_at, 2)
                            if final_assessment:
                                db_sess.assessment_summary_json = json.dumps(final_assessment)
                            db.commit()
                            logger.info(f"Persisted assessment outcome to SQLite for {self.session_id}")
                except Exception as db_e:
                    logger.warning(f"Could not persist session assessment to SQLite: {db_e}")

            logger.info(f"Executing safe room disconnect following interview conclusion for session {self.session_id}.")
            if room:
                await room.disconnect()
        except Exception as e:
            logger.warning(f"Error in safe terminal cleanup: {e}")
