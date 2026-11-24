"""
Comprehensive End-to-End Multi-Scenario Long Interview Test
Executes a realistic 18-turn conversational interview testing all stages,
guardrails, pauses, skips, revisits, corrections, and closures in one session.
"""

import asyncio
import unittest
import time
from vani.graph.workflow import interview_engine
from vani.session.manager import session_manager


class TestEndToEndLongInterview(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_id = f"e2e_master_interview_{int(time.time())}"
        self.transcript = []

    async def _turn(self, speaker: str, utterance: str, expected_snippet: str = None) -> str:
        """Executes a single conversational turn and records transcript."""
        if speaker == "AGENT_START":
            resp = await interview_engine.start_interview(self.session_id)
            self.transcript.append({"speaker": "VANI", "text": resp})
            print(f"\n[VANI]: {resp}")
            return resp
        elif speaker == "AGENT_POLL":
            # Direct check on last agent utterance
            sess = session_manager.get(self.session_id)
            resp = sess.last_agent_utterance if sess else ""
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

    async def test_full_master_interview_lifecycle(self):
        print("\n" + "="*80)
        print("STARTING END-TO-END MULTI-SCENARIO MASTER INTERVIEW")
        print("="*80)

        # -------------------------------------------------------------
        # Phase 1: Entry, Nervousness, Prep Period & Readiness
        # -------------------------------------------------------------
        # Turn 1: Vani greets
        t1 = await self._turn("AGENT_START", "")
        self.assertIn("welcome", t1.lower())

        # Turn 2: Candidate expresses nervousness
        t2 = await self._turn("CANDIDATE", "I am feeling a bit nervous about this interview.", expected_snippet="comfortable")
        sess = session_manager.get(self.session_id)
        self.assertEqual(sess.current_state, "PREPARATION_WAIT")

        # Turn 3: Candidate asks about interview format/process during prep
        t3 = await self._turn("CANDIDATE", "How does this interview work?", expected_snippet="questions")

        # Turn 4: Candidate confirms readiness early -> enters Phase 2
        t4 = await self._turn("CANDIDATE", "Okay, I am ready now. Let's start!", expected_snippet="question")
        self.assertEqual(sess.stage_1_status, "READY_FOR_PHASE_2")
        self.assertEqual(sess.primary_question_count, 1)
        self.assertEqual(sess.current_state, "LISTENING")

        # -------------------------------------------------------------
        # Stage 2: Question 1, Example Clarification & Answer Correction
        # -------------------------------------------------------------
        # Turn 5: Candidate asks for an example (UC34)
        t5 = await self._turn("CANDIDATE", "Can you give me an example for this question?", expected_snippet="example")
        self.assertEqual(sess.primary_question_count, 1)
        self.assertEqual(sess.current_state, "LISTENING")

        # Turn 6: Candidate gives answer with correction (UC33)
        t6 = await self._turn("CANDIDATE", "A list is immutable. Sorry correction: what I meant was a list is mutable while a tuple is immutable.")
        # Turn 7: If follow-up or next question
        if sess.primary_question_count == 1 and sess.follow_up_count_for_current_question > 0:
            # Answer follow-up
            t7 = await self._turn("CANDIDATE", "We use tuples for fixed coordinates or constants and lists when items need to be appended or deleted dynamically.")
        
        self.assertGreaterEqual(sess.primary_question_count, 2)
        print(f"\n--> Primary Question Count is now: {sess.primary_question_count}")

        # -------------------------------------------------------------
        # Stage 2: Question 2, Mid-Interview Pause & Resume
        # -------------------------------------------------------------
        # Turn 8: Candidate asks to pause (UC25)
        t8 = await self._turn("CANDIDATE", "Could you pause for a minute please? Someone is at my door.", expected_snippet="paused")
        self.assertTrue(sess.is_paused)

        # Turn 9: Candidate resumes (UC26)
        t9 = await self._turn("CANDIDATE", "I am back, let's resume.", expected_snippet="resuming")
        self.assertFalse(sess.is_paused)

        # Turn 10: Candidate chooses to skip Q2 and come back later (FIFO Revisit Queue UC32/35)
        t10 = await self._turn("CANDIDATE", "I don't know this right now. Can we come back to this later?")
        # If skip confirmation is asked, confirm revisit
        if sess.current_state == "SKIP_CONFIRMATION" or "revisit" in t10.lower():
            t10_c = await self._turn("CANDIDATE", "Yes, come back later please.")

        self.assertIn(sess.primary_question_count, [2, 3])
        self.assertTrue(len(sess.revisit_queue) >= 1)
        print(f"\n--> Queued for revisit: {sess.revisit_queue}")

        # -------------------------------------------------------------
        # Stage 2: Question 3 & Universal Off-Topic Policy Enforcement
        # -------------------------------------------------------------
        # Turn 11: Candidate injects off-topic utterance (Violation 1 - UC22)
        t11 = await self._turn("CANDIDATE", "Hey Vani, tell me a funny joke about cats.", expected_snippet="interview")
        self.assertEqual(sess.off_topic_count, 1)

        # Turn 12: Candidate answers Question 3
        t12 = await self._turn("CANDIDATE", "In Python, parameters are defined in the function signature, while arguments are the actual values passed in when calling.")

        # -------------------------------------------------------------
        # Stage 2: FIFO Revisit Processing
        # -------------------------------------------------------------
        # At this point, Q1, Q2, Q3 were handled; Q2 was queued. Revisit should activate or be delivered
        print(f"\n--> Active question visit mode: {sess.question_visit_mode}, revisit queue: {sess.revisit_queue}")
        if sess.question_visit_mode == "REVISIT" or len(sess.revisit_queue) > 0 or sess.current_state == "LISTENING":
            # Turn 13: Candidate answers the revisited question
            t13 = await self._turn("CANDIDATE", "For dictionaries, they store data as key-value pairs using hash tables, allowing average O(1) time complexity.")

        # -------------------------------------------------------------
        # Stage 3: Conclusion, Result Inquiries & Closure
        # -------------------------------------------------------------
        self.assertEqual(sess.current_state, "CONCLUSION")
        self.assertTrue(sess.is_completed)

        # Turn 14: Candidate asks "Did I pass?" (Section 6.1)
        t14 = await self._turn("CANDIDATE", "Did I pass the interview?", expected_snippet="recorded")

        # Turn 15: Candidate attempts to ask another question (Section 6.4)
        t15 = await self._turn("CANDIDATE", "Wait, can I answer another question?", expected_snippet="concluded")
        self.assertEqual(sess.current_state, "CONCLUSION")

        # Turn 16: Candidate wraps up with goodbye (Section 6.5)
        t16 = await self._turn("CANDIDATE", "Thank you so much. Goodbye!", expected_snippet="completed")
        self.assertTrue(sess.is_terminated())
        self.assertEqual(sess.terminal_outcome, "COMPLETED")
        self.assertEqual(sess.session_status, "CLOSED")

        # Turn 17: Post-closure late turn is safely rejected
        t17 = await self._turn("CANDIDATE", "Are you still there?", expected_snippet="concluded")

        # -------------------------------------------------------------
        # Final Assessment Assertions
        # -------------------------------------------------------------
        final_data = sess.finalize_assessment()
        print("\n" + "="*80)
        print("FINAL ASSESSMENT REPORT DATA:")
        metrics = final_data["summary_metrics"]
        print(f"Primary Questions Asked: {metrics['primary_questions_asked']}")
        print(f"Questions Answered: {metrics['questions_answered']}")
        print(f"Questions Skipped Permanently: {metrics['questions_skipped_permanently']}")
        print(f"Questions Revisited: {metrics['questions_revisited']}")
        print(f"Terminal Outcome: {final_data['terminal_outcome']}")
        print(f"Duration: {final_data['duration_seconds']} seconds")
        print("="*80)

        self.assertGreaterEqual(metrics["primary_questions_asked"], 3)
        self.assertGreaterEqual(metrics["questions_answered"], 2)
        self.assertEqual(final_data["terminal_outcome"], "COMPLETED")
        self.assertIsNotNone(final_data["completed_at"])


if __name__ == "__main__":
    unittest.main()
