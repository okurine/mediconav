"""
Baseline dispatcher and battery handling.

Policies:
- Choose the nearest eligible robot using actual path distance.
- Break distance ties using the lower robot ID.
- Require battery for pickup, delivery, and reaching a charger,
  plus a 5-percentage-point reserve.
- Idle robots stay where they finish unless they need charging.
- Idle robots unable to afford any waiting request may also charge.
"""

from environment import LAYOUT, build_grid
from pathfinding import find_path, path_length


GRID, LOCATIONS = build_grid(LAYOUT)
CHARGERS = LOCATIONS["C"]

BATTERY_RESERVE = 5.0


def nearest_charger(position):
    """
    Return (charger_coordinates, distance), or None if unreachable.
    Break equal-distance ties using charger coordinates.
    """
    options = []

    for charger in CHARGERS:
        distance = path_length(tuple(position), tuple(charger))

        if distance is not None:
            options.append((distance, tuple(charger)))

    if not options:
        return None

    distance, charger = min(options)
    return charger, distance


def required_battery(robot, request):
    """
    Battery needed for:
    current position -> pickup -> destination -> nearest charger.

    Return None if any part of the trip is unreachable.
    """
    pickup = tuple(request.pickup)
    destination = tuple(request.destination)

    to_pickup = path_length(tuple(robot.position), pickup)
    to_delivery = path_length(pickup, destination)
    charger_option = nearest_charger(destination)

    if (
        to_pickup is None
        or to_delivery is None
        or charger_option is None
    ):
        return None

    _, to_charger = charger_option

    total_moves = to_pickup + to_delivery + to_charger

    return (
        total_moves * robot.battery_per_move
        + BATTERY_RESERVE
    )


def can_complete_request(robot, request):
    """Check availability, reachability, and trip battery."""
    if not robot.is_available():
        return False

    needed = required_battery(robot, request)

    return needed is not None and robot.battery >= needed


def choose_robot(request, robots):
    """
    Shared dispatcher interface.

    Return the nearest eligible robot, or None.
    This function selects a robot; it does not assign the request.
    """
    candidates = []

    for robot in robots:
        if not can_complete_request(robot, request):
            continue

        distance = path_length(
            tuple(robot.position),
            tuple(request.pickup),
        )

        candidates.append((distance, robot.robot_id, robot))

    if not candidates:
        return None

    best = min(
        candidates,
        key=lambda candidate: (candidate[0], candidate[1]),
    )

    return best[2]


def handle_idle_charging(robots, pending_requests=None):
    """
    Start charging trips for idle robots that:
    - need charging according to their battery threshold; or
    - cannot afford any reachable waiting request.

    Return a list of robots whose charging trips were started.
    The controller still calls robot.step() every tick.
    """
    pending_requests = (
        [] if pending_requests is None else list(pending_requests)
    )

    started = []

    for robot in robots:
        # Do not interrupt deliveries, charging, or standby trips.
        if (
            robot.status != "available"
            or robot.assigned_request is not None
        ):
            continue

        should_charge = robot.needs_charging()

        if (
            not should_charge
            and pending_requests
            and robot.battery < 100.0
        ):
            requirements = [
                required_battery(robot, request)
                for request in pending_requests
            ]

            # Ignore unreachable tasks and tasks that cannot be
            # afforded even with a full battery.
            feasible_requirements = [
                needed
                for needed in requirements
                if needed is not None and needed <= 100.0
            ]

            if feasible_requirements:
                should_charge = (
                    robot.battery < min(feasible_requirements)
                )

        if not should_charge:
            continue

        option = nearest_charger(robot.position)

        if option is None:
            raise ValueError(
                f"Robot {robot.robot_id} cannot reach any charger."
            )

        charger, distance = option
        travel_cost = distance * robot.battery_per_move

        if robot.battery < travel_cost:
            raise ValueError(
                f"Robot {robot.robot_id} has insufficient "
                "battery to reach the nearest charger."
            )

        # Find the route before changing the robot's state.
        path = find_path(GRID, tuple(robot.position), charger)

        if path is None:
            raise ValueError(
                f"No charger path found for robot {robot.robot_id}."
            )

        robot.send_to_charger(charger)
        robot.set_path(path)

        started.append(robot)

    return started


def main():
    """Run independent checks for the baseline dispatcher."""
    from types import SimpleNamespace
    from robot import Robot, create_robots

    
    request = SimpleNamespace(
        request_id="REQ-TEST-001",
        pickup=LOCATIONS["I"][0],
        destination=LOCATIONS["L"][0],
    )

    print("BASELINE DISPATCHER TESTS ")

    
    # TEST 1: Select the nearest eligible robot.
    # All six robots start fully charged at the real C locations.
    robots = create_robots(LOCATIONS["C"])

    eligible_robots = [
        robot
        for robot in robots
        if can_complete_request(robot, request)
    ]

    assert eligible_robots, "Test needs an eligible robot."

    expected = min(
        eligible_robots,
        key=lambda robot: (
            path_length(robot.position, request.pickup),
            robot.robot_id,
        ),
    )

    selected = choose_robot(request, robots)

    assert selected is expected
    print(
        f"PASS 1: Nearest eligible robot selected "
        f"(robot {selected.robot_id})."
    )

    # TEST 2: Skip the nearest robot when its battery is low.
    # Use fresh robots so this test does not change Test 1.
    robots = create_robots(LOCATIONS["C"])

    nearest = choose_robot(request, robots)
    assert nearest is not None

    nearest.battery = 15.0

    selected = choose_robot(request, robots)

    remaining_candidates = [
        robot
        for robot in robots
        if can_complete_request(robot, request)
    ]

    assert remaining_candidates, "Test needs another eligible robot."

    expected = min(
        remaining_candidates,
        key=lambda robot: (
            path_length(robot.position, request.pickup),
            robot.robot_id,
        ),
    )

    assert selected is expected
    assert selected is not nearest

    print("PASS 2: Low-battery robot skipped.")

    # TEST 3: Charge a robot already at a charger.
    # Starting at 15%, it needs 17 ticks at 5 points per tick.
    # Arrival itself is handled on a separate tick.

    robot = Robot(0, CHARGERS[0])
    robot.battery = 15.0

    started = handle_idle_charging([robot])

    assert robot in started
    assert robot.task_phase == "to_charger"

    event = robot.step()

    assert event == "reached_charger"
    assert robot.status == "charging"

    for _ in range(17):
        event = robot.step()

    assert event == "fully_charged"
    assert robot.battery == 100.0
    assert robot.is_available()

    print("PASS 3: Charging restored full battery and availability.")


    # TEST 4: Return None when every robot is busy.
    # This checks selection only; the controller manages queuing.
    robots = create_robots(LOCATIONS["C"])

    for robot in robots:
        robot.status = "busy"

    assert choose_robot(request, robots) is None

    print("PASS 4: No robot selected when all robots are busy.")

    
    # TEST 5: Equal distance is resolved by lower robot ID.
    # Shared positions are intentional for this isolated test.
    # Put the higher ID first to verify list order does not win.

    robot_4 = Robot(4, LOCATIONS["C"][0])
    robot_1 = Robot(1, LOCATIONS["C"][0])

    assert can_complete_request(robot_4, request)
    assert can_complete_request(robot_1, request)

    selected = choose_robot(request, [robot_4, robot_1])

    assert selected is robot_1

    print("PASS 5: Equal-distance tie resolved by lower robot ID.")

    # TEST 6: Enforce the full-trip battery requirement.
    # The robot must afford pickup, delivery, travel to a charger,
    # and the reserve—not just pass the 20% availability check.

    robot = Robot(0, LOCATIONS["C"][0])
    needed = required_battery(robot, request)

    assert needed is not None
    assert needed <= 100.0
    assert needed - 1 > robot.low_battery_threshold, (
        "This test route must require enough battery to test "
        "the full-trip check independently of the low threshold."
    )

    robot.battery = needed - 1

    assert robot.is_available()
    assert choose_robot(request, [robot]) is None

    # Exactly enough battery, including reserve, should qualify.
    robot.battery = needed

    assert choose_robot(request, [robot]) is robot

    print("PASS 6: Full-trip battery requirement enforced.")

    # TEST 7: Travel to a charger from a neighboring floor cell.
    # Find a real walkable cell next to a charger rather than
    # hardcoding a position that might be a wall or bed.
  
    start = None

    for charger in CHARGERS:
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            row = charger[0] + dr
            col = charger[1] + dc

            if (
                0 <= row < GRID.shape[0]
                and 0 <= col < GRID.shape[1]
                and GRID[row, col] == 0
                and (row, col) not in CHARGERS
            ):
                start = (row, col)
                break

        if start is not None:
            break

    assert start is not None, (
        "Test needs a walkable non-charger cell next to a charger."
    )

    robot = Robot(0, start)
    robot.battery = 20.0

    started = handle_idle_charging([robot])

    assert robot in started
    assert len(robot.path) == 1

    event = robot.step()

    assert event == "reached_charger"
    assert robot.position in CHARGERS
    assert robot.battery == 19.0
    assert robot.status == "charging"

    print("PASS 7: Travel to charger consumed battery correctly.")

    print("\nAll seven dispatcher tests passed.")

if __name__ == "__main__":
    main()