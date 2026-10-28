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
    """True if loc is a valid (row, col) inside the hospital grid."""
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
        """Runs automatically right after the object is created."""
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
        """Convert to the dictionary format robots.py expects."""
        return {
            "request_id": self.request_id,
            "pickup": self.pickup,
            "destination": self.destination,
            "urgency": self.urgency.value,  # "red", "yellow", or "green"
            "arrival_time": self.arrival_time,
            "task_type": self.task_type,
        }