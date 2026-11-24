"""
End-to-End Test: Universal Off-Topic Termination After Revisited Question
Tests that when a candidate receives the revisited question and commits repeated
unrelated off-topic violations, Vani issues warnings and deterministically terminates
the interview session on the 3rd violation with outcome TERMINATED_BY_GUARDRAIL.
"""

import unittest
import time
from vani.graph.workflow import interview_engine
from vani.session.manager import session_manager


class TestOffTopicTerminationAfterRevisitedQuestion(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_id = f"e2e_revisit_ot_term_{int(time.time())}"
        self.transcript = []

    async def _turn(self, speaker: str, utterance: str, expected_snippet: str = None) -> str:
        """Executes a single conversational turn and records transcript."""
        if speaker == "AGENT_START":
            resp = await interview_engine.start_interview(self.session_id)
            self.transcript.append({"speaker": "VANI", "text": resp})
            print(f"\n[VANI]: {resp}")
            return resp
        else:
            self.transcript.append({"speaker": "CANDIDATE", "text": utterance})
            print(f"\n[CANDIDATE]: {utterance}")
            resp = await interview_engine.handle_candidate_utterance(self.session_id, utterance)
            self.transcript.append({"speaker": "VANI", "text": resp})
            print(f"[VANI]: {resp}")
            if expected_snippet:
                self.assertIn(expected_snippet.lower(), resp.lower())
            return resp

    async def test_off_topic_termination_on_revisited_question(self):
        print("\n" + "="*80)
        print("STARTING TEST: OFF-TOPIC TERMINATION AFTER REVISITED QUESTION")
        print("="*80)

        # -------------------------------------------------------------
        # 1. Phase 1: Greeting & Readiness
        # -------------------------------------------------------------
        await self._turn("AGENT_START", "")
        await self._turn("CANDIDATE", "I am ready, let's start!", expected_snippet="question")
        sess = session_manager.get(self.session_id)
        self.assertEqual(sess.stage_1_status, "READY_FOR_PHASE_2")
        self.assertEqual(sess.primary_question_count, 1)

        # -------------------------------------------------------------
        # 2. Stage 2: Question 1 Answered (Primary Q1 + Follow-up)
        # -------------------------------------------------------------
        t_q1 = await self._turn("CANDIDATE", "In Python, lists are mutable while tuples are immutable.")
        if sess.primary_question_count == 1 and sess.follow_up_count_for_current_question > 0:
            await self._turn("CANDIDATE", "Tuples are used for immutable constants, while lists are for dynamic collections.")
        print(f"\n--> Primary Question Count is now: {sess.primary_question_count}")

        # -------------------------------------------------------------
        # 3. Stage 2: Question 2 Queued for Revisit
        # -------------------------------------------------------------
        t_skip = await self._turn("CANDIDATE", "I don't know this right now. Can we come back to this later?")
        if sess.current_state == "SKIP_CONFIRMATION" or "revisit" in t_skip.lower():
            await self._turn("CANDIDATE", "Yes, come back later please.")

        self.assertTrue(len(sess.revisit_queue) >= 1)
        print(f"\n--> Queued for revisit: {sess.revisit_queue}")

        # -------------------------------------------------------------
        # 4. Stage 2: Question 3 Answered -> Triggers Revisit
        # -------------------------------------------------------------
        t_q3 = await self._turn("CANDIDATE", "Functions use def, parameters are variables in definition and arguments are values passed.")
        print(f"\n[VANI asked Revisited Question]: {sess.last_agent_utterance}")
        self.assertEqual(sess.question_visit_mode, "REVISIT")

        # -------------------------------------------------------------
        # 5. Candidate Commits 3 Off-Topic Violations on Revisited Question
        # -------------------------------------------------------------
        # Off-Topic Strike 1 (Redirect)
        t_ot1 = await self._turn("CANDIDATE", "Tell me a joke about dogs.", expected_snippet="interview")
        self.assertEqual(sess.off_topic_count, 1)
        self.assertFalse(sess.is_terminated())

        # Off-Topic Strike 2 (Warning)
        t_ot2 = await self._turn("CANDIDATE", "Play some music for me.", expected_snippet="focused")
        self.assertEqual(sess.off_topic_count, 2)
        self.assertFalse(sess.is_terminated())

        # Off-Topic Strike 3 (Termination)
        t_ot3 = await self._turn("CANDIDATE", "Sing me a song right now.", expected_snippet="closing")
        self.assertEqual(sess.off_topic_count, 3)

        # -------------------------------------------------------------
        # 6. Verify Deterministic Session Termination
        # -------------------------------------------------------------
        self.assertTrue(sess.is_terminated())
        self.assertEqual(sess.terminal_outcome, "TERMINATED_BY_GUARDRAIL")
        self.assertEqual(sess.termination_reason, "REPEATED_OFF_TOPIC_INTERACTIONS")
        self.assertIn(sess.session_status, ["TERMINATED", "CLOSED"])

        # -------------------------------------------------------------
        # 7. Verify Terminal State Protection (Late turns rejected)
        # -------------------------------------------------------------
        t_late = await self._turn("CANDIDATE", "Wait, can I answer the question now?")
        self.assertTrue("concluded" in t_late.lower() or "closed" in t_late.lower())

        # Verify finalized assessment state
        final_data = sess.finalize_assessment()
        print("\n" + "="*80)
        print("FINAL ASSESSMENT REPORT DATA:")
        print(f"Terminal Outcome: {final_data['terminal_outcome']}")
        print(f"Termination Reason: {final_data['termination_reason']}")
        print(f"Off-Topic Violations: {final_data['summary_metrics']['off_topic_violations']}")
        print("="*80)

        self.assertEqual(final_data["terminal_outcome"], "TERMINATED_BY_GUARDRAIL")
        self.assertEqual(final_data["termination_reason"], "REPEATED_OFF_TOPIC_INTERACTIONS")
        self.assertEqual(final_data["summary_metrics"]["off_topic_violations"], 3)


if __name__ == "__main__":
    unittest.main()
