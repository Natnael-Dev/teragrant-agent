"""
Runtime Smoke-Test Gate for Streamlit UI.
Executes the Streamlit application file using AppTest to catch any NameError, AttributeError,
ImportError, or layout bugs that py_compile cannot detect.
"""

import os
from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_app_boots_without_runtime_errors():
    os.environ.setdefault("GEMINI_API_KEY", "smoke-test-key")
    app_path = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.run()
    assert not at.exception, f"Streamlit app raised at runtime: {at.exception}"
