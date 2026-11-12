# Synthetic delivery request generator.
# Generates reproducible requests for different demand scenarios.

import random
from dataclasses import dataclass

from delivery_requests import DeliveryRequest, Urgency, RequestQueue, ArrivalSchedule, TASK_TYPES
from environment import LAYOUT, build_grid

# Task locations come straight from the real map
_, _cells = build_grid(LAYOUT)
LOCATION_CELLS = {letter: _cells[letter] for letter in "PMEIWLN"}

# Which letters each task type may start from and end at
REQUEST_TYPES = {
    "medication":       {"pickups": ["P"],           "destinations": ["E", "I", "W", "N"]},
    "medical_supplies": {"pickups": ["M"],           "destinations": ["E", "I", "W", "N"]},
    "lab_sample":       {"pickups": ["E", "I", "W"], "destinations": ["L"]},
}

assert set(REQUEST_TYPES) == set(TASK_TYPES), "REQUEST_TYPES and TASK_TYPES are out of sync"

@dataclass(frozen=True)
class Scenario:
    #Settings that describe one demand scenario.
    name: str
    num_requests: int
    mean_gap: float        # average time steps between arrivals
    urgency_weights: dict  # Urgency -> relative probability


SCENARIOS = {
    "normal": Scenario(
        name="normal",
        num_requests=20,
        mean_gap=10.0,
        urgency_weights={Urgency.RED: 0.15, Urgency.YELLOW: 0.35, Urgency.GREEN: 0.50},
    ),
    "busy": Scenario(
        name="busy",
        num_requests=40,
        mean_gap=3.0,
        urgency_weights={Urgency.RED: 0.15, Urgency.YELLOW: 0.35, Urgency.GREEN: 0.50},
    ),
    "emergency_heavy": Scenario(
        name="emergency_heavy",
        num_requests=20,
        mean_gap=10.0,
        urgency_weights={Urgency.RED: 0.60, Urgency.YELLOW: 0.30, Urgency.GREEN: 0.10},
    ),
}

TRAIN_SEEDS = list(range(1, 51))     # Q-learning learns on these days
TEST_SEEDS = list(range(100, 121))   # both dispatchers are scored on these unseen days


def generate_requests(
    scenario,
    seed=42,
    location_cells=LOCATION_CELLS,
    request_types=REQUEST_TYPES,
):
    #Generate a list of DeliveryRequests for one scenario, sorted by arrival time
    rng = random.Random(seed)

    urgencies = list(scenario.urgency_weights.keys())
    weights = list(scenario.urgency_weights.values())
    type_names = list(request_types.keys())

    requests = []
    current_time = 0.0

    for i in range(scenario.num_requests):
        current_time += rng.expovariate(1.0 / scenario.mean_gap)
        arrival_time = int(round(current_time))

        urgency = rng.choices(urgencies, weights=weights, k=1)[0]

        # The task type decides which letters are allowed for pickup and destination
        task_type = rng.choice(type_names)
        rule = request_types[task_type]
        pickup_letter = rng.choice(rule["pickups"])
        destination_letter = rng.choice(rule["destinations"])

        # A letter may cover several cells; pick one
        pickup = rng.choice(location_cells[pickup_letter])
        destination = rng.choice(location_cells[destination_letter])

        requests.append(
            DeliveryRequest(
                request_id=f"REQ-{i + 1:03d}",
                pickup=pickup,
                destination=destination,
                arrival_time=arrival_time,
                urgency=urgency,
                task_type=task_type,
            )
        )

    return requests


def summarize(requests):
    #Count requests per urgency level, e.g. {'red': 3, 'yellow': 7, 'green': 10}
    counts = {u.value: 0 for u in Urgency}
    for r in requests:
        counts[r.urgency.value] += 1
    return counts
