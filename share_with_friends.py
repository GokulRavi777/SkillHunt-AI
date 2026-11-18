"""Utility script to generate 1-click shareable test links for friends."""

from __future__ import annotations

import argparse
import datetime
import os
import sys
import uuid
from pathlib import Path

# Add repo root to sys.path
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from dotenv import load_dotenv

# Load local env
_local_env = Path(__file__).resolve().parent / ".env"
load_dotenv(_local_env if _local_env.exists() else None)

from livekit import api


def generate_share_link(
    candidate_name: str = "Guest Candidate",
    room_name: str | None = None,
    expiry_hours: int = 24,
) -> dict[str, str]:
    """Generate a 1-click test link that friends can open in their browser."""
    livekit_url = os.environ.get("LIVEKIT_URL")
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")

    if not livekit_url or not api_key or not api_secret:
        raise ValueError("Missing LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET in .env.")

    room = room_name or f"skillhunt-interview-{uuid.uuid4().hex[:6]}"
    identity = f"candidate-{uuid.uuid4().hex[:6]}"

    # Generate AccessToken valid for expiry_hours
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(candidate_name)
        .with_ttl(datetime.timedelta(hours=expiry_hours))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .to_jwt()
    )

    # 1-click URL using official LiveKit hosted client
    meet_url = f"https://meet.livekit.io/custom?liveKitUrl={livekit_url}&token={token}"

    return {
        "room_name": room,
        "candidate_name": candidate_name,
        "identity": identity,
        "expiry_hours": str(expiry_hours),
        "meet_url": meet_url,
        "token": token,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate 1-click SkillHunt AI test links for friends")
    parser.add_argument("--name", default="Guest Candidate", help="Name of the friend testing")
    parser.add_argument("--room", default=None, help="Optional custom room name")
    parser.add_argument("--hours", type=int, default=24, help="Token validity in hours (default: 24)")
    args = parser.parse_args()

    info = generate_share_link(
        candidate_name=args.name,
        room_name=args.room,
        expiry_hours=args.hours,
    )

    print("\n" + "=" * 60)
    print("🚀 SkillHunt AI — 1-CLICK SHAREABLE TEST LINK")
    print("=" * 60)
    print(f"Candidate: {info['candidate_name']}")
    print(f"Room:      {info['room_name']}")
    print(f"Validity:  {info['expiry_hours']} hours")
    print("-" * 60)
    print("Send this link to your friend (works on Mobile & Desktop Chrome/Safari):")
    print(f"\n{info['meet_url']}\n")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
