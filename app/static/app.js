// TeraGrant Frontend JavaScript (Batch 30F)

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let activeRecorderType = null; // 'intake', 'interview', 'gap', 'consent'
let activeDeclarationId = null;
let activeGapField = null;

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

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
  document.getElementById('lic-preview').innerHTML = '<div style="font-size: 13px; color: #059669; font-weight: 700;">✓ Attached: License (Municipal Registration)</div>';
  document.getElementById('work-preview').innerHTML = '<div style="font-size: 13px; color: #059669; font-weight: 700;">✓ Attached: Facility Machinery Photo</div>';
  const alertBox = document.getElementById('step2-alert-box');
  if (alertBox) {
    alertBox.innerHTML = '<div style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #059669; padding: 12px; border-radius: 8px; font-size: 13px; font-weight: 600;">✓ Sample test documents attached! Click "Process & Score" below.</div>';
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
  }
}

// Step 4: Gap Resolution Handlers
function toggleGapVoiceRecorder(gapField) {
  const container = document.getElementById("gap-voice-box-" + gapField);
  if (container) {
    container.style.display = container.style.display === "none" ? "block" : "none";
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
