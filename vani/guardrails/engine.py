import re
import logging
from typing import Tuple, List, Optional
from config.settings import settings
from vani.session.manager import SessionState

logger = logging.getLogger("vani.guardrails")

# Injection patterns that candidates might speak to hijack prompt or bypass interview
INJECTION_PATTERNS = [
    r"ignore\b.*?\binstructions",
    r"disregard\b.*?\binstructions",
    r"you are now (a|an|in) .* mode",
    r"system prompt",
    r"give me\b.*?\bscore",
    r"reveal (the|your) (secret|instructions|prompt)",
    r"\bbypass\b",
    r"\bsudo\b",
    r"assistant:",
    r"human:",
]

from dataclasses import dataclass

@dataclass
class PolicyDecision:
    action: str  # ALLOW, REDIRECT, WARN, TERMINATE, CLARIFY
    warning_level: int
    off_topic_count: int
    message: str
    should_terminate: bool = False

# Universal off-topic and termination messages
MSG_OFF_TOPIC_REDIRECT = "I'm here to conduct your interview. Can we proceed?"
MSG_OFF_TOPIC_WARN = "Please keep the conversation focused on the interview. Repeated unrelated interruptions may result in this session being closed."
MSG_OFF_TOPIC_TERMINATE = "I'm closing this interview session for now because we haven't been able to proceed. You can take some time and try again later."
MSG_POLITE_TERMINATE = "That's alright. We'll close this session for now. You can take some time and try again later."

class GuardrailsEngine:
    """Enforces the 25 critical guardrails through deterministic checks."""

    @staticmethod
    def check_prompt_injection(user_input: str) -> Tuple[bool, str]:
        """G01: Prompt injection protection."""
        lowered = user_input.lower()
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, lowered):
                logger.warning(f"G01: Prompt injection attempt detected: '{user_input}'")
                return False, "I am focused on conducting your technical interview. Let's return to the question."
        return True, ""

    @staticmethod
    def validate_skill(skill_name: str) -> Tuple[bool, str]:
        """G03 & G11: Invalid skill rejection & Skill switch validation."""
        supported = [s.lower() for s in settings.SUPPORTED_SKILLS]
        if not skill_name or skill_name.strip().lower() not in supported:
            return False, f"'{skill_name}' is not currently supported. Available skills are: {', '.join(settings.SUPPORTED_SKILLS)}."
        return True, ""

    @staticmethod
    def validate_primary_question_allowance(session: SessionState) -> Tuple[bool, str]:
        """G08: Primary question count limit (Max 3)."""
        if session.primary_question_count >= session.max_primary_questions:
            return False, f"Maximum of {session.max_primary_questions} primary questions reached."
        return True, ""

    @staticmethod
    def validate_follow_up_allowance(session: SessionState) -> Tuple[bool, str]:
        """G08: Follow-up limit (Max 1 per primary question)."""
        if session.follow_up_count_for_current_question >= session.max_follow_ups_per_question:
            return False, f"Maximum of {session.max_follow_ups_per_question} follow-up reached for this question."
        return True, ""

    @staticmethod
    def validate_duplicate_question(question_id: str, session: SessionState) -> Tuple[bool, str]:
        """G06: Duplicate question prevention."""
        if question_id in session.presented_questions:
            return False, f"Question {question_id} has already been presented in this session."
        return True, ""

    @staticmethod
    def validate_pause_state(session: SessionState) -> Tuple[bool, str]:
        """G09 & G23: Pause integrity & No progression while paused."""
        if session.is_paused:
            return False, "The interview is currently paused. Please say 'resume' or 'continue' when you are ready."
        return True, ""

    @staticmethod
    def validate_completion_state(session: SessionState) -> Tuple[bool, str]:
        """G21: Interview completion integrity."""
        if session.is_completed:
            return False, "This interview has concluded. Thank you for your time."
        return True, ""

    @staticmethod
    def enforce_output_length(text: str, max_words: int = settings.MAX_SPOKEN_RESPONSE_WORDS) -> str:
        """G13: Output length restriction for spoken clarity."""
        words = text.split()
        if len(words) <= max_words:
            return text
        
        # Truncate at sentence boundary if possible
        truncated = " ".join(words[:max_words])
        last_period = truncated.rfind(".")
        if last_period != -1 and last_period > len(truncated) * 0.6:
            return truncated[:last_period + 1]
        return truncated + "..."

    @staticmethod
    def handle_candidate_policy(
        session: SessionState,
        candidate_intent: str,
        current_stage: str = "STAGE_1",
        current_node: str = "",
        utterance: str = "",
    ) -> PolicyDecision:
        """Centralized Universal Policy & Off-Topic Handler.
        
        Evaluates candidate turn against global policy rules across ALL stages.
        Enforces a single interview-wide off-topic counter that survives stage transitions.
        """
        # 1. If session is already terminated, reject further interaction
        if session.is_terminated():
            return PolicyDecision(
                action="TERMINATE",
                warning_level=session.warning_level,
                off_topic_count=session.off_topic_count,
                message="This interview session has already been closed.",
                should_terminate=True,
            )

        # 2. Universal Off-Topic Policy
        if candidate_intent == "OFF_TOPIC":
            count = session.record_off_topic_violation()
            logger.warning(
                f"Universal Off-Topic Violation #{count} in session {session.session_id} "
                f"(Stage: {current_stage}, Node: {current_node})"
            )
            
            if count == 1:
                return PolicyDecision(
                    action="REDIRECT",
                    warning_level=1,
                    off_topic_count=1,
                    message=MSG_OFF_TOPIC_REDIRECT,
                    should_terminate=False,
                )
            elif count == 2:
                return PolicyDecision(
                    action="WARN",
                    warning_level=2,
                    off_topic_count=2,
                    message=MSG_OFF_TOPIC_WARN,
                    should_terminate=False,
                )
            else:
                session.terminate_session("REPEATED_OFF_TOPIC_INTERACTIONS")
                return PolicyDecision(
                    action="TERMINATE",
                    warning_level=3,
                    off_topic_count=count,
                    message=MSG_OFF_TOPIC_TERMINATE,
                    should_terminate=True,
                )

        # 3. Legitimate / On-topic candidate interaction
        return PolicyDecision(
            action="ALLOW",
            warning_level=session.warning_level,
            off_topic_count=session.off_topic_count,
            message="",
            should_terminate=False,
        )

guardrails = GuardrailsEngine()
