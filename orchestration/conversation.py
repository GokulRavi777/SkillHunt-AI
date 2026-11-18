"""SkillHunt AI Conversation Manager orchestrating LangChain, Gemini, and MCP tools."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

try:
    from ..prompts import DEFAULT_GREETING
except (ImportError, ValueError):
    try:
        from prompts import DEFAULT_GREETING
    except ImportError:
        from examples.vani_interview.prompts import DEFAULT_GREETING
from .llm import create_gemini_llm
from .mcp_client import create_mcp_client, load_vani_tools
from .prompts import ORCHESTRATION_SYSTEM_PROMPT

logger = logging.getLogger("skillhunt-conversation")

NON_ENGLISH_WARNING: str = "I can't understand. Please continue the conversation in English."
OFF_TOPIC_BOUNDARY_RESPONSE: str = "I am here to conduct your technical interview. Let's focus on the interview questions."
FLOW_BOUNDARY_RESPONSE: str = "The rules, interview structure, and topics were already provided during your lobby briefing. Please let me know when you are ready to begin."
NO_COACHING_RESPONSE: str = "As this is an assessment, I can't provide or reveal the answer during the interview. Please share what you know, or let me know if you would like to move on."
REPEAT_LIMIT_REACHED_RESPONSE: str = "I have repeated the question twice. Please share your best answer so we can continue with the interview."
HOLD_20S_AGREEMENT: str = "Sure, I will hold on for 20 seconds. Let me know when you're ready to proceed."
HOLD_EXHAUSTED_RESPONSE: str = "You have already used your 20-second pause quota. We cannot pause again. Would you like to proceed with the interview now, or take it after some time?"
ELABORATION_REQUEST: str = "Could you elaborate on how that works in practice?"



class ConversationManager:
    """Orchestrates candidate dialogue, LangChain Gemini model, and FastMCP tools."""

    def __init__(
        self,
        *,
        model: str = "gemini-3.5-flash-lite",
        api_key: str | None = None,
        system_prompt: str = ORCHESTRATION_SYSTEM_PROMPT,
        initial_greeting: str = DEFAULT_GREETING,
        max_tool_iterations: int = 5,
    ) -> None:
        self.model_name = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.initial_greeting = initial_greeting
        self.max_tool_iterations = max_tool_iterations

        self.messages: list[BaseMessage] = []
        self.tools: list[BaseTool] = []
        self.tool_map: dict[str, BaseTool] = {}
        self.llm = None
        self.llm_with_tools = None
        self.mcp_client = None
        self._initialized = False

        # In-memory interview session state (Pre-set from Candidate Profile)
        self.candidate_name: str = "Candidate"
        self.active_skill: str = "Python"
        self.active_difficulty: str = "Beginner"
        self.last_asked_question: str | None = None
        self.asked_question_ids: list[str] = []
        self.recorded_responses: list[dict[str, str]] = []

        # Assessment Lifecycle & Conversational Guardrails
        self.candidate_id: str | None = None
        self.room_name: str | None = None
        self.target_question_count: int = 3
        self.current_question_index: int = 0
        self.readiness_confirmed: bool = False
        self.is_on_hold: bool = False
        self.hold_used: bool = False
        self.global_follow_up_used: bool = False
        self.in_follow_up: bool = False
        self.elaboration_requested_current_q: bool = False
        self.is_completed: bool = False
        self.current_question_follow_ups: int = 0
        self.max_follow_ups_per_question: int = 1
        self.question_repeat_count: int = 0
        self.max_repeats_per_question: int = 2

    def is_hold_request(self, text: str) -> bool:
        """Check if candidate asked to wait or hold (Readiness Guardrail)."""
        lowered = text.lower().strip()
        hold_triggers = [
            "hold", "wait", "give me a minute", "give me a sec", "hang on",
            "pause", "give me some time", "one minute", "1 minute", "few seconds",
            "just a second", "just a minute", "give me 20", "20 seconds"
        ]
        return any(trigger in lowered for trigger in hold_triggers)

    def is_flow_or_topics_request(self, text: str) -> bool:
        """Detect candidate queries about interview syllabus, topics, flow, structure, or rules."""
        lowered = text.lower().strip()
        flow_triggers = [
            "flow", "topics", "topic", "syllabus", "structure", "format",
            "what will you ask", "what questions", "rules", "schedule", "agenda",
            "how many questions", "what are the questions", "interview flow"
        ]
        return any(trigger in lowered for trigger in flow_triggers)

    def is_vague_or_short_answer(self, text: str) -> bool:
        """Detect candidate responses that are too vague, brief (< 5 words), or non-committal."""
        cleaned = text.strip()
        words = cleaned.split()
        if len(words) < 5:
            lowered = cleaned.lower()
            if any(w in lowered for w in ["yes", "no", "maybe", "idk", "dunno", "not sure", "no idea", "don't know", "dont know", "fine", "ok"]):
                return True
            if len(words) <= 3 and not self.is_repeat_request(cleaned) and not self.is_hold_request(cleaned):
                return True
        return False

    def is_repeat_request(self, text: str) -> bool:
        """Check if candidate asked to repeat the active question (Conversational Guardrail 6)."""
        lowered = text.lower().strip()
        repeat_triggers = [
            "repeat", "say that again", "say again", "one more time", "pardon",
            "what was the question", "didn't hear", "did not hear", "come again",
            "can you repeat", "could you repeat", "repeat the question", "repeat that"
        ]
        return any(trigger in lowered for trigger in repeat_triggers)

    def is_coaching_or_answer_request(self, text: str) -> bool:
        """Detect requests for answers, solutions, or coaching (Conversational Guardrail 2)."""
        lowered = text.lower().strip()
        coaching_triggers = [
            "what is the answer", "what's the answer", "tell me the answer",
            "give me the answer", "give me the solution", "tell me how to do it",
            "what should i say", "tell me the correct way", "can you answer this",
            "solve it for me", "what is the expected answer", "what is correct answer",
            "give me solution", "tell me answer"
        ]
        return any(trigger in lowered for trigger in coaching_triggers)

    def is_off_topic_or_boundary_request(self, text: str) -> bool:
        """Detect off-topic or boundary-crossing requests (Conversational Guardrail 7)."""
        lowered = text.lower().strip()
        off_topic_triggers = [
            "what is the weather", "what's the weather", "tell me a joke", "sing a song",
            "who is the president", "who is the prime minister", "who is prime minister",
            "how old are you", "are you human", "write a poem", "give me a job",
            "what is your salary", "who made you", "tell me about yourself personally"
        ]
        return any(trigger in lowered for trigger in off_topic_triggers)

    def is_non_english(self, text: str) -> bool:
        """Detect non-English scripts, common Romanized Indic phrases, or language switch requests."""
        if not text or not text.strip():
            return False
        # Check non-Latin Unicode blocks (Devanagari, Tamil, Telugu, Kannada, Malayalam, Bengali, etc.)
        if re.search(r"[\u0900-\u0D7F\u0600-\u06FF]", text):
            return True
        lowered = text.lower()
        # Explicit language switch requests
        if any(f"in {lang}" in lowered or f"speak {lang}" in lowered for lang in ["hindi", "tamil", "telugu", "kannada", "malayalam", "bengali", "marathi", "gujarati"]):
            return True
        # Common Romanized Hindi / Tamil / regional tokens
        words = set(re.findall(r"\b[a-z]+\b", lowered))
        non_english_tokens = {
            # Hindi / Hinglish
            "kya", "nahi", "nahin", "mujhe", "tumhe", "aapka", "aapke", "kaise",
            "kaisa", "bolo", "batao", "samajh", "accha", "theek", "dhanyavad",
            "shukriya", "kripya", "namaste", "namaskar", "padha", "sunte", "baat",
            "karo", "karna", "karenge", "mera", "meri", "tere", "teri", "humko",
            # Tamil / Tanglish
            "enna", "solreenga", "pesu", "pesunga", "pesuren", "theriyathu",
            "puriyala", "puriyudha", "romba", "nandri", "vanakkam", "aama",
            "illai", "solla", "mudiyathu", "enakku", "ungalukku",
            # Telugu
            "cheppandi", "teliyadu", "ardham", "kaledu", "namaskaram", "dhanyavadalu",
        }
        return bool(words & non_english_tokens)

    def bind_session(self, candidate_id: str, room_name: str) -> None:
        """Bind candidate identity and room context to session (Lifecycle Guardrail 2)."""
        self.candidate_id = candidate_id
        self.room_name = room_name
        logger.info(f"Session bound to candidate '{candidate_id}' in room '{room_name}'.")

    def configure_candidate_session(
        self,
        candidate_name: str,
        skill: str,
        difficulty: str,
    ) -> str:
        """Configure session with candidate name, parsed skill, and selected difficulty.

        Returns personalized spoken greeting string.
        """
        self.candidate_id = candidate_name
        self.candidate_name = candidate_name
        self.active_skill = skill
        self.active_difficulty = difficulty

        # Formulate tailored greeting
        tailored_greeting = (
            f"Hello {candidate_name}! Welcome to your technical interview on {skill} "
            f"at the {difficulty} level. I am SkillHunt AI, your AI interviewer. Let's begin with our first question."
        )
        self.initial_greeting = tailored_greeting

        # Inject context instructions for Gemini
        context_instruction = (
            f"\n\nCURRENT INTERVIEW TARGET: Candidate '{candidate_name}' has chosen '{skill}' "
            f"at the '{difficulty}' proficiency level. All interview assessment questions must focus "
            f"specifically on '{skill}' and be calibrated for '{difficulty}' complexity."
        )
        if self.messages and isinstance(self.messages[0], SystemMessage):
            self.messages[0] = SystemMessage(content=self.system_prompt + context_instruction)
        if len(self.messages) > 1 and isinstance(self.messages[1], AIMessage):
            self.messages[1] = AIMessage(content=tailored_greeting)

        logger.info(
            f"Candidate session configured: name='{candidate_name}', skill='{skill}', difficulty='{difficulty}'"
        )
        return tailored_greeting

    async def initialize(self) -> None:
        """Connect to MCP server, discover tools, and bind to Gemini."""
        if self._initialized:
            return

        logger.info("Initializing MCP client and discovering interview tools...")
        self.mcp_client, self.tools = await load_vani_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}

        logger.info(f"Connecting LangChain Gemini ({self.model_name})...")
        self.llm = create_gemini_llm(
            model=self.model_name,
            api_key=self.api_key,
        )
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Seed conversation history
        self.reset()
        self._initialized = True
        logger.info("VANI ConversationManager initialized successfully.")

    def reset(self) -> None:
        """Reset conversation state and message history."""
        self.messages = [
            SystemMessage(content=self.system_prompt),
            AIMessage(content=self.initial_greeting),
        ]
        self.active_skill = "Python"
        self.active_difficulty = "Beginner"
        self.last_asked_question = None
        self.asked_question_ids = []
        self.recorded_responses = []
        self.current_question_index = 0
        self.readiness_confirmed = False
        self.is_on_hold = False
        self.hold_used = False
        self.global_follow_up_used = False
        self.in_follow_up = False
        self.elaboration_requested_current_q = False
        self.is_completed = False
        self.current_question_follow_ups = 0
        self.question_repeat_count = 0

    def _extract_text(self, content: Any) -> str:
        """Normalize message content to plain text."""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
            return " ".join(parts).strip()
        return str(content).strip()

    def _extract_tool_result_str(self, result: Any) -> str:
        """Convert tool result into text string for ToolMessage."""
        if isinstance(result, str):
            return result
        if isinstance(result, list):
            texts = []
            for item in result:
                if isinstance(item, dict) and "text" in item:
                    texts.append(str(item["text"]))
                else:
                    texts.append(str(item))
            return "\n".join(texts)
        if isinstance(result, dict):
            return json.dumps(result)
        return str(result)

    async def process_turn(self, user_transcript: str) -> str:
        """Process a candidate utterance through LangChain Gemini and MCP tools.

        Args:
            user_transcript: Transcribed speech from candidate.

        Returns:
            str: Spoken conversational response from VANI for TTS.
        """
        if not self._initialized:
            await self.initialize()

        cleaned_transcript = user_transcript.strip()
        if not cleaned_transcript:
            return "I am listening, please go ahead."

        # Language Enforcement Guardrail (Strictly English Only)
        if self.is_non_english(cleaned_transcript):
            logger.info(
                f"Non-English candidate speech detected: '{cleaned_transcript}'. Enforcing English guardrail."
            )
            self.messages.append(HumanMessage(content=cleaned_transcript))
            self.messages.append(AIMessage(content=NON_ENGLISH_WARNING))
            return NON_ENGLISH_WARNING

        # Conversational Guardrail 7: Candidate Request Boundaries (Off-Topic Requests)
        if self.is_off_topic_or_boundary_request(cleaned_transcript):
            logger.info(
                f"Off-topic candidate request: '{cleaned_transcript}'. Enforcing boundary guardrail."
            )
            self.messages.append(HumanMessage(content=cleaned_transcript))
            self.messages.append(AIMessage(content=OFF_TOPIC_BOUNDARY_RESPONSE))
            return OFF_TOPIC_BOUNDARY_RESPONSE

        # Conversational Guardrail 2: No Answer Coaching or Revealing Expected Answers
        if self.is_coaching_or_answer_request(cleaned_transcript):
            logger.info(
                f"Answer coaching request: '{cleaned_transcript}'. Enforcing no-coaching guardrail."
            )
            self.messages.append(HumanMessage(content=cleaned_transcript))
            self.messages.append(AIMessage(content=NO_COACHING_RESPONSE))
            return NO_COACHING_RESPONSE

        # Conversational Guardrail 6: Repetition and Clarification Limits (Max 2 repeats per question)
        if self.last_asked_question and self.is_repeat_request(cleaned_transcript):
            if self.question_repeat_count >= self.max_repeats_per_question:
                logger.info(
                    f"Repetition limit ({self.max_repeats_per_question}) reached for current question."
                )
                self.messages.append(HumanMessage(content=cleaned_transcript))
                self.messages.append(AIMessage(content=REPEAT_LIMIT_REACHED_RESPONSE))
                return REPEAT_LIMIT_REACHED_RESPONSE
            self.question_repeat_count += 1
            repeat_reply = f"Certainly. The question is: {self.last_asked_question}"
            logger.info(
                f"Repeating active question (count={self.question_repeat_count}): {self.last_asked_question}"
            )
            self.messages.append(HumanMessage(content=cleaned_transcript))
            self.messages.append(AIMessage(content=repeat_reply))
            return repeat_reply

        # Conversational Guardrail: Flow & Topics Query (Redirect to briefing rules)
        if self.is_flow_or_topics_request(cleaned_transcript):
            logger.info(
                f"Flow/topics query: '{cleaned_transcript}'. Enforcing flow boundary."
            )
            self.messages.append(HumanMessage(content=cleaned_transcript))
            self.messages.append(AIMessage(content=FLOW_BOUNDARY_RESPONSE))
            return FLOW_BOUNDARY_RESPONSE

        # Readiness Guardrail: 20-Second Hold Policy (Single-Use Quota)
        if self.is_hold_request(cleaned_transcript):
            self.messages.append(HumanMessage(content=cleaned_transcript))
            if not self.hold_used:
                self.hold_used = True
                self.is_on_hold = True
                self.readiness_confirmed = False
                logger.info("20-second hold granted to candidate.")
                self.messages.append(AIMessage(content=HOLD_20S_AGREEMENT))
                return HOLD_20S_AGREEMENT
            else:
                logger.info("Hold request rejected: 20-second quota exhausted.")
                self.messages.append(AIMessage(content=HOLD_EXHAUSTED_RESPONSE))
                return HOLD_EXHAUSTED_RESPONSE

        # Post-Greeting Readiness Gate
        if not self.readiness_confirmed:
            if any(w in cleaned_transcript.lower() for w in ["ready", "start", "begin", "yes", "go ahead", "let's go", "sure", "yeah", "yep", "ok", "okay"]):
                self.is_on_hold = False
                self.readiness_confirmed = True
                logger.info("Candidate confirmed readiness.")
            else:
                gate_resp = "Please confirm if you are ready to begin the interview, or if you need a 20-second pause."
                self.messages.append(HumanMessage(content=cleaned_transcript))
                self.messages.append(AIMessage(content=gate_resp))
                return gate_resp

        # Conversational Guardrail: Vague / Short Answer Elaboration Quota (Max 1 per question)
        if self.readiness_confirmed and self.last_asked_question and self.is_vague_or_short_answer(cleaned_transcript):
            if not self.elaboration_requested_current_q:
                self.elaboration_requested_current_q = True
                logger.info(f"Vague answer detected ('{cleaned_transcript}'). Asking 1 elaboration.")
                self.messages.append(HumanMessage(content=cleaned_transcript))
                self.messages.append(AIMessage(content=ELABORATION_REQUEST))
                return ELABORATION_REQUEST
            else:
                self.elaboration_requested_current_q = False

        self.messages.append(HumanMessage(content=cleaned_transcript))

        iteration = 0
        while iteration < self.max_tool_iterations:
            iteration += 1
            response = await self.llm_with_tools.ainvoke(self.messages)

            # Check if model requested tool executions
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # Direct conversational response
                self.messages.append(response)
                spoken_text = self._extract_text(response.content)
                logger.info(f"VANI response: {spoken_text}")
                return spoken_text

            # Append the AIMessage containing tool calls
            self.messages.append(response)

            for call in tool_calls:
                tool_name = call.get("name")
                call_id = call.get("id")
                args = call.get("args", {})
                logger.info(f"Executing MCP tool '{tool_name}' with args {args}")

                tool = self.tool_map.get(tool_name)
                if not tool:
                    err_msg = f"Error: Tool '{tool_name}' not found."
                    self.messages.append(ToolMessage(content=err_msg, tool_call_id=call_id))
                    continue

                try:
                    tool_raw_result = await tool.ainvoke(args)
                    result_str = self._extract_tool_result_str(tool_raw_result)

                    # Update internal tracking
                    if tool_name == "select_interview_skill":
                        self.active_skill = args.get("skill_name")
                        self.active_difficulty = args.get("difficulty", "Intermediate")
                    elif tool_name == "get_next_question":
                        try:
                            parsed = json.loads(result_str)
                            if isinstance(parsed, dict):
                                self.last_asked_question = parsed.get("question")
                                self.question_repeat_count = 0
                                self.current_question_follow_ups = 0
                                q_id = parsed.get("question_id")
                                if q_id and q_id not in self.asked_question_ids:
                                    self.asked_question_ids.append(q_id)
                        except Exception:
                            pass
                    elif tool_name == "save_interview_response":
                        self.recorded_responses.append(args)

                    self.messages.append(ToolMessage(content=result_str, tool_call_id=call_id))
                except Exception as ex:
                    logger.exception(f"Error executing MCP tool '{tool_name}': {ex}")
                    self.messages.append(
                        ToolMessage(content=f"Error executing tool: {ex}", tool_call_id=call_id)
                    )

        # Fallback if iterations exceeded
        fallback = await self.llm.ainvoke(self.messages)
        self.messages.append(fallback)
        return self._extract_text(fallback.content)
