/**
 * Multimodal Attendance & Engagement Agent
 * Attendance Review & Identity Binding Controller
 */

let allAttendanceRecords = [];
let currentSessionId = null;
let currentClassroomId = null;

document.addEventListener("DOMContentLoaded", () => {
    initAttendancePage();
    setupModalsAndFilters();
});

async function initAttendancePage() {
    const sel = document.getElementById("attSessionFilter");
    if (!sel) return;

    try {
        const res = await fetch("/api/sessions");
        const json = await res.json();
        sel.innerHTML = "";

        if (!json.success || json.data.length === 0) {
            sel.innerHTML = '<option value="">No sessions available</option>';
            return;
        }

        json.data.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.dataset.classId = s.classroom_id;
            opt.textContent = `#${s.id} - ${s.title} (${s.classroom_code || "Class"})`;
            sel.appendChild(opt);
        });

        if (sel.options.length > 0) {
            currentSessionId = parseInt(sel.value);
            currentClassroomId = parseInt(sel.selectedOptions[0].dataset.classId);
            loadAttendance(currentSessionId);
        }
    } catch (e) {
        console.error("Error loading session options:", e);
    }
}

async function loadAttendance(sessionId) {
    if (!sessionId) return;
    const tbody = document.getElementById("attendanceTableBody");
    if (!tbody) return;

    try {
        const res = await fetch(`/api/sessions/${sessionId}/attendance`);
        const json = await res.json();

        if (json.success) {
            allAttendanceRecords = json.data || [];
            applyFilters();
            updateAttendanceStats(allAttendanceRecords);
        }
    } catch (e) {
        console.error("Error loading attendance:", e);
    }
}

function updateAttendanceStats(records) {
    const detected = records.length;
    const present = records.filter(r => r.status === "present").length;
    const transient = records.filter(r => r.status === "transient").length;
    const reviewed = records.filter(r => r.reviewed_by_teacher === 1).length;

    document.getElementById("attStatDetected").textContent = detected;
    document.getElementById("attStatPresent").textContent = present;
    document.getElementById("attStatTransient").textContent = transient;
    document.getElementById("attStatReviewed").textContent = reviewed;
}

function applyFilters() {
    const query = (document.getElementById("attSearchInput").value || "").toLowerCase();
    const statusFilter = document.getElementById("attStatusFilter").value;

    const filtered = allAttendanceRecords.filter(r => {
        const matchesQuery = (
            r.participant_track_id.toLowerCase().includes(query) ||
            (r.student_name && r.student_name.toLowerCase().includes(query)) ||
            (r.student_id_number && r.student_id_number.toLowerCase().includes(query))
        );
        const matchesStatus = (statusFilter === "all" || r.status === statusFilter);
        return matchesQuery && matchesStatus;
    });

    renderAttendanceTable(filtered);
}

function renderAttendanceTable(records) {
    const tbody = document.getElementById("attendanceTableBody");
    if (!tbody) return;

    if (records.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
                    No attendance records match the selected criteria.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = records.map(r => {
        const isPresent = r.status === "present";
        const badgeClass = isPresent ? "status-present" : (r.status === "transient" ? "status-transient" : "status-absent");
        const fwdPct = Math.round((r.avg_head_pose_forward || 0) * 100);
        const firstSeenFmt = r.first_seen.split("T")[1]?.slice(0, 8) || r.first_seen;
        const lastSeenFmt = r.last_seen.split("T")[1]?.slice(0, 8) || r.last_seen;

        const studentDisplay = r.student_name 
            ? `<strong>${r.student_name}</strong> <span style="font-size: 0.75rem; color: var(--text-muted);">(${r.student_id_number})</span>`
            : `<button class="btn btn-secondary btn-sm" onclick="openBindModal('${r.participant_track_id}')"><i data-feather="link"></i> Bind Student</button>`;

        const verificationDisplay = r.reviewed_by_teacher
            ? `<span class="badge" style="background: var(--accent-purple-dim); color: var(--accent-purple);">Teacher Verified</span>`
            : `<span style="font-size: 0.75rem; color: var(--text-muted);">Auto Calculated</span>`;

        return `
            <tr>
                <td><strong>${r.participant_track_id}</strong></td>
                <td>${studentDisplay}</td>
                <td>${firstSeenFmt}</td>
                <td>${lastSeenFmt}</td>
                <td><strong>${r.presence_duration_seconds}s</strong></td>
                <td>${r.presence_percentage}%</td>
                <td>${fwdPct}%</td>
                <td><span class="status-badge ${badgeClass}">${r.status}</span></td>
                <td>${verificationDisplay}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="openReviewModal(${r.id}, '${r.participant_track_id}', '${r.status}')">
                        <i data-feather="edit-2"></i> Review
                    </button>
                </td>
            </tr>
        `;
    }).join("");

    if (window.feather) feather.replace();
}

function setupModalsAndFilters() {
    // Session filter dropdown
    const sel = document.getElementById("attSessionFilter");
    if (sel) {
        sel.addEventListener("change", (e) => {
            currentSessionId = parseInt(e.target.value);
            currentClassroomId = parseInt(e.target.selectedOptions[0].dataset.classId);
            loadAttendance(currentSessionId);
        });
    }

    // Search and Status filters
    const search = document.getElementById("attSearchInput");
    const statusSel = document.getElementById("attStatusFilter");
    if (search) search.addEventListener("input", applyFilters);
    if (statusSel) statusSel.addEventListener("change", applyFilters);

    // CSV Export
    const btnExport = document.getElementById("btnExportCsv");
    if (btnExport) btnExport.addEventListener("click", exportAttendanceCsv);

    // Review Modal
    const revModal = document.getElementById("reviewModal");
    const btnCloseRev = document.getElementById("btnCloseReviewModal");
    const btnCancelRev = document.getElementById("btnCancelReviewModal");
    if (btnCloseRev) btnCloseRev.addEventListener("click", () => revModal.style.display = "none");
    if (btnCancelRev) btnCancelRev.addEventListener("click", () => revModal.style.display = "none");

    const revForm = document.getElementById("reviewRecordForm");
    if (revForm) {
        revForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const recId = document.getElementById("modalRecordId").value;
            const newStatus = document.getElementById("modalStatusSelect").value;
            const teacher = document.getElementById("modalTeacherName").value;
            const notes = document.getElementById("modalReviewNotes").value;

            try {
                const res = await fetch(`/api/attendance/${recId}/review`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        status: newStatus,
                        teacher_name: teacher,
                        notes: notes
                    })
                });
                const data = await res.json();
                if (data.success) {
                    revModal.style.display = "none";
                    loadAttendance(currentSessionId);
                } else {
                    alert("Review error: " + data.error);
                }
            } catch (err) {
                alert("Request failed: " + err);
            }
        });
    }

    // Bind Modal
    const bindModal = document.getElementById("bindModal");
    const btnCloseBind = document.getElementById("btnCloseBindModal");
    const btnCancelBind = document.getElementById("btnCancelBindModal");
    if (btnCloseBind) btnCloseBind.addEventListener("click", () => bindModal.style.display = "none");
    if (btnCancelBind) btnCancelBind.addEventListener("click", () => bindModal.style.display = "none");

    const bindForm = document.getElementById("bindStudentForm");
    if (bindForm) {
        bindForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const trackId = document.getElementById("bindModalTrackId").value;
            const studentId = document.getElementById("bindStudentSelect").value;

            try {
                const res = await fetch(`/api/sessions/${currentSessionId}/attendance/bind`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ track_id: trackId, student_id: studentId })
                });
                const data = await res.json();
                if (data.success) {
                    bindModal.style.display = "none";
                    loadAttendance(currentSessionId);
                } else {
                    alert("Binding error: " + data.error);
                }
            } catch (err) {
                alert("Request failed: " + err);
            }
        });
    }
}

function openReviewModal(recordId, trackId, currentStatus) {
    document.getElementById("modalRecordId").value = recordId;
    document.getElementById("modalTrackId").value = trackId;
    document.getElementById("modalStatusSelect").value = currentStatus;
    document.getElementById("reviewModal").style.display = "flex";
}

async function openBindModal(trackId) {
    document.getElementById("bindModalTrackId").value = trackId;
    document.getElementById("bindModalTrackDisplay").value = trackId;
    
    const sel = document.getElementById("bindStudentSelect");
    sel.innerHTML = "<option value=''>Loading enrolled students...</option>";

    if (currentClassroomId) {
        try {
            const res = await fetch(`/api/classes/${currentClassroomId}/students`);
            const json = await res.json();
            sel.innerHTML = "<option value=''>Select Student Profile...</option>";
            if (json.success && json.data) {
                json.data.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s.id;
                    opt.textContent = `${s.name} (${s.student_id_number})`;
                    sel.appendChild(opt);
                });
            }
        } catch (e) {
            console.error("Error loading students for bind:", e);
        }
    }

    document.getElementById("bindModal").style.display = "flex";
}

function exportAttendanceCsv() {
    if (allAttendanceRecords.length === 0) {
        alert("No attendance records to export.");
        return;
    }

    const headers = ["Track ID", "Student Name", "Student ID", "Status", "Presence Sec", "Presence Pct", "Forward Gaze Pct", "First Seen", "Last Seen", "Teacher Verified"];
    const rows = allAttendanceRecords.map(r => [
        `"${r.participant_track_id}"`,
        `"${r.student_name || 'Anonymous'}"`,
        `"${r.student_id_number || ''}"`,
        `"${r.status}"`,
        r.presence_duration_seconds,
        r.presence_percentage,
        Math.round((r.avg_head_pose_forward || 0) * 100),
        `"${r.first_seen}"`,
        `"${r.last_seen}"`,
        r.reviewed_by_teacher ? "Yes" : "Auto"
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `attendance_session_${currentSessionId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
