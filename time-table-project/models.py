from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class Room:
    id: str
    capacity: int
    is_lab: bool

@dataclass(frozen=True)
class ClassSession:
    id: str             # e.g., "C1"
    course_code: str    # e.g., "FAI"
    name: str           # e.g., "Fundamentals of AI"
    instructor_id: str  # e.g., "Dr. Amit Shukla"
    cohort_id: str      # e.g., "1MSc1"
    students_count: int
    requires_lab: bool

@dataclass(frozen=True)
class Timeslot:
    id: str             # e.g., "TS1"
    day: str            # e.g., "Monday"
    time: str           # e.g., "09:30-10:30"

    def __str__(self):
        return f"{self.day} {self.time}"

Assignment = Tuple[Timeslot, Room]