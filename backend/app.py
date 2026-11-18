"""FastAPI Backend Server for SkillHunt AI Interview Platform.

Provides:
- Resume parsing and high-precision technical skills extraction (/api/resume/parse)
- Skills taxonomy reference (/api/skills/taxonomy)
- LiveKit WebRTC access token generation (/api/interview/token)
- Health check and session diagnostics (/api/health)
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel

# Load environment variables from vani_interview .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

try:
    from backend.resume_parser import (
        TECHNICAL_SKILLS_TAXONOMY,
        ParsedResume,
        parse_resume,
    )
except ImportError:
    from resume_parser import (
        TECHNICAL_SKILLS_TAXONOMY,
        ParsedResume,
        parse_resume,
    )

app = FastAPI(
    title="SkillHunt AI Interview Intelligence API",
    description="Backend microservice powering resume skill extraction and LiveKit WebRTC interview sessions.",
    version="2.0.0"
)

# Enable CORS for Vite frontend and local requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenRequest(BaseModel):
    candidateName: str
    selectedSkill: str
    proficiency: str
    roomName: str | None = None


def create_livekit_token(
    api_key: str,
    api_secret: str,
    identity: str,
    name: str,
    metadata: str,
    room_name: str,
    valid_hours: int = 6,
) -> str:
    """Create a standardized LiveKit Cloud JWT token using HS256."""
    now = int(time.time())
    claims = {
        "iss": api_key,
        "sub": identity,
        "name": name,
        "metadata": metadata,
        "nbf": now - 5,
        "exp": now + (valid_hours * 3600),
        "video": {
            "roomJoin": True,
            "room": room_name,
            "canPublish": True,
            "canSubscribe": True,
        },
    }
    return jwt.encode(claims, api_secret, algorithm="HS256")


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    """Health status and service diagnostic check."""
    livekit_url = os.getenv("LIVEKIT_URL", "wss://vani-2-0-1khnawsy.livekit.cloud")
    livekit_key = os.getenv("LIVEKIT_API_KEY", "")
    return {
        "status": "healthy",
        "service": "skillhunt_interview_backend",
        "livekitConfigured": bool(livekit_url and livekit_key),
        "livekitUrl": livekit_url,
        "skillsTaxonomyCount": sum(len(skills) for skills in TECHNICAL_SKILLS_TAXONOMY.values()),
    }


@app.get("/api/skills/taxonomy")
async def get_skills_taxonomy() -> dict[str, list[str]]:
    """Return full taxonomy of supported technical skills organized by category."""
    return TECHNICAL_SKILLS_TAXONOMY


@app.post("/api/resume/parse")
async def parse_resume_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload resume (PDF, DOCX, TXT) and extract candidate metadata and technical skills."""
    filename = file.filename or "uploaded_resume.pdf"
    ext = os.path.splitext(filename.lower())[1]

    if ext not in [".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Please upload a PDF, DOCX, or TXT file."
        )

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        parsed: ParsedResume = parse_resume(filename, content)
        return parsed.to_dict()

    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal resume parsing failure: {e}") from e


@app.post("/api/interview/token")
async def generate_interview_token(req: TokenRequest) -> dict[str, Any]:
    """Generate LiveKit WebRTC Access Token for the candidate session."""
    livekit_url = os.getenv("LIVEKIT_URL", "wss://vani-2-0-1khnawsy.livekit.cloud")
    api_key = os.getenv("LIVEKIT_API_KEY", "APIvdBWqMMzQekZ")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "86h0ViCAhVGx6HdxvWruT8N7f5VbbTEhbeWsAqVhMyJ")

    room_name = req.roomName or f"skillhunt-interview-{uuid.uuid4().hex[:8]}"
    participant_identity = f"candidate-{uuid.uuid4().hex[:6]}"

    metadata = json.dumps({
        "candidateName": req.candidateName,
        "selectedSkill": req.selectedSkill,
        "proficiency": req.proficiency,
        "sessionId": f"skillhunt_sess_{uuid.uuid4().hex[:8]}"
    })

    try:
        token = create_livekit_token(
            api_key=api_key,
            api_secret=api_secret,
            identity=participant_identity,
            name=req.candidateName,
            metadata=metadata,
            room_name=room_name
        )

        return {
            "token": token,
            "url": livekit_url,
            "roomName": room_name,
            "participantIdentity": participant_identity,
            "metadata": json.loads(metadata)
        }

    except Exception as e:
        return {
            "token": f"mock_jwt_token_{uuid.uuid4().hex}",
            "url": livekit_url,
            "roomName": room_name,
            "participantIdentity": participant_identity,
            "metadata": json.loads(metadata),
            "warning": f"Generated fallback token: {e}"
        }


@app.post("/api/interview/transcribe")
async def transcribe_audio_endpoint(
    audio_file: UploadFile = File(...)
) -> dict[str, Any]:
    """High-reliability audio transcription endpoint.
    
    Accepts candidate audio recorded directly from the browser (WebM or WAV).
    Uses Gnani STT REST API (en-IN) first with sub-100ms latency,
    and seamlessly falls back to Gemini 3.5 Flash Lite multimodal audio.
    """
    content = await audio_file.read()
    if not content or len(content) < 500:
        return {"status": "empty", "transcript": "", "detail": "Audio buffer too small or silent."}

    # 1. Attempt Gnani STT REST (low latency, en-IN optimized)
    gnani_key = os.getenv("GNANI_API_KEY")
    if gnani_key:
        try:
            import httpx
            files = {
                "audio_file": (
                    audio_file.filename or "audio.wav",
                    content,
                    audio_file.content_type or "audio/wav",
                )
            }
            data = {"language_code": "en-IN", "format": "verbatim"}
            headers = {"X-API-Key-ID": gnani_key}
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    "https://api.vachana.ai/stt/v3",
                    files=files,
                    data=data,
                    headers=headers,
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    transcript = res_json.get("transcript", "").strip()
                    if transcript:
                        return {
                            "status": "success",
                            "transcript": transcript,
                            "engine": "gnani_stt"
                        }
        except Exception:
            pass

    # 2. High-precision Gemini 3.5 Flash Lite Multimodal Audio Fallback
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            import google.genai as genai
            client = genai.Client(api_key=gemini_key)
            mime = audio_file.content_type or "audio/webm"
            if "wav" in mime:
                clean_mime = "audio/wav"
            elif "ogg" in mime:
                clean_mime = "audio/ogg"
            elif "mp4" in mime or "m4a" in mime:
                clean_mime = "audio/mp4"
            else:
                clean_mime = "audio/webm"

            part = genai.types.Part.from_bytes(data=content, mime_type=clean_mime)
            prompt = (
                "You are an expert audio speech transcriber for a live software engineering interview. "
                "Accurately transcribe the candidate's spoken speech in English. "
                "Output ONLY the exact words spoken by the user. "
                "Do NOT include commentary, timestamps, or quotes. "
                "If only silence, breath, or background static is heard, output empty string."
            )
            res = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[part, prompt]
            )
            transcription = (res.text or "").strip()
            # Clean common model noise/artifact outputs
            if transcription.lower() in ["00:00", "0:00", "none", "silence", "[silence]", "[noise]", "empty"]:
                transcription = ""

            if transcription:
                return {
                    "status": "success",
                    "transcript": transcription,
                    "engine": "gemini_multimodal"
                }
        except Exception as gemini_err:
            return {"status": "error", "transcript": "", "detail": str(gemini_err)}

    return {"status": "no_speech", "transcript": ""}


class TTSRequest(BaseModel):
    text: str
    voice: str = "Nalini"
    model: str = "timbre-v2.5"
    language: str = "en-IN"


@app.post("/api/interview/tts")
async def generate_interview_tts(req: TTSRequest) -> Response:
    """Generate high-fidelity spoken audio using Gnani TTS (Nalini voice)."""
    gnani_key = os.getenv("GNANI_API_KEY")
    if not gnani_key:
        raise HTTPException(status_code=500, detail="GNANI_API_KEY is not configured.")

    payload = {
        "text": req.text,
        "voice": req.voice,
        "model": req.model,
        "language": req.language,
        "audio_config": {
            "sample_rate": 16000,
            "encoding": "linear_pcm",
            "num_channels": 1,
            "container": "wav",
        },
    }
    headers = {
        "X-API-Key-ID": gnani_key,
        "Content-Type": "application/json",
    }
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.vachana.ai/api/v1/tts/inference",
                json=payload,
                headers=headers,
            )
            if resp.status_code == 200 and resp.content:
                return Response(content=resp.content, media_type="audio/wav")
            raise HTTPException(status_code=resp.status_code, detail=f"TTS synthesis failed: {resp.text[:200]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}") from e


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
