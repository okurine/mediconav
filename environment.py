import numpy as np

# Grid/hospital floor dimensions
ROWS = 15
COLS = 20

EMPTY_FLOOR = 0
WALL = 1
BED = 2
# Coordinates are (row, col), with (0, 0) at the top-left
# Robots can walk on/through:
# '.' = Open floor
# 'I' = ICU patient delivery location
# 'W' = Ward patient delivery location
# 'E' = Emergency patient delivery location
# 'P' = Pharmacy medication pickup location
# 'M' = Medical supply pickup location
# 'L' = Lab dropoff location
# 'N' = Nurse's station
# 'C' = Robot charging station

# Robots can NOT walk on/through:
# 'X' = Wall
# 'i' = ICU patient bed
# 'w' = Ward patient bed
# 'e' = Emergency patient bed
LAYOUT = [
    "XXXXXXXXXXXXXXXXXXXX",
    "Xi..i..X.C..X.w.w.wX",
    "XiIIi........WwWwWwX",
    "X..................X",
    "X......X...CX......X",
    "XXXXXXXXC...XXXXXXXX",
    "X.XPPX...........N.X",
    "X..................X",
    "X....C......C....N.X",
    "XXXXXXXX....XXXXXXXX",
    "Xee..eeX....XM..XLLX",
    "X.E...E........MX..X",
    "X.E...E.........X..X",
    "Xee..eeX.C..X......X",
    "XXXXXXXXXXXXXXXXXXXX"
    ]

# Convert the layout strings into a NumPy grid and a dictionary
# Args: layout (list of strings indicating grid components)
# Returns: array of the grid and coordinates of marked components
def build_grid(layout):
    grid = np.zeros((ROWS, COLS), dtype=int)
    locations = {}
    for r, row in enumerate(layout):
        for c, ch in enumerate(row):
            if ch == 'X':
                grid[r, c] = WALL
            elif ch.islower():
                grid[r,c] = BED
            elif ch.isupper():
                if ch not in locations:
                    locations[ch] = []
                locations[ch].append((r, c))
    return grid, locations

# Prints a map of the grid layout
# Args: layout (list of strings indicating grid components)
def print_map(layout):
    header = " ".join(str(c % 10) for c in range(COLS))
    print("   " + header)
    for r, row in enumerate(layout):
        print(f"{r:2} " + " ".join(row))

# Checks that the layout has the correct dimensions (ROWS rows, each COLS characters long)
# Args: layout (list of strings indicating grid components)
# Raises: ValueError if the number of rows or the length of any row is wrong
def validate_layout(layout):
    if len(layout) != ROWS:
        raise ValueError(f"Layout has {len(layout)} rows, expected {ROWS}")
    for r, row in enumerate(layout):
        if len(row) != COLS:
            raise ValueError(f"Row {r} has {len(row)} characters, expected {COLS}")

if __name__ == "__main__":
    validate_layout(LAYOUT)
    print_map(LAYOUT)
