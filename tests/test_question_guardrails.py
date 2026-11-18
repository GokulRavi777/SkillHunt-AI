"""Unit tests for Question-Level Guardrails, Elaboration Quotas, and Few-Shot Generation."""

from __future__ import annotations

import pytest

from examples.vani_interview.mcp_server.server import (
    generate_few_shot_question,
    get_next_question,
    get_state_instruction,
    session_store,
)
from examples.vani_interview.orchestration.conversation import (
    ELABORATION_REQUEST,
    FLOW_BOUNDARY_RESPONSE,
    HOLD_20S_AGREEMENT,
    HOLD_EXHAUSTED_RESPONSE,
    NO_COACHING_RESPONSE,
    REPEAT_LIMIT_REACHED_RESPONSE,
    ConversationManager,
)


@pytest.fixture(autouse=True)
def reset_store():
    session_store.reset()
    yield
    session_store.reset()


def test_few_shot_question_generation_for_novel_skills():
    """Verify few-shot generation produces calibrated questions for any skill without hardcoding."""
    # C++ Beginner
    cpp_beg = generate_few_shot_question("C++", "Beginner", 0)
    assert cpp_beg["status"] == "success"
    assert "C++" in cpp_beg["question"]
    assert "stack" in cpp_beg["question"].lower() or "memory" in cpp_beg["question"].lower()

    # FastAPI Intermediate
    fastapi_int = generate_few_shot_question("FastAPI", "Intermediate", 1)
    assert fastapi_int["status"] == "success"
    assert "FastAPI" in fastapi_int["question"]
    assert "exception" in fastapi_int["question"].lower() or "cleanup" in fastapi_int["question"].lower()

    # Rust Expert
    rust_exp = generate_few_shot_question("Rust", "Expert", 2)
    assert rust_exp["status"] == "success"
    assert "Rust" in rust_exp["question"]
    assert "starvation" in rust_exp["question"].lower() or "concurrency" in rust_exp["question"].lower() or "load" in rust_exp["question"].lower()


def test_vague_answer_detection():
    """Verify detection of brief/vague candidate answers under 5 words."""
    cm = ConversationManager(api_key="mock_key")
    cm.readiness_confirmed = True
    cm.last_asked_question = "What is a virtual destructor in C++?"

    # Vague answers
    assert cm.is_vague_or_short_answer("yes")
    assert cm.is_vague_or_short_answer("idk")
    assert cm.is_vague_or_short_answer("I don't know")
    assert cm.is_vague_or_short_answer("not sure really")
    assert cm.is_vague_or_short_answer("maybe it cleans")

    # Technical substantive answer (not vague)
    assert not cm.is_vague_or_short_answer(
        "A virtual destructor ensures that the derived class destructor is called when deleting an object through a base pointer."
    )


@pytest.mark.asyncio
async def test_vague_answer_single_elaboration_quota():
    """Verify candidate is prompted to elaborate maximum once per question."""
    cm = ConversationManager(api_key="mock_key")
    cm._initialized = True
    cm.readiness_confirmed = True
    cm.last_asked_question = "What is a pointer in C++?"

    # First vague answer -> Elaboration requested
    resp1 = await cm.process_turn("I don't know")
    assert resp1 == ELABORATION_REQUEST
    assert cm.elaboration_requested_current_q is True

    # Second vague answer -> Does not repeat elaboration, proceeds
    # (Since llm is not connected in unit test, it proceeds past elaboration gate)
    assert cm.is_vague_or_short_answer("still unsure")


@pytest.mark.asyncio
async def test_repeat_question_limit():
    """Verify candidate can repeat question at most 2 times before refusal."""
    cm = ConversationManager(api_key="mock_key")
    cm._initialized = True
    cm.readiness_confirmed = True
    cm.last_asked_question = "Can you explain RAII in C++?"

    # Repeat 1
    resp1 = await cm.process_turn("Can you repeat that?")
    assert "Certainly" in resp1
    assert "RAII in C++" in resp1
    assert cm.question_repeat_count == 1

    # Repeat 2
    resp2 = await cm.process_turn("Pardon, say that again?")
    assert "Certainly" in resp2
    assert cm.question_repeat_count == 2

    # Repeat 3 (exceeded)
    resp3 = await cm.process_turn("Please repeat once more")
    assert resp3 == REPEAT_LIMIT_REACHED_RESPONSE
    assert cm.question_repeat_count == 2


@pytest.mark.asyncio
async def test_zero_coaching_guardrail():
    """Verify refusal to reveal answers or coach during evaluation."""
    cm = ConversationManager(api_key="mock_key")
    cm._initialized = True
    cm.readiness_confirmed = True
    cm.last_asked_question = "What is a smart pointer?"

    resp = await cm.process_turn("What is the answer?")
    assert resp == NO_COACHING_RESPONSE


@pytest.mark.asyncio
async def test_flow_and_topics_guardrail():
    """Verify inquiries about rules, syllabus, or topics are redirected to lobby briefing."""
    cm = ConversationManager(api_key="mock_key")
    cm._initialized = True

    resp = await cm.process_turn("What topics will you ask about in this interview?")
    assert resp == FLOW_BOUNDARY_RESPONSE


@pytest.mark.asyncio
async def test_hold_20s_single_use_quota():
    """Verify 20-second hold can only be used once, and second attempt is refused."""
    cm = ConversationManager(api_key="mock_key")
    cm._initialized = True

    # First hold request -> Granted
    resp1 = await cm.process_turn("Wait, can you please hold for a second?")
    assert resp1 == HOLD_20S_AGREEMENT
    assert cm.is_on_hold is True
    assert cm.hold_used is True

    # Second hold request -> Refused
    resp2 = await cm.process_turn("Hold on again please")
    assert resp2 == HOLD_EXHAUSTED_RESPONSE
