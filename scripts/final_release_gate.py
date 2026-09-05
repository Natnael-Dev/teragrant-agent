#!/usr/bin/env python3
"""
ALPHAX / TeraGrant V2 — Final Automated Release Gate.
Performs an end-to-end audit of test suites, offline replay capability,
repository hygiene, and hardcoded credential exposure.

Exit Code:
  0: All release checks passed (V2 APPROVED)
  1: One or more checks failed (RELEASE BLOCKED)
"""

import os
import sys
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ASCII_SUCCESS_BANNER = """
==============================================================================
   ████████╗███████╗██████╗  █████╗  ██████╗ ██████╗  █████╗ ███╗   ██╗████████╗
   ╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔════╝ ██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝
      ██║   █████╗  ██████╔╝███████║██║  ███╗██████╔╝███████║██╔██╗ ██║   ██║   
      ██║   ██╔══╝  ██╔══██╗██╔══██║██║   ██║██╔══██╗██╔══██║██║╚██╗██║   ██║   
      ██║   ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║██║  ██║██║ ╚████║   ██║   
      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   
------------------------------------------------------------------------------
                  ✅ ALPHAX V2 RELEASE APPROVED
------------------------------------------------------------------------------
   All automated audits passed:
   ✔ Full Pytest Regression Suite: 0 Failures
   ✔ Keyless Deterministic Replay: Exit Code 0
   ✔ Repository Cleanliness & Spec De-duplication: Verified
   ✔ Static Credential & Secret Exposure Audit: Clean
==============================================================================
"""

ASCII_FAILURE_BANNER = """
==============================================================================
   ❌ RELEASE BLOCKED — ONE OR MORE AUDIT CRITERIA FAILED
==============================================================================
"""


def log_step(msg: str):
    print(f"\n[GATE-CHECK] {msg}")


def check_pytest_suite() -> bool:
    log_step("Executing Full Pytest Suite (pytest -q)...")
    env = os.environ.copy()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)

    if proc.returncode != 0:
        print(f"[FAIL] Pytest exited with code {proc.returncode}")
        return False

    if "failed" in proc.stdout.lower() or "error" in proc.stdout.lower():
        # Check if there are failures reported
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        last_line = lines[-1] if lines else ""
        if "failed" in last_line.lower() or "error" in last_line.lower():
            print(f"[FAIL] Failures detected in pytest summary: {last_line}")
            return False

    print("[PASS] Full Pytest suite passed with 0 failures.")
    return True


def check_keyless_demo() -> bool:
    log_step("Verifying Keyless Replay Script (python scripts/run_keyless_demo.py)...")
    script_path = PROJECT_ROOT / "scripts" / "run_keyless_demo.py"
    if not script_path.exists():
        print(f"[FAIL] Missing demo script: {script_path}")
        return False

    # Run in sterile environment without API keys
    env = os.environ.copy()
    env.pop("GOOGLE_API_KEY", None)
    env.pop("GEMINI_API_KEY", None)

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    print(proc.stdout)
    if proc.returncode != 0:
        print(f"[FAIL] Keyless demo exited with code {proc.returncode}")
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        return False

    if "Total Score" not in proc.stdout:
        print("[FAIL] 'Total Score' missing from demo script output")
        return False

    print("[PASS] Keyless replay succeeded without API keys.")
    return True


def check_repository_hygiene() -> bool:
    log_step("Auditing Repository Cleanliness & Spec De-duplication...")
    forbidden_items = [
        PROJECT_ROOT / "project details.md",
        PROJECT_ROOT / "project_details.md",
        PROJECT_ROOT / "docs" / "figma_screenshots",
    ]

    for item in forbidden_items:
        if item.exists():
            print(f"[FAIL] Forbidden redundant item found: {item}")
            return False

    print("[PASS] Zero duplicate specs or legacy screenshot directories detected.")
    return True


def check_credential_exposure() -> bool:
    log_step("Auditing Python Source Files for Credential Leakage...")
    target_dirs = [
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "agents",
        PROJECT_ROOT / "extractors",
        PROJECT_ROOT / "schemas",
        PROJECT_ROOT / "scripts",
    ]

    # Regex patterns for Google Gemini keys or hardcoded secret assignments
    api_key_regex = re.compile(r"AIza[0-9A-Za-z_-]{35}")
    hardcoded_secret_regex = re.compile(r"""(?:api_key|apiKey|secret|token)\s*=\s*['"]([0-9a-zA-Z_-]{24,})['"]""")

    allowed_placeholders = {
        "your_gemini_api_key_here",
        "mock-gemini-offline",
        "offline-replay",
    }

    violations = []

    for d in target_dirs:
        if not d.exists():
            continue
        for py_file in d.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"[WARN] Unable to read {py_file}: {e}")
                continue

            # Check standard Gemini API key format
            matches = api_key_regex.findall(content)
            if matches:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: Found hardcoded Google API Key: {matches}")

            # Check general secret assignments
            for match in hardcoded_secret_regex.finditer(content):
                val = match.group(1)
                if val not in allowed_placeholders and not val.startswith("test_"):
                    violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: Potential hardcoded secret: '{val[:6]}...'")

    if violations:
        print("[FAIL] Credential scan identified potential leaks:")
        for v in violations:
            print(f"  - {v}")
        return False

    print("[PASS] Static credential audit clean; zero hardcoded secrets found.")
    return True


def main():
    print("=" * 78)
    print("          ALPHAX / TERAGRANT V2 — AUTOMATED RELEASE GATE AUDIT        ")
    print("=" * 78)

    checks = [
        ("Hygiene Audit", check_repository_hygiene),
        ("Credential Scan", check_credential_exposure),
        ("Keyless Replay", check_keyless_demo),
        ("Pytest Suite", check_pytest_suite),
    ]

    for name, check_fn in checks:
        if not check_fn():
            print(ASCII_FAILURE_BANNER)
            print(f"Audit failed at phase: {name}")
            sys.exit(1)

    print(ASCII_SUCCESS_BANNER)
    sys.exit(0)


if __name__ == "__main__":
    main()
