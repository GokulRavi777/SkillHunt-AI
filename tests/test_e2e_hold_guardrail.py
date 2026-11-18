"""End-to-end simulation of VANI 2.0 interview greeting and 1-minute hold guardrail."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from examples.vani_interview.agent import DEFAULT_GREETING, VaniConfig, VaniInterviewAgent


@pytest.mark.asyncio
async def test_full_interview_greeting_and_1min_hold_guardrails() -> None:
    config = VaniConfig.from_env()
    agent = VaniInterviewAgent(config=config)
    mock_session = MagicMock()
    mock_session.say = AsyncMock()
    agent._session = mock_session

    # Step 1: Candidate enters room & greeting delivered
    await agent.conversation_manager.initialize()
    agent.conversation_manager.bind_session("cand_123", "room_test")
    assert "Welcome to your Python technical interview!" in DEFAULT_GREETING
    assert "Are you ready to begin?" in DEFAULT_GREETING

    # Step 2: Candidate asks to hold
    hold_utterance = "Wait a second, can you please hold on for a minute? I need a sip of water."
    response_hold = await agent.conversation_manager.process_turn(hold_utterance)
    assert agent.conversation_manager.is_hold_request(hold_utterance)
    assert agent.conversation_manager.is_on_hold
    assert not agent.conversation_manager.readiness_confirmed
    # No technical questions fetched while candidate is on hold
    assert len(agent.conversation_manager.asked_question_ids) == 0

    # Step 3A: Simulating 60s Hold Timer Expiration (Candidate remained silent)
    await agent._run_hold_timer(delay=0.01)
    assert mock_session.say.called
    timeout_spoken = mock_session.say.call_args[0][0]
    assert "continue with the interview" in timeout_spoken.lower()
    assert "nervous" in timeout_spoken.lower()
    # Confirm allow_interruptions was set to False
    call_kwargs = mock_session.say.call_args[1]
    assert call_kwargs.get("allow_interruptions") is False

    # Step 3B: Candidate says they are ready now
    mock_session.say.reset_mock()
    candidate_ready = "I'm ready now, let's begin the interview!"
    response_q1 = await agent.conversation_manager.process_turn(candidate_ready)
    assert agent.conversation_manager.readiness_confirmed
    assert not agent.conversation_manager.is_on_hold
    # Question 1 must be fetched immediately upon readiness confirmation
    assert len(agent.conversation_manager.asked_question_ids) == 1
    assert "mutable" in response_q1.lower() or "python" in response_q1.lower()

    # Step 4: Candidate answers Question 1
    q1_answer = "In Python, lists are mutable so we can modify them in place, while tuples are immutable."
    response_eval = await agent.conversation_manager.process_turn(q1_answer)
    assert len(agent.conversation_manager.asked_question_ids) >= 1
    assert len(agent.conversation_manager.recorded_responses) >= 1
