/**
 * Multimodal Attendance & Engagement Agent
 * Session Management & Creation Controller
 */

let uploadedVideoPath = "";
let uploadedAudioPath = "";

document.addEventListener("DOMContentLoaded", () => {
    loadSessionsList();
    loadClassroomsDropdown();
    setupSessionModals();
});

async function loadSessionsList() {
    const tbody = document.getElementById("sessionsTableBody");
    const countBadge = document.getElementById("sessionTableCountBadge");
    if (!tbody) return;

    try {
        const res = await fetch("/api/sessions");
        const json = await res.json();
        
        if (!json.success || json.data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
                        No sessions recorded yet. Click "Create New Session" or "Seed Demo Data" to begin.
                    </td>
                </tr>`;
            if (countBadge) countBadge.textContent = "0 Sessions";
            return;
        }

        if (countBadge) countBadge.textContent = `${json.data.length} Sessions`;

        tbody.innerHTML = json.data.map(s => {
            const isLive = s.is_live;
            const statusClass = isLive ? "status-present" : (s.status === "completed" ? "status-excused" : "status-transient");
            const durationMin = Math.round((s.duration_seconds || 0) / 60);

            return `
                <tr>
                    <td><strong>#${s.id}</strong></td>
                    <td><strong>${s.title}</strong></td>
                    <td>${s.classroom_name || "Class"} (${s.classroom_code || "CS"})</td>
                    <td><span class="badge" style="background: rgba(0, 240, 255, 0.1); color: var(--accent-cyan);">${s.input_type}</span></td>
                    <td>${durationMin} min</td>
                    <td>${s.present_count || 0} / ${s.total_detected_count || 0}</td>
                    <td><span class="status-badge ${statusClass}">${isLive ? "LIVE 🔴" : s.status}</span></td>
                    <td>
                        <div style="display: flex; gap: 0.4rem;">
                            ${isLive ? `
                                <button class="btn btn-danger btn-sm" onclick="stopSessionFromTable(${s.id})"><i data-feather="square"></i> Stop</button>
                                <a href="/" class="btn btn-primary btn-sm"><i data-feather="eye"></i> Live</a>
                            ` : `
                                <button class="btn btn-secondary btn-sm" onclick="startSessionFromTable(${s.id})"><i data-feather="play"></i> Start</button>
                                <a href="/reports" class="btn btn-secondary btn-sm"><i data-feather="file-text"></i> Report</a>
                            `}
                        </div>
                    </td>
                </tr>
            `;
        }).join("");

        if (window.feather) feather.replace();
    } catch (e) {
        console.error("Error loading sessions list:", e);
    }
}

async function loadClassroomsDropdown() {
    const sel = document.getElementById("modalClassSelect");
    if (!sel) return;

    try {
        const res = await fetch("/api/classes");
        const json = await res.json();
        sel.innerHTML = '<option value="">Select Classroom...</option>';

        if (json.success && json.data) {
            json.data.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.id;
                opt.textContent = `${c.name} (${c.code})`;
                sel.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Error loading classrooms dropdown:", e);
    }
}

function setupSessionModals() {
    // Session Modal
    const sessModal = document.getElementById("newSessionModal");
    const btnOpenSess = document.getElementById("btnOpenNewSessionModal");
    const btnCloseSess = document.getElementById("btnCloseSessionModal");
    const btnCancelSess = document.getElementById("btnCancelSessionModal");

    if (btnOpenSess) btnOpenSess.addEventListener("click", () => {
        loadClassroomsDropdown();
        sessModal.style.display = "flex";
    });
    if (btnCloseSess) btnCloseSess.addEventListener("click", () => sessModal.style.display = "none");
    if (btnCancelSess) btnCancelSess.addEventListener("click", () => sessModal.style.display = "none");

    // Classroom Modal
    const classModal = document.getElementById("classroomModal");
    const btnOpenClass = document.getElementById("btnOpenClassroomModal");
    const btnCloseClass = document.getElementById("btnCloseClassModal");
    const btnCancelClass = document.getElementById("btnCancelClassModal");

    if (btnOpenClass) btnOpenClass.addEventListener("click", () => classModal.style.display = "flex");
    if (btnCloseClass) btnCloseClass.addEventListener("click", () => classModal.style.display = "none");
    if (btnCancelClass) btnCancelClass.addEventListener("click", () => classModal.style.display = "none");

    // Input Type toggle
    const inputTypeSel = document.getElementById("modalInputType");
    const vidGroup = document.getElementById("videoUploadGroup");
    const audGroup = document.getElementById("audioUploadGroup");

    if (inputTypeSel) {
        inputTypeSel.addEventListener("change", (e) => {
            const val = e.target.value;
            vidGroup.style.display = (val === "video_file" || val === "multimodal") ? "block" : "none";
            audGroup.style.display = (val === "audio_file" || val === "multimodal") ? "block" : "none";
        });
    }

    // File Upload Listeners
    const vidFileInput = document.getElementById("modalVideoFile");
    if (vidFileInput) {
        vidFileInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (file) {
                uploadedVideoPath = await uploadFile(file, "videoUploadStatus");
            }
        });
    }

    const audFileInput = document.getElementById("modalAudioFile");
    if (audFileInput) {
        audFileInput.addEventListener("change", async (e) => {
            const file = e.target.files[0];
            if (file) {
                uploadedAudioPath = await uploadFile(file, "audioUploadStatus");
            }
        });
    }

    // Submit New Session Form
    const sessForm = document.getElementById("newSessionForm");
    if (sessForm) {
        sessForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const classId = document.getElementById("modalClassSelect").value;
            const title = document.getElementById("modalSessionTitle").value;
            const inputType = document.getElementById("modalInputType").value;
            const notes = document.getElementById("modalSessionNotes").value;

            try {
                const res = await fetch("/api/sessions", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        classroom_id: classId,
                        title: title,
                        input_type: inputType,
                        video_source: uploadedVideoPath,
                        audio_source: uploadedAudioPath,
                        notes: notes
                    })
                });
                const data = await res.json();
                if (data.success) {
                    sessModal.style.display = "none";
                    // Immediately launch session worker
                    await fetch(`/api/sessions/${data.session_id}/start`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({})
                    });
                    alert(`Session #${data.session_id} launched! Redirecting to live dashboard...`);
                    window.location.href = "/";
                } else {
                    alert("Error creating session: " + data.error);
                }
            } catch (err) {
                alert("Request failed: " + err);
            }
        });
    }

    // Submit New Classroom Form
    const classForm = document.getElementById("newClassForm");
    if (classForm) {
        classForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("modalClassName").value;
            const code = document.getElementById("modalClassCode").value;
            const subject = document.getElementById("modalClassSubject").value;
            const dept = document.getElementById("modalClassDept").value;

            try {
                const res = await fetch("/api/classes", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, code, subject, department: dept })
                });
                const data = await res.json();
                if (data.success) {
                    alert("Classroom created successfully!");
                    classModal.style.display = "none";
                    loadClassroomsDropdown();
                } else {
                    alert("Error: " + data.error);
                }
            } catch (err) {
                alert("Request failed: " + err);
            }
        });
    }
}

async function uploadFile(file, statusElId) {
    const statusEl = document.getElementById(statusElId);
    if (statusEl) statusEl.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        const json = await res.json();
        if (json.success) {
            if (statusEl) statusEl.textContent = `✓ Uploaded: ${json.filename}`;
            return json.file_path;
        } else {
            if (statusEl) statusEl.textContent = `Upload failed: ${json.error}`;
            return "";
        }
    } catch (e) {
        if (statusEl) statusEl.textContent = `Upload error: ${e}`;
        return "";
    }
}

async function startSessionFromTable(sessionId) {
    try {
        const res = await fetch(`/api/sessions/${sessionId}/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
            loadSessionsList();
        } else {
            alert("Error: " + data.error);
        }
    } catch (e) {
        alert("Failed to start session: " + e);
    }
}

async function stopSessionFromTable(sessionId) {
    try {
        const res = await fetch(`/api/sessions/${sessionId}/stop`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        const data = await res.json();
        if (data.success) {
            loadSessionsList();
        } else {
            alert("Error: " + data.error);
        }
    } catch (e) {
        alert("Failed to stop session: " + e);
    }
}
