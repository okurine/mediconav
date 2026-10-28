import heapq
import itertools

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from temp_layout import GRID_ROWS, GRID_COLS

# A location is a (row, column) pair, e.g. (3, 7)
Location = Tuple[int, int]


class Urgency(Enum):
    RED = "red"        # high priority
    YELLOW = "yellow"  # medium priority
    GREEN = "green"    # low priority


# Lower number = served first by the queue
URGENCY_PRIORITY = {
    Urgency.RED: 1,
    Urgency.YELLOW: 2,
    Urgency.GREEN: 3,
}


class RequestStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"


def is_in_bounds(loc: Location) -> bool:
    # True if loc is a valid (row, col) inside the hospital grid.
    row, col = loc
    return 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS


@dataclass
class DeliveryRequest:
    request_id: str
    pickup: Location
    destination: Location
    arrival_time: int
    urgency: Urgency
    task_type: str = "medicine"
    status: RequestStatus = RequestStatus.PENDING
    assigned_robot_id: Optional[int] = None

    def __post_init__(self):
        # Runs automatically right after the object is created.
        if not is_in_bounds(self.pickup):
            raise ValueError(f"{self.request_id}: pickup {self.pickup} is outside the grid")
        if not is_in_bounds(self.destination):
            raise ValueError(f"{self.request_id}: destination {self.destination} is outside the grid")
        if self.pickup == self.destination:
            raise ValueError(f"{self.request_id}: pickup and destination are the same")
        if self.arrival_time < 0:
            raise ValueError(f"{self.request_id}: arrival_time cannot be negative")
        if not isinstance(self.urgency, Urgency):
            raise ValueError(f"{self.request_id}: urgency must be an Urgency value")

    def to_dict(self) -> dict:
        # Convert to the dictionary format robots.py expects.
        return {
            "request_id": self.request_id,
            "pickup": self.pickup,
            "destination": self.destination,
            "urgency": self.urgency.value,  # "red", "yellow", or "green"
            "arrival_time": self.arrival_time,
            "task_type": self.task_type,
        }


# Pending requests waiting for a robot.
# Order: red before yellow before green.
# Same urgency: earliest arrival first (FIFO)
class RequestQueue:
    def __init__(self):
        self._heap = []
        self._ids = set()
        self._counter = itertools.count()

    def add(self, request):
        if request.status != RequestStatus.PENDING:
            raise ValueError(f"{request.request_id} is not pending")
        if request.request_id in self._ids:
            raise ValueError(f"{request.request_id} is already in the queue")

        entry = (
            URGENCY_PRIORITY[request.urgency],  # 1. urgency
            request.arrival_time,               # 2. arrival time
            next(self._counter),                # 3. tie-breaker
            request,
        )
        heapq.heappush(self._heap, entry)
        self._ids.add(request.request_id)

    def pop_next(self):
        # Remove and return the highest-priority request, or None if empty
        if not self._heap:
            return None
        request = heapq.heappop(self._heap)[-1]
        self._ids.remove(request.request_id)
        return request

    def peek_next(self):
        # Return the highest-priority request without removing it, or None
        return self._heap[0][-1] if self._heap else None

    def __len__(self):
        return len(self._heap)

    def pending_requests(self):
        # All waiting requests in priority order (for display or the dispatcher)
        return [entry[-1] for entry in sorted(self._heap)]

    def count_by_urgency(self):
        counts = {u.value: 0 for u in Urgency}
        for entry in self._heap:
            counts[entry[-1].urgency.value] += 1
        return counts

# Holds generated requests and releases them when their arrival time is reached
class ArrivalSchedule:

    def __init__(self, requests):
        self._upcoming = sorted(requests, key=lambda r: r.arrival_time)
        self._next_index = 0

    def release(self, current_time):
        # Return all requests whose arrival_time <= current_time that haven't been released yet
        arrived = []
        while (
            self._next_index < len(self._upcoming)
            and self._upcoming[self._next_index].arrival_time <= current_time
        ):
            arrived.append(self._upcoming[self._next_index])
            self._next_index += 1
        return arrived

    def remaining(self):
        # Number of requests that haven't arrived yet
        return len(self._upcoming) - self._next_index
