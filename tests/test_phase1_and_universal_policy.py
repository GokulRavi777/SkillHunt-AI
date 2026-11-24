import asyncio
import os
import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from vani.session.manager import session_manager
from vani.guardrails.engine import (
    guardrails,
    MSG_OFF_TOPIC_REDIRECT,
    MSG_OFF_TOPIC_WARN,
    MSG_OFF_TOPIC_TERMINATE,
    MSG_POLITE_TERMINATE,
)
from vani.graph.workflow import interview_engine

class TestPhase1AndUniversalPolicy(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.session_id = f"test_p1_{os.urandom(4).hex()}"
        session_manager.cleanup(self.session_id)

    def tearDown(self):
        session_manager.cleanup(self.session_id)

    # ==========================================
    # Phase 1 Test Cases (P1-01 to P1-15)
    # ==========================================

    async def test_p1_01_candidate_joins_session_initialized(self):
        """P1-01: Candidate joins -> Session initialized and greeting returned."""
        greeting = await interview_engine.start_interview(self.session_id)
        session = session_manager.get_or_create(self.session_id)
        self.assertIn("I'm Vani, your AI interviewer", greeting)
        self.assertIn("How are you doing today?", greeting)
        self.assertTrue(session.greeting_completed)
        self.assertEqual(session.stage_1_status, "IN_PROGRESS")
        self.assertEqual(session.current_state, "AWAITING_CANDIDATE")

    async def test_p1_02_duplicate_join_event(self):
        """P1-02: Duplicate join event -> No duplicate session or duplicate greeting."""
        g1 = await interview_engine.start_interview(self.session_id)
        g2 = await interview_engine.start_interview(self.session_id)
        self.assertEqual(g1, g2)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.stage_1_status, "IN_PROGRESS")

    async def test_p1_03_candidate_social_response(self):
        """P1-03: Candidate says I'm good -> Acknowledge politely."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "I'm doing good, thank you")
        self.assertIn("Glad to hear that", reply)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.current_state, "AWAITING_CANDIDATE")

    async def test_p1_04_candidate_expresses_nervousness(self):
        """P1-04: Candidate expresses nervousness -> Reassure and set preparation state."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "I'm a little nervous")
        self.assertIn("completely fine", reply.lower())
        self.assertIn("comfortable", reply.lower())
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.current_state, "PREPARATION_WAIT")
        self.assertEqual(session.readiness_status, "PENDING")
        self.assertEqual(session.wait_reason, "NERVOUSNESS")
        self.assertIsNotNone(session.wait_started_at)

    async def test_p1_05_candidate_requests_time(self):
        """P1-05: Candidate requests time -> Set preparation state."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "Can you give me a minute?")
        self.assertIn("take a moment", reply.lower())
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.current_state, "PREPARATION_WAIT")
        self.assertEqual(session.readiness_status, "PENDING")
        self.assertEqual(session.wait_reason, "REQUEST_TIME")

    async def test_p1_06_candidate_confirms_readiness_early(self):
        """P1-06: Candidate confirms readiness early during prep -> Immediate progression."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "I need a moment")
        # Candidate confirms early without waiting for timeout
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "I'm ready now, let's start")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.stage_1_status, "READY_FOR_PHASE_2")
        self.assertEqual(session.readiness_status, "READY")
        self.assertIn("Question one", reply)

    async def test_p1_07_preparation_timer_expires(self):
        """P1-07: Preparation timer expires -> Ask readiness confirmation."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "I'm nervous")
        prompt = await interview_engine.handle_preparation_timeout(self.session_id)
        self.assertEqual(prompt, "Are you ready to proceed with your interview?")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.current_state, "READINESS_CONFIRMATION")

    async def test_p1_08_candidate_confirms_after_timeout(self):
        """P1-08: Candidate confirms after timeout -> Phase 2 transition."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Give me a moment")
        await interview_engine.handle_preparation_timeout(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "Yes, let's start")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.stage_1_status, "READY_FOR_PHASE_2")
        self.assertIn("Question one", reply)

    async def test_p1_09_candidate_still_not_ready(self):
        """P1-09: Candidate still not ready -> Polite termination."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Give me a moment")
        await interview_engine.handle_preparation_timeout(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "No, not yet, I need more time")
        self.assertEqual(reply, MSG_POLITE_TERMINATE)
        session = session_manager.get_or_create(self.session_id)
        self.assertTrue(session.is_terminated())
        self.assertEqual(session.termination_reason, "CANDIDATE_REFUSAL")

    async def test_p1_10_candidate_explicitly_refuses(self):
        """P1-10: Candidate explicitly refuses immediately -> Immediate termination without timer."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "I don't want to continue")
        self.assertEqual(reply, MSG_POLITE_TERMINATE)
        session = session_manager.get_or_create(self.session_id)
        self.assertTrue(session.is_terminated())
        self.assertEqual(session.termination_reason, "CANDIDATE_REFUSAL")

    async def test_p1_11_ambiguous_confirmation_one_clarification(self):
        """P1-11: Ambiguous confirmation -> One clarification attempt."""
        await interview_engine.start_interview(self.session_id)
        reply1 = await interview_engine.handle_candidate_utterance(self.session_id, "Maybe")
        self.assertIn("Just to confirm, would you like to proceed with your interview now?", reply1)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.clarification_count, 1)

    async def test_p1_12_confirmation_timeout_terminates(self):
        """P1-12: Confirmation timeout -> Polite termination."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "I am nervous")
        await interview_engine.handle_preparation_timeout(self.session_id)
        term_reply = await interview_engine.handle_confirmation_timeout(self.session_id)
        self.assertEqual(term_reply, MSG_POLITE_TERMINATE)
        session = session_manager.get_or_create(self.session_id)
        self.assertTrue(session.is_terminated())
        self.assertEqual(session.termination_reason, "CONFIRMATION_TIMEOUT")

    async def test_p1_13_candidate_asks_what_vani_is(self):
        """P1-13: Candidate asks what Vani is -> Explanation, no off-topic violation."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "What is Vani?")
        self.assertIn("I am Vani, an AI technical interviewer", reply)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 0)
        self.assertEqual(session.warning_level, 0)

    async def test_p1_14_candidate_asks_about_process(self):
        """P1-14: Candidate asks about process -> Explanation, no off-topic violation."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "How does this interview work?")
        self.assertIn("three primary technical questions", reply)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 0)

    async def test_p1_15_empty_transcript_no_violation(self):
        """P1-15: Empty transcript -> Silence handling, no off-topic violation."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "   ")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 0)

    # ==========================================
    # Universal Off-Topic Policy Tests (UO-01 to UO-15)
    # ==========================================

    async def test_uo_01_first_off_topic_turn_redirect(self):
        """UO-01: First off-topic turn in Phase 1 -> Redirect."""
        await interview_engine.start_interview(self.session_id)
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke")
        self.assertEqual(reply, MSG_OFF_TOPIC_REDIRECT)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 1)
        self.assertEqual(session.warning_level, 1)
        self.assertFalse(session.is_terminated())

    async def test_uo_02_second_off_topic_turn_warning(self):
        """UO-02: Second off-topic turn in Phase 1 -> Formal warning."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke")
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "What's the weather today?")
        self.assertEqual(reply, MSG_OFF_TOPIC_WARN)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 2)
        self.assertEqual(session.warning_level, 2)
        self.assertFalse(session.is_terminated())

    async def test_uo_03_third_off_topic_turn_termination(self):
        """UO-03: Third off-topic turn in Phase 1 -> Automatic termination."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke")
        await interview_engine.handle_candidate_utterance(self.session_id, "What is the weather?")
        reply = await interview_engine.handle_candidate_utterance(self.session_id, "Sing a song for me")
        self.assertEqual(reply, MSG_OFF_TOPIC_TERMINATE)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 3)
        self.assertEqual(session.warning_level, 3)
        self.assertTrue(session.is_terminated())
        self.assertEqual(session.termination_reason, "REPEATED_OFF_TOPIC_INTERACTIONS")

    async def test_uo_04_to_06_off_topic_in_technical_stage(self):
        """UO-04 to UO-06: Off-topic violations during technical questioning enforce universal policy."""
        # Enter Phase 2
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Yes, I am ready")
        
        # Turn 1: Off-topic during technical Q1 -> Redirect
        r1 = await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke please")
        self.assertEqual(r1, MSG_OFF_TOPIC_REDIRECT)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 1)

        # Turn 2: Second off-topic -> Warning
        r2 = await interview_engine.handle_candidate_utterance(self.session_id, "Play some music")
        self.assertEqual(r2, MSG_OFF_TOPIC_WARN)
        self.assertEqual(session.off_topic_count, 2)

        # Turn 3: Third off-topic -> Automatic Termination
        r3 = await interview_engine.handle_candidate_utterance(self.session_id, "Write a poem")
        self.assertEqual(r3, MSG_OFF_TOPIC_TERMINATE)
        self.assertEqual(session.off_topic_count, 3)
        self.assertTrue(session.is_terminated())

    async def test_uo_07_relevant_response_does_not_reset_counter(self):
        """UO-07: Relevant response after first violation -> Counter is preserved and NOT reset."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 1)

        # Candidate gives a relevant response
        await interview_engine.handle_candidate_utterance(self.session_id, "I am doing well, thank you")
        self.assertEqual(session.off_topic_count, 1, "Counter must NOT reset after relevant response")

    async def test_uo_08_violations_across_stage_transitions(self):
        """UO-08: Off-topic counter persists across Phase 1 to Phase 2 stage transitions."""
        # Violation 1 in Phase 1
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 1)

        # Advance to Phase 2
        await interview_engine.handle_candidate_utterance(self.session_id, "Yes, I am ready")
        self.assertEqual(session.stage_1_status, "READY_FOR_PHASE_2")
        self.assertEqual(session.off_topic_count, 1, "Counter must persist into Phase 2")

        # Violation 2 in Phase 2 -> Must be Warning (level 2)
        r2 = await interview_engine.handle_candidate_utterance(self.session_id, "Sing a song")
        self.assertEqual(r2, MSG_OFF_TOPIC_WARN)
        self.assertEqual(session.off_topic_count, 2)

    async def test_uo_09_to_11_legitimate_interactions_not_penalized(self):
        """UO-09 to UO-11: Legitimate questions, requests for time, empty speech do not increment counter."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "What did you say?")
        await interview_engine.handle_candidate_utterance(self.session_id, "Can you give me a minute?")
        await interview_engine.handle_candidate_utterance(self.session_id, "   ")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 0)

    async def test_uo_12_single_turn_single_increment(self):
        """UO-12: Single turn increments violation counter at most once."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke and what is the weather")
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.off_topic_count, 1)

    async def test_uo_13_reconnect_preserves_policy_state(self):
        """UO-13: Reconnect retrieves same session and preserves off-topic state."""
        await interview_engine.start_interview(self.session_id)
        await interview_engine.handle_candidate_utterance(self.session_id, "Tell me a joke")
        # Simulating reconnect by retrieving session from session manager
        reconnected_session = session_manager.get_or_create(self.session_id)
        self.assertEqual(reconnected_session.off_topic_count, 1)
        self.assertEqual(reconnected_session.warning_level, 1)

    async def test_uo_14_input_after_termination_rejected(self):
        """UO-14: Further input after termination is strictly rejected."""
        await interview_engine.start_interview(self.session_id)
        # Terminate via refusal
        await interview_engine.handle_candidate_utterance(self.session_id, "I don't want to continue")
        session = session_manager.get_or_create(self.session_id)
        self.assertTrue(session.is_terminated())
        
        # Subsequent input
        post_term_reply = await interview_engine.handle_candidate_utterance(self.session_id, "Wait, I changed my mind")
        self.assertTrue("close" in post_term_reply.lower() or "closed" in post_term_reply.lower())

    async def test_uo_15_final_tts_message_verified(self):
        """UO-15: Final termination message is accurately set before session close."""
        await interview_engine.start_interview(self.session_id)
        term_msg = await interview_engine.handle_candidate_utterance(self.session_id, "I don't want to continue")
        self.assertEqual(term_msg, MSG_POLITE_TERMINATE)
        session = session_manager.get_or_create(self.session_id)
        self.assertEqual(session.last_agent_utterance, MSG_POLITE_TERMINATE)

if __name__ == "__main__":
    unittest.main()
