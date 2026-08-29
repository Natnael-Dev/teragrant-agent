"""
Live Interactive Extraction Demo Script.
Runs Vision OCR (License) and Audio Voice Note extractions against real Gemini models.

Usage:
    python scripts/live_extraction_demo.py [--image path/to/license.jpg] [--audio path/to/voicenote.mp3]
"""

import argparse
import base64
import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extractors.config import get_api_key
from extractors.vision_extractor import extract_license_data
from extractors.audio_extractor import extract_audio_story


# Minimal 1x1 valid PNG image in base64 format for fallback testing
SAMPLE_BASE64_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

# Minimal 1-second silent MP3 binary placeholder
SAMPLE_BASE64_MP3 = (
    "//uQxAAAAAAAAAAAAAAAAAAAAAAAWGluZwAAAA8AAAACAAACcQCAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA"
    "//////////////////////////////////////////////////////////////////8AAAA8TEFNRTMuMTAwA8MAAAAAAAAAABQAUCRCQABm"
    "AAAAnEAA////////////////////////////////////////////////////////////////////////////////////////////////////"
    "////////////////////////////////////////////////////////////////"
)


def create_sample_files() -> tuple[str, str]:
    """Create sample dummy image and audio files for testing when real files are not provided."""
    temp_dir = Path(tempfile.gettempdir()) / "teragrant_demo"
    temp_dir.mkdir(parents=True, exist_ok=True)

    img_path = temp_dir / "sample_trade_license.png"
    with open(img_path, "wb") as f:
        f.write(base64.b64decode(SAMPLE_BASE64_PNG))

    audio_path = temp_dir / "sample_voice_note.mp3"
    with open(audio_path, "wb") as f:
        f.write(base64.b64decode(SAMPLE_BASE64_MP3))

    return str(img_path), str(audio_path)


def main():
    parser = argparse.ArgumentParser(description="TeraGrant Live Extraction Demo")
    parser.add_argument("--image", type=str, default=None, help="Path to a business license image")
    parser.add_argument("--audio", type=str, default=None, help="Path to an audio voice note file")
    parser.add_argument("--model", type=str, default="gemini-2.0-flash", help="Gemini model ID")
    args = parser.parse_args()

    print("=" * 70)
    print("      TERAGRANT AGENT - LIVE INTAKE EXTRACTION DEMO")
    print("=" * 70)

    # 1. Check API Key
    try:
        api_key = get_api_key()
        masked_key = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
        print(f"[OK] Gemini API Key detected: {masked_key}")
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("\nPlease set your GEMINI_API_KEY environment variable before running this script:")
        print("  Windows PowerShell: $env:GEMINI_API_KEY=\"your_key_here\"")
        print("  Linux/macOS:        export GEMINI_API_KEY=\"your_key_here\"")
        sys.exit(1)

    # 2. Determine file paths
    default_img, default_audio = create_sample_files()
    image_path = args.image or default_img
    audio_path = args.audio or default_audio

    # 3. Vision Extraction Demo
    print("\n" + "-" * 70)
    print(f"[*] Running Vision Extraction (License OCR) on: {image_path}")
    print(f"[*] Model: {args.model}")
    print("-" * 70)
    try:
        license_result = extract_license_data(image_path=image_path, model=args.model)
        print("\n[SUCCESS] Extracted License Data (Pydantic Model Output):")
        print(license_result.model_dump_json(indent=2))
    except Exception as err:
        print(f"[FAILED] Vision extraction encountered error: {err}")

    # 4. Audio Extraction Demo
    print("\n" + "-" * 70)
    print(f"[*] Running Multilingual Audio Extraction on: {audio_path}")
    print(f"[*] Model: {args.model}")
    print("-" * 70)
    try:
        audio_result = extract_audio_story(audio_path=audio_path, model=args.model)
        print("\n[SUCCESS] Extracted Audio Story (Pydantic Model Output):")
        print(audio_result.model_dump_json(indent=2))
    except Exception as err:
        print(f"[FAILED] Audio extraction encountered error: {err}")

    print("\n" + "=" * 70)
    print("      LIVE EXTRACTION DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
