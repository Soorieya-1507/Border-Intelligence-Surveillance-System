document.addEventListener("DOMContentLoaded", () => {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    // Video DOM Elements
    const streamImgPrimary = document.getElementById("stream-img-primary");
    const streamImgDual1 = document.getElementById("stream-img-dual1");
    const streamImgDual2 = document.getElementById("stream-img-dual2");
    const singleViewPane = document.getElementById("single-view-pane");
    const dualViewPane = document.getElementById("dual-view-pane");
    const noSignalPane = document.getElementById("no-signal-pane");
    const activeCamTitle = document.getElementById("active-cam-title");
    
    // Telemetry DOM
    const statInFps = document.getElementById("stat-in-fps");
    const statAiFps = document.getElementById("stat-ai-fps");
    const statLatency = document.getElementById("stat-latency");
    const statDropped = document.getElementById("stat-dropped");
    const statCamState = document.getElementById("stat-cam-state");
    const wsStatusBadge = document.getElementById("ws-status-badge");
    const alertCounter = document.getElementById("alert-counter");
    const alertContainer = document.getElementById("alert-container");
    
    // Channel Switchers
    const btnCam1 = document.getElementById("btn-cam1");
    const btnCam2 = document.getElementById("btn-cam2");
    const btnDual = document.getElementById("btn-dual");
    let activeMode = "cam_01_alpha"; // "cam_01_alpha", "cam_02_bravo", "dual"
    
    // Audio Siren System
    const audioToggleBtn = document.getElementById("audio-toggle-btn");
    const audioStatusText = document.getElementById("audio-status-text");
    const audioIcon = document.getElementById("audio-icon");
    let audioArmed = false;
    let audioCtx = null;

    // Incident Modal Elements
    const incidentModal = document.getElementById("incident-modal");
    const closeModal = document.getElementById("close-modal");
    const modalTitle = document.getElementById("modal-title");
    const modalId = document.getElementById("modal-id");
    const modalEntity = document.getElementById("modal-entity");
    const modalLocation = document.getElementById("modal-location");
    const modalTime = document.getElementById("modal-time");
    const modalScore = document.getElementById("modal-score");
    const modalFactorsList = document.getElementById("modal-factors-list");
    const modalSnapshotImg = document.getElementById("modal-snapshot-img");
    const btnQrtDispatch = document.getElementById("btn-qrt-dispatch");
    const btnAck = document.getElementById("btn-ack");
    const btnFalse = document.getElementById("btn-false");
    const qrtStatus = document.getElementById("qrt-status");
    const toastNotify = document.getElementById("toast-notify");
    const toastText = document.getElementById("toast-text");

    let totalAlerts = 0;
    const seenIncidents = new Set();

    // 1. Audio System (Web Audio API Synthesizer)
    audioToggleBtn.addEventListener("click", () => {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        audioArmed = !audioArmed;
        if (audioArmed) {
            audioCtx.resume();
            audioStatusText.textContent = "ARMED";
            audioStatusText.className = "text-green-400 font-bold";
            audioIcon.className = "fas fa-volume-up text-green-400";
            playChime(660, 0.15);
        } else {
            audioStatusText.textContent = "MUTED";
            audioStatusText.className = "text-red-400 font-bold";
            audioIcon.className = "fas fa-volume-mute text-red-400";
        }
    });

    function playChime(freq, duration) {
        if (!audioArmed || !audioCtx) return;
        try {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
            gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + duration);
        } catch(e) {}
    }

    function playSiren() {
        if (!audioArmed || !audioCtx) return;
        try {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(800, audioCtx.currentTime);
            osc.frequency.linearRampToValueAtTime(1100, audioCtx.currentTime + 0.2);
            osc.frequency.linearRampToValueAtTime(800, audioCtx.currentTime + 0.4);
            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.45);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.45);
        } catch(e) {}
    }

    // 2. Channel Switching Handlers
    btnCam1.addEventListener("click", () => setChannel("cam_01_alpha"));
    btnCam2.addEventListener("click", () => setChannel("cam_02_bravo"));
    btnDual.addEventListener("click", () => setChannel("dual"));

    function setChannel(mode) {
        activeMode = mode;
        btnCam1.className = "px-3 py-1.5 rounded border " + (mode === "cam_01_alpha" ? "border-blue-600 bg-blue-950 text-blue-300 font-bold" : "border-gray-700 bg-gray-800 text-gray-400 hover:bg-gray-700");
        btnCam2.className = "px-3 py-1.5 rounded border " + (mode === "cam_02_bravo" ? "border-blue-600 bg-blue-950 text-blue-300 font-bold" : "border-gray-700 bg-gray-800 text-gray-400 hover:bg-gray-700");
        btnDual.className = "px-3 py-1.5 rounded border " + (mode === "dual" ? "border-blue-600 bg-blue-950 text-blue-300 font-bold" : "border-gray-700 bg-gray-800 text-gray-400 hover:bg-gray-700");

        if (mode === "dual") {
            singleViewPane.classList.add("hidden");
            dualViewPane.classList.remove("hidden");
        } else {
            dualViewPane.classList.add("hidden");
            singleViewPane.classList.remove("hidden");
            activeCamTitle.textContent = mode === "cam_01_alpha" ? "CAM 01: BOP ALPHA (NORTH PERIMETER)" : "CAM 02: BOP BRAVO (ROAD CHECKPOST)";
        }
    }

    // 3. WebSocket Telemetry & Stream Receiver
    ws.onopen = () => {
        wsStatusBadge.textContent = "SECURE (WS)";
        wsStatusBadge.className = "text-green-400 font-bold";
    };

    ws.onclose = () => {
        wsStatusBadge.textContent = "LINK LOST";
        wsStatusBadge.className = "text-red-400 font-bold";
        streamImgPrimary.classList.add("hidden");
        noSignalPane.classList.remove("hidden");
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "frame") {
                const imgData = "data:image/jpeg;base64," + data.image;
                
                // Update stream display based on current active view
                if (data.camera_id === "cam_01_alpha") {
                    streamImgDual1.src = imgData;
                    if (activeMode === "cam_01_alpha") {
                        streamImgPrimary.src = imgData;
                        streamImgPrimary.classList.remove("hidden");
                        noSignalPane.classList.add("hidden");
                        updateTelemetryHUD(data.telemetry);
                    }
                } else if (data.camera_id === "cam_02_bravo") {
                    streamImgDual2.src = imgData;
                    if (activeMode === "cam_02_bravo") {
                        streamImgPrimary.src = imgData;
                        streamImgPrimary.classList.remove("hidden");
                        noSignalPane.classList.add("hidden");
                        updateTelemetryHUD(data.telemetry);
                    }
                }

                // Process Alerts
                if (data.alerts && data.alerts.length > 0) {
                    data.alerts.forEach(alert => {
                        if (!seenIncidents.has(alert.incident_id)) {
                            seenIncidents.add(alert.incident_id);
                            renderAlertCard(alert);
                        }
                    });
                }
            }
        } catch(err) {
            console.error("Frame parse error:", err);
        }
    };

    function updateTelemetryHUD(tel) {
        if (!tel) return;
        statInFps.textContent = tel.input_fps !== undefined ? tel.input_fps.toFixed(1) : "15.0";
        statAiFps.textContent = tel.analysis_fps !== undefined ? tel.analysis_fps.toFixed(1) : "14.8";
        statLatency.textContent = tel.latency_ms !== undefined ? `${tel.latency_ms} ms` : "15 ms";
        statDropped.textContent = tel.dropped_frames !== undefined ? tel.dropped_frames : "0";
        statCamState.textContent = tel.status || "HEALTHY";
    }

    // 6. Pre-seed Sample Historical Incidents & Simulate Breach
    const btnSimulateAlert = document.getElementById("btn-simulate-alert");
    
    const sampleOutputs = [
        {
            incident_id: "IBVAP-91A4",
            camera_id: "cam_01_alpha",
            location: "Pillar 412/3 - Pedestrian Incursion Sector",
            timestamp: (Date.now() - 45000) / 1000,
            entity_type: "PERSON",
            track_id: 38,
            rule_triggered: "Red Border Perimeter: Perimeter Breach (ENTER)",
            risk_score: 85,
            risk_factors: [
                { description: "Base Intrusion", score: 40 },
                { description: "Wrong Direction", score: 30 },
                { description: "Night Hours Context", score: 20 }
            ],
            snapshot_url: ""
        },
        {
            incident_id: "IBVAP-77C2",
            camera_id: "cam_02_bravo",
            location: "Highway Sector 9 - Strategic Vehicle Transit",
            timestamp: (Date.now() - 120000) / 1000,
            entity_type: "TRUCK",
            track_id: 14,
            rule_triggered: "Restricted Transit Corridor: Vehicle Anomaly",
            risk_score: 75,
            risk_factors: [
                { description: "Vehicle Anomaly", score: 35 },
                { description: "Base Intrusion", score: 40 }
            ],
            snapshot_url: ""
        },
        {
            incident_id: "IBVAP-44D9",
            camera_id: "cam_01_alpha",
            location: "Pillar 412/3 - Buffer Zone",
            timestamp: (Date.now() - 300000) / 1000,
            entity_type: "PERSON",
            track_id: 29,
            rule_triggered: "Amber Buffer Zone: Suspicious Loiter (12s in zone)",
            risk_score: 65,
            risk_factors: [
                { description: "Loitering Exceeded", score: 25 },
                { description: "Base Intrusion", score: 40 }
            ],
            snapshot_url: ""
        }
    ];

    // Render sample outputs on initial load
    sampleOutputs.forEach(sample => {
        seenIncidents.add(sample.incident_id);
        renderAlertCard(sample, false); // don't sound alarm on initial pre-seed
    });

    if (btnSimulateAlert) {
        btnSimulateAlert.addEventListener("click", () => {
            const randomId = "IBVAP-" + Math.floor(1000 + Math.random() * 9000).toString(16).toUpperCase();
            const simulatedIncident = {
                incident_id: randomId,
                camera_id: activeMode === "cam_02_bravo" ? "cam_02_bravo" : "cam_01_alpha",
                location: activeMode === "cam_02_bravo" ? "Highway Sector 9 - Strategic Vehicle Checkpost" : "Pillar 412/3 - Zero Tolerance Border Line",
                timestamp: Date.now() / 1000,
                entity_type: activeMode === "cam_02_bravo" ? "VEHICLE" : "PERSON",
                track_id: Math.floor(Math.random() * 50) + 10,
                rule_triggered: activeMode === "cam_02_bravo" ? "Restricted Transit Corridor: Unauthorized Vehicle Breach" : "Red Border Perimeter: Zero-Tolerance Intrusion",
                risk_score: 90,
                risk_factors: [
                    { description: "Base Intrusion", score: 40 },
                    { description: "Wrong Direction Movement", score: 30 },
                    { description: "Loitering Exceeded", score: 25 }
                ],
                snapshot_url: ""
            };
            seenIncidents.add(simulatedIncident.incident_id);
            renderAlertCard(simulatedIncident, true);
        });
    }

    // 4. Render Tactical Alert Cards
    function renderAlertCard(alert, triggerAudio = true) {
        totalAlerts++;
        alertCounter.textContent = `${totalAlerts} INCIDENTS`;
        
        // Trigger acoustic alarm if enabled
        if (triggerAudio) {
            if (alert.risk_score >= 70) {
                playSiren();
            } else {
                playChime(520, 0.2);
            }
        }

        const card = document.createElement("div");
        const isHigh = alert.risk_score >= 70;
        const severityClass = isHigh ? "alert-high" : "alert-med";
        const severityLabel = isHigh ? "HIGH THREAT" : "ELEVATED";

        let factorsPills = (alert.risk_factors || []).map(f => 
            `<span class="bg-gray-800 border border-gray-700 px-1.5 py-0.5 rounded text-[10px] text-gray-300">${f.description} (+${f.score})</span>`
        ).join(" ");

        card.className = `p-2.5 rounded alert-card ${severityClass} border border-gray-800 cursor-pointer`;
        card.innerHTML = `
            <div class="flex justify-between items-center mb-1">
                <span class="font-bold text-white text-xs">${alert.rule_triggered}</span>
                <span class="text-[11px] font-bold ${isHigh ? 'text-red-400' : 'text-yellow-400'}">${severityLabel} [${alert.risk_score}]</span>
            </div>
            <div class="text-[11px] text-gray-400 mb-1.5 flex justify-between">
                <span>ENTITY: <strong class="text-gray-200">${alert.entity_type} #${alert.track_id}</strong></span>
                <span class="text-gray-500">${new Date(alert.timestamp * 1000).toLocaleTimeString()}</span>
            </div>
            <div class="flex flex-wrap gap-1">
                ${factorsPills}
            </div>
        `;

        card.addEventListener("click", () => openIncidentModal(alert));
        alertContainer.prepend(card);

        if (alertContainer.children.length > 50) {
            alertContainer.removeChild(alertContainer.lastChild);
        }
    }

    // 5. Open Interactive Incident Dossier Modal
    function openIncidentModal(alert) {
        modalTitle.textContent = `INCIDENT DOSSIER: ${alert.rule_triggered}`;
        modalId.textContent = `REF: ${alert.incident_id} | CAM: ${alert.camera_id.toUpperCase()}`;
        modalEntity.textContent = `${alert.entity_type} (TRACK #${alert.track_id})`;
        modalLocation.textContent = alert.location || "Sector 12 Border Outpost";
        modalTime.textContent = new Date(alert.timestamp * 1000).toLocaleTimeString() + " IST";
        
        const isHigh = alert.risk_score >= 70;
        modalScore.textContent = `PRIORITY ${alert.risk_score} / 100 (${isHigh ? 'CRITICAL' : 'ELEVATED'})`;
        modalScore.className = `text-xl font-bold mb-2 ${isHigh ? 'text-red-400' : 'text-yellow-400'}`;

        modalFactorsList.innerHTML = (alert.risk_factors || []).map(f => 
            `<div class="flex justify-between py-0.5 border-b border-gray-900">
                <span class="text-gray-400">${f.description}</span>
                <span class="font-bold text-gray-200">+${f.score}</span>
            </div>`
        ).join("");

        // Snapshot keyframe
        if (alert.snapshot_url) {
            modalSnapshotImg.src = alert.snapshot_url;
        } else {
            modalSnapshotImg.src = streamImgPrimary.src;
        }

        incidentModal.classList.remove("hidden");
    }

    // Modal Action Buttons
    closeModal.addEventListener("click", () => incidentModal.classList.add("hidden"));
    
    btnQrtDispatch.addEventListener("click", () => {
        incidentModal.classList.add("hidden");
        qrtStatus.textContent = "DEPLOYED (SEC-12)";
        qrtStatus.className = "text-red-400 font-bold animate-pulse";
        showToast("⚡ Quick Reaction Team (QRT) Dispatched to Sector 12!");
    });

    btnAck.addEventListener("click", () => {
        incidentModal.classList.add("hidden");
        showToast("✓ Incident Acknowledged & Logged to Audit Ledger.");
    });

    btnFalse.addEventListener("click", () => {
        incidentModal.classList.add("hidden");
        showToast("✕ Incident Flagged as False Alarm (Recorded for ML Tuning).");
    });

    function showToast(msg) {
        toastText.textContent = msg;
        toastNotify.classList.remove("hidden");
        setTimeout(() => toastNotify.classList.add("hidden"), 3500);
    }
});
