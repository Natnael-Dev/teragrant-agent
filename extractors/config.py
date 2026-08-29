"""
Configuration and Client Factory for Google Gemini API.
Includes Client Timeout Cap and Smart Error-Class Failover / Fallback Chain.
"""

import json
import os
import socket
import time
from typing import Optional, Any, Tuple, List, Dict
from dotenv import load_dotenv
import httpx
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

# Fallback chain for automatic failover when a model returns 404 / retired / quota exceeded
MODEL_FALLBACK_CHAIN: List[str] = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-2.5-pro",
    "gemini-3.1-pro-preview",
]


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
    Initializes and returns a Google GenAI Client instance with a hard 30-second timeout cap
    (http_options timeout=30000 ms) and explicitly forced v1 API version.
    """
    effective_key = api_key or get_api_key()
    # CRITICAL: Force v1 API version to avoid v1beta 404 errors with standard model names
    http_opts = types.HttpOptions(timeout=30000, api_version="v1")
    return genai.Client(api_key=effective_key, http_options=http_opts)


def is_network_error(err: Exception) -> bool:
    """
    Classifies whether an exception is a transport/network layer failure
    (e.g., TCP timeout, DNS resolution failure, connection reset/refused, WinError 10060, httpx network/timeout error).
    """
    if isinstance(err, (
        TimeoutError,
        ConnectionError,
        socket.timeout,
        socket.gaierror,
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
    )):
        return True

    if isinstance(err, OSError):
        win_err = getattr(err, "winerror", None)
        if win_err in (10060, 10061, 10054, 10051, 10065, 10053):
            return True
        err_no = getattr(err, "errno", None)
        if err_no in (110, 111, 101, 104):
            return True

    err_str = str(err).lower()
    network_indicators = [
        "10060",
        "winerror 10060",
        "wsaetimedout",
        "timed out",
        "timeout",
        "connection error",
        "connection refused",
        "connection reset",
        "network unreachable",
        "name or service not known",
        "getaddrinfo failed",
        "failed to establish a new connection",
        "max retries exceeded",
        "transport error",
        "connecterror",
        "readtimeout",
    ]
    if any(ind in err_str for ind in network_indicators):
        return True

    # Check wrapped causes
    if err.__cause__ and is_network_error(err.__cause__):
        return True
    if err.__context__ and is_network_error(err.__context__):
        return True

    return False


def call_gemini_with_fallback(
    client: Any,
    model: Optional[str],
    contents: Any,
    config: Any,
) -> Tuple[Any, str]:
    """
    Executes client.models.generate_content with smart error-class failover:
    - Automatically walks MODEL_FALLBACK_CHAIN candidates on failure.
    - Captures and surfaces granular error details across every model candidate.
    - If it's a network error, retries ONCE on the SAME model, then moves to next.
    - If it's a 404 / 429 / not found / quota / deprecation, walks the MODEL_FALLBACK_CHAIN candidates.

    Args:
        client: The initialized genai.Client instance.
        model: Optional requested model name. Defaults to MODEL_FALLBACK_CHAIN[0].
        contents: Input parts (text, image, audio).
        config: GenerateContentConfig.

    Returns:
        Tuple[Any, str]: (response object, model_name_used)
    """
    candidates = [str(model)] if model else []
    for m in MODEL_FALLBACK_CHAIN:
        if m not in candidates:
            candidates.append(m)

    errors: Dict[str, str] = {}
    for candidate in candidates:
        try:
            # Force string conversion of model name
            response = client.models.generate_content(
                model=str(candidate),
                contents=contents,
                config=config,
            )
            return response, candidate
        except Exception as err:
            errors[str(candidate)] = str(err)
            err_str = str(err).lower()

            # If it's a network error, retry ONCE on the SAME model, then move to next
            if is_network_error(err):
                time.sleep(1)
                try:
                    retry_resp = client.models.generate_content(
                        model=str(candidate),
                        contents=contents,
                        config=config,
                    )
                    return retry_resp, candidate
                except Exception as retry_err:
                    errors[f"{candidate}_retry"] = str(retry_err)
                    continue  # Move to next model in chain

            # If it's a 404, 429, not found, unsupported, deprecated, or quota error, log and move to next
            if any(k in err_str for k in ("404", "429", "not found", "is not supported", "quota", "deprecated", "resource_exhausted", "permission_denied", "403", "invalid_argument", "400")):
                continue

    # If we get here, ALL models failed.
    raise RuntimeError(f"All models failed. Details: {json.dumps(errors)}")
