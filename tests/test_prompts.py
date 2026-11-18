"""Unit tests for VANI interviewer prompts, skills, and personality configuration."""

from __future__ import annotations

import pytest

from examples.vani_interview.prompts import (
    DEFAULT_GREETING,
    SUPPORTED_SKILLS,
    get_default_greeting,
    get_supported_skills,
    get_system_prompt,
)

pytestmark = pytest.mark.unit


def test_supported_skills_list():
    """Verify all required technical skills are present."""
    expected_skills = {"Python", "Java", "JavaScript", "React", "SQL", "Docker"}
    skills = get_supported_skills()
    assert set(skills) == expected_skills
    assert len(skills) == 6


def test_supported_skills_returns_copy():
    """Ensure mutating the returned list does not alter the module constant."""
    skills = get_supported_skills()
    skills.append("Kubernetes")
    assert "Kubernetes" not in SUPPORTED_SKILLS


def test_default_greeting_content():
    """Verify default greeting introduces SkillHunt AI and asks how the candidate is doing."""
    greeting = get_default_greeting()
    assert "Hello!" in greeting
    assert "SkillHunt AI" in greeting
    assert "technical interview" in greeting
    assert greeting == DEFAULT_GREETING


def test_system_prompt_role_and_responsibilities():
    """Verify system prompt defines SkillHunt AI's role, duties, and conversational flow."""
    prompt = get_system_prompt()
    assert "SkillHunt AI" in prompt
    assert "AI technical interviewer" in prompt
    assert "one question at a time" in prompt
    assert "relevant follow-up" in prompt
    assert "handle interruptions naturally" in prompt.lower()
    assert "change the discussion topic" in prompt


def test_system_prompt_supported_skills_included():
    """Verify all supported skills are listed in the system prompt."""
    prompt = get_system_prompt()
    for skill in SUPPORTED_SKILLS:
        assert skill in prompt


def test_system_prompt_behavioral_rules():
    """Verify critical boundaries and behavioral rules."""
    prompt = get_system_prompt()
    # Rules against scoring and pass/fail verdicts
    assert "do not score or rank" in prompt.lower()
    assert "hiring recommendations" in prompt.lower()
    # Speech constraints
    assert "concise" in prompt.lower()
    assert "suitable for speech" in prompt.lower()
    assert "monologues" in prompt.lower()
    # Question constraint
    assert "never ask multiple technical questions at once" in prompt.lower()
    # Dynamic question generation
    assert "dynamically" in prompt.lower()
