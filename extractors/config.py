"""
Configuration and API client management for Gemini models.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()


def get_api_key() -> str:
    """
    Retrieve the Gemini API key from environment variables.
    Checks GEMINI_API_KEY first, then GOOGLE_API_KEY.
    Raises ValueError with actionable instructions if missing.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "Gemini API key is not configured! Please set GEMINI_API_KEY in your environment "
            "or in a .env file at the project root."
        )
    return api_key


def get_gemini_client(api_key: Optional[str] = None):
    """
    Instantiate and return a google-genai Client.
    """
    from google import genai

    key = api_key or get_api_key()
    return genai.Client(api_key=key)
