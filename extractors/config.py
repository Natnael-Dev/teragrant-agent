"""
Configuration and Client Factory for Google Gemini API.
Includes Model Fallback Chain for 404/Retired Model resilience.
"""

import os
from typing import Optional, Any, Tuple, List
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

# Fallback chain for automatic failover when a model returns 404 / retired
MODEL_FALLBACK_CHAIN: List[str] = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]


def get_api_key() -> str:
    """
    Retrieves the Gemini API key from environment variables.
    Checks GEMINI_API_KEY and GOOGLE_API_KEY.
    """
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError(
            "Gemini API key is not configured. "
            "Please set GEMINI_API_KEY or GOOGLE_API_KEY in your environment or .env file."
        )
    return key


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """
    Initializes and returns a Google GenAI Client instance.
    """
    effective_key = api_key or get_api_key()
    return genai.Client(api_key=effective_key)


def call_gemini_with_fallback(
    client: Any,
    model: Optional[str],
    contents: Any,
    config: Any,
) -> Tuple[Any, str]:
    """
    Executes client.models.generate_content with automatic 404/NotFound failover
    across the MODEL_FALLBACK_CHAIN.

    Args:
        client: The initialized genai.Client instance.
        model: Optional requested model name. Defaults to MODEL_FALLBACK_CHAIN[0].
        contents: Input parts (text, image, audio).
        config: GenerateContentConfig.

    Returns:
        Tuple[Any, str]: (response object, model_name_used)
    """
    primary_model = model or MODEL_FALLBACK_CHAIN[0]
    
    # Build candidate model list with primary first, followed by remaining fallback chain
    candidates = [primary_model]
    for fallback_m in MODEL_FALLBACK_CHAIN:
        if fallback_m not in candidates:
            candidates.append(fallback_m)

    last_err: Optional[Exception] = None
    for candidate in candidates:
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=contents,
                config=config,
            )
            return response, candidate
        except Exception as err:
            err_str = str(err).lower()
            last_err = err
            # Check for 404 / NotFound / Model not found
            if "404" in err_str or "not found" in err_str or "not_found" in err_str or "is not supported" in err_str:
                continue
            # For other non-404 errors on the first attempt, also try the next model just in case of model-specific failure
            continue

    if last_err:
        raise last_err
    raise RuntimeError("Failed to generate content across all fallback models.")
