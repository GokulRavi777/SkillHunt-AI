"""Unit and smoke tests for VANI agent configuration, credentials, and session assembly."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from examples.vani_interview.agent import (
    VaniConfig,
    VaniInterviewAgent,
    create_agent_session,
)
from examples.vani_interview.prompts import VANI_SYSTEM_PROMPT

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Unit tests (Mocked, hermetic, fast, no external network calls)
# ---------------------------------------------------------------------------


def test_default_config_values():
    """Verify default values when environment provides only required credentials."""
    env = {
        "GNANI_API_KEY": "test-gnani-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "LIVEKIT_URL": "wss://test.livekit.cloud",
        "LIVEKIT_API_KEY": "test-lk-key",
        "LIVEKIT_API_SECRET": "test-lk-secret",
    }
    with patch.dict(os.environ, env, clear=True):
        config = VaniConfig.from_env(load_env_file=False)
        assert config.gemini_model == "gemini-3.5-flash-lite"
        assert config.gnani_stt_language == "en-IN"
        assert config.gnani_tts_voice == "Nalini"
        assert config.gnani_tts_model == "timbre-v2.5"
        assert config.gnani_tts_language == "en-IN"
        assert config.gnani_api_key == "test-gnani-key"
        assert config.gemini_api_key == "test-gemini-key"
        assert config.endpointing_min_delay == 0.15
        assert config.endpointing_max_delay == 0.40
        assert config.vad_min_silence_duration == 0.25


def test_custom_gemini_model_preserved():
    """Verify that user-specified GEMINI_MODEL is preserved and never silently replaced."""
    env = {
        "GNANI_API_KEY": "test-gnani-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "GEMINI_MODEL": "gemini-3.5-flash-lite",
    }
    with patch.dict(os.environ, env, clear=True):
        config = VaniConfig.from_env(load_env_file=False)
        assert config.gemini_model == "gemini-3.5-flash-lite"


def test_google_api_key_fallback():
    """Verify that GOOGLE_API_KEY is used if GEMINI_API_KEY is omitted."""
    env = {
        "GNANI_API_KEY": "test-gnani-key",
        "GOOGLE_API_KEY": "test-google-key",
    }
    with patch.dict(os.environ, env, clear=True):
        config = VaniConfig.from_env(load_env_file=False)
        assert config.gemini_api_key == "test-google-key"


def test_missing_credentials_detection():
    """Verify missing credentials detection returns exact variable names."""
    with patch.dict(os.environ, {}, clear=True):
        config = VaniConfig.from_env(load_env_file=False)
        missing = config.validate_credentials(require_livekit=True)
        assert "LIVEKIT_URL" in missing
        assert "LIVEKIT_API_KEY" in missing
        assert "LIVEKIT_API_SECRET" in missing
        assert "GNANI_API_KEY" in missing
        assert "GEMINI_API_KEY" in missing


def test_missing_credentials_raises_without_leaking_secrets():
    """Ensure ensure_valid_credentials raises ValueError without exposing secret values."""
    secret_value = "my-super-secret-key-12345"
    env = {
        "GNANI_API_KEY": secret_value,
        # GEMINI_API_KEY is intentionally missing
    }
    with patch.dict(os.environ, env, clear=True):
        config = VaniConfig.from_env(load_env_file=False)
        with pytest.raises(ValueError) as exc_info:
            config.ensure_valid_credentials(require_livekit=False)

        error_message = str(exc_info.value)
        assert "GEMINI_API_KEY" in error_message
        # Verify secrets are never echoed in error messages
        assert secret_value not in error_message


def test_agent_initialization():
    """Verify VaniInterviewAgent uses the VANI system prompt."""
    agent = VaniInterviewAgent()
    assert agent.instructions == VANI_SYSTEM_PROMPT


def test_create_agent_session_assembly():
    """Verify create_agent_session wires STT, TTS, LLM, VAD and options properly."""
    config = VaniConfig(
        gnani_api_key="mock-gnani-key",
        gemini_api_key="mock-gemini-key",
        gemini_model="gemini-3.5-flash-lite",
        gnani_stt_language="en-IN",
        gnani_tts_voice="Nalini",
        gnani_tts_model="timbre-v2.5",
        gnani_tts_language="en-IN",
    )

    mock_stt = MagicMock()
    mock_tts = MagicMock()
    mock_llm = MagicMock()
    mock_vad = MagicMock()

    session = create_agent_session(
        config,
        stt_override=mock_stt,
        tts_override=mock_tts,
        llm_override=mock_llm,
        vad_override=mock_vad,
    )

    assert session.stt is mock_stt
    assert session.tts is mock_tts
    assert session.llm is mock_llm
    assert session.vad is mock_vad
    assert session._opts.turn_handling is not None
    assert session._opts.endpointing.get("min_delay") == 0.15
    assert session._opts.endpointing.get("max_delay") == 0.40
    assert session._opts.interruption.get("resume_false_interruption") is False
    assert session._opts.preemptive_generation.get("enabled") is False


# ---------------------------------------------------------------------------
# Optional live provider smoke tests (run only when environment credentials exist)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
    reason="GEMINI_API_KEY not configured in environment",
)
def test_live_gemini_smoke():
    """Smoke test Gemini model instantiation with actual credentials."""
    from livekit.plugins import google

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    llm = google.LLM(model="gemini-3.5-flash-lite", api_key=api_key)
    assert llm._opts.model == "gemini-3.5-flash-lite"


@pytest.mark.skipif(
    not os.environ.get("GNANI_API_KEY"),
    reason="GNANI_API_KEY not configured in environment",
)
def test_live_gnani_smoke():
    """Smoke test Gnani STT & TTS instantiation with actual credentials."""
    from livekit.plugins import gnani

    api_key = os.environ["GNANI_API_KEY"]
    stt = gnani.STT(language="en-IN", api_key=api_key, sample_rate=16000, use_streaming=True)
    tts = gnani.TTS(
        voice="Nalini",
        model="timbre-v2.5",
        language="en-IN",
        api_key=api_key,
        sample_rate=16000,
        synthesize_method="websocket",
    )
    assert stt._opts.language == "en-IN"
    assert tts._opts.voice == "Nalini"
