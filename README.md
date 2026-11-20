
# MediCoNav – Intelligent Hospital Robot Coordination

AI-based hospital delivery robot dispatch simulation. Six robots deliver medications, supplies, and lab samples across a single-floor hospital grid.

The project compares a rule-based dispatcher with a Q-learning dispatcher to improve delivery efficiency and prioritize urgent requests.

**Technologies:** Python | A* Path Planning | Q-Learning | Multi-Robot Systems

## Shared Conventions

- Grid: 15 rows x 20 columns. Coordinates are `(row, column)`, rows 0-14, columns 0-19.
- 1 time step = each moving robot moves 1 cell.
- 6 robots, 3 urgency levels: `red` (high), `yellow` (medium), `green` (low).
- Synthetic data only, with fixed random seeds so results are reproducible.

## Features and File Descriptions

### Hospital Map (`environment.py`)

- Robots can walk on `.` and on task locations. They cannot walk on walls or beds.

| Symbol | Meaning |
|--------|---------|
| `X` | Wall |
| `i` `w` `e` | ICU, ward, and emergency beds |
| `I` `W` `E` | ICU, ward, and emergency patient delivery locations |
| `P` | Pharmacy (medication pickup) |
| `M` | Medical supply pickup |
| `L` | Lab dropoff |
| `N` | Nurses station |
| `C` | Robot charging station |

### Robots (`robot.py`)

- Six robots, each with an ID, position, status (`available`, `busy`, `charging`), battery level, and an assigned request.
- A robot can be assigned a request only when it is available, has no task, and its battery is above the low threshold.

### Synthetic Delivery Requests (`delivery_requests.py`, `data_generator.py`)

- Each request has an ID, pickup, destination, arrival time, urgency, and task type.
- Invalid requests are rejected when created: off-grid cells, same pickup and destination, negative arrival time, or invalid request parameters.

### Baseline Dispatcher (`dispatcher.py`)

- Selects the nearest eligible robot; breaks ties by lower robot ID.
- Checks battery for pickup, delivery, and reaching a charger, plus a 5% reserve.
- Sends idle robots to charge when needed.
- Run seven independent tests: `python dispatcher.py`.

### A* Path Planning (`pathfinding.py`)

- Computes shortest paths between hospital locations.
- Avoids walls, beds, and other non-walkable cells.

### Simulation (`simulation.py`)

- Coordinates robot movement, request assignments, deliveries, and charging.
- Tracks simulation time and delivery events.

### Q-Learning Agent (`q_agent.py`)

- Implements Q-learning, Q-value updates, and epsilon-greedy action selection.
- Learns improved dispatch decisions through repeated training episodes.

### RL Dispatcher (`q_dispatcher.py`)

- Uses the Q-learning agent to select eligible robots.
- Considers request urgency and robot availability when making dispatch decisions.

### RL Training (`train_q.py`)

- Trains the Q-learning agent under different hospital workloads.
- Saves learned policies and training results.

### Performance Evaluation (`evaluate.py`)

- Compares the baseline and Q-learning dispatchers.
- Evaluates delivery times and request completion performance.

## Simulation Scenarios

- Normal workload
- Busy hospital
- Emergency-heavy workload

## Getting Started

```bash
git clone https://github.com/okurine/mediconav.git
cd mediconav

python simulation.py
python dispatcher.py
```

## Contributors

- Rishita Chawla
- Pratap Yogesh Patil
- Ella Xu
- Thejaswini Srinivasan Manjula


