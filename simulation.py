"""MediCoNav simulation controller (Person 4).

One tick moves each active robot at most one cell. Each invocation starts
with independent robots, requests, queue and event log.
"""
from environment import LAYOUT, validate_layout, build_grid
from robot import create_robots
from delivery_requests import RequestQueue, ArrivalSchedule, RequestStatus
from data_generator import SCENARIOS, generate_requests
from pathfinding import find_path
from dispatcher import handle_idle_charging


def run_simulation(scenario_name, seed, dispatcher, verbose=False):
    """Run one simulated day; return training-compatible aggregate metrics.

    Red response time is arrival -> pickup (not arrival -> assignment).
    No event is printed unless verbose=True.
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario_name!r}; choose from {list(SCENARIOS)}")
    validate_layout(LAYOUT)
    grid, locations = build_grid(LAYOUT)
    robots = create_robots(locations["C"])
    requests = generate_requests(SCENARIOS[scenario_name], seed=seed)
    schedule = ArrivalSchedule(requests)
    queue = RequestQueue()
    event_log = []
    assignments = {}
    pickups = {}
    deliveries = {}
    max_steps = max(600, max((r.arrival_time for r in requests), default=0) + 600)

    def log(time, event, request_id=None, robot_id=None):
        entry = {"time": time, "event": event,
                 "request_id": request_id, "robot_id": robot_id}
        event_log.append(entry)
        if verbose:
            print(entry)

    try:
        for now in range(max_steps):
            for request in schedule.release(now):
                queue.add(request)
                log(now, "arrived", request.request_id)

            # The dispatcher owns the choice. Never replace a Q-agent choice.
            while len(queue):
                request = queue.peek_next(now)
                robot = dispatcher.choose_robot(
                    request, robots, queue_behind=len(queue) - 1, now=now
                )
                if robot is None:
                    break
                if robot not in robots or not robot.is_available():
                    raise ValueError("Dispatcher selected a non-available/unknown robot")
                pickup_path = find_path(grid, tuple(robot.position), tuple(request.pickup))
                if pickup_path is None:
                    raise ValueError(f"No pickup route for {request.request_id}")
                queue.pop_next(now)
                robot.receive_assignment(request.to_dict())
                robot.set_path(pickup_path)
                request.status = RequestStatus.ASSIGNED
                request.assigned_robot_id = robot.robot_id
                assignments[request.request_id] = now
                log(now, "assigned", request.request_id, robot.robot_id)

            # Charging policy is shared with the baseline implementation.
            handle_idle_charging(robots, queue.pending_requests(now))

            for robot in robots:
                if robot.status not in ("busy", "charging"):
                    continue
                request_id = (robot.assigned_request or {}).get("request_id")
                target = robot.get_target()
                if robot.status == "busy" and target is not None and not robot.path:
                    path = find_path(grid, tuple(robot.position), tuple(target))
                    if path is None:
                        raise ValueError(f"No path for robot {robot.robot_id} to {target}")
                    robot.set_path(path)
                event = robot.step()
                if event == "battery_empty":
                    raise RuntimeError(f"Robot {robot.robot_id} ran out of battery")
                if event is not None:
                    log(now, event, request_id, robot.robot_id)
                if event == "picked_up":
                    pickups[request_id] = now
                elif event == "delivered":
                    deliveries[request_id] = now
                    next(r for r in requests if r.request_id == request_id).status = RequestStatus.COMPLETED

            if len(deliveries) == len(requests) and schedule.remaining() == 0:
                break
    finally:
        # One terminal transition per day, even if the simulation fails.
        dispatcher.end_day()

    delivery_times = [deliveries[r.request_id] - r.arrival_time
                      for r in requests if r.request_id in deliveries]
    red_times = [pickups[r.request_id] - r.arrival_time
                 for r in requests if r.urgency.value == "red" and r.request_id in pickups]
    results = {
        "completed": len(deliveries),
        "total": len(requests),
        "avg_delivery_time": sum(delivery_times) / len(delivery_times) if delivery_times else 0.0,
        "avg_red_response_time": sum(red_times) / len(red_times) if red_times else 0.0,
    }
    if verbose:
        print("Final results:", results)
        print("Recorded events:", len(event_log))
    return results


def run(scenario, seed, dispatcher):
    """Alias for callers using the original Person 4 contract."""
    return run_simulation(scenario, seed, dispatcher)


if __name__ == "__main__":
    from q_dispatcher import NearestDispatcher
    run_simulation("normal", 42, NearestDispatcher(), verbose=True)
