"""
Q-learning agent for choosing which free robot gets the request at the front of the queue.
Pure Python: it does not depend on the simulation, so it can be tested on its own.
"""

import random

# Action 0 = nearest free robot, action 1 = second-nearest free robot
ACTIONS = ["nearest", "second_nearest"]

URGENCY_WEIGHT = {"red": 3.0, "yellow": 2.0, "green": 1.0}


def valid_actions(free_count):
    """With only one free robot there is only one choice."""
    return [0, 1] if free_count >= 2 else [0]


def encode_state(urgency, free_count, nearest_distance, queue_behind=0):
    """
    Turn the situation into a small, hashable state.
      urgency          : "red", "yellow" or "green"
      free_count       : how many robots are free right now
      nearest_distance : A* distance from the closest free robot to the pickup
      queue_behind     : how many OTHER requests are waiting behind this one
    """
    free = "one" if free_count == 1 else "few" if free_count <= 3 else "many"
    dist = "near" if nearest_distance <= 8 else "medium" if nearest_distance <= 20 else "far"
    waiting = "none" if queue_behind == 0 else "few" if queue_behind <= 3 else "many"
    return (urgency, free, dist, waiting)


def compute_reward(urgency, wait_time, travel_ticks):
    """
    Negative score; closer to zero is better.
      wait_time    : ticks the request has already waited in the queue
      travel_ticks : robot's trip to the pickup plus pickup to destination
    """
    return -URGENCY_WEIGHT[urgency] * (wait_time + travel_ticks)


class QAgent:
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=1.0,
                 epsilon_min=0.05, epsilon_decay=0.99, seed=0):
        self.alpha = alpha                  # learning rate: how big each nudge is
        self.gamma = gamma                  # how much future rewards matter
        self.epsilon = epsilon              # chance of a random (exploring) choice
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q = {}                         # state -> one Q-value per action
        self.rng = random.Random(seed)      # its own dice, so training is repeatable

    def _values(self, state):
        """Q-values for a state, created at zero the first time we see it."""
        if state not in self.q:
            self.q[state] = [0.0] * len(ACTIONS)
        return self.q[state]

    def choose_action(self, state, valid, explore=True):
        """Pick an action from the valid ones. Use explore=False when testing."""
        if explore and self.rng.random() < self.epsilon:
            return self.rng.choice(valid)                    # explore: try something
        values = self._values(state)
        return max(valid, key=lambda a: values[a])           # exploit: best known

    def update(self, state, action, reward, next_state, next_valid):
        """
        Nudge the old value toward: reward + gamma * (best value of the next state).
        Pass next_state=None when the day is over.
        """
        values = self._values(state)
        if next_state is None:
            best_next = 0.0
        else:
            next_values = self._values(next_state)
            best_next = max(next_values[a] for a in next_valid)
        values[action] += self.alpha * (reward + self.gamma * best_next - values[action])

    def end_episode(self):
        """Call once per simulated day: explore a little less next time."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
