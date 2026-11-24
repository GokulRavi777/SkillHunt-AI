import os
from pathlib import Path
from dotenv import load_dotenv

# Find .env in project directory or parent directory
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    # LiveKit Cloud Configuration
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "wss://vani-2-0-1khnawsy.livekit.cloud")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")
    AGENT_NAME: str = os.getenv("AGENT_NAME", "vani-interviewer")

    # Gnani Voice AI (STT & TTS)
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    GNANI_STT_LANGUAGE: str = os.getenv("GNANI_STT_LANGUAGE", "en-IN")
    GNANI_STT_USE_STREAMING: bool = os.getenv("GNANI_STT_USE_STREAMING", "false").lower() == "true"
    GNANI_TTS_VOICE: str = os.getenv("GNANI_TTS_VOICE", "Nalini")
    GNANI_TTS_MODEL: str = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")
    GNANI_TTS_LANGUAGE: str = os.getenv("GNANI_TTS_LANGUAGE", "en-IN")

    # Google Gemini Intelligence
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    # Interview Constraints & Guardrails
    MAX_PRIMARY_QUESTIONS: int = 3
    MAX_FOLLOW_UPS_PER_QUESTION: int = 1
    MAX_SPOKEN_RESPONSE_WORDS: int = 65
    PREPARATION_WAIT_SECONDS: float = float(os.getenv("PREPARATION_WAIT_SECONDS", "20.0"))
    CONFIRMATION_TIMEOUT_SECONDS: float = float(os.getenv("CONFIRMATION_TIMEOUT_SECONDS", "20.0"))

    # Supported Skills
    SUPPORTED_SKILLS: list[str] = [
        "Python",
        "Java",
        "JavaScript",
        "React",
        "SQL",
        "Docker",
    ]

settings = Settings()
