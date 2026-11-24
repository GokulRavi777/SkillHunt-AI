import sys
import os
import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vani.graph.workflow import interview_engine
from vani.session.manager import session_manager
from vani.guardrails.engine import MSG_OFF_TOPIC_TERMINATE


class TestStage3ConclusionAndClosure(unittest.IsolatedAsyncioTestCase):
    """Exhaustive test suite verifying Stage 3 interview conclusion, inquiries, assessment finalization, and session closure."""

    async def asyncSetUp(self):
        self.session_id = f"test_st3_{self._testMethodName}"
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
        return session, resp

    async def _answer_primary_and_follow_up(self, session_id: str, answer_text: str, follow_up_answer: str = "Lists can have items added or removed dynamically, whereas tuples have fixed contents ensuring data integrity.") -> str:
        """Answers a question and handles its follow-up if asked."""
        res = await interview_engine.handle_candidate_utterance(session_id, answer_text)
        session = session_manager.get(session_id)
        if session.follow_up_count_for_current_question > 0 and not session.is_completed and session.question_visit_mode != "REVISIT":
            res = await interview_engine.handle_candidate_utterance(session_id, follow_up_answer)
        return res

    async def _advance_to_conclusion(self, session_id: str):
        """Advances session through Q1, Q2, and Q3 cleanly into Stage 3 Conclusion."""
        session, _ = await self._onboard_to_phase2(session_id)
        # Q1
        await self._answer_primary_and_follow_up(
            session_id,
            "Lists are mutable and defined with square brackets, while tuples are immutable and defined with parentheses.",
            "Lists can have items added or removed dynamically, whereas tuples have fixed contents ensuring data integrity."
        )
        # Q2
        await self._answer_primary_and_follow_up(
            session_id,
            "Dictionaries store key-value pairs using hash tables for constant time O(1) lookups.",
            "A dictionary lookup uses hashing to access values in O(1) time without iterating through a list."
        )
        # Q3
        r_q3 = await self._answer_primary_and_follow_up(
            session_id,
            "We define functions using the def keyword, and return passes a value back to the caller while print just writes to the console.",
            "If a function does not have a return statement, it implicitly returns None in Python."
        )
        return session, r_q3

    async def test_01_normal_completion_all_three_questions(self):
        """Normal completion: All 3 primary questions answered, revisit queue empty -> enters Stage 3 Conclusion."""
        session, r_q3 = await self._advance_to_conclusion(self.session_id)

        self.assertTrue(session.is_completed)
        self.assertEqual(session.current_state, "CONCLUSION")
        self.assertEqual(session.active_question_stage, "STAGE_3_CONCLUSION")
        self.assertIn("we've completed all the questions", r_q3.lower())
        self.assertIn("conclude", r_q3.lower())
        self.assertTrue(session.assessment_finalized)
        self.assertIsNotNone(session.final_assessment)

    async def test_02_conclusion_after_permanent_skip(self):
        """Conclusion after permanent skip: Q1 skipped permanently, Q2 and Q3 answered -> concludes directly."""
        session, _ = await self._onboard_to_phase2(self.session_id)

        # Skip Q1 permanently
        await interview_engine.handle_candidate_utterance(self.session_id, "Can we skip this?")
        await interview_engine.handle_candidate_utterance(self.session_id, "Skip it permanently.")
        self.assertEqual(session.question_state["py_q1"]["status"], "SKIPPED_PERMANENTLY")

        # Q2 & Q3
        await self._answer_primary_and_follow_up(
            self.session_id,
            "Dictionaries store key-value pairs using hash tables for constant time O(1) lookups.",
            "A dictionary lookup uses hashing to access values in O(1) time without iterating through a list."
        )
        r_q3 = await self._answer_primary_and_follow_up(
            self.session_id,
            "We define functions using the def keyword, and return passes a value back to the caller while print just writes to the console.",
            "If a function does not have a return statement, it implicitly returns None in Python."
        )

        self.assertTrue(session.is_completed)
        self.assertEqual(session.current_state, "CONCLUSION")
        self.assertEqual(len(session.revisit_queue), 0)
        self.assertIn("completed all the questions", r_q3.lower())

    async def test_03_stage3_entered_only_after_fifo_revisit_resolved(self):
        """Revisit queue gate: Stage 3 conclusion is NOT entered while revisit queue has pending questions."""
        session, _ = await self._onboard_to_phase2(self.session_id)

        # Skip Q1 for revisit
        await interview_engine.handle_candidate_utterance(self.session_id, "Can we skip this?")
        await interview_engine.handle_candidate_utterance(self.session_id, "Revisit later.")
        self.assertEqual(len(session.revisit_queue), 1)

        # Answer Q2 & Q3
        await self._answer_primary_and_follow_up(
            self.session_id,
            "Dictionaries store key-value pairs using hash tables for constant time O(1) lookups.",
            "A dictionary lookup uses hashing to access values in O(1) time without iterating through a list."
        )
        r_q3 = await self._answer_primary_and_follow_up(
            self.session_id,
            "We define functions using the def keyword, and return passes a value back to the caller while print just writes to the console.",
            "If a function does not have a return statement, it implicitly returns None in Python."
        )

        # Must NOT conclude yet: must present queued Q1 revisit!
        self.assertEqual(session.question_visit_mode, "REVISIT")
        self.assertEqual(session.current_question_id, "py_q1")
        self.assertIn("return to", r_q3.lower())

        # Candidate answers Q1 revisit
        r_rev = await interview_engine.handle_candidate_utterance(
            self.session_id,
            "Lists are mutable and use square brackets, while tuples are immutable and use parentheses."
        )
        # Now revisit queue is empty -> Enters conclusion!
        self.assertTrue(session.is_completed)
        self.assertEqual(session.current_state, "CONCLUSION")
        self.assertIn("conclude", r_rev.lower())

    async def test_04_pass_inquiry(self):
        """Section 6.1: Candidate asks 'Did I pass?' -> Non-committal assessment process explanation."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        # Candidate asks if they passed
        r_pass = await interview_engine.handle_candidate_utterance(self.session_id, "Did I pass the interview?")
        self.assertIn("assessment outcome will be determined through the evaluation process", r_pass.lower())
        self.assertEqual(session.current_state, "CONCLUSION")

    async def test_05_feedback_inquiry(self):
        """Section 6.2: Candidate asks for feedback -> Directs to assessment results process without exposing rubrics."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        # Candidate asks for feedback
        r_fb = await interview_engine.handle_candidate_utterance(self.session_id, "How did I perform? Can I get feedback?")
        self.assertIn("detailed feedback will be available through the assessment results process", r_fb.lower())
        self.assertEqual(session.current_state, "CONCLUSION")

    async def test_06_is_interview_over_inquiry(self):
        """Section 6.3: Candidate asks whether the interview is over -> Confirms completion without restarting."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        r_over = await interview_engine.handle_candidate_utterance(self.session_id, "Is the interview over?")
        self.assertIn("yes, we've completed your interview", r_over.lower())
        self.assertEqual(session.current_state, "CONCLUSION")

    async def test_07_attempt_to_answer_another_question_rejected(self):
        """Section 6.4: Candidate attempts to answer another question -> Politely declined, Stage 2 not reopened."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        r_another = await interview_engine.handle_candidate_utterance(self.session_id, "Wait, I want to answer another question.")
        self.assertIn("we've already completed the interview", r_another.lower())
        self.assertEqual(session.primary_question_count, 3)

    async def test_08_thank_you_concludes_and_finalizes(self):
        """Section 5: Candidate says 'Thank you' -> Delivers final closing response and sets COMPLETED outcome."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        r_thanks = await interview_engine.handle_candidate_utterance(self.session_id, "Thank you.")
        self.assertIn("you're welcome. your interview has now been completed. have a good day", r_thanks.lower())
        self.assertEqual(session.terminal_outcome, "COMPLETED")
        self.assertEqual(session.session_status, "CLOSED")
        self.assertTrue(session.cleanup_completed)

    async def test_09_goodbye_concludes_and_finalizes(self):
        """Section 6.5: Candidate says goodbye -> Brief closing delivered, sets COMPLETED outcome, marks cleanup."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        r_bye = await interview_engine.handle_candidate_utterance(self.session_id, "Goodbye!")
        self.assertIn("have a great day", r_bye.lower())
        self.assertEqual(session.terminal_outcome, "COMPLETED")
        self.assertTrue(session.cleanup_completed)

    async def test_10_voluntary_termination_during_stage2(self):
        """Section 7: Voluntary candidate termination during active technical questions -> TERMINATED_BY_CANDIDATE."""
        session, _ = await self._onboard_to_phase2(self.session_id)
        self.assertEqual(session.primary_question_count, 1)

        r_stop = await interview_engine.handle_candidate_utterance(self.session_id, "I want to stop the interview.")
        self.assertIn("we'll end the interview here. thank you for your time", r_stop.lower())
        self.assertEqual(session.terminal_outcome, "TERMINATED_BY_CANDIDATE")
        self.assertEqual(session.termination_reason, "TERMINATED_BY_CANDIDATE")
        self.assertTrue(session.is_completed)
        self.assertTrue(session.cleanup_completed)
        self.assertTrue(session.assessment_finalized)

    async def test_11_voluntary_termination_during_stage3(self):
        """Section 7: Voluntary candidate termination during conclusion -> TERMINATED_BY_CANDIDATE."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        r_stop = await interview_engine.handle_candidate_utterance(self.session_id, "Please end this session now.")
        self.assertIn("we'll end the interview here. thank you for your time", r_stop.lower())
        self.assertEqual(session.terminal_outcome, "TERMINATED_BY_CANDIDATE")
        self.assertTrue(session.cleanup_completed)

    async def test_12_voluntary_termination_during_stage1(self):
        """Section 7: Voluntary candidate termination during Stage 1 onboarding -> TERMINATED_BY_CANDIDATE."""
        await interview_engine.start_interview(self.session_id)
        session = session_manager.get(self.session_id)

        r_stop = await interview_engine.handle_candidate_utterance(self.session_id, "I don't want to continue.")
        self.assertIn("we'll end the interview here. thank you for your time", r_stop.lower())
        self.assertEqual(session.terminal_outcome, "TERMINATED_BY_CANDIDATE")
        self.assertTrue(session.is_completed)

    async def test_13_terminal_state_protection_rejects_late_input(self):
        """Terminal State Protection: Late candidate inputs arriving after closure are rejected safely."""
        session, _ = await self._advance_to_conclusion(self.session_id)
        self.assertEqual(session.current_state, "CONCLUSION")

        # Complete interview with Thank you
        await interview_engine.handle_candidate_utterance(self.session_id, "Thank you.")
        self.assertTrue(session.is_terminated())

        # Candidate speaks again after session is already closed
        r_late = await interview_engine.handle_candidate_utterance(self.session_id, "Wait, what is my score?")
        self.assertTrue("concluded" in r_late.lower() or "closed" in r_late.lower())
        # Questions must not change
        self.assertEqual(session.primary_question_count, 3)

    async def test_14_assessment_finalization_idempotency(self):
        """Assessment finalization: Repeated calls do not duplicate records or recalculate completed_at."""
        session, _ = await self._advance_to_conclusion(self.session_id)

        first_eval = session.finalize_assessment()
        self.assertTrue(session.assessment_finalized)
        first_completed_at = first_eval["completed_at"]

        # Call again
        await asyncio.sleep(0.01)
        second_eval = session.finalize_assessment()
        self.assertIs(first_eval, second_eval)
        self.assertEqual(first_completed_at, second_eval["completed_at"])
        self.assertEqual(second_eval["summary_metrics"]["primary_questions_asked"], 3)

    async def test_15_distinct_terminal_outcomes(self):
        """Section 8: Verifies distinct terminal outcomes (COMPLETED, TERMINATED_BY_CANDIDATE, TERMINATED_BY_GUARDRAIL)."""
        # Case 1: TERMINATED_BY_GUARDRAIL (3rd off-topic)
        s_guard = session_manager.get_or_create("s_guard")
        s_guard.record_off_topic_violation()
        s_guard.record_off_topic_violation()
        s_guard.record_off_topic_violation()
        self.assertEqual(s_guard.terminal_outcome, "TERMINATED_BY_GUARDRAIL")
        session_manager.cleanup("s_guard")

        # Case 2: TERMINATED_BY_CANDIDATE
        s_cand = session_manager.get_or_create("s_cand")
        s_cand.terminate_session("TERMINATED_BY_CANDIDATE")
        self.assertEqual(s_cand.terminal_outcome, "TERMINATED_BY_CANDIDATE")
        session_manager.cleanup("s_cand")

        # Case 3: TERMINATED_BY_SYSTEM_ERROR
        s_err = session_manager.get_or_create("s_err")
        s_err.terminate_session("SYSTEM_ERROR")
        self.assertEqual(s_err.terminal_outcome, "TERMINATED_BY_SYSTEM_ERROR")
        session_manager.cleanup("s_err")

        # Case 4: COMPLETED
        s_comp = session_manager.get_or_create("s_comp")
        s_comp.is_completed = True
        s_comp.terminal_outcome = "COMPLETED"
        eval_comp = s_comp.finalize_assessment()
        self.assertEqual(eval_comp["terminal_outcome"], "COMPLETED")
        session_manager.cleanup("s_comp")


if __name__ == "__main__":
    unittest.main()
