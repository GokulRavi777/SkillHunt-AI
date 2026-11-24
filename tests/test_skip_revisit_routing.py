"""Automated Test Suite for Dynamic Question Skip and Revisit Routing in VANI 2.0.

Validates all 12 required test conditions:
1. Explicit permanent skip (Q2 -> Confirmation -> SKIP_ENTIRELY -> Q3 -> Conclusion)
2. Explicit revisit preference (Q2 -> Confirmation -> REVISIT_AFTER_NEXT -> Q3 -> Q2 Revisit -> Conclusion)
3. Ambiguous clarification response (triggers retry)
4. Clarification retry limit (2nd ambiguous response returns control to Q2)
5. Q2 permanent skip never revisits Q2
6. Q2 revisit happens exactly once
7. Q2 revisit proceeds directly to Conclusion
8. Resume after interruption at skip confirmation
9. Resume during Q3
10. Resume during Q2 revisit
11. Skill switching is rejected
12. Existing interview workflows remain functional
"""
import unittest
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import patch, AsyncMock
from vani.graph.workflow import interview_engine, interview_graph
from vani.session.manager import session_manager
from vani.schemas.models import SkipPreferenceDecision, SkipIntentDecision


class TestSkipRevisitRouting(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Fresh isolated session ID for each test
        self.session_id = f"test_session_{self._testMethodName}"
        session_manager.cleanup(self.session_id)

    async def asyncTearDown(self):
        session_manager.cleanup(self.session_id)

    async def _onboard_to_q2(self, session_id: str):
        """Helper to advance a session to Q2."""
        await interview_engine.start_interview(session_id)
        await interview_engine.handle_candidate_utterance(session_id, "yes I am ready")
        # Answer Q1 (and any follow-up) to advance to Q2
        await self._answer_primary_and_follow_up(
            session_id,
            "Lists are mutable and defined with square brackets, while tuples are immutable and defined with parentheses.",
            "Lists can have items added or removed dynamically, whereas tuples have fixed contents ensuring data integrity."
        )
        session = session_manager.get(session_id)
        self.assertEqual(session.primary_question_count, 2)
        return session

    async def _answer_primary_and_follow_up(self, session_id: str, answer_text: str, follow_up_answer: str = "Understood, that is my complete technical answer.") -> str:
        """Answers a question and handles its follow-up if asked."""
        res = await interview_engine.handle_candidate_utterance(session_id, answer_text)
        session = session_manager.get(session_id)
        if session.follow_up_count_for_current_question > 0 and not session.is_completed and session.question_visit_mode != "REVISIT":
            res = await interview_engine.handle_candidate_utterance(session_id, follow_up_answer)
        return res

    async def test_01_explicit_permanent_skip(self):
        """Scenario A: Q2 -> Confirmation -> SKIP_ENTIRELY -> Q3 -> Conclusion (never revisits Q2)."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)
        q2_id = session.current_question_id

        # Candidate requests skip
        r_skip = await interview_engine.handle_candidate_utterance(session_id, "Can we skip this question?")
        self.assertIn("permanently or revisit", r_skip.lower())
        self.assertEqual(session.current_state, "SKIP_CONFIRMATION")

        # Candidate chooses permanent skip
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="SKIP_ENTIRELY", confidence=0.99, reasoning="Explicit")):
            r_pref = await interview_engine.handle_candidate_utterance(session_id, "Skip it completely.")

        self.assertIn("let's move to the next question", r_pref.lower())
        self.assertEqual(session.skip_preference, "SKIP_ENTIRELY")
        self.assertIn(q2_id, session.skipped_question_ids)
        self.assertEqual(session.primary_question_count, 3)

        # Answer Q3 (and follow-up if asked)
        r_q3 = await self._answer_primary_and_follow_up(
            session_id,
            "We define functions using the def keyword, and return passes a value back to the caller while print just writes to the console.",
            "If a function does not have a return statement, it implicitly returns None in Python."
        )
        # Directly concludes without revisiting Q2!
        self.assertTrue(session.is_completed)
        self.assertNotIn(q2_id, session.revisited_question_ids)
        self.assertIn("conclude", r_q3.lower())

    async def test_02_explicit_revisit_preference(self):
        """Scenario B: Q2 -> Confirmation -> REVISIT_AFTER_NEXT -> Q3 -> Q2 Revisit -> Conclusion."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)
        q2_id = session.current_question_id

        # Candidate requests skip
        r_skip = await interview_engine.handle_candidate_utterance(session_id, "Can we skip this question?")
        self.assertIn("permanently or revisit", r_skip.lower())

        # Candidate chooses revisit after next
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="REVISIT_AFTER_NEXT", confidence=0.98, reasoning="Revisit")):
            r_pref = await interview_engine.handle_candidate_utterance(session_id, "Ask me after Q3.")

        self.assertIn("come back to this question after the remaining questions", r_pref.lower())
        self.assertEqual(session.skip_preference, "REVISIT_AFTER_NEXT")
        self.assertTrue(any(q["id"] == q2_id for q in session.revisit_queue))
        self.assertEqual(session.primary_question_count, 3)

        # Answer Q3 (and follow-up if asked)
        r_q3 = await self._answer_primary_and_follow_up(
            session_id,
            "We define functions using the def keyword, and return passes a value back to the caller while print just writes to the console.",
            "If a function does not have a return statement, it implicitly returns None in Python."
        )
        # Revisit Q2 is triggered!
        self.assertIn("return to", r_q3.lower())
        self.assertEqual(session.question_visit_mode, "REVISIT")
        self.assertEqual(session.current_question_id, q2_id)
        self.assertFalse(session.is_completed)

        # Answer Q2 Revisit
        r_revisit_ans = await interview_engine.handle_candidate_utterance(
            session_id,
            "Dictionaries store key value pairs using hash tables for constant time O(1) lookups."
        )
        # Completes interview directly after revisit!
        self.assertTrue(session.is_completed)
        self.assertTrue(session.q2_revisit_completed)
        self.assertIn(q2_id, session.revisited_question_ids)
        self.assertIn("conclude", r_revisit_ans.lower())

    async def test_03_ambiguous_clarification_response(self):
        """Scenario C: Ambiguous response asks for clarification without assuming skip or revisit."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)

        await interview_engine.handle_candidate_utterance(session_id, "Can we skip this question?")

        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="UNCLEAR", confidence=0.5, reasoning="Ambiguous")):
            r_clarify = await interview_engine.handle_candidate_utterance(session_id, "Maybe later.")

        self.assertIn("Could you please clarify", r_clarify)
        self.assertEqual(session.current_state, "SKIP_CONFIRMATION")
        self.assertEqual(session.clarification_retry_count, 1)

    async def test_04_clarification_retry_limit(self):
        """Scenario C part 2: Second ambiguous response reaches limit and returns control to active question."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)

        await interview_engine.handle_candidate_utterance(session_id, "Can we skip this question?")

        # First ambiguous response (retry_count becomes 1)
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="UNCLEAR", confidence=0.5, reasoning="Ambiguous")):
            await interview_engine.handle_candidate_utterance(session_id, "Maybe later.")

        # Second ambiguous response (retry_count was 1, exceeds limit -> returns to Q2)
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="UNCLEAR", confidence=0.5, reasoning="Ambiguous")):
            r_return = await interview_engine.handle_candidate_utterance(session_id, "I don't know what to say.")

        self.assertIn("Let's return to our current question", r_return)
        self.assertEqual(session.current_state, "LISTENING")
        self.assertEqual(session.skip_preference, "UNRESOLVED")
        self.assertEqual(session.primary_question_count, 2)

    async def test_05_q2_permanent_skip_never_revisits(self):
        """Rule A verification: Q2 is never queued or asked again after permanent skip."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)
        q2_id = session.current_question_id

        await interview_engine.handle_candidate_utterance(session_id, "skip question")
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="SKIP_ENTIRELY", confidence=0.99, reasoning="Skip")):
            await interview_engine.handle_candidate_utterance(session_id, "Drop it permanently.")

        self.assertEqual(len(session.revisit_queue), 0)
        self.assertIn(q2_id, session.skipped_question_ids)

    async def test_06_q2_revisit_happens_exactly_once(self):
        """Rule B verification: Q2 revisit is removed from queue and cannot execute twice."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)
        q2_id = session.current_question_id

        await interview_engine.handle_candidate_utterance(session_id, "skip question")
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="REVISIT_AFTER_NEXT", confidence=0.99, reasoning="Revisit")):
            await interview_engine.handle_candidate_utterance(session_id, "Revisit it later.")

        # Revisit queue contains 1 item
        self.assertEqual(len(session.revisit_queue), 1)

        # Trigger route_after_q3 via answering Q3
        await self._answer_primary_and_follow_up(
            session_id,
            "Functions are defined with def, and return gives data back whereas print just outputs to stdout."
        )
        # Revisit queue is now empty (popped)
        self.assertEqual(len(session.revisit_queue), 0)
        self.assertFalse(session.has_pending_revisit())

    async def test_07_q2_revisit_proceeds_to_conclusion(self):
        """Rule B verification: After answering the revisited question, interview ends immediately."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)

        await interview_engine.handle_candidate_utterance(session_id, "skip")
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="REVISIT_AFTER_NEXT", confidence=0.99, reasoning="Revisit")):
            await interview_engine.handle_candidate_utterance(session_id, "revisit after next")

        # Answer Q3
        await self._answer_primary_and_follow_up(
            session_id,
            "Functions are defined with def, and return gives data back whereas print just outputs to stdout."
        )
        # Answer Q2 revisit
        r_end = await interview_engine.handle_candidate_utterance(
            session_id,
            "Dictionaries store key value pairs using hash tables for constant time O(1) lookups."
        )
        self.assertTrue(session.is_completed)
        self.assertIn("conclude", r_end.lower())

    async def test_08_resume_after_interruption_at_skip_confirmation(self):
        """Scenario D1: Pausing and resuming while in SKIP_CONFIRMATION preserves state and choices."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)

        await interview_engine.handle_candidate_utterance(session_id, "Can we skip this question?")
        self.assertEqual(session.current_state, "SKIP_CONFIRMATION")

        # Pause
        r_pause = await interview_engine.handle_candidate_utterance(session_id, "Wait, give me a moment to pause.")
        self.assertTrue(session.is_paused)

        # Resume
        r_resume = await interview_engine.handle_candidate_utterance(session_id, "I am back, let's continue.")
        self.assertFalse(session.is_paused)
        self.assertEqual(session.current_state, "SKIP_CONFIRMATION")

        # Can still answer preference
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="SKIP_ENTIRELY", confidence=0.99, reasoning="Skip")):
            r_pref = await interview_engine.handle_candidate_utterance(session_id, "Skip it completely.")
        self.assertEqual(session.skip_preference, "SKIP_ENTIRELY")

    async def test_09_resume_during_q3(self):
        """Scenario D2: Pausing and resuming during Q3 preserves question context."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)

        await interview_engine.handle_candidate_utterance(session_id, "skip")
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="REVISIT_AFTER_NEXT", confidence=0.99, reasoning="Revisit")):
            await interview_engine.handle_candidate_utterance(session_id, "revisit")

        self.assertEqual(session.primary_question_count, 3)

        # Pause during Q3
        await interview_engine.handle_candidate_utterance(session_id, "hold on pause please")
        self.assertTrue(session.is_paused)

        # Resume during Q3
        await interview_engine.handle_candidate_utterance(session_id, "ready now resume")
        self.assertFalse(session.is_paused)
        self.assertEqual(session.primary_question_count, 3)
        self.assertTrue(session.has_pending_revisit())

    async def test_10_resume_during_q2_revisit(self):
        """Scenario D3: Pausing and resuming during Q2 revisit preserves revisit mode."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)

        await interview_engine.handle_candidate_utterance(session_id, "skip")
        with patch("vani.llm.model.model_service.classify_skip_preference",
                   new_callable=AsyncMock,
                   return_value=SkipPreferenceDecision(preference="REVISIT_AFTER_NEXT", confidence=0.99, reasoning="Revisit")):
            await interview_engine.handle_candidate_utterance(session_id, "revisit")

        await self._answer_primary_and_follow_up(
            session_id,
            "We define functions using the def keyword, and return passes a value back to the caller while print outputs to console."
        )
        self.assertEqual(session.question_visit_mode, "REVISIT")

        # Pause during revisit
        await interview_engine.handle_candidate_utterance(session_id, "pause for a second")
        self.assertTrue(session.is_paused)

        # Resume during revisit
        await interview_engine.handle_candidate_utterance(session_id, "continue now")
        self.assertFalse(session.is_paused)
        self.assertEqual(session.question_visit_mode, "REVISIT")

    async def test_11_skill_switching_is_rejected(self):
        """Rule D: Skill immutability - candidate cannot switch skill mid-interview."""
        session_id = self.session_id
        session = await self._onboard_to_q2(session_id)

        r_switch = await interview_engine.handle_candidate_utterance(
            session_id,
            "Can you change the programming language now, I want JavaScript?"
        )
        self.assertIn("Skill switching is not permitted once the interview has started", r_switch)
        self.assertEqual(session.selected_skill, "Python")

    async def test_12_existing_interview_workflows_remain_functional(self):
        """Standard flow without skip (Q1 -> Q2 -> Q3) remains 100% functional."""
        session_id = self.session_id
        await interview_engine.start_interview(session_id)
        await interview_engine.handle_candidate_utterance(session_id, "yes ready")

        # Q1
        await self._answer_primary_and_follow_up(
            session_id,
            "Lists are mutable and defined with square brackets, while tuples are immutable and defined with parentheses.",
            "Lists can have items added or removed dynamically, whereas tuples have fixed contents ensuring data integrity."
        )
        session = session_manager.get(session_id)
        self.assertEqual(session.primary_question_count, 2)

        # Q2
        await self._answer_primary_and_follow_up(
            session_id,
            "Dictionaries store key value pairs using hash tables for constant time O(1) lookups.",
            "Keys must be immutable data types so they can be hashed consistently."
        )
        self.assertEqual(session.primary_question_count, 3)

        # Q3
        r3 = await self._answer_primary_and_follow_up(
            session_id,
            "We define functions using the def keyword, and return passes a value back to the caller while print just writes to the console."
        )
        self.assertTrue(session.is_completed)
        self.assertEqual(session.primary_question_count, 3)
        self.assertEqual(len(session.revisit_queue), 0)


if __name__ == "__main__":
    unittest.main()
