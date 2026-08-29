// TeraGrant Frontend JavaScript (Batch 29F)

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

document.addEventListener("DOMContentLoaded", () => {
  const recordCircle = document.getElementById("record-circle");
  const waveBars = document.getElementById("wave-bars");
  const recordCaption = document.getElementById("record-caption");
  const audioFileInput = document.getElementById("audio-file-input");
  const transcriptBubble = document.getElementById("transcript-bubble");
  const transcriptText = document.getElementById("transcript-text");
  const factChips = document.getElementById("fact-chips");
  const continueBtn = document.getElementById("btn-continue");

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

      showProcessingState();
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
        showError("Failed to upload and transcribe audio: " + err.message);
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
            showProcessingState();

            // Check if we are on the interview page
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
                showError("Transcription error: " + err.message);
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
        } catch (err) {
          alert("Microphone access denied or unavailable: " + err.message);
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

  function showProcessingState() {
    if (recordCaption) {
      recordCaption.classList.remove("recording");
      recordCaption.innerText = "● Analyzing with zero-hallucination auditor...";
    }
  }

  function handleTranscribeResult(data) {
    if (data.error) {
      showError(data.error.message || "Failed to transcribe audio.");
      if (recordCaption) recordCaption.innerText = "Tap to record or speak";
      return;
    }

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
      continueBtn.disabled = false;
      continueBtn.style.opacity = "1";
      continueBtn.style.cursor = "pointer";
    }
    if (recordCaption) recordCaption.innerText = "✓ Transcription complete — tap to record again";
  }

  function showError(msg) {
    alert("Notice: " + msg);
  }
});

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
