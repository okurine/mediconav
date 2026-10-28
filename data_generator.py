# Synthetic delivery request generator.
# Generates reproducible requests for different demand scenarios.

import random
from dataclasses import dataclass

from delivery_requests import DeliveryRequest, Urgency
from temp_layout import TEMP_PICKUP_LOCATIONS, TEMP_DESTINATIONS, TEMP_TASK_TYPES


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


def generate_requests(
    scenario,
    seed=42,
    pickups=TEMP_PICKUP_LOCATIONS,
    destinations=TEMP_DESTINATIONS,
    task_types=TEMP_TASK_TYPES,
):
    #Generate a list of DeliveryRequests for one scenario, sorted by arrival time."""
    rng = random.Random(seed)

    urgencies = list(scenario.urgency_weights.keys())
    weights = list(scenario.urgency_weights.values())
    pickup_cells = list(pickups.values())
    destination_cells = list(destinations.values())

    requests = []
    current_time = 0.0

    for i in range(scenario.num_requests):
        # Random gap until the next request (averages scenario.mean_gap)
        current_time += rng.expovariate(1.0 / scenario.mean_gap)
        arrival_time = int(round(current_time))

        urgency = rng.choices(urgencies, weights=weights, k=1)[0]
        pickup = rng.choice(pickup_cells)

        # Re-pick if destination matches pickup (possible once real locations overlap)
        destination = rng.choice(destination_cells)
        while destination == pickup:
            destination = rng.choice(destination_cells)

        task_type = rng.choice(task_types)

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


from data_generator import SCENARIOS, generate_requests, summarize

reqs = generate_requests(SCENARIOS["normal"], seed=42)
for r in reqs[:5]:
    print(r.request_id, r.arrival_time, r.urgency.value, r.pickup, "->", r.destination)

print(summarize(reqs))
print(summarize(generate_requests(SCENARIOS["emergency_heavy"], seed=42)))