"""Unit tests for the Candidate Skill & Difficulty Configuration Pipeline."""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from langchain_core.messages import SystemMessage, AIMessage

from examples.vani_interview.orchestration.conversation import ConversationManager
from examples.vani_interview.agent import VaniInterviewAgent, VaniConfig


def test_conversation_manager_configure_candidate_session():
    """Verify that configure_candidate_session configures skill, difficulty, greeting, and system prompt."""
    cm = ConversationManager(model="gemini-3.5-flash-lite", api_key="mock_key")
    cm.messages = [
        SystemMessage(content="You are VANI."),
        AIMessage(content="Hello!"),
    ]

    greeting = cm.configure_candidate_session(
        candidate_name="Gokul R",
        skill="Python",
        difficulty="Expert",
    )

    assert cm.candidate_id == "Gokul R"
    assert cm.active_skill == "Python"
    assert cm.active_difficulty == "Expert"

    # Greeting must explicitly mention candidate name, skill, and difficulty
    assert "Gokul R" in greeting
    assert "Python" in greeting
    assert "Expert" in greeting

    # System instruction must include skill & difficulty directive
    assert "Gokul R" in cm.messages[0].content
    assert "Python" in cm.messages[0].content
    assert "Expert" in cm.messages[0].content


@pytest.mark.asyncio
async def test_agent_on_enter_extracts_participant_metadata():
    """Verify that agent.on_enter extracts LiveKit participant metadata and binds session."""
    agent = VaniInterviewAgent()
    agent.conversation_manager.initialize = AsyncMock()
    agent.conversation_manager.tool_map = {
        "select_interview_skill": AsyncMock(ainvoke=AsyncMock(return_value={"status": "success"}))
    }

    # Mock LiveKit participant with metadata
    mock_participant = MagicMock()
    mock_participant.name = "Gokul R"
    mock_participant.metadata = json.dumps({
        "candidateName": "Gokul R",
        "selectedSkill": "FastAPI",
        "proficiency": "Intermediate",
    })

    mock_room = MagicMock()
    mock_room.name = "skillhunt-room-101"
    mock_room.remote_participants = {"p1": mock_participant}

    mock_session = MagicMock()
    mock_session.room = mock_room
    mock_session.say = AsyncMock()

    agent._session_override = mock_session
    agent._session = mock_session

    await agent.on_enter()

    # Verify conversation manager was updated with extracted skill & difficulty
    assert "Gokul R" in agent.conversation_manager.candidate_id
    assert agent.conversation_manager.active_skill == "FastAPI"
    assert agent.conversation_manager.active_difficulty == "Intermediate"

    # Verify greeting was spoken with candidate name, skill, and difficulty
    spoken_greeting = mock_session.say.call_args[0][0]
    assert "Gokul R" in spoken_greeting
    assert "FastAPI" in spoken_greeting
    assert "Intermediate" in spoken_greeting

    # Verify FastMCP tool was synchronized
    agent.conversation_manager.tool_map["select_interview_skill"].ainvoke.assert_awaited_once_with({
        "skill_name": "FastAPI",
        "difficulty": "Intermediate",
    })
