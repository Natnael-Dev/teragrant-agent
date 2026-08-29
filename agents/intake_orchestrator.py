"""
Parallel Multimodal Intake Orchestrator.
Executes voice, license OCR, and workshop computer vision extractions concurrently
using ThreadPoolExecutor, recording granular latency timings and handling errors gracefully.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, Dict, Any

from extractors.audio_extractor import extract_audio_story
from extractors.vision_extractor import extract_license_data
from extractors.workshop_extractor import extract_workshop_data
from extractors.schemas import AudioTranscriptExtraction, LicenseExtraction, WorkshopExtraction
from schemas.gap_schema import Gap, GapPriority


def run_intake_parallel(
    voice_path: Optional[str] = None,
    license_path: Optional[str] = None,
    workshop_path: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> Tuple[
    Optional[AudioTranscriptExtraction],
    Optional[LicenseExtraction],
    Optional[WorkshopExtraction],
    Dict[str, float],
    list[Gap],
]:
    """
    Runs audio, license, and workshop extractions concurrently.
    Returns (audio_data, license_data, workshop_data, timings_dict, failure_gaps).
    """
    timings: Dict[str, float] = {
        "audio_seconds": 0.0,
        "license_seconds": 0.0,
        "workshop_seconds": 0.0,
        "total_parallel_seconds": 0.0,
    }
    failure_gaps: list[Gap] = []

    audio_res: Optional[AudioTranscriptExtraction] = None
    license_res: Optional[LicenseExtraction] = None
    workshop_res: Optional[WorkshopExtraction] = None

    def _extract_audio():
        nonlocal audio_res
        if not voice_path:
            return
        t0 = time.time()
        try:
            audio_res = extract_audio_story(audio_path=voice_path, model=model, api_key=api_key, client=client)
        except Exception as e:
            failure_gaps.append(
                Gap(
                    field_name="audio_voice_note",
                    reason_missing=f"Audio intake failed or was unavailable: {str(e)}",
                    required_from="Applicant",
                    priority=GapPriority.HIGH,
                )
            )
        finally:
            timings["audio_seconds"] = round(time.time() - t0, 2)

    def _extract_license():
        nonlocal license_res
        if not license_path:
            return
        t0 = time.time()
        try:
            license_res = extract_license_data(image_path=license_path, model=model, api_key=api_key, client=client)
        except Exception as e:
            failure_gaps.append(
                Gap(
                    field_name="trade_license_document",
                    reason_missing=f"Trade license extraction failed or was unreadable: {str(e)}",
                    required_from="Applicant",
                    priority=GapPriority.HIGH,
                )
            )
        finally:
            timings["license_seconds"] = round(time.time() - t0, 2)

    def _extract_workshop():
        nonlocal workshop_res
        if not workshop_path:
            return
        t0 = time.time()
        try:
            workshop_res = extract_workshop_data(image_path=workshop_path, model=model, api_key=api_key, client=client)
        except Exception as e:
            failure_gaps.append(
                Gap(
                    field_name="workshop_facility_photo",
                    reason_missing=f"Workshop facility photo extraction failed: {str(e)}",
                    required_from="Site Visit / Applicant",
                    priority=GapPriority.LOW,
                )
            )
        finally:
            timings["workshop_seconds"] = round(time.time() - t0, 2)

    t_start = time.time()
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_audio = executor.submit(_extract_audio)
        f_lic = executor.submit(_extract_license)
        f_work = executor.submit(_extract_workshop)

        f_audio.result()
        f_lic.result()
        f_work.result()

    timings["total_parallel_seconds"] = round(time.time() - t_start, 2)
    return audio_res, license_res, workshop_res, timings, failure_gaps
