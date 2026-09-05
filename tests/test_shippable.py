"""
Shippable Hygiene and Keyless Replay Verification Suite.
Validates that the repository conforms to hackathon shippable criteria:
1. README documents core principles, prototype grid, provenance, and keyless execution.
2. Keyless replay script runs reliably without API keys and outputs deterministic scores.
3. Redundant specification files are completely removed from repository root.
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_readme_contains_required_sections():
    """Assert README contains all required architectural and transparency sections."""
    readme_path = PROJECT_ROOT / "README.md"
    assert readme_path.exists(), "README.md must exist in root directory"

    content = readme_path.read_text(encoding="utf-8")

    assert "Code owns the numbers" in content, "README must include core principle 'Code owns the numbers'"
    assert "ALPHAX Internal Prototype" in content, "README must explicitly label the ALPHAX Internal Prototype grid"
    assert "Provenance" in content, "README must document the Provenance Ledger"
    assert "Keyless Demo" in content, "README must document the Keyless Demo execution instructions"


def test_keyless_demo_script_runs():
    """
    Execute python scripts/run_keyless_demo.py in a clean environment without API keys.
    Assert that it exits with code 0 and prints the deterministic score.
    """
    script_path = PROJECT_ROOT / "scripts" / "run_keyless_demo.py"
    assert script_path.exists(), f"Keyless demo script must exist at {script_path}"

    env = os.environ.copy()
    # Strip any active API keys to verify genuine keyless execution
    env.pop("GOOGLE_API_KEY", None)
    env.pop("GEMINI_API_KEY", None)

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        env=env,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    assert proc.returncode == 0, f"Demo script failed with exit code {proc.returncode}:\n{proc.stderr}"
    assert "Total Score" in proc.stdout, "Demo script output must include 'Total Score'"
    assert "KEYLESS DETERMINISTIC REPLAY SUCCESSFUL" in proc.stdout


def test_no_duplicate_specs_exist():
    """Assert that duplicate/redundant specification documents are not in repository root."""
    spec_a = PROJECT_ROOT / "project details.md"
    spec_b = PROJECT_ROOT / "project_details.md"
    figma_dir = PROJECT_ROOT / "docs" / "figma_screenshots"

    assert not spec_a.exists(), f"Duplicate file '{spec_a.name}' must not exist in repository root"
    assert not spec_b.exists(), f"Duplicate file '{spec_b.name}' must not exist in repository root"
    assert not figma_dir.exists(), f"Unnecessary design folder '{figma_dir}' must not exist in docs/"
