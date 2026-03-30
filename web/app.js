const startCameraButton = document.getElementById("startCameraButton");
const startLiveButton = document.getElementById("startLiveButton");
const stopLiveButton = document.getElementById("stopLiveButton");
const cameraSelect = document.getElementById("cameraSelect");
const refreshCameraButton = document.getElementById("refreshCameraButton");
const intervalSelect = document.getElementById("intervalSelect");
const amountInput = document.getElementById("amountInput");
const saveTemplateButton = document.getElementById("saveTemplateButton");
const statusText = document.getElementById("status");
const cameraFeed = document.getElementById("cameraFeed");
const captureCanvas = document.getElementById("captureCanvas");
const previewPlaceholder = document.getElementById("previewPlaceholder");
const resultCard = document.getElementById("resultCard");
const resultBadge = document.getElementById("resultBadge");
const resultLabel = document.getElementById("resultLabel");
const stateText = document.getElementById("stateText");
const amountText = document.getElementById("amountText");
const recommendationText = document.getElementById("recommendationText");
const finalVerdictText = document.getElementById("finalVerdictText");
const meterFill = document.getElementById("meterFill");
const confidenceText = document.getElementById("confidenceText");
const featureDump = document.getElementById("featureDump");

let mediaStream = null;
let liveTimer = null;
let predictionInFlight = false;
let selectedCameraId = localStorage.getItem("preferredCameraId") || "";
let verdictHistory = [];

function isLikelyExternalCamera(label) {
  const text = (label || "").toLowerCase();
  return text.includes("usb") || text.includes("logitech") || text.includes("external");
}

function setStatus(text) {
  statusText.textContent = text;
}

function computeFinalVerdict() {
  const now = Date.now();
  verdictHistory = verdictHistory.filter((item) => now - item.timestamp < 5000);

  if (verdictHistory.length < 4) {
    return "Final verdict: collecting frames...";
  }

  const stateCounts = {};
  const amountCounts = {};

  verdictHistory.forEach((item) => {
    stateCounts[item.note_state] = (stateCounts[item.note_state] || 0) + 1;
    if (item.amount !== "unknown") {
      amountCounts[item.amount] = (amountCounts[item.amount] || 0) + 1;
    }
  });

  const dominantState = Object.entries(stateCounts).sort((a, b) => b[1] - a[1])[0];
  const dominantAmount = Object.entries(amountCounts).sort((a, b) => b[1] - a[1])[0];

  if (!dominantState || dominantState[1] / verdictHistory.length < 0.65) {
    return "Final verdict: unstable reading, hold the note steady for 2-3 seconds.";
  }

  const stateTextValue = dominantState[0] === "original"
    ? "ORIGINAL"
    : dominantState[0] === "fake"
      ? "FAKE"
      : "UNCERTAIN";
  const amountTextValue = dominantAmount ? dominantAmount[0] : "unknown";
  return `Final verdict: ${stateTextValue} note, amount ${amountTextValue}.`;
}

function updateResult(payload) {
  const confidencePercent = Math.round((payload.confidence || 0) * 100);
  const isGenuine = payload.note_state === "original";
  const isUncertain = payload.note_state === "uncertain";
  const amountConfidencePercent = Math.round((payload.amount_confidence || 0) * 100);

  verdictHistory.push({
    timestamp: Date.now(),
    note_state: payload.note_state,
    amount: payload.amount,
  });

  resultCard.hidden = false;
  resultBadge.textContent = isGenuine ? "Original" : isUncertain ? "Uncertain" : "Fake";
  resultBadge.classList.remove("ok", "warn", "neutral");
  resultBadge.classList.add(isGenuine ? "ok" : isUncertain ? "neutral" : "warn");

  resultLabel.textContent = isGenuine
    ? "The note appears original in this live scan."
    : isUncertain
      ? "The scan is uncertain. Adjust lighting and hold note steady."
      : "The note appears fake in this live scan.";

  stateText.textContent = `Detected state: ${payload.note_state.toUpperCase()}`;
  amountText.textContent = `Detected amount: ${payload.amount} (${amountConfidencePercent}% confidence)`;
  recommendationText.textContent = `Recommendation: ${payload.recommendation}`;
  finalVerdictText.textContent = computeFinalVerdict();

  meterFill.style.width = `${confidencePercent}%`;
  confidenceText.textContent = `Confidence: ${confidencePercent}%`;
  featureDump.textContent = JSON.stringify(payload.details, null, 2);
}

async function listCameras() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoInputs = devices.filter((d) => d.kind === "videoinput");

    cameraSelect.innerHTML = "";
    if (videoInputs.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No camera found";
      cameraSelect.appendChild(option);
      return;
    }

    videoInputs.forEach((device, index) => {
      const option = document.createElement("option");
      option.value = device.deviceId;
      option.textContent = device.label || `Camera ${index + 1}`;
      cameraSelect.appendChild(option);
    });

    if (selectedCameraId) {
      const exists = videoInputs.some((d) => d.deviceId === selectedCameraId);
      if (exists) {
        cameraSelect.value = selectedCameraId;
      }
    }

    if (!cameraSelect.value && videoInputs.length > 0) {
      const preferredExternal = videoInputs.find((d) => isLikelyExternalCamera(d.label));
      cameraSelect.value = (preferredExternal || videoInputs[0]).deviceId;
      selectedCameraId = cameraSelect.value;
      localStorage.setItem("preferredCameraId", selectedCameraId);
    }
  } catch (error) {
    setStatus(`Camera list error: ${error.message}`);
  }
}

async function startCamera() {
  if (mediaStream) {
    return;
  }

  try {
    selectedCameraId = cameraSelect.value || selectedCameraId;
    const videoConstraint = selectedCameraId
      ? { deviceId: { exact: selectedCameraId } }
      : { facingMode: "environment" };

    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: videoConstraint,
      audio: false,
    });

    cameraFeed.srcObject = mediaStream;
    cameraFeed.hidden = false;
    previewPlaceholder.hidden = true;
    startLiveButton.disabled = false;
    setStatus("Camera started. Position your note in front of the lens.");

    await listCameras();
    const track = mediaStream.getVideoTracks()[0];
    const settings = track.getSettings();
    if (settings.deviceId) {
      selectedCameraId = settings.deviceId;
      cameraSelect.value = settings.deviceId;
      localStorage.setItem("preferredCameraId", selectedCameraId);
    }
  } catch (error) {
    setStatus(`Camera error: ${error.message}`);
  }
}

function stopLiveDetection() {
  if (liveTimer) {
    clearInterval(liveTimer);
    liveTimer = null;
  }
  startLiveButton.disabled = false;
  stopLiveButton.disabled = true;
  setStatus("Live detection stopped.");
  verdictHistory = [];
  finalVerdictText.textContent = "Final verdict: collecting frames...";
}

async function predictFrameOnce() {
  if (!mediaStream || predictionInFlight || cameraFeed.videoWidth === 0 || cameraFeed.videoHeight === 0) {
    return;
  }

  predictionInFlight = true;
  const context = captureCanvas.getContext("2d");
  if (!context) {
    setStatus("Live detection error: browser canvas is unavailable.");
    predictionInFlight = false;
    return;
  }

  captureCanvas.width = cameraFeed.videoWidth;
  captureCanvas.height = cameraFeed.videoHeight;
  context.drawImage(cameraFeed, 0, 0, captureCanvas.width, captureCanvas.height);

  try {
    const blob = await new Promise((resolve) => {
      captureCanvas.toBlob(resolve, "image/jpeg", 0.85);
    });

    if (!blob) {
      throw new Error("Could not capture camera frame.");
    }

    const formData = new FormData();
    formData.append("file", blob, "frame.jpg");

    const response = await fetch("/predict", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || "Prediction failed.");
    }

    updateResult(payload);
    setStatus("Live detection active.");
  } catch (error) {
    setStatus(`Live detection error: ${error.message}`);
  } finally {
    predictionInFlight = false;
  }
}

async function saveCurrentFrameAsTemplate() {
  if (!mediaStream || cameraFeed.videoWidth === 0 || cameraFeed.videoHeight === 0) {
    setStatus("Start camera first before saving template.");
    return;
  }

  const amountValue = amountInput.value.trim();
  if (!amountValue) {
    setStatus("Enter amount first, for example 2000.");
    return;
  }

  const context = captureCanvas.getContext("2d");
  if (!context) {
    setStatus("Template save error: browser canvas is unavailable.");
    return;
  }

  captureCanvas.width = cameraFeed.videoWidth;
  captureCanvas.height = cameraFeed.videoHeight;
  context.drawImage(cameraFeed, 0, 0, captureCanvas.width, captureCanvas.height);

  const blob = await new Promise((resolve) => {
    captureCanvas.toBlob(resolve, "image/jpeg", 0.9);
  });

  if (!blob) {
    setStatus("Template save error: could not capture frame.");
    return;
  }

  const formData = new FormData();
  formData.append("amount", amountValue);
  formData.append("file", blob, `template_${amountValue}.jpg`);

  try {
    const response = await fetch("/denomination/template", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not save template.");
    }
    setStatus(`Template saved for amount ${payload.amount}. Capture 4-8 templates for best results.`);
  } catch (error) {
    setStatus(`Template save error: ${error.message}`);
  }
}

function startLiveDetection() {
  if (!mediaStream) {
    setStatus("Start camera first.");
    return;
  }

  stopLiveDetection();

  const intervalMs = Number(intervalSelect.value);
  startLiveButton.disabled = true;
  stopLiveButton.disabled = false;
  setStatus("Starting live detection...");

  predictFrameOnce();
  liveTimer = setInterval(() => {
    predictFrameOnce();
  }, intervalMs);
}

function stopCamera() {
  stopLiveDetection();
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
  cameraFeed.srcObject = null;
  cameraFeed.hidden = true;
  previewPlaceholder.hidden = false;
  startLiveButton.disabled = true;
  setStatus("Camera stopped.");
}

startCameraButton.addEventListener("click", async () => {
  if (mediaStream) {
    stopCamera();
    startCameraButton.textContent = "Start Camera";
    return;
  }

  await startCamera();
  if (mediaStream) {
    startCameraButton.textContent = "Stop Camera";
  }
});

cameraSelect.addEventListener("change", async () => {
  selectedCameraId = cameraSelect.value;
  localStorage.setItem("preferredCameraId", selectedCameraId);
  if (mediaStream) {
    stopCamera();
    startCameraButton.textContent = "Start Camera";
    await startCamera();
    if (mediaStream) {
      startCameraButton.textContent = "Stop Camera";
    }
  }
});

refreshCameraButton.addEventListener("click", async () => {
  await listCameras();
  setStatus("Camera list refreshed.");
});

startLiveButton.addEventListener("click", startLiveDetection);
stopLiveButton.addEventListener("click", stopLiveDetection);
saveTemplateButton.addEventListener("click", saveCurrentFrameAsTemplate);

window.addEventListener("beforeunload", () => {
  stopCamera();
});

listCameras();
