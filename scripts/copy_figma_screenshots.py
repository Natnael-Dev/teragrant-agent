"""
Script to collect and organize all Figma screenshots into docs/figma_screenshots/
"""

import os
import shutil
from pathlib import Path

SOURCE_DIRS = [
    Path(r"C:\Users\HP\.gemini\antigravity-ide\brain\1356f8ec-29cb-44e1-9ea0-ba42fea421fa\.user_uploaded"),
    Path(r"C:\Users\HP\.gemini\antigravity-ide\brain\1356f8ec-29cb-44e1-9ea0-ba42fea421fa\.tempmediaStorage"),
]

DEST_DIR = Path(r"c:\Users\HP\OneDrive\Desktop\AI Hackaton\docs\figma_screenshots")
DEST_DIR.mkdir(parents=True, exist_ok=True)

# Collect all files
files = []
for src in SOURCE_DIRS:
    if src.exists():
        for f in src.glob("*.png"):
            files.append(f)

# Sort by name / timestamp
files.sort(key=lambda x: x.name)

print(f"Found {len(files)} screenshot files.")

# Screen mapping based on conversation history & screen definitions
SCREEN_NAMES = {
    "media_1788029685168.png": "00_ui_style_reference.png",
    "media_1788035672006.png": "01_home_screen_en.png",
    "media_1788035992953.png": "02_step1_tell_story_recording.png",
    "media_1788036051522.png": "03_step1_tell_story_extracted.png",
    "media_1788036186733.png": "04_step2_upload_evidence.png",
    "media_1788036325018.png": "05_step3_review_application.png",
    "media_1788036677216.png": "06_step4_gaps_and_contradictions.png",
    "media_1788036687437.png": "07_step5_declarations_consent.png",
    "media_1788036822436.png": "08_step6_readiness_pack_download.png",
    "media_1788036942848.png": "09_reviewer_dashboard_kpis_shortlist.png",
    "media_1788036973454.png": "10_reviewer_committee_defense_modal.png",
    "media_1788038431706.png": "11_home_screen_rendered_verify.png",
    "media_1788039477666.png": "12_home_screen_live_audit.png",
}

for f in files:
    # 1. Copy with original filename
    dest_orig = DEST_DIR / f.name
    shutil.copy2(f, dest_orig)
    
    # 2. Copy with mapped readable name if mapped
    readable_name = SCREEN_NAMES.get(f.name)
    if readable_name:
        dest_readable = DEST_DIR / readable_name
        shutil.copy2(f, dest_readable)
        print(f"Copied {f.name} -> {readable_name}")
    else:
        print(f"Copied {f.name}")

print("\nDone! All Figma screenshots organized in docs/figma_screenshots/")
