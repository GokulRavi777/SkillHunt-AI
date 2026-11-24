import sys
import os
import unittest
import asyncio
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vani.graph.workflow import interview_engine
from vani.session.manager import session_manager
from vani.schemas.models import SkipPreferenceDecision


class TestStage2FifoAndQuestionManagement(unittest.IsolatedAsyncioTestCase):
    """Exhaustive test suite verifying Stage 2 technical questions, FIFO revisit queue, per-question allowances, hints, and timeouts."""

    async def asyncSetUp(self):
        self.session_id = f"test_st2_{self._testMethodName}"
        session_manager.cleanup(self.session_id)

    async def asyncTearDown(self):
        session_manager.cleanup(self.session_id)

    async def _onboard_to_phase2(self, session_id: str):
        """Helper to advance a session past Stage 1 into Stage 2 (Q1 active)."""
        await interview_engine.start_interview(session_id)
        resp = await interview_engine.handle_candidate_utterance(session_id, "yes I am ready")
        session = session_manager.get(session_id)
        self.assertEqual(session.stage_1_status, "READY_FOR_PHASE_2")
        self.assertEqual(session.primary_question_count, 1)
        self.assertEqual(session.current_question_id, "py_q1")
        return session, resp

    async def _answer_primary_and_follow_up(self, session_id: str, answer_text: str, follow_up_answer: str = "Understood, that is my complete technical answer.") -> str:
        """Answers a question and handles its follow-up if asked."""
        res = await interview_engine.handle_candidate_utterance(session_id, answer_text)
        session = session_manager.get(session_id)
        if session.follow_up_count_for_current_question > 0 and not session.is_completed and session.question_visit_mode != "REVISIT":
            res = await interview_engine.handle_candidate_utterance(session_id, follow_up_answer)
        return res

    async def test_01_q1_normal_answer_and_evaluation(self):
        """Primary question normal answer: collects response, updates concepts, evaluates, and advances."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        q1_id = session.current_question_id

        # Candidate answers Q1
        resp = await interview_engine.handle_candidate_utterance(
            self.session_id,
            "Lists are mutable and use square brackets, whereas tuples are immutable and use parentheses."
        )
        self.assertIn(q1_id, session.question_state)
        q1_state = session.question_state[q1_id]
        self.assertIn(q1_state["status"], ["ANSWERED", "PENDING"])
        self.assertIsNotNone(q1_state["original_response"])
        self.assertIn("mutable", q1_state["original_response"].lower())

    async def test_02_q1_hint_request_policy(self):
        """Hint policy: Vani politely declines hints, does not consume clarification or off-topic counters."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        initial_off_topic = session.off_topic_count

        resp = await interview_engine.handle_candidate_utterance(self.session_id, "Can you give me a hint?")
        self.assertIn("can't provide hints", resp.lower())
        self.assertEqual(session.off_topic_count, initial_off_topic)
        self.assertEqual(session.primary_question_count, 1)
        # Still on Q1
        self.assertEqual(session.current_question_id, "py_q1")

    async def test_03_q1_clarification_allowance_limit(self):
        """Clarification allowance: maximum one clarification/example per primary question."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        q1_id = session.current_question_id

        # First clarification/example
        resp1 = await interview_engine.handle_candidate_utterance(self.session_id, "Can you give an example?")
        self.assertIn("example", resp1.lower())
        self.assertEqual(session.question_state[q1_id]["clarification_count"], 1)

        # Second clarification request on same question must be declined politely
        resp2 = await interview_engine.handle_candidate_utterance(self.session_id, "Can you give me another example?")
        self.assertIn("already provided an example", resp2.lower())
        self.assertEqual(session.question_state[q1_id]["clarification_count"], 1)

    async def test_04_q1_answer_timeout(self):
        """Answer timeout: 30-second answer window expires, marks UNANSWERED_TIMEOUT and advances to Q2."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        q1_id = session.current_question_id

        timeout_resp = await interview_engine.handle_answer_timeout(self.session_id)
        self.assertIn("allotted time", timeout_resp.lower())
        self.assertEqual(session.question_state[q1_id]["status"], "UNANSWERED_TIMEOUT")
        self.assertEqual(session.primary_question_count, 2)
        self.assertEqual(session.current_question_id, "py_q2")

    async def test_05_permanent_skip_never_enters_queue(self):
        """Permanent skip: question is marked SKIPPED_PERMANENTLY, consumes primary slot, never enqueued."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        q1_id = session.current_question_id

        # Candidate requests skip
        r_skip = await interview_engine.handle_candidate_utterance(self.session_id, "Can we skip this?")
        self.assertIn("permanently or revisit", r_skip.lower())

        # Chooses permanent skip
        r_pref = await interview_engine.handle_candidate_utterance(self.session_id, "Skip it permanently.")
        self.assertIn("alright. let's move to the next question", r_pref.lower())

        self.assertEqual(session.question_state[q1_id]["status"], "SKIPPED_PERMANENTLY")
        self.assertFalse(session.question_state[q1_id]["revisit_allowed"])
        self.assertNotIn(q1_id, [q["id"] for q in session.revisit_queue])
        self.assertEqual(session.primary_question_count, 2)

    async def test_06_fifo_queue_ordering_q1_and_q2(self):
        """FIFO Revisit Queue: Candidate skips Q1 and Q2 for revisit, queue order is strictly [Q1, Q2]."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        q1_id = session.current_question_id

        # Skip Q1 for revisit
        await interview_engine.handle_candidate_utterance(self.session_id, "I don't know. Can we skip this?")
        await interview_engine.handle_candidate_utterance(self.session_id, "I want to try it later.")
        self.assertEqual(len(session.revisit_queue), 1)
        self.assertEqual(session.revisit_queue[0]["id"], q1_id)
        self.assertEqual(session.primary_question_count, 2)

        # Skip Q2 for revisit
        q2_id = session.current_question_id
        await interview_engine.handle_candidate_utterance(self.session_id, "Can we skip this question?")
        await interview_engine.handle_candidate_utterance(self.session_id, "Revisit it later.")
        self.assertEqual(len(session.revisit_queue), 2)
        self.assertEqual([q["id"] for q in session.revisit_queue], [q1_id, q2_id])
        self.assertEqual(session.primary_question_count, 3)

        # Answer Q3
        r_q3 = await interview_engine.handle_candidate_utterance(
            self.session_id,
            "We define functions using the def keyword, and return passes a value back while print outputs to console."
        )
        # Primary questions finished -> First FIFO revisit (Q1) is presented!
        self.assertEqual(session.question_visit_mode, "REVISIT")
        self.assertEqual(session.current_question_id, q1_id)
        self.assertIn("return to", r_q3.lower())

        # Candidate answers Q1 revisit
        r_q1_rev = await interview_engine.handle_candidate_utterance(
            self.session_id,
            "Lists are mutable brackets and tuples are immutable parentheses."
        )
        # Next FIFO revisit (Q2) is presented!
        self.assertEqual(session.question_visit_mode, "REVISIT")
        self.assertEqual(session.current_question_id, q2_id)
        self.assertFalse(session.is_completed)

        # Candidate answers Q2 revisit
        r_q2_rev = await interview_engine.handle_candidate_utterance(
            self.session_id,
            "Dictionaries store key-value pairs using hash tables for constant time O(1) lookups."
        )
        # Revisit queue is now completely empty -> Interview concludes!
        self.assertTrue(session.is_completed)
        self.assertEqual(len(session.revisit_queue), 0)
        self.assertIn("conclude", r_q2_rev.lower())

    async def test_07_per_question_revisit_allowance_enforcement(self):
        """Per-question revisit allowance: Question can only be revisited once; second revisit request is rejected."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        q1_id = session.current_question_id

        # Skip Q1 with revisit
        await interview_engine.handle_candidate_utterance(self.session_id, "Can we skip this?")
        await interview_engine.handle_candidate_utterance(self.session_id, "Revisit later.")

        # Answer Q2 directly (and its follow-up if asked)
        await self._answer_primary_and_follow_up(
            self.session_id,
            "Dictionaries store key-value pairs using hash tables for constant time O(1) lookups."
        )
        # Answer Q3 directly
        r_q3 = await self._answer_primary_and_follow_up(
            self.session_id,
            "Functions use def and return sends data back to caller."
        )
        # Revisit Q1 starts
        self.assertEqual(session.question_visit_mode, "REVISIT")
        self.assertEqual(session.current_question_id, q1_id)

        # Candidate requests another skip/revisit during revisit
        r_second_skip = await interview_engine.handle_candidate_utterance(
            self.session_id,
            "Can we skip this and come back to it later again?"
        )
        self.assertIn("already used its revisit opportunity", r_second_skip.lower())
        # Revisit allowance exhausted, no duplicate queuing
        self.assertEqual(len(session.revisit_queue), 0)
        self.assertTrue(session.is_completed)

    async def test_08_q3_follow_up_restriction_preserved(self):
        """Follow-up limit: Q3 strictly allows no follow-ups (can_ask_follow_up returns False)."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        session.primary_question_count = 3
        session.current_question_id = "py_q3"

        self.assertFalse(session.can_ask_follow_up())

    async def test_09_duplicate_queue_protection(self):
        """Queue integrity: Attempting to queue the same question twice is strictly rejected."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        q1_id = session.current_question_id

        enqueued_first = session.queue_for_revisit(q1_id, "Explain lists and tuples")
        self.assertTrue(enqueued_first)
        self.assertEqual(len(session.revisit_queue), 1)

        # Attempt to queue same question again
        enqueued_second = session.queue_for_revisit(q1_id, "Explain lists and tuples")
        self.assertEqual(len(session.revisit_queue), 1)

    async def test_10_empty_revisit_queue_skips_revisit_phase(self):
        """Empty revisit queue: If no questions were skipped for revisit, interview completes after Q3."""
        session, _ = await self._onboard_to_phase2(self.session_id)

        # Answer Q1 (and follow up if any)
        await self._answer_primary_and_follow_up(
            self.session_id,
            "Lists are mutable and tuples are immutable."
        )
        # Answer Q2 (and follow up if any)
        await self._answer_primary_and_follow_up(
            self.session_id,
            "Dictionaries use hash tables for O(1) lookups."
        )
        # Answer Q3
        r_q3 = await self._answer_primary_and_follow_up(
            self.session_id,
            "Functions use def and return gives value back."
        )
        self.assertTrue(session.is_completed)
        self.assertIn("conclude", r_q3.lower())
        self.assertEqual(len(session.revisit_queue), 0)


if __name__ == "__main__":
    unittest.main()
