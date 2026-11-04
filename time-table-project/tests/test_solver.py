import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, initial_rooms, initial_timeslots, initial_courses
from csp_solver import ClassTimetableCSP, BacktrackingSolver, MinConflictsSolver
from models import Room, ClassSession, Timeslot

BASE = {"rooms": initial_rooms, "timeslots": initial_timeslots, "courses": initial_courses}


def session(id, cohort="A", instructor="X", students=10, lab=False, course_id=""):
    return ClassSession(id, id, id, instructor, cohort, students, lab, course_id or id)


class TimeslotTests(unittest.TestCase):
    def test_overlap(self):
        a = Timeslot.create("1", "Monday", "09:00-11:00")
        self.assertTrue(a.overlaps(Timeslot.create("2", "Monday", "10:00-12:00")))
        self.assertFalse(a.overlaps(Timeslot.create("3", "Monday", "11:00-12:00")))  # back-to-back is fine
        self.assertFalse(a.overlaps(Timeslot.create("4", "Tuesday", "09:00-11:00")))

    def test_invalid_time(self):
        for bad in ("9-10", "11:00-10:00", "25:00-26:00", ""):
            with self.assertRaises(ValueError):
                Timeslot.create("1", "Monday", bad)


class SolverTests(unittest.TestCase):
    def assert_valid(self, csp, schedule):
        self.assertEqual(len(schedule), len(csp.sessions))
        items = list(schedule.items())
        for i, (a, av) in enumerate(items):
            self.assertIn(av, csp.domains[a])
            for b, bv in items[i + 1:]:
                self.assertFalse(csp.conflicts(a, av, b, bv), f"{a.id} clashes with {b.id}")

    def test_overlapping_slots_are_respected(self):
        slots = [Timeslot.create("1", "Mon", "09:00-11:00"), Timeslot.create("2", "Mon", "10:00-12:00"),
                 Timeslot.create("3", "Mon", "11:00-12:00")]
        csp = ClassTimetableCSP([session("a"), session("b")], [Room("R", 50, False)], slots)
        result, _ = BacktrackingSolver(csp).solve()
        self.assert_valid(csp, result)
        self.assertEqual({v[0].id for v in result.values()} & {"1", "3"}, {"1", "3"})

    def test_best_fit_room(self):
        rooms = [Room("Big", 200, False), Room("Small", 20, False)]
        csp = ClassTimetableCSP([session("a", students=15)], rooms, [Timeslot.create("1", "Mon", "09:00-10:00")])
        result, _ = BacktrackingSolver(csp).solve()
        self.assertEqual(next(iter(result.values()))[1].id, "Small")

    def test_same_course_different_days(self):
        slots = [Timeslot.create(str(i), d, t) for i, (d, t) in enumerate(
            [("Mon", "09:00-10:00"), ("Mon", "10:00-11:00"), ("Tue", "09:00-10:00")])]
        sessions = [session("a1", course_id="A"), session("a2", course_id="A")]
        csp = ClassTimetableCSP(sessions, [Room("R", 50, False)], slots)
        result, _ = BacktrackingSolver(csp).solve()
        self.assert_valid(csp, result)
        self.assertEqual({v[0].day for v in result.values()}, {"Mon", "Tue"})

    def test_infeasible_returns_none(self):
        csp = ClassTimetableCSP([session("a"), session("b")], [Room("R", 50, False)],
                                [Timeslot.create("1", "Mon", "09:00-10:00")])
        solver = BacktrackingSolver(csp)
        self.assertIsNone(solver.solve()[0])
        self.assertFalse(solver.timed_out)

    def test_min_conflicts_finds_valid_schedule(self):
        slots = [Timeslot.create(str(i), "Mon", f"{8 + i:02d}:00-{9 + i:02d}:00") for i in range(6)]
        sessions = [session(f"s{i}", cohort=f"C{i % 3}", instructor=f"I{i % 2}") for i in range(6)]
        csp = ClassTimetableCSP(sessions, [Room("R1", 50, False), Room("R2", 50, False)], slots)
        result, _ = MinConflictsSolver(csp, seed=1).solve()
        self.assert_valid(csp, result)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_sample_data_solves(self):
        r = self.client.post("/api/solve", json=BASE)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json["schedule"]), len(initial_courses))

    def test_duplicate_course_ids_are_not_lost(self):
        courses = [dict(c, id="C1") for c in initial_courses]
        r = self.client.post("/api/solve", json=dict(BASE, courses=courses))
        self.assertEqual(len(r.json["schedule"]), len(initial_courses))

    def test_sessions_per_week(self):
        courses = [dict(c, sessionsPerWeek=2) for c in initial_courses]
        r = self.client.post("/api/solve", json=dict(BASE, courses=courses))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json["schedule"]), 2 * len(initial_courses))

    def test_pigeonhole_is_reported_immediately(self):
        courses = [dict(initial_courses[0], instructor=f"I{i}") for i in range(len(initial_timeslots) + 1)]
        r = self.client.post("/api/solve", json=dict(BASE, courses=courses))
        self.assertEqual(r.status_code, 400)
        self.assertIn("non-overlapping", r.json["diagnostics"][0])

    def test_bad_input_returns_400(self):
        self.assertEqual(self.client.post("/api/solve", data="x", content_type="text/plain").status_code, 400)
        self.assertEqual(self.client.post("/api/solve", json=dict(BASE, courses=[{"id": "C1"}])).status_code, 400)
        r = self.client.post("/api/solve", json=dict(BASE, timeslots=[{"day": "Monday", "time": "9-10"}]))
        self.assertEqual(r.status_code, 400)

    def test_no_timeslots_message(self):
        r = self.client.post("/api/solve", json=dict(BASE, timeslots=[]))
        self.assertIn("No timeslots", r.json["diagnostics"][0])


if __name__ == "__main__":
    unittest.main()
