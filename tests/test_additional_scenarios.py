import asyncio
import os
import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from vani.session.manager import session_manager
from vani.graph.workflow import interview_engine

class TestAdditionalScenarios(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.session_id = f"test_uc_additional_{os.urandom(4).hex()}"
        session_manager.cleanup(self.session_id)
        self.session = session_manager.get_or_create(self.session_id)
        self.session.selected_skill = "Python"
        self.session.record_primary_question("py_q1", "Explain Python decorators.", "Decorators & Metaprogramming")
        self.session.current_state = "LISTENING"

    async def asyncTearDown(self):
        session_manager.cleanup(self.session_id)

    async def test_uc31_remaining_questions_query(self):
        """UC31: Candidate asks how many questions remain."""
        resp = await interview_engine.handle_candidate_utterance(
            self.session_id, "How many questions remain in this interview?"
        )
        print(f"UC31 Response: {resp}")
        self.assertIn("1 of 3", resp)
        self.assertIn("2 primary questions remaining", resp)
        self.assertIn("conditionally", resp.lower())
        # Question count must NOT be incremented
        self.assertEqual(self.session.primary_question_count, 1)

    async def test_uc32_skip_question(self):
        """UC32: Candidate requests to skip a question."""
        initial_count = self.session.primary_question_count
        resp = await interview_engine.handle_candidate_utterance(
            self.session_id, "I would like to skip this question please."
        )
        print(f"UC32 Response: {resp}")
        self.assertIn("skipping", resp.lower())
        # Primary count must advance to next question
        self.assertEqual(self.session.primary_question_count, 2)
        # Follow-up count for the skipped question must be 0
        self.assertEqual(self.session.follow_up_count_for_current_question, 0)

    async def test_uc34_request_example(self):
        """UC34: Candidate requests an example."""
        resp = await interview_engine.handle_candidate_utterance(
            self.session_id, "Could you please give me an example of what you mean?"
        )
        print(f"UC34 Response: {resp}")
        self.assertIn("example", resp.lower())
        # Question count and follow-up count must NOT change
        self.assertEqual(self.session.primary_question_count, 1)
        self.assertEqual(self.session.follow_up_count_for_current_question, 0)

    async def test_uc33_answer_correction(self):
        """UC33: Candidate corrects an answer."""
        # Answer initially
        await interview_engine.handle_candidate_utterance(
            self.session_id, "Decorators are classes that inherit from object."
        )
        # Correct answer
        resp = await interview_engine.handle_candidate_utterance(
            self.session_id, "Actually wait, let me correct that, decorators are higher order functions that wrap other functions using closures."
        )
        print(f"UC33 Response: {resp}")
        self.assertTrue(len(resp) > 10)
        self.assertTrue(any(a.get("is_corrected") for a in self.session.candidate_answers))

if __name__ == "__main__":
    unittest.main()
