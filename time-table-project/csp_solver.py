import copy
import time
import random
from typing import Dict, List, Optional, Tuple
from models import Room, ClassSession, Timeslot, Assignment

class ClassTimetableCSP:
    def __init__(self, sessions: List[ClassSession], rooms: List[Room], timeslots: List[Timeslot]):
        self.sessions = sessions
        self.rooms = rooms
        self.timeslots = timeslots
        
        # Build domains D(c) = Timeslots x Rooms filtered by static unary constraints
        self.domains: Dict[ClassSession, List[Assignment]] = {}
        for session in self.sessions:
            valid_domain = []
            for slot in timeslots:
                for room in rooms:
                    # Capacity match and Lab match checks
                    if room.capacity >= session.students_count and (not session.requires_lab or room.is_lab):
                        valid_domain.append((slot, room))
            self.domains[session] = valid_domain

    def is_consistent(self, session: ClassSession, assignment: Assignment, schedule: Dict[ClassSession, Assignment]) -> bool:
        """Hard constraint evaluator."""
        slot, room = assignment
        for other_session, (other_slot, other_room) in schedule.items():
            if other_slot.day == slot.day and other_slot.time == slot.time:
                # 1. Room Double-Booking Constraint
                if other_room.id == room.id:
                    return False
                # 2. Faculty Clash Constraint
                if other_session.instructor_id.strip().lower() == session.instructor_id.strip().lower():
                    return False
                # 3. Student Cohort Clash Constraint
                if other_session.cohort_id.strip().lower() == session.cohort_id.strip().lower():
                    return False
        return True

class BacktrackingSolver:
    def __init__(self, csp: ClassTimetableCSP):
        self.csp = csp
        self.backtracks = 0

    def solve(self) -> Tuple[Optional[Dict[ClassSession, Assignment]], float]:
        start_time = time.perf_counter()
        initial_domains = copy.deepcopy(self.csp.domains)
        result = self._backtrack({}, initial_domains)
        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000.0
        return result, execution_time_ms

    def _select_unassigned_variable(
        self, schedule: Dict[ClassSession, Assignment], domains: Dict[ClassSession, List[Assignment]]
    ) -> ClassSession:
        """Minimum Remaining Values (MRV) Heuristic."""
        unassigned = [s for s in self.csp.sessions if s not in schedule]
        return min(unassigned, key=lambda s: len(domains[s]))

    def _forward_check(
        self, 
        assigned_session: ClassSession, 
        assignment: Assignment, 
        domains: Dict[ClassSession, List[Assignment]], 
        schedule: Dict[ClassSession, Assignment]
    ) -> Optional[Dict[ClassSession, List[Assignment]]]:
        """Prunes domains of remaining unassigned variables."""
        new_domains = copy.deepcopy(domains)
        slot, room = assignment

        for unassigned in self.csp.sessions:
            if unassigned in schedule or unassigned == assigned_session:
                continue

            pruned_domain = []
            for (cand_slot, cand_room) in new_domains[unassigned]:
                if cand_slot.day == slot.day and cand_slot.time == slot.time:
                    if (cand_room.id == room.id or 
                        unassigned.instructor_id.strip().lower() == assigned_session.instructor_id.strip().lower() or 
                        unassigned.cohort_id.strip().lower() == assigned_session.cohort_id.strip().lower()):
                        continue
                pruned_domain.append((cand_slot, cand_room))

            if not pruned_domain:
                return None  # Domain wipeout detected
            
            new_domains[unassigned] = pruned_domain

        return new_domains

    def _backtrack(
        self, schedule: Dict[ClassSession, Assignment], domains: Dict[ClassSession, List[Assignment]]
    ) -> Optional[Dict[ClassSession, Assignment]]:
        if len(schedule) == len(self.csp.sessions):
            return schedule

        var = self._select_unassigned_variable(schedule, domains)

        for value in domains[var]:
            if self.csp.is_consistent(var, value, schedule):
                schedule[var] = value
                
                # Forward checking step
                pruned_domains = self._forward_check(var, value, domains, schedule)
                if pruned_domains is not None:
                    result = self._backtrack(schedule, pruned_domains)
                    if result is not None:
                        return result
                
                # Undo assignment (Backtrack)
                del schedule[var]
                self.backtracks += 1

        return None

class MinConflictsSolver:
    def __init__(self, csp: ClassTimetableCSP, max_steps: int = 1000):
        self.csp = csp
        self.max_steps = max_steps

    def _count_conflicts(self, session: ClassSession, assignment: Assignment, schedule: Dict[ClassSession, Assignment]) -> int:
        conflicts = 0
        slot, room = assignment

        for other_session, (other_slot, other_room) in schedule.items():
            if other_session == session:
                continue
            if other_slot.day == slot.day and other_slot.time == slot.time:
                if other_room.id == room.id:
                    conflicts += 1
                if other_session.instructor_id.strip().lower() == session.instructor_id.strip().lower():
                    conflicts += 1
                if other_session.cohort_id.strip().lower() == session.cohort_id.strip().lower():
                    conflicts += 1
        return conflicts

    def solve(self) -> Tuple[Optional[Dict[ClassSession, Assignment]], int]:
        current_schedule: Dict[ClassSession, Assignment] = {}
        for session in self.csp.sessions:
            if not self.csp.domains[session]:
                return None, 0
            current_schedule[session] = random.choice(self.csp.domains[session])

        for step in range(self.max_steps):
            conflicted_sessions = [
                s for s in self.csp.sessions 
                if self._count_conflicts(s, current_schedule[s], current_schedule) > 0
            ]

            if not conflicted_sessions:
                return current_schedule, step

            session = random.choice(conflicted_sessions)
            best_value = current_schedule[session]
            min_conflicts = float('inf')

            for value in self.csp.domains[session]:
                conflicts = self._count_conflicts(session, value, current_schedule)
                if conflicts < min_conflicts:
                    min_conflicts = conflicts
                    best_value = value

            current_schedule[session] = best_value

        return None, self.max_steps

class ConflictExplainer:
    @staticmethod
    def explain_static_impossibility(session: ClassSession, rooms: List[Room]) -> List[str]:
        reasons = []
        suitable_capacity = [r for r in rooms if r.capacity >= session.students_count]
        if not suitable_capacity:
            reasons.append(
                f"Course '{session.course_code}' ({session.name}): Enrolled count ({session.students_count}) exceeds all room capacities."
            )
        elif session.requires_lab:
            suitable_lab = [r for r in suitable_capacity if r.is_lab]
            if not suitable_lab:
                reasons.append(
                    f"Course '{session.course_code}' ({session.name}): Requires a lab, but no lab room has capacity >= {session.students_count}."
                )
        return reasons