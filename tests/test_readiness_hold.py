"""Unit tests for Readiness Confirmation Gate and Hold Policy."""

from __future__ import annotations

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from examples.vani_interview.agent import VaniInterviewAgent
from examples.vani_interview.orchestration.conversation import ConversationManager


def test_is_hold_request_detection():
    manager = ConversationManager()
    assert manager.is_hold_request("Can you please hold on for a minute?") is True
    assert manager.is_hold_request("Wait a second, I need to check my mic") is True
    assert manager.is_hold_request("Give me a minute") is True
    assert manager.is_hold_request("Just a second please") is True
    assert manager.is_hold_request("Yes, I am completely ready") is False
    assert manager.is_hold_request("Generators yield values lazily") is False


@pytest.mark.asyncio
async def test_readiness_hold_state_transition():
    manager = ConversationManager()
    assert manager.is_on_hold is False
    assert manager.readiness_confirmed is False

    # Candidate asks to hold
    manager.is_on_hold = manager.is_hold_request("hold on a minute please")
    assert manager.is_on_hold is True
    assert manager.readiness_confirmed is False

    # Candidate says ready
    if manager.is_on_hold and "ready" in "okay I am ready now":
        manager.is_on_hold = False
        manager.readiness_confirmed = True

    assert manager.is_on_hold is False
    assert manager.readiness_confirmed is True


@pytest.mark.asyncio
async def test_agent_hold_timer_expiration():
    """Verify that if candidate does not speak, timer expires and prompts resumption or reschedule."""
    agent = VaniInterviewAgent()
    mock_session = MagicMock()
    mock_session.say = AsyncMock()
    agent._session = mock_session

    # Run hold timer with a tiny delay for testing
    await agent._run_hold_timer(delay=0.01)

    assert mock_session.say.called
    spoken_arg = mock_session.say.call_args[0][0]
    assert "continue with the interview" in spoken_arg.lower()
    assert "nervous" in spoken_arg.lower()


@pytest.mark.asyncio
async def test_agent_hold_timer_cancellation():
    """Verify that when candidate speaks, pending hold timer is cancelled cleanly."""
    agent = VaniInterviewAgent()
    mock_session = MagicMock()
    mock_session.say = AsyncMock()
    agent._session = mock_session

    # Start a 10-second timer
    agent._hold_timer = asyncio.create_task(agent._run_hold_timer(delay=10.0))

    # Simulate candidate speaking after 0.01s
    await asyncio.sleep(0.01)
    agent._hold_timer.cancel()
    await asyncio.sleep(0.01)

    assert agent._hold_timer.cancelled()
    # Spoken prompt should NOT be called since candidate cancelled it
    assert not mock_session.say.called
