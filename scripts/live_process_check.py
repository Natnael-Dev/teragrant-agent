"""
Live End-to-End Proof for Batch 33F: Multimodal Document Extraction & Digital Twin Mapping.
Posts REAL files to /api/transcribe and /api/process via FastAPI TestClient against live Gemini API.
"""

import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.server import app, SESSION

def main():
    print("=" * 70)
    print("BATCH 33F: LIVE MULTIMODAL INTAKE & DIGITAL TWIN PROOF")
    print("=" * 70)

    client = TestClient(app)

    # 1. Step 1: Voice transcription (optional but sets up session context)
    voice_path = PROJECT_ROOT / "data" / "proof_voice.mp3"
    if voice_path.exists():
        print(f"\n[1/3] Uploading audio note: {voice_path.name} ({voice_path.stat().st_size} bytes)...")
        with open(voice_path, "rb") as f:
            voice_resp = client.post(
                "/api/transcribe",
                files={"audio": ("proof_voice.mp3", f, "audio/mpeg")},
                data={"lang": "en"}
            )
        print(f"Status: {voice_resp.status_code}")
        v_data = voice_resp.json()
        print(f"Transcript: {v_data.get('transcript', '')[:90]}...")
        print(f"Fact Chips: {v_data.get('chips', [])}")
    else:
        print(f"Warning: {voice_path} not found.")

    # 2. Step 2: Upload Documents (/api/process)
    lic_path = PROJECT_ROOT / "data" / "test_assets" / "license_clean.png"
    if not lic_path.exists():
        lic_path = PROJECT_ROOT / "data" / "test_assets" / "license_clean.jpg"

    work_path = PROJECT_ROOT / "data" / "test_assets" / "workshop_berbere.jpg"

    print(f"\n[2/3] Uploading Trade License & Workshop Photo to /api/process...")
    print(f" - License: {lic_path.name} ({lic_path.stat().st_size} bytes)")
    print(f" - Workshop: {work_path.name} ({work_path.stat().st_size} bytes)")

    with open(lic_path, "rb") as f_lic, open(work_path, "rb") as f_work:
        proc_resp = client.post(
            "/api/process",
            files={
                "license": (lic_path.name, f_lic, "image/png" if lic_path.suffix == ".png" else "image/jpeg"),
                "workshop": (work_path.name, f_work, "image/jpeg")
            },
            data={"use_preset": "false"}
        )

    print(f"Process Endpoint Response Status: {proc_resp.status_code}")
    res_json = proc_resp.json()
    print("Process Response JSON:", res_json)

    # 3. Verify Session State & Extractions
    lic_extracted = SESSION.get("license_data")
    work_extracted = SESSION.get("workshop_data")
    twin_data = SESSION.get("digital_twin_data")
    pack_res = SESSION.get("pack_res")
    prov = SESSION.get("pack_res").provenance if SESSION.get("pack_res") else {}

    print("\n" + "=" * 70)
    print("EXTRACTION RESULTS SUMMARY:")
    print("=" * 70)
    
    print("\n--- [LICENSE EXTRACTION] ---")
    if lic_extracted:
        print(f"  TIN Number:      {lic_extracted.tin_number}")
        print(f"  Owner Name:      {lic_extracted.owner_name}")
        print(f"  Business Name:   {lic_extracted.business_name}")
        print(f"  Location:        {lic_extracted.location}")
        print(f"  Issue Date:      {lic_extracted.registration_date}")
        print(f"  Is Legible:      {lic_extracted.is_legible}")
    else:
        print("  None")

    print("\n--- [WORKSHOP EXTRACTION] ---")
    if work_extracted:
        print(f"  Estimated People:{work_extracted.estimated_people_present}")
        print(f"  Machinery Items: {work_extracted.visible_machinery}")
        print(f"  Safety Notes:    {work_extracted.workplace_safety_observations[:80]}...")
        print(f"  Is Legible:      {work_extracted.is_legible}")
    else:
        print("  None")

    print("\n--- [SYNTHESIZED DIGITAL TWIN] ---")
    if twin_data:
        for k, v in twin_data.items():
            print(f"  {k:20}: {v}")

    print("\n--- [PROVENANCE LEDGER] ---")
    for field_path, p in prov.items():
        print(f"  {field_path:30} -> Val: {p.value} | Status: {p.status.value} | Conf: {p.confidence} | Src: {p.source_type}")

    # 4. Mandatory Assertions
    print("\n" + "=" * 70)
    print("RUNNING MANDATORY TRUTH ASSERTIONS:")
    print("=" * 70)

    assert lic_extracted is not None, "License extraction must succeed"
    assert lic_extracted.tin_number == "0045678901", f"Expected TIN '0045678901', got '{lic_extracted.tin_number}'"
    print("✓ ASSERTION PASSED: tin_number == '0045678901'")

    assert lic_extracted.owner_name and "Dexter" in lic_extracted.owner_name, f"Expected owner containing 'Dexter', got '{lic_extracted.owner_name}'"
    print(f"✓ ASSERTION PASSED: owner contains 'Dexter' ('{lic_extracted.owner_name}')")

    assert lic_extracted.business_name and "Spice Mill" in lic_extracted.business_name, f"Expected business name containing 'Spice Mill', got '{lic_extracted.business_name}'"
    print(f"✓ ASSERTION PASSED: trade name contains 'Spice Mill' ('{lic_extracted.business_name}')")

    assert lic_extracted.location and "Bekoji" in lic_extracted.location, f"Expected location containing 'Bekoji', got '{lic_extracted.location}'"
    print(f"✓ ASSERTION PASSED: location contains 'Bekoji' ('{lic_extracted.location}')")

    assert work_extracted is not None, "Workshop extraction must succeed"
    assert isinstance(work_extracted.estimated_people_present, int) and work_extracted.estimated_people_present > 0, f"Expected people int > 0, got {work_extracted.estimated_people_present}"
    print(f"✓ ASSERTION PASSED: workshop people estimate is int > 0 ({work_extracted.estimated_people_present})")

    assert twin_data["tin_number"] == "0045678901", "Twin tin_number matches"
    assert "Dexter Spice Mill" in str(twin_data["company_name"]), "Twin company name matches"
    assert "Bekoji" in str(twin_data["location"]), "Twin location matches"
    print("✓ ALL ASSERTIONS PASSED! End-to-end zero-fabrication extraction verified.")

if __name__ == "__main__":
    main()
