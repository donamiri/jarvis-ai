// ===== Live mic waveform visualizer =====
const canvas = document.getElementById("viz");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
const corePanel = document.getElementById("corePanel");
const cmdOverlay = document.getElementById("cmdOverlay");
const cmdOverlayText = document.getElementById("cmdOverlayText");

const cpuValEl = document.getElementById("cpuVal");
const memValEl = document.getElementById("memVal");
const timeValEl = document.getElementById("timeVal");
const netValEl = document.getElementById("netVal");
const appsValEl = document.getElementById("appsVal");

let analyser, data, audioCtx;
let currentHudMode = "idle";
let lastHeardPhrase = "";
let overlayTimeoutId = null;

function setStatus(text) {
  if (statusEl) statusEl.textContent = text;
}

function setCoreMode(state) {
  if (!corePanel) return;
  const s = String(state || "").toLowerCase();
  let mode = "idle";

  if (s === "listening" || s === "standby" || s === "online") {
    mode = "listening";
  } else if (s === "routing" || s === "thinking") {
    mode = "thinking";
  } else if (s === "executing") {
    mode = "executing";
  } else if (s === "speaking") {
    mode = "speaking";
  } else if (s === "offline" || s === "restarting") {
    mode = "idle";
  }

  corePanel.dataset.mode = mode;
  currentHudMode = mode;
}

function showCommandOverlay(phrase) {
  if (!cmdOverlay || !cmdOverlayText) return;
  const clean = (phrase || "").trim();
  cmdOverlayText.textContent = clean ? clean.toUpperCase() : "WORKING...";

  cmdOverlay.classList.add("visible");
  if (overlayTimeoutId) clearTimeout(overlayTimeoutId);
  overlayTimeoutId = setTimeout(() => {
    cmdOverlay.classList.remove("visible");
  }, 2600);
}

function draw() {
  if (!analyser) return requestAnimationFrame(draw);

  analyser.getByteTimeDomainData(data);

  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);

  const cx = width / 2;
  const cy = height / 2;
  const minDim = Math.min(width, height);

  // Base radius sits inside the CSS ring; audio pushes the line outward/inward.
  const baseRadius = minDim * 0.28;
  const maxRadiusOffset = minDim * 0.18;

  // How many segments to draw around the circle
  const segments = 200;
  const angleStep = (Math.PI * 2) / segments;

  // Inner guide ring
  ctx.save();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(80,220,255,0.28)";
  ctx.beginPath();
  ctx.arc(cx, cy, baseRadius * 0.78, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();

  // Outer glowing waveform ring
  const gradient = ctx.createRadialGradient(
    cx,
    cy,
    baseRadius * 0.6,
    cx,
    cy,
    baseRadius + maxRadiusOffset
  );
  gradient.addColorStop(0.0, "rgba(110,240,255,0.15)");
  gradient.addColorStop(0.4, "rgba(140,245,255,0.95)");
  gradient.addColorStop(1.0, "rgba(40,200,255,0.30)");

  const intensity = currentHudMode === "speaking" ? 1.4 : 1.0;

  ctx.lineWidth = 2 * intensity;
  ctx.strokeStyle = gradient;
  ctx.shadowBlur = 26 * intensity;
  ctx.shadowColor = "rgba(140,245,255,0.95)";

  ctx.beginPath();

  for (let i = 0; i <= segments; i++) {
    const dataIndex = Math.floor((i / segments) * data.length);
    const v = (data[dataIndex] - 128) / 128; // -1..1
    const radius = baseRadius + v * maxRadiusOffset;

    // Start at top (-Math.PI / 2) and wrap clockwise
    const angle = -Math.PI / 2 + i * angleStep;

    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;

    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }

  ctx.closePath();
  ctx.stroke();
  requestAnimationFrame(draw);
}

async function startMic() {
  try {
    setStatus("Requesting microphone access...");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtx.createMediaStreamSource(stream);

    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 2048;

    source.connect(analyser);

    data = new Uint8Array(analyser.fftSize);

    setStatus("MIC ACTIVE — speak.");
    draw();
  } catch (err) {
    console.error(err);
    setStatus("MIC BLOCKED — enable microphone permissions.");
  }
}

// ===== WebSocket link to Python Jarvis =====
const cmdInput = document.getElementById("cmd");
const voiceBtn = document.getElementById("voiceBtn");
const logEl = document.getElementById("logText");
const stateLine = document.getElementById("stateLine");
const subLine = document.getElementById("subLine");

function addLog(line) {
  if (!logEl) return;
  const lines = (logEl.textContent + "\n" + line).trim().split("\n");
  logEl.textContent = lines.slice(-14).join("\n");
}

function setState(main, sub) {
  if (stateLine) stateLine.innerHTML = `STATUS: <b>${main}</b>`;
  if (subLine) subLine.textContent = sub || "";
}

function updateTelemetry(data) {
  if (timeValEl && data.time) {
    timeValEl.textContent = String(data.time);
  }
  if (typeof data.cpu === "number" && cpuValEl) {
    cpuValEl.textContent = `${data.cpu.toFixed(0)}%`;
  }
  if (typeof data.mem === "number" && memValEl) {
    memValEl.textContent = `${data.mem.toFixed(0)}%`;
  }
  if (typeof data.online === "boolean" && netValEl) {
    const online = data.online;
    netValEl.textContent = online ? "ONLINE" : "OFFLINE";
    netValEl.style.color = online
      ? "rgba(160,255,200,0.9)"
      : "rgba(255,140,140,0.9)";
  }
  if (Array.isArray(data.apps) && appsValEl) {
    appsValEl.textContent = data.apps.length ? data.apps.join(" · ") : "—";
  }
}

let ws;

function connectWS() {
  setState("CONNECTING", "Linking to ws://127.0.0.1:8765 …");
  ws = new WebSocket("ws://127.0.0.1:8765");

  ws.onopen = () => {
    setState("ONLINE", "Jarvis brain connected.");
    addLog("HUD: Connected to Jarvis.");
    setCoreMode("online");
  };

  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data.type === "status") {
        setState(String(data.state || "").toUpperCase(), "");
        setCoreMode(data.state);
        if (data.state === "executing") {
          showCommandOverlay(lastHeardPhrase || data.tool || "");
        }
      }
      if (data.type === "heard") {
        addLog(`YOU: ${data.text}`);
        lastHeardPhrase = data.text || "";
      }
      if (data.type === "result") {
        addLog(`JARVIS: ${data.text}`);
        setCoreMode("speaking");
        setTimeout(() => {
          setCoreMode("listening");
        }, 1200);
      }
      if (data.type === "error") {
        addLog(`ERROR: ${data.message}`);
      }
      if (data.type === "telemetry") {
        updateTelemetry(data);
      }
    } catch {}
  };

  ws.onclose = () => {
    setState("OFFLINE", "Retrying…");
    setCoreMode("offline");
    setTimeout(connectWS, 1200);
  };

  ws.onerror = () => {
    try { ws.close(); } catch {}
  };
}

function sendTypedCommand(text) {
  const msg = (text || "").trim();
  if (!msg) return;

  addLog(`YOU (hud): ${msg}`);

  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify({ type: "command", text: msg }));
  } else {
    addLog("HUD: Not connected to Jarvis.");
  }
}

function triggerVoice() {
  addLog("YOU (hud): [VOICE MODE]");
  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify({ type: "voice" }));
  } else {
    addLog("HUD: Not connected to Jarvis.");
  }
}

// Typed command on Enter (input)
if (cmdInput) {
  cmdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const text = cmdInput.value;
      cmdInput.value = "";
      sendTypedCommand(text);
    }
  });
}

// Voice button click
if (voiceBtn) {
  voiceBtn.addEventListener("click", () => {
    triggerVoice();
  });
}

// ===== HUD Keyboard Shortcuts (HUD must be focused) =====
// V -> voice, Esc -> clear input, / -> focus command input
window.addEventListener("keydown", (e) => {
  // Don't steal typing while you're inside the command box (except Esc)
  const typingInInput = document.activeElement === cmdInput;

  if (e.key === "Escape") {
    if (cmdInput) cmdInput.value = "";
    if (cmdInput) cmdInput.blur();
    addLog("HUD: cleared input.");
    return;
  }

  // Press "/" to jump into the command box quickly
  if (e.key === "/" && cmdInput && !typingInInput) {
    e.preventDefault();
    cmdInput.focus();
    addLog("HUD: command input focused.");
    return;
  }

  // V triggers voice when NOT typing in the input box
  if ((e.key === "v" || e.key === "V") && !typingInInput) {
    e.preventDefault();
    triggerVoice();
    return;
  }
});

// Start everything
connectWS();
startMic();