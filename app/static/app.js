// TeraGrant Frontend JavaScript (Batch 28F)

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

  // Upload handler
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

  // Live recording handler
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
          };

          mediaRecorder.start();
          isRecording = true;
          recordCircle.classList.add("pulsing");
          if (waveBars) waveBars.classList.add("active");
          if (recordCaption) recordCaption.innerText = "● Recording... tap to stop";
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
        recordCircle.classList.remove("pulsing");
        if (waveBars) waveBars.classList.remove("active");
        if (recordCaption) recordCaption.innerText = "● Processing audio note...";
      }
    });
  }

  function showProcessingState() {
    if (recordCaption) recordCaption.innerText = "● Analyzing with zero-hallucination auditor...";
  }

  function handleTranscribeResult(data) {
    if (data.error) {
      showError(data.error.message || "Failed to transcribe audio.");
      if (recordCaption) recordCaption.innerText = "● Ready to record";
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
    if (recordCaption) recordCaption.innerText = "✓ Transcription complete";
  }

  function showError(msg) {
    alert("Notice: " + msg);
  }
});
