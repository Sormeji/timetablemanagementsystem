let rooms = [];
let timeslots = [];
let courses = [];
let currentSchedule = null;

// Load Initial Monsoon 2026 Dataset on Startup
document.addEventListener("DOMContentLoaded", async () => {
    // Initial UI render with empty state
    renderAll();

    try {
        const response = await fetch('/api/initial-data');
        if (!response.ok) throw new Error("Network response was not ok");
        const data = await response.json();
        
        rooms = data.rooms || [];
        timeslots = data.timeslots || [];
        courses = data.courses || [];
        renderAll();
    } catch (err) {
        console.warn("Could not load initial API dataset, starting with fallback UI:", err);
    }

    // Attach form handlers safely
    setupFormListeners();
});

// Render Input Lists
function renderAll() {
    renderCourses();
    renderRooms();
    renderTimeslots();
}

function renderCourses() {
    const list = document.getElementById('courseList');
    if (!list) return;

    if (courses.length === 0) {
        list.innerHTML = `<p class="text-xs text-slate-500 italic p-2">No courses added yet.</p>`;
        return;
    }

    list.innerHTML = courses.map((c, i) => `
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-700/50 flex justify-between items-center text-xs">
            <div>
                <span class="font-bold text-indigo-400">${escapeHtml(c.code)}</span> - ${escapeHtml(c.name || '')}
                <div class="text-slate-400">Faculty: ${escapeHtml(c.instructor)} | Cohort: ${escapeHtml(c.cohort)}</div>
                <div class="text-slate-500">${c.students} Students ${c.requiresLab ? '• 🧪 Lab' : ''}</div>
            </div>
            <button onclick="deleteCourse(${i})" class="text-rose-400 hover:text-rose-300 p-1 font-bold">✕</button>
        </div>
    `).join('');
}

function renderRooms() {
    const list = document.getElementById('roomList');
    if (!list) return;

    if (rooms.length === 0) {
        list.innerHTML = `<p class="text-xs text-slate-500 italic p-2">No rooms added yet.</p>`;
        return;
    }

    list.innerHTML = rooms.map((r, i) => `
        <div class="bg-slate-900/60 p-2.5 rounded border border-slate-700/50 flex justify-between items-center text-xs">
            <div>
                <span class="font-bold text-slate-200">Room ${escapeHtml(r.id)}</span>
                <div class="text-slate-400">Capacity: ${r.capacity} seats</div>
                <div class="text-indigo-400">${r.is_lab ? '🧪 Laboratory' : '🏫 Lecture Hall'}</div>
            </div>
            <button onclick="deleteRoom(${i})" class="text-rose-400 hover:text-rose-300 p-1 font-bold">✕</button>
        </div>
    `).join('');
}

function renderTimeslots() {
    const list = document.getElementById('slotList');
    if (!list) return;

    if (timeslots.length === 0) {
        list.innerHTML = `<p class="text-xs text-slate-500 italic p-2">No timeslots added yet.</p>`;
        return;
    }

    list.innerHTML = timeslots.map((t, i) => `
        <div class="bg-slate-900/40 p-2 rounded flex justify-between items-center text-xs text-slate-300">
            <span>${escapeHtml(t.day)} (${escapeHtml(t.time)})</span>
            <button onclick="deleteSlot(${i})" class="text-rose-400 hover:text-rose-300 font-bold">✕</button>
        </div>
    `).join('');
}

// Attach Form Submit Handlers safely
function setupFormListeners() {
    const courseForm = document.getElementById('courseForm');
    if (courseForm) {
        courseForm.addEventListener('submit', (e) => {
            e.preventDefault();
            courses.push({
                id: "C" + (courses.length + 1),
                code: document.getElementById('cCode').value.trim(),
                name: document.getElementById('cName').value.trim(),
                instructor: document.getElementById('cFaculty').value.trim(),
                cohort: document.getElementById('cCohort').value.trim(),
                students: parseInt(document.getElementById('cStudents').value) || 0,
                requiresLab: document.getElementById('cLab').checked
            });
            e.target.reset();
            renderCourses();
        });
    }

    const roomForm = document.getElementById('roomForm');
    if (roomForm) {
        roomForm.addEventListener('submit', (e) => {
            e.preventDefault();
            rooms.push({
                id: document.getElementById('rId').value.trim(),
                capacity: parseInt(document.getElementById('rCap').value) || 0,
                is_lab: document.getElementById('rLab').checked
            });
            e.target.reset();
            renderRooms();
        });
    }

    const slotForm = document.getElementById('slotForm');
    if (slotForm) {
        slotForm.addEventListener('submit', (e) => {
            e.preventDefault();
            timeslots.push({
                id: "TS" + (timeslots.length + 1),
                day: document.getElementById('sDay').value,
                time: document.getElementById('sTime').value.trim()
            });
            renderTimeslots();
        });
    }
}

function deleteCourse(i) { courses.splice(i, 1); renderCourses(); }
function deleteRoom(i) { rooms.splice(i, 1); renderRooms(); }
function deleteSlot(i) { timeslots.splice(i, 1); renderTimeslots(); }

// Tab Switching
function switchTab(tab) {
    const tabInput = document.getElementById('tabInput');
    const tabOutput = document.getElementById('tabOutput');
    const viewInput = document.getElementById('viewInput');
    const viewOutput = document.getElementById('viewOutput');

    if (!tabInput || !tabOutput || !viewInput || !viewOutput) return;

    if (tab === 'input') {
        tabInput.className = "px-4 py-2 text-sm font-semibold rounded-t-lg bg-slate-800 text-indigo-400 border-t-2 border-indigo-400 cursor-pointer";
        tabOutput.className = "px-4 py-2 text-sm font-semibold rounded-t-lg text-slate-400 hover:text-slate-200 cursor-pointer";
        viewInput.classList.remove('hidden');
        viewOutput.classList.add('hidden');
    } else {
        tabOutput.className = "px-4 py-2 text-sm font-semibold rounded-t-lg bg-slate-800 text-indigo-400 border-t-2 border-indigo-400 cursor-pointer";
        tabInput.className = "px-4 py-2 text-sm font-semibold rounded-t-lg text-slate-400 hover:text-slate-200 cursor-pointer";
        viewOutput.classList.remove('hidden');
        viewInput.classList.add('hidden');
    }
}

// Execute Solver Engine via Flask API
async function runSolver() {
    const diagContainer = document.getElementById('diagnosticContainer');
    const diagList = document.getElementById('diagnosticList');
    if (diagContainer) diagContainer.classList.add('hidden');
    if (diagList) diagList.innerHTML = '';

    try {
        const response = await fetch('/api/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rooms, timeslots, courses })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            currentSchedule = data.schedule;
            const statTime = document.getElementById('statTime');
            const statBacktracks = document.getElementById('statBacktracks');
            const statsBar = document.getElementById('statsBar');
            const exportBtn = document.getElementById('exportBtn');

            if (statTime) statTime.innerText = `${data.stats.timeMs} ms`;
            if (statBacktracks) statBacktracks.innerText = data.stats.backtracks;
            if (statsBar) statsBar.classList.remove('hidden');
            if (exportBtn) exportBtn.classList.remove('hidden');

            renderTimetable(data.schedule);
            switchTab('output');
        } else {
            if (diagContainer) diagContainer.classList.remove('hidden');
            if (diagList) {
                const errors = data.diagnostics || [data.message || "Constraint satisfaction failed."];
                diagList.innerHTML = errors.map(d => `<p>• ${escapeHtml(d)}</p>`).join('');
            }
        }
    } catch (err) {
        console.error("CSP Solver Error:", err);
        if (diagContainer) diagContainer.classList.remove('hidden');
        if (diagList) diagList.innerHTML = `<p>• Error contacting backend Flask CSP server. Make sure Python app is running.</p>`;
    }
}

// Render Timetable Output Grid
function renderTimetable(schedule) {
    const container = document.getElementById('timetableContainer');
    if (!container) return;

    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
    
    let html = '';
    days.forEach(day => {
        const dayItems = Object.entries(schedule).filter(([_, item]) => item.slot && item.slot.day === day);
        if (dayItems.length === 0) return;

        html += `
            <div class="bg-slate-800 border border-slate-700 rounded-xl p-4 space-y-3">
                <h3 class="text-md font-bold text-indigo-400 border-b border-slate-700 pb-2">${day}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    ${dayItems.map(([_, item]) => `
                        <div class="bg-slate-900 border border-slate-700/80 p-3 rounded-lg flex flex-col justify-between space-y-2">
                            <div class="flex justify-between items-start">
                                <span class="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">${escapeHtml(item.slot.time)}</span>
                                <span class="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Venue: ${escapeHtml(item.room.id)}</span>
                            </div>
                            <div>
                                <div class="font-bold text-sm text-slate-100">${escapeHtml(item.courseCode)}: ${escapeHtml(item.courseName || '')}</div>
                                <div class="text-xs text-slate-400 mt-1">Instructor: <span class="text-slate-200">${escapeHtml(item.instructor)}</span></div>
                                <div class="text-xs text-slate-400">Cohort: <span class="text-slate-200">${escapeHtml(item.cohort)}</span> (${item.students} students)</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });

    if (!html) {
        html = `<div class="bg-slate-800 border border-slate-700 rounded-xl p-8 text-center text-slate-400">No scheduled sessions found.</div>`;
    }

    container.innerHTML = html;
}

// Export CSV
function exportCSV() {
    if (!currentSchedule) return;
    let csv = "Day,Time,Room,Course Code,Course Name,Instructor,Cohort,Requires Lab\n";
    Object.values(currentSchedule).forEach(item => {
        csv += `"${item.slot.day}","${item.slot.time}","${item.room.id}","${item.courseCode}","${item.courseName || ''}","${item.instructor}","${item.cohort}","${item.requiresLab ? 'Yes' : 'No'}"\n`;
    });

    const link = document.createElement("a");
    link.href = encodeURI("data:text/csv;charset=utf-8," + csv);
    link.download = "collision_free_timetable.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Helper utility to sanitize strings
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}