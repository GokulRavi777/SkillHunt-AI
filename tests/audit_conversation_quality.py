import asyncio
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from vani.session.manager import session_manager
from vani.llm.question_generator import question_generator
from vani.graph.workflow import interview_engine

CANDIDATE_SCENARIOS = [
    {
        "category": "short_answer",
        "primary_question": "Could you explain how decorators work in Python and what problem they solve?",
        "topic": "Decorators & Metaprogramming",
        "expected_concepts": ["higher-order functions", "wrappers", "args and kwargs", "closure"],
        "candidate_input": "They wrap functions.",
        "description": "Very short, 3-word answer."
    },
    {
        "category": "incomplete_answer",
        "primary_question": "Could you explain how decorators work in Python and what problem they solve?",
        "topic": "Decorators & Metaprogramming",
        "expected_concepts": ["higher-order functions", "wrappers", "args and kwargs", "functools.wraps"],
        "candidate_input": "A decorator takes a function as an argument and returns an inner function that adds some logging.",
        "description": "Partial answer; mentions wrappers and logging, but omits argument forwarding and metadata preservation."
    },
    {
        "category": "incorrect_answer",
        "primary_question": "What is the Global Interpreter Lock (GIL) in CPython, and how does it affect multithreaded code?",
        "topic": "Memory Management & GIL",
        "expected_concepts": ["CPython thread safety", "single-threaded bytecode", "multiprocessing"],
        "candidate_input": "The GIL makes Python multithreading faster by running multiple CPU threads on different cores simultaneously.",
        "description": "Factually incorrect claim about GIL running threads on multiple CPU cores simultaneously."
    },
    {
        "category": "off_topic_answer",
        "primary_question": "What is the Global Interpreter Lock (GIL) in CPython, and how does it affect multithreaded code?",
        "topic": "Memory Management & GIL",
        "expected_concepts": ["CPython thread safety", "multiprocessing"],
        "candidate_input": "I think the weather is really nice today, and I like building Lego models.",
        "description": "Completely off-topic utterance."
    },
    {
        "category": "practical_example",
        "primary_question": "Could you explain how decorators work in Python and what problem they solve?",
        "topic": "Decorators & Metaprogramming",
        "expected_concepts": ["higher-order functions", "wrappers", "functools.wraps"],
        "candidate_input": "In my last project, I built a retry decorator that caught HTTP request timeouts, logged the attempt, and retried three times with exponential backoff.",
        "description": "Practical implementation example with retry logic."
    },
    {
        "category": "strong_understanding",
        "primary_question": "How do generators differ from normal functions in Python, and how does yield manage memory?",
        "topic": "Generators & Iterators",
        "expected_concepts": ["lazy evaluation", "yield statement", "iterator protocol", "stack frame preservation"],
        "candidate_input": "Generators adhere to the iterator protocol via __iter__ and __next__. Unlike functions that return an entire list in memory, yield suspends the frame's execution state and yields values lazily, avoiding O(N) memory consumption.",
        "description": "Strong, deep technical answer."
    },
    {
        "category": "does_not_know",
        "primary_question": "What is the Global Interpreter Lock (GIL) in CPython, and how does it affect multithreaded code?",
        "topic": "Memory Management & GIL",
        "expected_concepts": ["CPython thread safety"],
        "candidate_input": "Honestly, I haven't worked with CPython internals or the GIL directly, so I am not sure about that.",
        "description": "Candidate candidly admits they do not know."
    },
    {
        "category": "clarification_request",
        "primary_question": "Could you explain how decorators work in Python and what problem they solve?",
        "topic": "Decorators & Metaprogramming",
        "expected_concepts": ["higher-order functions"],
        "candidate_input": "Are you asking specifically about standard function decorators, or do you also want me to cover class decorators?",
        "description": "Candidate asks for clarification on scope."
    },
]

async def audit_scenarios():
    print("=" * 80)
    print("VANI 2.0 CONVERSATION QUALITY AUDIT")
    print("=" * 80)

    results = []

    for i, s in enumerate(CANDIDATE_SCENARIOS, 1):
        session_id = f"audit_session_{s['category']}_{int(time.time())}"
        session_manager.cleanup(session_id)
        session = session_manager.get_or_create(session_id)
        session.selected_skill = "Python"
        session.record_primary_question(
            question_id=f"q_{i}",
            question_text=s["primary_question"],
            topic=s["topic"],
            expected_concepts=s["expected_concepts"]
        )
        session.current_state = "LISTENING"

        t0 = time.time()
        response = await interview_engine.handle_candidate_utterance(session_id, s["candidate_input"])
        latency = time.time() - t0

        # Auditing metrics
        words = len(response.split())
        question_marks = response.count("?")
        has_scoring = any(w in response.lower() for w in ["score", "grade", "/10", "points", "marks", "fail", "pass"])

        result_item = {
            "scenario": s["category"],
            "description": s["description"],
            "input": s["candidate_input"],
            "response": response,
            "latency": latency,
            "word_count": words,
            "question_marks": question_marks,
            "has_scoring": has_scoring,
            "state_after": session.current_state,
            "follow_up_count": session.follow_up_count_for_current_question,
            "primary_count": session.primary_question_count,
        }
        results.append(result_item)

        print(f"\n[{i}/8] Scenario: {s['category'].upper()}")
        print(f"Candidate Input: \"{s['candidate_input']}\"")
        print(f"VANI Response:   \"{response}\"")
        print(f"Latency: {latency:.2f}s | Words: {words} | Questions: {question_marks} | Scoring Detected: {has_scoring}")
        print(f"Follow-up Count: {session.follow_up_count_for_current_question} | Primary Count: {session.primary_question_count}")

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    for r in results:
        status = "PASS" if r["question_marks"] <= 1 and not r["has_scoring"] and r["word_count"] <= settings.MAX_SPOKEN_RESPONSE_WORDS else "WARN"
        print(f"- {r['scenario']}: [{status}] latency={r['latency']:.2f}s, words={r['word_count']}, questions={r['question_marks']}")

if __name__ == "__main__":
    asyncio.run(audit_scenarios())
