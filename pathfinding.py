import heapq
from collections import deque
from environment import ROWS, COLS, EMPTY_FLOOR, build_grid, LAYOUT
GRID, LOCATIONS = build_grid(LAYOUT)

DISTANCES = {}


# Finds the walkable cells directly up, down, left, and right of a cell
# Args: grid (array from build_grid), cell (row, col)
# Returns: list of available (row, col) for direct neighbors of a given cell
def get_neighbors(grid, cell):
    r, c = cell
    possible_n = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    neighbors = []

    for nr, nc in possible_n:
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            if grid[nr, nc] == EMPTY_FLOOR:
                neighbors.append((nr, nc))

    return neighbors

# Estimates the distance from cell to the goal using Manhattan distance
# Args: cell (row, col), goal (row, col)
# Returns: estimated number of steps (int)
def heuristic(cell, goal):
    r1, c1 = cell
    r2, c2 = goal

    md = abs(r1 - r2) + abs(c1 - c2)

    return md

# Find shortest path from start to goal using A* search
# Args: grid (array from build_grid), start (row, col), goal (row, col)
# Returns: list of (row, col) cells from start to goal (includes both),
#          or None if no route exists
def find_path(grid, start, goal):
    frontier = []
    heapq.heappush(frontier, (heuristic(start, goal), 0, start, [start]))
    visited = set()

    while frontier:
        f, g, cell, path = heapq.heappop(frontier)
        if cell not in visited:
            visited.add(cell)

            if cell == goal:
                return path

            for nb in get_neighbors(grid, cell):
                # every move costs 1 step
                new_g = g + 1
                heapq.heappush(frontier, (new_g + heuristic(nb, goal), new_g, nb, path + [nb]))

    return None

# Finds # of steps from source to every reachable cell using BFS
# Args: grid (array from build_grid), source (row, col)
# Returns: dict mapping each reachable (row, col) to its distance from source
def bfs_dist(grid, source):
    distances = {source: 0}
    queue = deque([source])

    while queue:
        cell = queue.popleft()
        for nb in get_neighbors(grid, cell):
            if nb not in distances:
                distances[nb] = distances[cell] + 1
                queue.append(nb)

    return distances


# precompute distances from every task location once
# so path_length can have a fast lookup instead of new search
for coords in LOCATIONS.values():
    for cds in coords:
        DISTANCES[cds] = bfs_dist(GRID, cds)

# Finds # of steps from start to a task location
# Args: start (row, col), goal (row, col) of a task location
# Returns: number of steps (int), or None if goal is not a task location
def path_length(start, goal):
    if goal not in DISTANCES:
        return None
    
    return DISTANCES[goal].get(start)

    

