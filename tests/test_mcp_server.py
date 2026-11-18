"""Unit and integration tests for VANI FastMCP server tools and prompt architecture."""

from __future__ import annotations

import pytest

from examples.vani_interview.mcp_server.data import (
    SUPPORTED_DIFFICULTIES,
    InMemorySessionStore,
)
from examples.vani_interview.mcp_server.server import (
    build_main_system_prompt,
    get_assessment_status,
    get_next_question,
    get_state_instruction,
    save_interview_response,
    select_interview_skill,
    session_store,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the session store before each test."""
    session_store.reset()
    yield
    session_store.reset()


def test_build_main_system_prompt_dynamic_injection():
    """Verify that build_main_system_prompt dynamically injects candidate profile and remains immutable."""
    prompt = build_main_system_prompt(
        candidate_name="Gokul R",
        skill="C++",
        proficiency="Beginner",
    )
    assert "Gokul R" in prompt
    assert "C++" in prompt
    assert "Beginner" in prompt
    assert "SkillHunt AI" in prompt
    assert "20 seconds" in prompt
    assert "Strict English" in prompt


def test_get_state_instruction_all_states():
    """Verify state instruction retrieval for every interview lifecycle phase."""
    # Greeting state
    greet = get_state_instruction(state="greeting", candidate_name="Gokul R", skill="C++", proficiency="Beginner")
    assert greet["status"] == "success"
    assert greet["state"] == "greeting"
    assert "Gokul R" in greet["instruction"]
    assert "C++" in greet["instruction"]

    # Readiness gate
    gate = get_state_instruction(state="readiness_gate", candidate_name="Gokul R", skill="C++", proficiency="Beginner")
    assert gate["status"] == "success"
    assert "20-second hold" in gate["instruction"]

    # Flow boundary
    flow = get_state_instruction(state="flow_boundary")
    assert flow["status"] == "success"
    assert "rules" in flow["instruction"].lower()

    # 20s hold start
    hold_start = get_state_instruction(state="hold_20s_start")
    assert hold_start["status"] == "success"
    assert "20 seconds" in hold_start["instruction"]

    # 20s hold expired
    hold_exp = get_state_instruction(state="hold_20s_expired")
    assert hold_exp["status"] == "success"
    assert "Twenty seconds have passed" in hold_exp["instruction"]

    # Hold exhausted
    hold_exh = get_state_instruction(state="hold_exhausted")
    assert hold_exh["status"] == "success"
    assert "already used your 20-second pause quota" in hold_exh["instruction"]

    # Question turn
    q_turn = get_state_instruction(
        state="question_turn",
        skill="C++",
        proficiency="Beginner",
        question="What is a pointer?",
    )
    assert q_turn["status"] == "success"
    assert "What is a pointer?" in q_turn["instruction"]

    # Completed
    comp = get_state_instruction(state="completed", candidate_name="Gokul R")
    assert comp["status"] == "success"
    assert "Gokul R" in comp["instruction"]


def test_select_interview_skill_universal_acceptance():
    """Verify that any skill extracted from a candidate resume is accepted without static whitelist blocking."""
    # Standard skill
    res1 = select_interview_skill(skill_name="C++", difficulty="Beginner")
    assert res1["status"] == "success"
    assert res1["selected_skill"] == "C++"

    # Novel dynamic skill from resume
    res2 = select_interview_skill(skill_name="FastAPI", difficulty="Intermediate")
    assert res2["status"] == "success"
    assert res2["selected_skill"] == "FastAPI"

    # Kubernetes from resume
    res3 = select_interview_skill(skill_name="Kubernetes", difficulty="Expert")
    assert res3["status"] == "success"
    assert res3["selected_skill"] == "Kubernetes"


def test_select_interview_skill_invalid_difficulty():
    """Verify invalid difficulty level raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported difficulty"):
        select_interview_skill("Python", "Master")


def test_get_next_question():
    """Verify question generation for any skill."""
    result = get_next_question("Python", "Intermediate")
    assert result["status"] == "success"
    assert result["skill"] == "Python"
    assert result["difficulty"] == "Intermediate"
    assert "question" in result
    assert result["question_id"] in session_store.state.asked_question_ids


def test_get_next_question_dynamic_skill():
    """Verify dynamic question generation for a novel skill like C++."""
    result = get_next_question("C++", "Beginner")
    assert result["status"] == "success"
    assert "C++" in result["skill"]
    assert "question" in result


def test_save_interview_response():
    """Verify recording of candidate responses in session store."""
    result = save_interview_response(
        skill_name="Python",
        question="What is a decorator?",
        candidate_response="A function that takes another function and extends its behavior.",
    )
    assert result["status"] == "success"
    assert result["total_recorded"] == 1
    assert len(session_store.state.recorded_responses) == 1
    recorded = session_store.state.recorded_responses[0]
    assert recorded.skill_name == "Python"
    assert "decorator" in recorded.question.lower()


def test_save_interview_response_validation():
    """Verify empty question or response validation."""
    with pytest.raises(ValueError, match="Question cannot be empty"):
        save_interview_response("Python", "", "Some answer")

    with pytest.raises(ValueError, match="Candidate response cannot be empty"):
        save_interview_response("Python", "What is GIL?", "   ")


def test_lifecycle_session_binding():
    """Verify Candidate Session Binding (Guardrail 2)."""
    session_store.bind_session(candidate_id="cand_123", room_name="room_abc")
    assert session_store.state.candidate_id == "cand_123"
    assert session_store.state.room_name == "room_abc"


def test_lifecycle_readiness_confirmation():
    """Verify Readiness Confirmation Gate (Guardrail 3)."""
    assert session_store.state.readiness_confirmed is False
    session_store.confirm_readiness()
    assert session_store.state.readiness_confirmed is True
    assert session_store.state.status.value == "IN_PROGRESS"


def test_lifecycle_follow_up_quota():
    """Verify Follow-Up Quota Enforcement (Guardrail 5)."""
    session_store.record_question("py_beg_1")
    assert session_store.can_follow_up() is True
    assert session_store.record_follow_up() is True
    # Second follow-up must be rejected by quota guardrail (max 1)
    assert session_store.can_follow_up() is False
    assert session_store.record_follow_up() is False


def test_lifecycle_question_completion_and_termination():
    """Verify Question Completion Enforcement (Guardrail 4 & 9)."""
    assert session_store.is_question_quota_reached() is False
    can_conclude, _ = session_store.can_conclude_assessment()
    assert can_conclude is False  # Cannot conclude prematurely (Guardrail 8)

    # Record 3 answers to hit target
    session_store.record_response("Python", "Q1", "Ans1")
    session_store.record_response("Python", "Q2", "Ans2")
    session_store.record_response("Python", "Q3", "Ans3")

    assert session_store.is_question_quota_reached() is True
    can_conclude, reason = session_store.can_conclude_assessment()
    assert can_conclude is True
    assert session_store.state.status.value == "COMPLETED"


def test_lifecycle_authorized_early_termination():
    """Verify Authorized Early Termination (Guardrail 8 & 9)."""
    session_store.record_response("Python", "Q1", "Ans1")
    can_conclude, reason = session_store.can_conclude_assessment(candidate_explicit_exit=True)
    assert can_conclude is True
    assert session_store.state.status.value == "TERMINATED_EARLY"
