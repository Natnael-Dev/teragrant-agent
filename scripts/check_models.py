import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from extractors.config import get_gemini_client


def main():
    print("🔍 Testing Gemini API Connection...")
    try:
        client = get_gemini_client()
        print("✅ Client initialized successfully.")
        print("📋 Fetching available models...")
        models = list(client.models.list())
        print(f"✅ Found {len(models)} models. First 10:")
        for i, m in enumerate(models):
            if i >= 10:
                break
            print(f"  - {m.name}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
