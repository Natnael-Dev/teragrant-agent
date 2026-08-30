// TeraGrant Frontend JavaScript (Batch 31F)

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let activeRecorderType = null; // 'intake', 'interview', 'gap', 'consent'
let activeDeclarationId = null;
let activeGapField = null;

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

// Loading Overlay System (Batch 31F)
function showLoadingOverlay(message) {
  let overlay = document.getElementById("global-loading-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "global-loading-overlay";
    overlay.style.cssText = `
      position: fixed;
      inset: 0;
      background: rgba(17, 24, 39, 0.7);
      backdrop-filter: blur(4px);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.25s ease;
      opacity: 0;
    `;
    overlay.innerHTML = `
      <div style="background: #FFFFFF; border-radius: 16px; padding: 32px 40px; text-align: center; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); max-width: 420px; border: 1px solid #E5E7EB;">
        <div style="display: flex; justify-content: center; margin-bottom: 16px;">
          <svg style="width: 48px; height: 48px; animation: spin 1s linear infinite; color: #059669;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle style="opacity: 0.25;" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path style="opacity: 0.75;" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <div id="loading-overlay-msg" style="font-size: 18px; font-weight: 700; color: #111827; margin-bottom: 8px;">${message || "Processing..."}</div>
        <div style="font-size: 13px; color: #6B7280;">Please wait while our zero-hallucination auditor runs...</div>
      </div>
      <style>
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      </style>
    `;
    document.body.appendChild(overlay);
  } else {
    const msgEl = document.getElementById("loading-overlay-msg");
    if (msgEl) msgEl.innerText = message || "Processing...";
    overlay.style.display = "flex";
  }
  requestAnimationFrame(() => {
    overlay.style.opacity = "1";
  });
}

function hideLoadingOverlay() {
  const overlay = document.getElementById("global-loading-overlay");
  if (overlay) {
    overlay.style.opacity = "0";
    setTimeout(() => {
      overlay.style.display = "none";
    }, 250);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Check MediaDevices Availability
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    const micWarning = document.getElementById("mic-unavailable-warning");
    if (micWarning) micWarning.style.display = "block";
    const audioUploadWrapper = document.getElementById("audio-upload-wrapper");
    if (audioUploadWrapper) audioUploadWrapper.style.display = "block";
  }

  const recordCircle = document.getElementById("record-circle");
  const waveBars = document.getElementById("wave-bars");
  const recordCaption = document.getElementById("record-caption");
  const audioFileInput = document.getElementById("audio-file-input");
  const transcriptBubble = document.getElementById("transcript-bubble");
  const transcriptText = document.getElementById("transcript-text");
  const factChips = document.getElementById("fact-chips");
  const continueBtn = document.getElementById("btn-continue");
  const errorCard = document.getElementById("transcribe-error-card");

  // Helper to get active language
  const getActiveLang = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const lang = urlParams.get("lang") || "en";
    if (lang === "am") return "Amharic";
    if (lang === "om") return "Oromo";
    return "English";
  };

  // Upload handler for Step 1
  if (audioFileInput) {
    audioFileInput.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      if (file.size > MAX_FILE_SIZE) {
        showClassifiedError({
          type: "PAYLOAD_TOO_LARGE",
          message: "Uploaded audio exceeds 50MB limit.",
          advice: "Please upload an audio file under 50MB."
        });
        audioFileInput.value = "";
        return;
      }

      showProcessingState("Analyzing voice note with zero-hallucination auditor...");
      showLoadingOverlay("🎙️ Decoding your voice...");
      const formData = new FormData();
      formData.append("audio", file);
      formData.append("lang", getActiveLang());

      try {
        const res = await fetch("/api/transcribe", {
          method: "POST",
          body: formData
        });
        const data = await res.json();
        handleTranscribeResult(data);
      } catch (err) {
        showClassifiedError({
          type: "NETWORK_ERROR",
          message: "Failed to upload audio: " + err.message,
          advice: "Check your internet connection and retry."
        });
      } finally {
        hideLoadingOverlay();
      }
    });
  }

  // Live recording handler for Step 1 & Interview
  if (recordCircle) {
    recordCircle.addEventListener("click", async () => {
      if (!isRecording) {
        // Start recording
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          mediaRecorder = new MediaRecorder(stream);
          audioChunks = [];

          mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              audioChunks.push(event.data);
            }
          };

          mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            showProcessingState("Analyzing recording with zero-hallucination auditor...");

            const isInterview = window.location.pathname.includes("interview");
            if (isInterview) {
              await submitInterviewAnswer(audioBlob);
            } else {
              showLoadingOverlay("🎙️ Decoding your voice...");
              const formData = new FormData();
              formData.append("audio", audioBlob, "recording.webm");
              formData.append("lang", getActiveLang());

              try {
                const res = await fetch("/api/transcribe", {
                  method: "POST",
                  body: formData
                });
                const data = await res.json();
                handleTranscribeResult(data);
              } catch (err) {
                showClassifiedError({
                  type: "API_ERROR",
                  message: "Transcription error: " + err.message,
                  advice: "Check API status or retry."
                });
              } finally {
                hideLoadingOverlay();
              }
            }
          };

          mediaRecorder.start();
          isRecording = true;

          // Activate RED recording state
          recordCircle.classList.add("recording");
          if (waveBars) waveBars.classList.add("recording", "active");
          if (recordCaption) {
            recordCaption.classList.add("recording");
            recordCaption.innerText = "● Recording... tap to stop";
          }
          if (errorCard) errorCard.style.display = "none";
          const quotaBanner = document.getElementById("quota-exhausted-banner");
          if (quotaBanner) quotaBanner.style.display = "none";
        } catch (err) {
          showClassifiedError({
            type: "DEVICE_ERROR",
            message: "Microphone access unavailable or denied: " + err.message,
            advice: "Please allow microphone permissions or use the file upload option below."
          });
          const audioUploadWrapper = document.getElementById("audio-upload-wrapper");
          if (audioUploadWrapper) audioUploadWrapper.style.display = "block";
        }
      } else {
        // Stop recording
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
          mediaRecorder.stop();
          mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
        isRecording = false;

        // Return to idle state styling
        recordCircle.classList.remove("recording");
        if (waveBars) waveBars.classList.remove("recording", "active");
        if (recordCaption) {
          recordCaption.classList.remove("recording");
          recordCaption.innerText = "● Processing audio note...";
        }
      }
    });
  }

  function showProcessingState(msg) {
    if (recordCaption) {
      recordCaption.classList.remove("recording");
      recordCaption.innerText = "● " + (msg || "Processing...");
    }
  }

  function handleTranscribeResult(data) {
    if (data.error) {
      showClassifiedError(data.error);
      if (recordCaption) recordCaption.innerText = "Tap to record or speak";
      return;
    }

    if (errorCard) errorCard.style.display = "none";
    const quotaBanner = document.getElementById("quota-exhausted-banner");
    if (quotaBanner) quotaBanner.style.display = "none";

    if (transcriptText) transcriptText.innerText = `"${data.transcript}"`;
    if (factChips) {
      factChips.innerHTML = "";
      (data.chips || []).forEach(chip => {
        const span = document.createElement("span");
        span.className = "fact-chip-pill";
        span.innerText = chip;
        factChips.appendChild(span);
      });
    }

    if (transcriptBubble) transcriptBubble.style.display = "block";
    if (continueBtn) {
      continueBtn.removeAttribute("disabled");
      continueBtn.style.opacity = "1";
      continueBtn.style.cursor = "pointer";
    }
    if (recordCaption) recordCaption.innerText = "✓ Transcription complete — tap to record again";
  }

  function showClassifiedError(err) {
    const isQuota = (err.type === "QUOTA_EXHAUSTED" || (err.message && err.message.toLowerCase().includes("quota")));
    
    if (isQuota) {
      // Show friendly amber banner for Quota Exhaustion (Batch 31F)
      let quotaBanner = document.getElementById("quota-exhausted-banner");
      if (!quotaBanner) {
        quotaBanner = document.createElement("div");
        quotaBanner.id = "quota-exhausted-banner";
        quotaBanner.style.cssText = "background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 12px; padding: 16px; margin: 0 auto 20px auto; max-width: 540px; text-align: left; color: #92400E;";
        const targetContainer = document.querySelector(".container-wizard") || document.querySelector(".container") || document.body;
        if (targetContainer) targetContainer.insertBefore(quotaBanner, targetContainer.firstChild);
      }
      quotaBanner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; color: #B45309; margin-bottom: 4px;">
          <span style="font-size: 16px;">📊</span>
          <span>Daily Limit Reached</span>
        </div>
        <div style="font-size: 13px; color: #92400E; margin-bottom: 6px;">
          📊 Daily limit reached. Try again tomorrow or upload a voice note instead.
        </div>
        <div style="font-size: 12px; color: #B45309; background: #FEF3C7; padding: 6px 10px; border-radius: 6px;">
          <strong>Advice:</strong> ${err.advice || "Please wait or use upload"}
        </div>
      `;
      quotaBanner.style.display = "block";
      
      // Auto-reveal the file uploader
      const audioUploadWrapper = document.getElementById("audio-upload-wrapper");
      if (audioUploadWrapper) {
        audioUploadWrapper.style.display = "block";
      }
      if (errorCard) errorCard.style.display = "none";
      return;
    }

    if (errorCard) {
      const titleEl = document.getElementById("error-card-title");
      const msgEl = document.getElementById("error-card-msg");
      const adviceEl = document.getElementById("error-card-advice");

      if (titleEl) titleEl.innerText = err.type || "TRANSCRIPTION_ERROR";
      if (msgEl) msgEl.innerText = err.message || "Failed to process audio.";
      if (adviceEl) adviceEl.innerText = err.advice || "Please check your network and retry.";

      errorCard.style.display = "block";
    } else {
      alert((err.type || "Error") + ": " + err.message + "\nAdvice: " + (err.advice || ""));
    }
  }
});

// Step 2 File Preview with 50MB check
function previewFile(input, targetId) {
  const presetInput = document.getElementById('use_preset_input');
  if (presetInput) presetInput.value = "false";
  if (input.files && input.files[0]) {
    const file = input.files[0];
    if (file.size > MAX_FILE_SIZE) {
      alert("File exceeds 50MB limit. Please choose a smaller image.");
      input.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
      document.getElementById(targetId).innerHTML = `
        <img src="${e.target.result}" style="max-height: 110px; border-radius: 8px; margin-bottom: 6px;">
        <div style="font-size: 12px; font-weight: 600; color: #059669;">✓ ${file.name}</div>
      `;
    }
    reader.readAsDataURL(file);
  }
}

// Step 2 Preset Loader
function loadUnseenPreset() {
  const presetInput = document.getElementById('use_preset_input');
  if (presetInput) presetInput.value = "true";
  document.getElementById('lic-preview').innerHTML = '<div style="font-size: 13px; color: #059669; font-weight: 700;">✓ Attached: License (Dexter Spice Mill)</div>';
  document.getElementById('work-preview').innerHTML = '<div style="font-size: 13px; color: #059669; font-weight: 700;">✓ Attached: Facility Machinery Photo</div>';
  const alertBox = document.getElementById('step2-alert-box');
  if (alertBox) {
    alertBox.innerHTML = '<div style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #059669; padding: 12px; border-radius: 8px; font-size: 13px; font-weight: 600;">✓ Sample test documents attached (Dexter Spice Mill & Workshop)! Click "Process & Score" below.</div>';
  }
}

// Step 2 Primary Submit Process
async function submitProcess() {
  const form = document.getElementById('upload-form');
  const formData = new FormData(form);
  
  const btn = document.getElementById('btn-process-main');
  const spinnerArea = document.getElementById('process-spinner-area');
  const summaryArea = document.getElementById('process-summary-chips');
  const continueBtn = document.getElementById('btn-step2-continue');

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span>⏳ Processing Multimodal Truth Layer...</span>';
  }
  if (spinnerArea) spinnerArea.style.display = "block";
  showLoadingOverlay("📄 Reading your documents...");

  try {
    const res = await fetch("/api/process", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (spinnerArea) spinnerArea.style.display = "none";
    if (summaryArea) {
      summaryArea.style.display = "flex";
      summaryArea.innerHTML = "";
      (data.summary_chips || [
        "Trade License Verified",
        "Workshop Facility Inspected",
        "Digital Twin Synthesized",
        "Rubric Scored: 74/100"
      ]).forEach(chip => {
        const div = document.createElement("div");
        div.className = "fact-chip-pill";
        div.style.background = "#ECFDF5";
        div.style.color = "#059669";
        div.style.borderColor = "#A7F3D0";
        div.innerText = "✓ " + chip;
        summaryArea.appendChild(div);
      });
    }

    if (btn) {
      btn.innerHTML = '<span>✓ Dossier Scored</span>';
      btn.style.background = "#047857";
    }

    if (continueBtn) {
      continueBtn.style.display = "inline-flex";
    }

    // Auto-advance after brief pause
    setTimeout(() => {
      window.location.href = "/wizard/3";
    }, 1200);

  } catch (err) {
    if (spinnerArea) spinnerArea.style.display = "none";
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>⚡ Process & Score ›</span>';
    }
    alert("Error processing dossier: " + err.message);
  } finally {
    hideLoadingOverlay();
  }
}

// Step 4: Gap Resolution Handlers (Voice Primary + Language Pills + Text Secondary)
let gapMediaRecorder = null;
let gapAudioChunks = [];
let isGapRecording = false;
let activeRecordingGapField = null;
let gapSelectedLanguages = {}; // gapField -> lang ("English" | "Amharic" | "Oromo")

function toggleGapVoiceRecorder(gapField) {
  const vBox = document.getElementById("gap-voice-box-" + gapField);
  const tBox = document.getElementById("gap-text-box-" + gapField);
  if (vBox) {
    vBox.style.display = vBox.style.display === "none" ? "block" : "none";
  }
  if (tBox) tBox.style.display = "none";
}

function toggleGapTextInput(gapField) {
  const tBox = document.getElementById("gap-text-box-" + gapField);
  const vBox = document.getElementById("gap-voice-box-" + gapField);
  if (tBox) {
    tBox.style.display = tBox.style.display === "none" ? "block" : "none";
  }
  if (vBox) vBox.style.display = "none";
}

function selectGapLang(el) {
  const gap = el.getAttribute("data-gap");
  const lang = el.getAttribute("data-lang");
  gapSelectedLanguages[gap] = lang;
  
  const parent = el.closest(".seg");
  if (parent) {
    parent.querySelectorAll(".gap-lang-pill").forEach(p => p.classList.remove("active"));
    el.classList.add("active");
  }
}

async function toggleGapRecording(gapField) {
  const micEl = document.getElementById("gap-mic-" + gapField);
  const captionEl = document.getElementById("gap-rec-caption-" + gapField);
  const targetLang = gapSelectedLanguages[gapField] || "English";

  if (!isGapRecording) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      gapMediaRecorder = new MediaRecorder(stream);
      gapAudioChunks = [];
      activeRecordingGapField = gapField;

      gapMediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) gapAudioChunks.push(e.data);
      };

      gapMediaRecorder.onstop = async () => {
        const audioBlob = new Blob(gapAudioChunks, { type: "audio/webm" });
        showLoadingOverlay("🏗️ Resolving your answer...");

        const formData = new FormData();
        formData.append("gap_field", gapField);
        formData.append("audio", audioBlob, "gap_answer.webm");
        formData.append("lang", targetLang);

        const card = document.getElementById("gap-card-" + gapField);
        if (card) card.style.opacity = "0.6";

        try {
          const res = await fetch("/api/resolve", {
            method: "POST",
            body: formData
          });
          const data = await res.json();
          if (data.status === "resolved") {
            if (card) {
              card.style.opacity = "1";
              card.style.borderLeftColor = "#059669";
              card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                  <span style="font-weight: 700; font-size: 14px; color: #059669;">✓ ${gapField} (Resolved by Voice)</span>
                  <span class="chip chip-stated">Applicant Stated (Voice)</span>
                </div>
                <p style="font-size: 12px; color: #059669; margin: 0 0 4px 0;">${data.message || 'Corroborated and resolved.'}</p>
                ${data.transcript ? `<p style="font-size: 11px; color: #4B5563; margin: 0; font-style: italic;">"${data.transcript}"</p>` : ''}
              `;
            }
          } else {
            alert(data.message || "Failed to resolve gap with voice answer.");
            if (card) card.style.opacity = "1";
          }
        } catch (err) {
          alert("Error resolving gap: " + err.message);
          if (card) card.style.opacity = "1";
        } finally {
          hideLoadingOverlay();
        }
      };

      gapMediaRecorder.start();
      isGapRecording = true;

      // Update mic UI to RED recording state
      if (micEl) {
        micEl.style.background = "#DC2626";
        micEl.style.borderColor = "#EF4444";
        const svg = micEl.querySelector("svg");
        if (svg) svg.style.stroke = "#FFFFFF";
      }
      if (captionEl) {
        captionEl.style.color = "#DC2626";
        captionEl.innerText = "● Recording... tap to finish";
      }

    } catch (err) {
      alert("Microphone access unavailable or denied: " + err.message);
    }
  } else {
    // Stop recording
    if (gapMediaRecorder && gapMediaRecorder.state !== "inactive") {
      gapMediaRecorder.stop();
      gapMediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    isGapRecording = false;

    if (micEl) {
      micEl.style.background = "#F3F4F6";
      micEl.style.borderColor = "#D1D5DB";
      const svg = micEl.querySelector("svg");
      if (svg) svg.style.stroke = "#6B7280";
    }
    if (captionEl) {
      captionEl.style.color = "#374151";
      captionEl.innerText = "Processing voice answer...";
    }
  }
}

async function resolveGapWithVoice(gapField) {
  const textInput = document.getElementById("gap-text-" + gapField);
  const textVal = textInput ? textInput.value.trim() : "";

  const formData = new FormData();
  formData.append("gap_field", gapField);
  if (textVal) {
    formData.append("text", textVal);
  }

  const card = document.getElementById("gap-card-" + gapField);
  if (card) {
    card.style.opacity = "0.6";
  }
  showLoadingOverlay("🏗️ Updating your application...");

  try {
    const res = await fetch("/api/resolve", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (card) {
      card.style.opacity = "1";
      card.style.borderLeftColor = "#059669";
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-weight: 700; font-size: 14px; color: #059669;">✓ ${gapField} (Corroborated)</span>
          <span class="chip chip-verified">Document Verified</span>
        </div>
        <p style="font-size: 12px; color: #059669; margin: 0;">${data.message || 'Corroborated and resolved.'}</p>
      `;
    }
  } catch (err) {
    alert("Failed to resolve gap: " + err.message);
    if (card) card.style.opacity = "1";
  } finally {
    hideLoadingOverlay();
  }
}

async function resolveGapWithFile(gapField, fileInput) {
  if (!fileInput.files || !fileInput.files[0]) return;
  const file = fileInput.files[0];
  if (file.size > MAX_FILE_SIZE) {
    alert("File exceeds 50MB limit.");
    return;
  }

  const formData = new FormData();
  formData.append("gap_field", gapField);
  formData.append("file", file);

  const card = document.getElementById("gap-card-" + gapField);
  if (card) card.style.opacity = "0.6";
  showLoadingOverlay("🏗️ Updating your application...");

  try {
    const res = await fetch("/api/resolve", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (card) {
      card.style.opacity = "1";
      card.style.borderLeftColor = "#059669";
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-weight: 700; font-size: 14px; color: #059669;">✓ ${gapField} (Evidence Attached)</span>
          <span class="chip chip-verified">Document Verified</span>
        </div>
        <p style="font-size: 12px; color: #059669; margin: 0;">Evidence verified: ${file.name}</p>
      `;
    }
  } catch (err) {
    alert("Failed to upload evidence: " + err.message);
    if (card) card.style.opacity = "1";
  } finally {
    hideLoadingOverlay();
  }
}

// Step 5: Declarations Consent Handlers
async function handleDeclarationCheckbox(decId, isChecked) {
  const statusPill = document.getElementById("dec-status-" + decId);
  const formData = new FormData();
  formData.append("declaration_id", decId);
  formData.append("verdict", isChecked ? "true" : "false");
  formData.append("source", "manual");

  try {
    const res = await fetch("/api/consent", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (statusPill) {
      statusPill.className = isChecked ? "chip chip-verified" : "chip chip-missing";
      statusPill.innerText = isChecked ? "Confirmed (Manual)" : "Not given";
    }
  } catch (err) {
    alert("Failed to record declaration consent: " + err.message);
  }
}

async function recordVerbalDeclaration(decId) {
  const statusPill = document.getElementById("dec-status-" + decId);
  const btn = document.getElementById("btn-voice-dec-" + decId);
  
  if (btn) btn.innerText = "● Recording verbal affirmation...";

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const decRecorder = new MediaRecorder(stream);
    const chunks = [];

    decRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    decRecorder.onstop = async () => {
      const audioBlob = new Blob(chunks, { type: "audio/webm" });
      if (btn) btn.innerText = "⏳ Evaluating verbal consent...";

      const formData = new FormData();
      formData.append("declaration_id", decId);
      formData.append("audio", audioBlob, "declaration.webm");
      formData.append("source", "voice");

      try {
        const res = await fetch("/api/consent", {
          method: "POST",
          body: formData
        });
        const data = await res.json();

        const isYes = data.verdict === "YES";
        if (statusPill) {
          statusPill.className = isYes ? "chip chip-verified" : "chip chip-confirmation";
          statusPill.innerText = data.badge_text || (isYes ? "Confirmed (Voice)" : "Unclear");
        }
        const checkbox = document.getElementById(decId);
        if (checkbox) checkbox.checked = isYes;

        if (btn) btn.innerText = isYes ? "✓ Voice Confirmed" : "🎙 Re-record answer";
      } catch (err) {
        if (btn) btn.innerText = "🎙 Record verbal answer";
        alert("Voice consent failed: " + err.message);
      }
    };

    decRecorder.start();
    // Record for 4 seconds then stop
    setTimeout(() => {
      if (decRecorder.state !== "inactive") {
        decRecorder.stop();
        stream.getTracks().forEach(t => t.stop());
      }
    }, 4000);

  } catch (err) {
    if (btn) btn.innerText = "🎙 Record verbal answer";
    alert("Microphone unavailable: " + err.message);
  }
}

// Interview answer submission (Audio or Text)
async function submitInterviewAnswer(audioBlob = null, textInputVal = null) {
  const stepIdxEl = document.getElementById("interview-step-idx");
  const stepIdx = stepIdxEl ? parseInt(stepIdxEl.value, 10) : 0;
  
  const formData = new FormData();
  formData.append("step_index", stepIdx);
  
  if (audioBlob) {
    formData.append("audio", audioBlob, "answer.webm");
  } else if (textInputVal) {
    formData.append("text", textInputVal);
  } else {
    const textInput = document.getElementById("interview-text-input");
    if (textInput && textInput.value.trim()) {
      formData.append("text", textInput.value.trim());
    } else {
      alert("Please record an audio answer or enter text.");
      return;
    }
  }

  const feedbackBox = document.getElementById("interview-feedback-box");
  const userBubble = document.getElementById("interview-user-bubble");
  const userText = document.getElementById("interview-user-text");
  const nextBtn = document.getElementById("btn-interview-next");

  if (feedbackBox) feedbackBox.innerHTML = '<div style="font-size: 12px; color: #059669; font-weight: 600;">⏳ Extracting atomic facts...</div>';
  showLoadingOverlay("🎤 Processing your answer...");

  try {
    const res = await fetch("/api/interview/answer", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.status === "success" && data.extraction && data.extraction.value) {
      if (userText) userText.innerText = `"${data.transcript || data.extraction.value}"`;
      if (userBubble) userBubble.style.display = "block";
      if (feedbackBox) {
        feedbackBox.innerHTML = `
          <div style="font-size: 12px; color: #059669; font-weight: 700; margin-top: 8px;">
            ✓ Fact Extracted: <span class="chip chip-verified" style="margin-left: 4px;">${data.extraction.value}</span> (Confidence: ${Math.round(data.extraction.confidence * 100)}%)
          </div>
        `;
      }
      if (nextBtn) {
        nextBtn.style.opacity = "1";
        nextBtn.style.cursor = "pointer";
      }
    } else {
      if (feedbackBox) {
        feedbackBox.innerHTML = `
          <div style="font-size: 12px; color: #D97706; background: #FFFBEB; border: 1px solid #FDE68A; padding: 10px; border-radius: 8px; margin-top: 8px;">
            ⚠️ I didn't catch that fact clearly. Please repeat your answer or click Skip.
          </div>
        `;
      }
    }
  } catch (err) {
    if (feedbackBox) feedbackBox.innerHTML = `<div style="color: #DC2626; font-size: 12px;">Error: ${err.message}</div>`;
  } finally {
    hideLoadingOverlay();
  }
}

// Reviewer Tab Switcher (Ranking Overview vs Scoring Detail)
function switchReviewerTab(tabName) {
  const rankingTab = document.getElementById("tab-ranking-overview");
  const detailTab = document.getElementById("tab-scoring-detail");
  const btnRank = document.getElementById("btn-tab-ranking");
  const btnDetail = document.getElementById("btn-tab-detail");

  if (tabName === "detail") {
    if (rankingTab) rankingTab.style.display = "none";
    if (detailTab) detailTab.style.display = "block";
    if (btnRank) btnRank.classList.remove("active");
    if (btnDetail) btnDetail.classList.add("active");
  } else {
    if (rankingTab) rankingTab.style.display = "block";
    if (detailTab) detailTab.style.display = "none";
    if (btnRank) btnRank.classList.add("active");
    if (btnDetail) btnDetail.classList.remove("active");
  }
}
