# MediCoNav

AI-based hospital delivery robot dispatch simulation. Six robots deliver
medications, supplies, and lab samples across a single-floor hospital grid.

## Shared conventions

- Grid: 15 rows x 20 columns. Coordinates are `(row, column)`, rows 0-14, columns 0-19
- 1 time step = each moving robot moves 1 cell
- 6 robots, 3 urgency levels: `red` (high), `yellow` (medium), `green` (low)
- Synthetic data only, with fixed random seeds so results are reproducible

## Features

### Hospital map (`environment.py`)
- Robots can walk on `.` and on task locations. They cannot walk on walls or beds
- Legend:

| Symbol | Meaning |
|---|---|
| `X` | wall |
| `i` `w` `e` | ICU, ward, and emergency beds |
| `I` `W` `E` | ICU, ward, and emergency patient delivery locations |
| `P` | pharmacy (medication pickup) |
| `M` | medical supply pickup |
| `L` | lab dropoff |
| `N` | nurses station |
| `C` | robot charging station |


### Robots (`robot.py`)
- Six robots, each with an ID, position, status (`available`, `busy`, `charging`),
  battery level, and an assigned request
- A robot can be assigned a request only when it is available, has no task,
  and its battery is above the low threshold

### Synthetic delivery requests (`delivery_requests.py`, `data_generator.py`)
- Each request has an ID, pickup, destination, arrival time, urgency, and task type
- Invalid requests are rejected when created: off-grid cells, same pickup and
  destination, negative arrival time, or an