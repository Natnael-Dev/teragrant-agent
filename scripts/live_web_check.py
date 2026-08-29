"""
Live Web Check Script for Multilingual Voice Transcription (Batch 30F).
Uses FastAPI TestClient to POST the REAL voice file data/proof_voice.mp3
to /api/transcribe against the live Gemini API endpoint.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv()

from app.server import app

def main():
    client = TestClient(app)
    voice_path = PROJECT_ROOT / "data" / "proof_voice.mp3"
    if not voice_path.exists():
        print(f"ERROR: Audio file not found at {voice_path}")
        sys.exit(1)

    print(f"==> Reading audio payload from {voice_path.name} ({voice_path.stat().st_size} bytes)...")
    with open(voice_path, "rb") as f:
        audio_bytes = f.read()

    print("==> Dispatching POST /api/transcribe with real Gemini API...")
    response = client.post(
        "/api/transcribe",
        files={"audio": ("proof_voice.mp3", audio_bytes, "audio/mpeg")},
        data={"lang": "English"}
    )

    print(f"HTTP Status: {response.status_code}")
    data = response.json()
    print("Response JSON:")
    print("-" * 60)
    print(f"Status: {'SUCCESS' if not data.get('error') else 'ERROR'}")
    print(f"Transcript: {data.get('transcript')}")
    print(f"Fact Chips: {data.get('chips')}")
    if data.get("error"):
        print(f"Error Details: {data.get('error')}")
    print("-" * 60)

    if response.status_code == 200 and data.get("transcript"):
        print("✓ LIVE TRANSCRIPTION TEST PASSED!")
    else:
        print("✗ LIVE TRANSCRIPTION TEST FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
