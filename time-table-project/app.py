from flask import Flask, render_template, request, jsonify
from models import Room, ClassSession, Timeslot
from csp_solver import ClassTimetableCSP, BacktrackingSolver, MinConflictsSolver, ConflictExplainer

app = Flask(__name__)

# Sample Initial Dataset (Monsoon 2026 Curriculum)
initial_rooms = [
    {"id": "CSE009", "capacity": 60, "is_lab": False},
    {"id": "CSE005", "capacity": 50, "is_lab": False},
    {"id": "CSE010", "capacity": 40, "is_lab": False},
    {"id": "CSE002", "capacity": 35, "is_lab": True},
    {"id": "CSE115", "capacity": 35, "is_lab": True}
]

initial_timeslots = [
    {"id": "TS1", "day": "Monday", "time": "09:30-10:30"},
    {"id": "TS2", "day": "Monday", "time": "11:30-13:00"},
    {"id": "TS3", "day": "Monday", "time": "14:00-15:30"},
    {"id": "TS4", "day": "Tuesday", "time": "09:30-11:00"},
    {"id": "TS5", "day": "Tuesday", "time": "11:00-12:30"},
    {"id": "TS6", "day": "Wednesday", "time": "09:30-11:00"},
    {"id": "TS7", "day": "Wednesday", "time": "11:00-12:30"},
    {"id": "TS8", "day": "Thursday", "time": "09:30-11:00"},
    {"id": "TS9", "day": "Thursday", "time": "14:00-15:30"},
    {"id": "TS10", "day": "Friday", "time": "09:30-11:00"},
    {"id": "TS11", "day": "Friday", "time": "11:00-12:30"}
]

initial_courses = [
    {"id": "C1", "code": "FAI", "name": "Fundamentals of AI", "instructor": "Dr. Amit Shukla", "cohort": "1MSc1", "students": 45, "requiresLab": False},
    {"id": "C2", "code": "FML", "name": "Fundamentals of ML", "instructor": "Dr. Reshma Rastogi", "cohort": "1MSc1", "students": 30, "requiresLab": True},
    {"id": "C3", "code": "OSD", "name": "Operating Systems", "instructor": "Dr. Shachi Sharma", "cohort": "MCA1", "students": 40, "requiresLab": False},
    {"id": "C4", "code": "MFCS", "name": "Math Foundations", "instructor": "Dr. Manvi Grover", "cohort": "MCA1", "students": 40, "requiresLab": False},
    {"id": "C5", "code": "OT", "name": "Optimization Tech", "instructor": "Dr. Garima", "cohort": "1MSc1", "students": 45, "requiresLab": False},
    {"id": "C6", "code": "FSD3", "name": "Full Stack Dev 3", "instructor": "Dr. Anurag Tiwari", "cohort": "MCA3", "students": 30, "requiresLab": True},
    {"id": "C7", "code": "COD", "name": "Computer Org", "instructor": "Prof. Pranab K. Muhuri", "cohort": "MCA1", "students": 40, "requiresLab": False},
    {"id": "C8", "code": "DBMS", "name": "Database Systems", "instructor": "Dr. Ashwini B", "cohort": "MCA1", "students": 30, "requiresLab": True}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/initial-data', methods=['GET'])
def get_initial_data():
    return jsonify({
        "rooms": initial_rooms,
        "timeslots": initial_timeslots,
        "courses": initial_courses
    })

@app.route('/api/solve', methods=['POST'])
def solve_timetable():
    data = request.json
    raw_rooms = data.get('rooms', [])
    raw_slots = data.get('timeslots', [])
    raw_courses = data.get('courses', [])

    # Instantiate data model objects
    rooms = [Room(id=r['id'], capacity=int(r['capacity']), is_lab=r['is_lab']) for r in raw_rooms]
    timeslots = [Timeslot(id=t.get('id', f"TS{i}"), day=t['day'], time=t['time']) for i, t in enumerate(raw_slots)]
    sessions = [
        ClassSession(
            id=c['id'],
            course_code=c['code'],
            name=c.get('name', ''),
            instructor_id=c['instructor'],
            cohort_id=c['cohort'],
            students_count=int(c['students']),
            requires_lab=c['requiresLab']
        ) for c in raw_courses
    ]

    # Initialize CSP
    csp = ClassTimetableCSP(sessions, rooms, timeslots)

    # 1. Check for domain wipeouts/static conflicts before solving
    diagnostics = []
    for session in sessions:
        if not csp.domains[session]:
            reasons = ConflictExplainer.explain_static_impossibility(session, rooms)
            diagnostics.extend(reasons)

    if diagnostics:
        return jsonify({
            "success": False,
            "schedule": None,
            "diagnostics": diagnostics,
            "stats": None
        }), 400

    # 2. Run Backtracking Search with Forward Checking
    solver = BacktrackingSolver(csp)
    solution, execution_time = solver.solve()

    if solution:
        # Format response
        formatted_schedule = {}
        for session, (slot, room) in solution.items():
            formatted_schedule[session.id] = {
                "courseCode": session.course_code,
                "courseName": session.name,
                "instructor": session.instructor_id,
                "cohort": session.cohort_id,
                "students": session.students_count,
                "requiresLab": session.requires_lab,
                "slot": {"id": slot.id, "day": slot.day, "time": slot.time},
                "room": {"id": room.id, "capacity": room.capacity, "is_lab": room.is_lab}
            }
        return jsonify({
            "success": True,
            "schedule": formatted_schedule,
            "diagnostics": [],
            "stats": {
                "timeMs": round(execution_time, 2),
                "backtracks": solver.backtracks
            }
        })
    else:
        return jsonify({
            "success": False,
            "schedule": None,
            "diagnostics": ["Backtracking search exhausted without finding a conflict-free solution. Hard constraints violate faculty, cohort, or room boundaries. Try adding more timeslots or venues."],
            "stats": {"timeMs": round(execution_time, 2), "backtracks": solver.backtracks}
        }), 422

if __name__ == '__main__':
    app.run(debug=True, port=5000)