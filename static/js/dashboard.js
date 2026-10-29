/**
 * Multimodal Attendance & Engagement Agent
 * Real-Time Dashboard Controller
 */

let engagementChart = null;
let activeSessionId = null;
let pollInterval = null;
let isSessionRunning = false;

document.addEventListener("DOMContentLoaded", () => {
    initChart();
    loadSessions();
    setupEventListeners();
});

function initChart() {
    const ctx = document.getElementById("engagementTrendChart");
    if (!ctx) return;

    engagementChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: [],
            datasets: [
                {
                    label: "Fused Engagement",
                    data: [],
                    borderColor: "#00F0FF",
                    backgroundColor: "rgba(0, 240, 255, 0.12)",
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 3,
                    pointHoverRadius: 6
                },
                {
                    label: "Visual Focus",
                    data: [],
                    borderColor: "#00E676",
                    borderWidth: 1.8,
                    borderDash: [4, 4],
                    fill: false,
                    tension: 0.35,
                    pointRadius: 2
                },
                {
                    label: "Acoustic Activity",
                    data: [],
                    borderColor: "#7C4DFF",
                    borderWidth: 1.8,
                    borderDash: [2, 2],
                    fill: false,
                    tension: 0.35,
                    pointRadius: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "top",
                    labels: { color: "#94A3B8", font: { size: 11, family: "Inter" } }
                },
                tooltip: {
                    mode: "index",
                    intersect: false,
                    backgroundColor: "#111D35",
                    titleColor: "#00F0FF",
                    bodyColor: "#F0F4F8",
                    borderColor: "#1B2A4A",
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: "rgba(27, 42, 74, 0.5)" },
                    ticks: { color: "#64748B", font: { size: 10 } }
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: "rgba(27, 42, 74, 0.5)" },
                    ticks: {
                        color: "#64748B",
                        font: { size: 10 },
                        callback: val => val + "%"
                    }
                }
            }
        }
    });
}

async function loadSessions() {
    const sel = document.getElementById("sessionSelector");
    if (!sel) return;

    try {
        const res = await fetch("/api/sessions");
        const json = await res.json();
        sel.innerHTML = "";

        if (!json.success || json.data.length === 0) {
            sel.innerHTML = '<option value="">No sessions found. Seed demo data or create a session.</option>';
            return;
        }

        json.data.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.textContent = `#${s.id} - ${s.title} (${s.classroom_code || "Class"}) [${s.status.toUpperCase()}]`;
            if (s.is_live) {
                opt.textContent += " 🔴 LIVE";
                opt.selected = true;
            }
            sel.appendChild(opt);
        });

        // Pick first session by default
        if (sel.options.length > 0) {
            activeSessionId = parseInt(sel.value);
            onSessionChanged(activeSessionId);
        }
    } catch (e) {
        console.error("Error loading sessions:", e);
    }
}

function setupEventListeners() {
    const sel = document.getElementById("sessionSelector");
    if (sel) {
        sel.addEventListener("change", (e) => {
            activeSessionId = parseInt(e.target.value);
            onSessionChanged(activeSessionId);
        });
    }

    const btnStart = document.getElementById("btnStartSession");
    const btnStop = document.getElementById("btnStopSession");

    if (btnStart) {
        btnStart.addEventListener("click", () => startActiveSession());
    }
    if (btnStop) {
        btnStop.addEventListener("click", () => stopActiveSession());
    }

    const btnReloadFeed = document.getElementById("btnToggleFeed");
    if (btnReloadFeed) {
        btnReloadFeed.addEventListener("click", () => {
            const img = document.getElementById("liveVideoFeed");
            if (img && activeSessionId) {
                img.src = `/api/sessions/${activeSessionId}/feed?t=${Date.now()}`;
            }
        });
    }
}

async function onSessionChanged(sessionId) {
    if (!sessionId) return;

    try {
        const res = await fetch(`/api/sessions/${sessionId}/status`);
        const json = await res.json();
        
        isSessionRunning = json.is_live || false;
        updateControls(isSessionRunning);

        const img = document.getElementById("liveVideoFeed");
        if (img) {
            img.src = `/api/sessions/${sessionId}/feed?t=${Date.now()}`;
        }

        // Fetch immediate updates
        fetchSessionData(sessionId);

        // Manage polling loop
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(() => {
            fetchSessionData(sessionId);
        }, 1800);
    } catch (e) {
        console.error("Session change error:", e);
    }
}

function updateControls(running) {
    const btnStart = document.getElementById("btnStartSession");
    const btnStop = document.getElementById("btnStopSession");
    const hudStatus = document.getElementById("hudStatus");

    if (running) {
        btnStart.style.display = "none";
        btnStop.style.display = "inline-flex";
        if (hudStatus) {
            hudStatus.textContent = "STREAMING LIVE";
            hudStatus.style.borderColor = "var(--accent-emerald)";
            hudStatus.style.color = "var(--accent-emerald)";
        }
    } else {
        btnStart.style.display = "inline-flex";
        btnStop.style.display = "none";
        if (hudStatus) {
            hudStatus.textContent = "STOPPED";
            hudStatus.style.borderColor = "rgba(255, 255, 255, 0.15)";
            hudStatus.style.color = "#E2E8F0";
        }
    }
}

async function startActiveSession() {
    if (!activeSessionId) return;
    try {
        const res = await fetch(`/api/sessions/${activeSessionId}/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
            isSessionRunning = true;
            updateControls(true);
            const img = document.getElementById("liveVideoFeed");
            if (img) img.src = `/api/sessions/${activeSessionId}/feed?t=${Date.now()}`;
            fetchSessionData(activeSessionId);
        } else {
            alert("Could not start session: " + data.error);
        }
    } catch (e) {
        alert("Error starting session: " + e);
    }
}

async function stopActiveSession() {
    if (!activeSessionId) return;
    try {
        const res = await fetch(`/api/sessions/${activeSessionId}/stop`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();
        if (data.success) {
            isSessionRunning = false;
            updateControls(false);
            fetchSessionData(activeSessionId);
            alert("Session stopped and finalized locally.");
        } else {
            alert("Could not stop session: " + data.error);
        }
    } catch (e) {
        alert("Error stopping session: " + e);
    }
}

async function fetchSessionData(sessionId) {
    if (!sessionId) return;

    try {
        // 1. Fetch Status / FPS
        const statRes = await fetch(`/api/sessions/${sessionId}/status`);
        const statJson = await statRes.json();
        if (statJson.success && statJson.data) {
            const d = statJson.data;
            document.getElementById("liveFpsBadge").textContent = (d.fps || 0.0) + " FPS";
            document.getElementById("hudElapsed").textContent = Math.round(d.elapsed_seconds || 0) + "s";
            
            if (d.speech_ratio !== undefined) {
                document.getElementById("statSpeechRatio").textContent = d.speech_ratio + "%";
            }
            if (d.dominant_audio_state) {
                document.getElementById("statAudioDominant").textContent = d.dominant_audio_state;
            }
            if (d.data_quality) {
                document.getElementById("statDataQuality").textContent = d.data_quality;
            }
        }

        // 2. Fetch Attendance Snapshot
        const attRes = await fetch(`/api/sessions/${sessionId}/attendance`);
        const attJson = await attRes.json();
        if (attJson.success) {
            renderAttendanceSnapshot(attJson.data);
        }

        // 3. Fetch Analytics & Timeline
        const anaRes = await fetch(`/api/sessions/${sessionId}/analytics`);
        const anaJson = await anaRes.json();
        if (anaJson.success && anaJson.data) {
            renderAnalytics(anaJson.data);
        }

        // 4. Fetch AI Recommendations
        const recRes = await fetch(`/api/sessions/${sessionId}/recommendations`);
        const recJson = await recRes.json();
        if (recJson.success) {
            renderRecommendations(recJson.data);
        }

        if (window.feather) feather.replace();
    } catch (e) {
        console.error("Dashboard fetch error:", e);
    }
}

function renderAttendanceSnapshot(records) {
    const tbody = document.getElementById("attendanceSnapshotBody");
    const countBadge = document.getElementById("attCountBadge");
    if (!tbody) return;

    countBadge.textContent = `${records.length} Participants`;

    const detected = records.length;
    const present = records.filter(r => r.status === "present").length;
    const attRate = detected > 0 ? Math.round((present / detected) * 100) : 0;

    document.getElementById("statDetected").textContent = detected;
    document.getElementById("statActiveTracks").textContent = detected;
    document.getElementById("statPresent").textContent = present;
    document.getElementById("statAttendanceRate").textContent = attRate + "%";

    if (records.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
                    No participants detected yet in this session.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = records.map(r => {
        const isPres = r.status === "present";
        const badgeClass = isPres ? "status-present" : (r.status === "transient" ? "status-transient" : "status-absent");
        const fwdPct = Math.round((r.avg_head_pose_forward || 0) * 100);

        return `
            <tr>
                <td><strong>${r.participant_track_id}</strong></td>
                <td>${r.student_name || '<span style="color: var(--text-muted);">Anonymous Track</span>'}</td>
                <td>${r.presence_duration_seconds}s</td>
                <td>${r.presence_percentage}%</td>
                <td>${fwdPct}%</td>
                <td><span class="status-badge ${badgeClass}">${r.status}</span></td>
            </tr>
        `;
    }).join("");
}

function renderAnalytics(data) {
    if (!data) return;

    document.getElementById("statEngagement").textContent = (data.avg_engagement_score || 50.0) + "%";
    
    const lvlEl = document.getElementById("statEngagementLevel");
    const score = data.avg_engagement_score || 50.0;
    if (score >= 75) {
        lvlEl.textContent = "High";
        lvlEl.style.background = "var(--accent-emerald-dim)";
        lvlEl.style.color = "var(--accent-emerald)";
    } else if (score >= 50) {
        lvlEl.textContent = "Moderate";
        lvlEl.style.background = "var(--accent-cyan-dim)";
        lvlEl.style.color = "var(--accent-cyan)";
    } else {
        lvlEl.textContent = "Low";
        lvlEl.style.background = "var(--accent-amber-dim)";
        lvlEl.style.color = "var(--accent-amber)";
    }

    // Update Chart.js timeline
    if (engagementChart && data.timeline && data.timeline.length > 0) {
        const labels = data.timeline.map(t => t.time_label);
        const fused = data.timeline.map(t => t.fused_score);
        const visual = data.timeline.map(t => t.visual_score);
        const audio = data.timeline.map(t => t.audio_score);

        engagementChart.data.labels = labels;
        engagementChart.data.datasets[0].data = fused;
        engagementChart.data.datasets[1].data = visual;
        engagementChart.data.datasets[2].data = audio;
        engagementChart.update("none"); // Smooth update without jarring re-render
    }
}

function renderRecommendations(recs) {
    const list = document.getElementById("recommendationsList");
    const countBadge = document.getElementById("recCountBadge");
    if (!list) return;

    countBadge.textContent = `${recs.length} Tips`;

    if (recs.length === 0) {
        list.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding: 2.5rem 1rem;">
                <p>No active recommendations logged yet.</p>
                <p style="font-size: 0.8rem;">Recommendations are generated based on sustained participation shifts.</p>
            </div>`;
        return;
    }

    list.innerHTML = recs.map(r => `
        <div class="rec-item">
            <div class="rec-item-header">
                <span class="rec-category">${r.category}</span>
                <span class="rec-confidence">Evidence: ${r.confidence}</span>
            </div>
            <div class="rec-observation"><strong>Observation:</strong> ${r.observation}</div>
            <div class="rec-action-box"><strong>Suggested Action:</strong> ${r.suggested_action}</div>
            <div class="rec-reason"><strong>Reason:</strong> ${r.reason}</div>
            <div class="rec-footer">
                <span style="font-size: 0.72rem; color: var(--text-muted); margin-right: auto;">
                    Status: <strong style="color: var(--accent-cyan);">${(r.applied_status || "pending").toUpperCase()}</strong>
                </span>
                <button class="btn btn-secondary btn-sm" onclick="markRecStatus(${r.id}, 'acknowledged')">Acknowledge</button>
                <button class="btn btn-primary btn-sm" onclick="markRecStatus(${r.id}, 'applied')">Applied</button>
            </div>
        </div>
    `).join("");
}

async function markRecStatus(recId, status) {
    try {
        const res = await fetch(`/api/recommendations/${recId}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status })
        });
        const data = await res.json();
        if (data.success) {
            fetchSessionData(activeSessionId);
        }
    } catch (e) {
        console.error("Error updating recommendation status:", e);
    }
}
