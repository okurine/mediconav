class Robot:
    def __init__(self, robot_id, position):
        # Basic information
        self.robot_id = robot_id
        self.position = tuple(position)

        # Robot state
        self.battery = 100.0
        self.status = "available"
        self.task_phase = None
        self.assigned_request = None

        # Remaining route supplied by A*
        self.path = []

        # Target for charging or standby activities
        self.internal_target = None

        # Example battery settings — Still have to agree with team
        self.low_battery_threshold = 20.0
        self.battery_per_move = 1.0
        self.charge_per_tick = 5.0

    def needs_charging(self):
        """Return True when battery is at or below the threshold."""
        return self.battery <= self.low_battery_threshold

    def is_available(self):
        """Check whether the dispatcher can assign this robot."""
        return (
            self.status == "available"
            and self.assigned_request is None
            and not self.needs_charging()
        )

    def receive_assignment(self, request):
        """Receive a delivery selected by the dispatcher."""
        if not self.is_available():
            raise ValueError("This robot is not available.")

        required_fields = [
            "request_id",
            "pickup",
            "destination",
            "urgency",
            "arrival_time",
        ]

        for name in required_fields:
            if name not in request:
                raise ValueError("Request is missing: " + name)

        if request["urgency"] not in ["red", "yellow", "green"]:
            raise ValueError("Urgency must be red, yellow, or green.")

        self.assigned_request = request.copy()
        self.assigned_request["pickup"] = tuple(request["pickup"])
        self.assigned_request["destination"] = tuple(
            request["destination"]
        )

        self.status = "busy"
        self.task_phase = "to_pickup"
        self.internal_target = None
        self.path = []

    def get_target(self):
        """Return the robot's current destination."""
        if self.task_phase == "to_pickup":
            return self.assigned_request["pickup"]

        if self.task_phase == "to_delivery":
            return self.assigned_request["destination"]

        if self.task_phase in ["to_charger", "to_standby"]:
            return self.internal_target

        return None

    def set_path(self, path):
        """
        Store a complete route supplied by A*.

        A* must check map boundaries and obstacles.
        This method checks adjacency and the route's endpoint.
        """
        target = self.get_target()

        if target is None:
            raise ValueError("Assign a task before setting a path.")

        new_path = [tuple(position) for position in path]

        # A* may include the robot's starting cell.
        if new_path and new_path[0] == self.position:
            new_path.pop(0)

        previous_position = self.position

        for next_position in new_path:
            row_change = abs(
                next_position[0] - previous_position[0]
            )
            column_change = abs(
                next_position[1] - previous_position[1]
            )

            if row_change + column_change != 1:
                raise ValueError(
                    "Each move must be one cell up, down, left, or right."
                )

            previous_position = next_position

        if previous_position != target:
            raise ValueError("The path must end at the current target.")

        self.path = new_path

    def send_to_charger(self, charging_station):
        """Prepare an idle robot to travel to a charging station."""
        if (
            self.status != "available"
            or self.assigned_request is not None
        ):
            raise ValueError("Robot must be idle before charging.")

        self.internal_target = tuple(charging_station)
        self.task_phase = "to_charger"
        self.status = "busy"
        self.path = []

    def send_to_standby(self, standby_position):
        """Prepare an available robot to return to standby."""
        if not self.is_available():
            raise ValueError(
                "Robot must be available and have enough battery."
            )

        self.internal_target = tuple(standby_position)
        self.task_phase = "to_standby"
        self.status = "busy"
        self.path = []

    def step(self):
        """
        Advance the robot by one simulation tick.

        Returns an event when something important happens.
        """
        if self.status == "charging":
            self.battery = min(
                100.0,
                self.battery + self.charge_per_tick,
            )

            if self.battery >= 100.0:
                self.status = "available"
                self.task_phase = None
                return "fully_charged"

            return None

        # Handle cases where the robot is already at its target.
        event = self.check_arrival()

        if event is not None:
            return event

        # Wait until the controller supplies a path.
        if not self.path:
            return None

        if self.battery < self.battery_per_move:
            return "battery_empty"

        # Move one cell.
        self.position = self.path.pop(0)

        self.battery = max(
            0.0,
            self.battery - self.battery_per_move,
        )

        return self.check_arrival()

    def check_arrival(self):
        """Update state when the robot reaches its target."""
        target = self.get_target()

        if target is None or self.position != target:
            return None

        self.path = []

        if self.task_phase == "to_pickup":
            self.task_phase = "to_delivery"
            return "picked_up"

        if self.task_phase == "to_delivery":
            self.assigned_request = None
            self.task_phase = None
            self.status = "available"
            return "delivered"

        if self.task_phase == "to_charger":
            self.internal_target = None
            self.task_phase = None
            self.status = "charging"
            return "reached_charger"

        if self.task_phase == "to_standby":
            self.internal_target = None
            self.task_phase = None
            self.status = "available"
            return "reached_standby"

        return None

    def get_state(self):
        """Return a snapshot for the controller or dispatcher."""
        request_id = None

        if self.assigned_request is not None:
            request_id = self.assigned_request["request_id"]

        return {
            "robot_id": self.robot_id,
            "position": self.position,
            "battery": self.battery,
            "status": self.status,
            "task_phase": self.task_phase,
            "request_id": request_id,
            "target": self.get_target(),
            "needs_charging": self.needs_charging(),
            "remaining_steps": len(self.path),
        }


def create_robots(start_positions):
    """Create six robots at the agreed starting coordinates."""
    if len(start_positions) != 6:
        raise ValueError("Provide exactly six starting positions.")

    robots = []

    for robot_id, position in enumerate(start_positions):
        robot = Robot(robot_id, position)
        robots.append(robot)

    return robots


# Independent demonstration using sample coordinates and paths.
if __name__ == "__main__":
    start_positions = [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
    ]

    robots = create_robots(start_positions)
    robot = robots[0]

    request = {
        "request_id": "REQ-001",
        "task_type": "emergency_medication",
        "pickup": (0, 2),
        "destination": (1, 2),
        "urgency": "red",
        "arrival_time": 0,
    }

    # The dispatcher normally makes this call.
    robot.receive_assignment(request)

    # A* normally supplies this route.
    robot.set_path([(0, 0), (0, 1), (0, 2)])

    print(robot.step())  # None: moves to (0, 1)
    print(robot.step())  # picked_up

    # After pickup, supply the route to the delivery destination.
    robot.set_path([(0, 2), (1, 2)])

    print(robot.step())  # delivered

    # Demonstrate returning to standby.
    robot.send_to_standby((0, 0))
    robot.set_path([(1, 2), (1, 1), (1, 0), (0, 0)])

    while robot.task_phase == "to_standby":
        print(robot.step())

    # Demonstrate a low-battery situation.
    robot.battery = 20.0

    robot.send_to_charger((1, 0))
    robot.set_path([(0, 0), (1, 0)])

    print(robot.step())  # reached_charger

    while robot.status == "charging":
        print(robot.step())

    # Print all six robot states.
    for robot in robots:
        print(robot.get_state())


# Have to still discuss charging locations