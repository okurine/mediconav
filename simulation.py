# MediCoNav - Hospital Robot Simulation
# Person 4: Simulation Controller

# Import teammates' modules
from environment import LAYOUT, validate_layout, build_grid
from robot import create_robots
from delivery_requests import RequestQueue, ArrivalSchedule
from data_generator import SCENARIOS, generate_requests
from collections import deque


def find_path(grid, start, goal):
    """
    Find a shortest path using BFS.

    Coordinates use (row, column).
    Movement is up, down, left, or right.
    """

    rows, cols = grid.shape

    queue = deque([start])
    visited = {start}
    parent = {}

    directions = [
        (-1, 0),  # Up
        (1, 0),   # Down
        (0, -1),  # Left
        (0, 1)    # Right
    ]

    while queue:
        current = queue.popleft()

        if current == goal:
            path = []

            while current != start:
                path.append(current)
                current = parent[current]

            path.reverse()
            return path

        for dr, dc in directions:
            nr = current[0] + dr
            nc = current[1] + dc

            neighbor = (nr, nc)

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            if neighbor in visited:
                continue

            # Assumes 0 represents a walkable cell.
            if grid[nr][nc] != 0:
                continue

            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)

    return None

def select_best_robot(grid, robots, request, chargers):
    best_robot = None
    shortest_distance = float("inf")

    for robot in robots:

        # Only consider robots that are available
        if not robot.is_available():
            continue

        # Calculate distance from robot to pickup
        pickup_path = find_path(
            grid,
            tuple(robot.position),
            tuple(request.pickup)
        )

        # Skip robots that cannot reach the pickup
        if pickup_path is None:
            continue

        distance = len(pickup_path)

        # Check battery for pickup, delivery and charging
        delivery_path = find_path(
            grid,
            tuple(request.pickup),
            tuple(request.destination)
        )

        if delivery_path is None:
            continue

        charger_distances = []

        for charger in chargers:
            charger_path = find_path(
                grid,
                tuple(request.destination),
                tuple(charger)
            )

            if charger_path is not None:
                charger_distances.append(len(charger_path))

        if not charger_distances:
            continue

        total_steps = (
            distance
            + len(delivery_path)
            + min(charger_distances)
        )

        required_battery = (
            total_steps * robot.battery_per_move
        ) + 5

        if robot.battery < required_battery:
            continue

        # Prefer the closest eligible robot
        if distance < shortest_distance:
            shortest_distance = distance
            best_robot = robot

    return best_robot


def main():
    print("===== MEDICONAV HOSPITAL SIMULATION =====")

    # Step 1: Load the hospital environment
    validate_layout(LAYOUT)
    grid, locations = build_grid(LAYOUT)

    print("\nHospital grid:", grid.shape)

    # Step 2: Initialize the six robots
    robots = create_robots(locations["C"])

    print("Total robots:", len(robots))

    # Step 3: Generate sample delivery requests
    requests = generate_requests(SCENARIOS["normal"], seed=42)

    print("Total requests generated:", len(requests))

    # Step 4: Initialize the queue and arrival schedule
    queue = RequestQueue()
    schedule = ArrivalSchedule(requests)

    # Step 5: Display robot states
    print("\n--- INITIAL ROBOT STATES ---")

    for robot in robots:
        print(robot.get_state())

    print("\nInitialization successful!")

     # Step 4: Test BFS pathfinding
    print("\n===== TESTING BFS PATHFINDING =====")

    start = robots[0].position
    goal = locations["C"][1]

    path = find_path(grid, start, goal)

    print("Starting position:", start)
    print("Destination:", goal)

    if path is not None:
        print("Path found!")
        print("Number of steps:", len(path))
        print("Path:", path)
    else:
        print("No valid path found!")

    
    # Step 6: Start the simulation clock
    print("\n===== STARTING SIMULATION CLOCK =====")

    completed_requests = set()
    delivery_completion_times = {}
    pickup_times = {}

    max_steps = 600

    for current_time in range(max_steps):

        print(f"\n--- Time Step {current_time} ---")

        # Get requests arriving at the current time
        new_requests = schedule.release(current_time)

        # Add new requests to the pending queue
        for request in new_requests:
            queue.add(request)

            print(
                f"New request arrived: {request.request_id}"
            )

        # Charging: select the closest reachable station for each idle robot.
        # Reserve enough battery to travel there before accepting more work.
        for robot in robots:
            # is_available() excludes robots at <=20% battery.
            # Idle low-battery robots must still be allowed to charge.
            if robot.status != "available" or robot.assigned_request is not None:
                continue

            charger_options = []
            for charger in locations["C"]:
                path = find_path(grid, tuple(robot.position), tuple(charger))
                if path is not None:
                    charger_options.append((len(path), charger, path))

            if not charger_options:
                print(f"WARNING: Robot {robot.robot_id} cannot reach a charger")
                continue

            charger_steps, nearest_charger, charger_path = min(
                charger_options, key=lambda item: item[0]
            )
            # A 30-unit reserve or the energy to reach the charger plus 10,
            # whichever is greater.  Check this before assigning new work.
            charging_threshold = max(
                30, charger_steps * robot.battery_per_move + 10
            )
            if robot.battery < charging_threshold:
                if robot.battery < charger_steps * robot.battery_per_move:
                    print(f"WARNING: Robot {robot.robot_id} lacks battery to reach charger")
                    continue
                robot.send_to_charger(nearest_charger)
                robot.set_path(charger_path)
                print(
                    f"Time {current_time}: Robot {robot.robot_id} "
                    f"heading to charger at {nearest_charger}"
                )

        # Step 7.2: Intelligent robot assignment
        while len(queue) > 0:

            request = queue.peek_next()

            robot = select_best_robot(
                grid,
                robots,
                request,
                locations["C"]
            )

            if robot is None:
                break

            pickup_path = find_path(
                grid,
                tuple(robot.position),
                tuple(request.pickup)
            )

            print(
                f"DISPATCH CHECK: {request.request_id} "
                f"-> Robot {robot.robot_id}, "
                f"Distance: {len(pickup_path)} steps, "
                f"Battery: {robot.battery:.1f}%"
            )

            request = queue.pop_next()

            robot.receive_assignment(request.to_dict())

            print(
                f"Time {current_time}: Robot {robot.robot_id} "
                f"assigned {request.request_id} "
                f"({request.urgency.value.upper()})"
            )

        # Step 8: Move assigned robots

        for robot in robots:

            # Allow charging robots to recharge each tick
            if robot.status == "charging":
                event = robot.step()

                if event == "fully_charged":
                    print(
                        f"Time {current_time}: "
                        f"Robot {robot.robot_id} fully charged!"
                    )

                continue

            # Only busy robots should follow delivery paths
            if robot.status != "busy":
                continue


            # Find where the robot needs to go
            target = robot.get_target()

            if target is None:
                continue

            # Calculate a path if the robot needs one
            if not robot.path:
                path = find_path(
                    grid,
                    tuple(robot.position),
                    tuple(target)
                )

                if path is None:
                    print(
                        f"Robot {robot.robot_id}: "
                        "No valid path found!"
                    )
                    continue

                robot.set_path(path)

            current_request = robot.assigned_request

            if current_request is not None:
                request_id = current_request["request_id"]
            else:
                request_id = None

            # Move the robot one grid cell
            event = robot.step()

            if event == "reached_charger":
                print(
                    f"Time {current_time}: Robot {robot.robot_id} "
                    f"reached charging station and started charging."
    )

            elif event == "picked_up":
                if request_id is not None:
                    pickup_times[request_id] = current_time

                print(
                    f"Time {current_time}: Robot {robot.robot_id} "
                    f"picked up its delivery."
                )
            elif event == "battery_empty":
                print(
                    f"Time {current_time}: Robot {robot.robot_id} "
                    f"ran out of battery!"
    )

            if event == "delivered" and request_id is not None:
                if request_id not in completed_requests:
                    completed_requests.add(request_id)

                    # Record when the delivery finished
                    delivery_completion_times[request_id] = current_time

                    print(
                        f"Robot {robot.robot_id} completed "
                        f"delivery {request_id} at time {current_time}"
                    )
    # Display how many requests are waiting
        print(f"Pending requests: {len(queue)}")

        print(f"Completed: {len(completed_requests)} / {len(requests)}")
        # Stop simulation when every request is completed
        if len(completed_requests) == len(requests):
            print(
                f"\nAll {len(requests)} deliveries completed "
                f"at time step {current_time}!"
            )
            break

    print("\nSimulation clock test completed!")

    # Step 8.1: Delivery completion rate
    total_requests = len(requests)
    completed_deliveries = len(completed_requests)

    if total_requests > 0:
        completion_rate = (completed_deliveries / total_requests) * 100
    else:
        completion_rate = 0

    print(f"Delivery completion rate: {completion_rate:.2f}%")

        # Step 8.2B: Average delivery time
    total_delivery_time = 0
    measured_deliveries = 0

    for request in requests:
        if request.request_id in delivery_completion_times:
            completion_time = delivery_completion_times[request.request_id]
            delivery_time = completion_time - request.arrival_time

            total_delivery_time += delivery_time
            measured_deliveries += 1

    if measured_deliveries > 0:
        average_delivery_time = total_delivery_time / measured_deliveries
    else:
        average_delivery_time = 0

    print(f"Average delivery time: {average_delivery_time:.2f} time steps")
        # Step 8.3B: Average RED emergency response time
    total_emergency_response_time = 0
    red_requests_served = 0

    for request in requests:
        if request.urgency.value.upper() == "RED":
            if request.request_id in pickup_times:
                pickup_time = pickup_times[request.request_id]
                response_time = pickup_time - request.arrival_time

                total_emergency_response_time += response_time
                red_requests_served += 1

    if red_requests_served > 0:
        average_emergency_response_time = (
            total_emergency_response_time / red_requests_served
        )

        print(
            f"Average RED emergency response time: "
            f"{average_emergency_response_time:.2f} time steps"
        )
    else:
        print("Average RED emergency response time: N/A (no RED pickups)")
    print("\n===== FINAL SIMULATION RESULTS =====")

    print("Total requests generated:", len(requests))
    print("Completed deliveries:", len(completed_requests))
    print("Pending requests:", len(queue))
    print("Unfinished request IDs:", [r.request_id for r in requests if r.request_id not in completed_requests])

    busy_robots = 0

    for robot in robots:
        if not robot.is_available():
            busy_robots += 1

    available_robots = len(robots) - busy_robots

    print("Busy robots:", busy_robots)
    print("Available robots:", available_robots)

    print("\n===== FINAL ROBOT STATES =====")

    
    print("\n===== ROBOT DIAGNOSTICS =====")

    for robot in robots:
        state = robot.get_state()

        print(f"\nRobot {robot.robot_id}")
        print("Position:", state["position"])
        print("Status:", state["status"])
        print("Task phase:", state["task_phase"])
        print("Target:", state["target"])
        print("Remaining steps:", state["remaining_steps"])
        print("Battery:", state["battery"])
        print("Needs charging:", state["needs_charging"])





if __name__ == "__main__":
    main()


