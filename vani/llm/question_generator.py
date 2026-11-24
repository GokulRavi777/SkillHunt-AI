import re
import logging
from typing import Dict, Any, Optional, List
from vani.llm.model import model_service
from vani.llm.prompt_builder import prompt_builder
from vani.llm.prompts import SYSTEM_INTERVIEWER_INSTRUCTION
from vani.session.manager import SessionState
from config.settings import settings

logger = logging.getLogger("vani.question_gen")

class QuestionValidator:
    """Deterministic validation of generated questions against guardrails."""

    @staticmethod
    def validate_question(
        question_text: str,
        skill: str,
        presented_questions: List[str],
        max_words: int = 50,
    ) -> tuple[bool, str]:
        if not question_text or len(question_text.strip()) < 10:
            return False, "Question is too short or empty."

        words = question_text.split()
        if len(words) > max_words:
            return False, f"Question exceeds maximum spoken word length ({len(words)} > {max_words})."

        # Check for multiple questions (e.g. multiple question marks)
        q_marks = question_text.count("?")
        if q_marks > 1:
            return False, "Contains multiple question marks; only 1 question allowed."

        # Check for unwanted formatting (markdown, code tags)
        if any(char in question_text for char in ["*", "`", "#", "{", "}"]):
            return False, "Contains markdown or code syntax unsuitable for speech."

        # Check duplicate
        for prev in presented_questions:
            if question_text.strip().lower() == prev.strip().lower():
                return False, "Question is a duplicate of a previously asked question."

        return True, "Valid"

    @staticmethod
    def clean_for_speech(text: str) -> str:
        """Strips out markdown asterisks, backticks, emojis, and extra whitespace."""
        clean = re.sub(r"[\*`#_\[\]\(\)\{\}]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean


class DynamicQuestionGenerator:
    """Core question generation engine implementing dynamic prompt assembly and validation."""

    def __init__(self) -> None:
        self.validator = QuestionValidator()

    async def generate_primary_question(
        self,
        session: SessionState,
        topic: str,
        subtopic: str,
        difficulty: str = "Mid-Level",
        question_type: str = "conceptual",
    ) -> Dict[str, Any]:
        """Generates a dynamic primary question using few-shot prompt construction."""
        skill = session.selected_skill or "Python"
        remaining_allowance = session.max_primary_questions - session.primary_question_count

        prompt = prompt_builder.build_primary_question_prompt(
            skill=skill,
            topic=topic,
            subtopic=subtopic,
            difficulty=difficulty,
            question_type=question_type,
            previously_asked_questions=session.presented_questions,
            concepts_explored=session.concepts_mentioned,
            remaining_primary_allowance=remaining_allowance,
        )

        # Call Gemini
        result = await model_service.invoke_json(prompt, system_prompt=SYSTEM_INTERVIEWER_INSTRUCTION)
        q_text = result.get("question_text", "")
        q_text = self.validator.clean_for_speech(q_text)

        # Validate
        is_valid, reason = self.validator.validate_question(
            q_text,
            skill=skill,
            presented_questions=session.presented_questions,
            max_words=settings.MAX_SPOKEN_RESPONSE_WORDS,
        )

        if not is_valid:
            logger.warning(f"Generated primary question failed validation ({reason}). Using safe fallback.")
            q_text = f"Could you explain how {subtopic or topic} works in {skill} and what design advantages it provides?"

        return {
            "question_text": q_text,
            "topic": topic,
            "subtopic": subtopic,
            "difficulty": difficulty,
            "expected_concepts": result.get("expected_concepts", [topic, subtopic]),
            "question_type": question_type,
        }

    async def generate_follow_up(
        self,
        session: SessionState,
        candidate_answer: str,
        concepts_identified: List[str],
        missing_concepts: List[str],
        follow_up_type: str = "follow_up",
    ) -> Dict[str, Any]:
        """Generates a contextual follow-up or cross-question grounded in candidate's answer."""
        skill = session.selected_skill or "Python"
        remaining_allowance = session.max_follow_ups_per_question - session.follow_up_count_for_current_question
        primary_q = session.current_question_text or "the previous question"

        prompt = prompt_builder.build_follow_up_prompt(
            skill=skill,
            primary_question=primary_q,
            candidate_answer=candidate_answer,
            concepts_identified=concepts_identified,
            missing_concepts=missing_concepts,
            concepts_already_explored=session.concepts_mentioned,
            follow_up_history=session.follow_up_history,
            remaining_follow_up_allowance=remaining_allowance,
            follow_up_type=follow_up_type,
        )

        result = await model_service.invoke_json(prompt, system_prompt=SYSTEM_INTERVIEWER_INSTRUCTION)
        q_text = result.get("question_text", "")
        q_text = self.validator.clean_for_speech(q_text)
        ack = result.get("acknowledgment", "Got it.")
        ack = self.validator.clean_for_speech(ack)

        # Validate
        is_valid, reason = self.validator.validate_question(
            q_text,
            skill=skill,
            presented_questions=session.presented_questions,
            max_words=settings.MAX_SPOKEN_RESPONSE_WORDS,
        )

        if not is_valid:
            logger.warning(f"Follow-up question failed validation ({reason}). Using fallback.")
            if missing_concepts:
                q_text = f"How would you address {missing_concepts[0]} in this scenario?"
            else:
                q_text = f"Could you walk me through an edge case or potential pitfall with that approach?"

        return {
            "acknowledgment": ack,
            "question_text": q_text,
            "full_spoken_utterance": f"{ack} {q_text}".strip(),
            "target_concept": result.get("target_concept", ""),
            "question_type": follow_up_type,
        }

question_generator = DynamicQuestionGenerator()
