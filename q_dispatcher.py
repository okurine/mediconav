"""
Glue between the simulation and the Q-learning agent.
Both dispatchers have the same two methods, so the simulation can swap them:
    choose_robot(request, robots, queue_behind, now) -> robot, or None
    end_day()
"""

import dispatcher as baseline 
from pathfinding import path_length
from q_agent import encode_state, valid_actions, compute_reward


def ranked_candidates(request, robots):
    """Robots that can finish this request, nearest first (ties: lower robot ID).
    Same eligibility and ordering as the baseline, so action 0 == the baseline's choice."""
    ranked = []
    for robot in robots:
        if not baseline.can_complete_request(robot, request):
            continue
        distance = path_length(tuple(robot.position), tuple(request.pickup))
        ranked.append((distance, robot.robot_id, robot))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked


class NearestDispatcher:
    """The rule-based baseline, wrapped to match the interface above."""

    def choose_robot(self, request, robots, queue_behind=0, now=0):
        return baseline.choose_robot(request, robots)

    def end_day(self):
        pass


class QDispatcher:
    def __init__(self, agent, explore=True, learn=True):
        self.agent = agent
        self.explore = explore        # False when testing
        self.learn = learn            # False when testing
        self._pending = None          # last decision, waiting for the next state
        self.decisions = 0
        self.real_choices = 0         # decisions with 2+ eligible robots
        self.total_reward = 0.0       # sum of rewards this day (for the learning curve)
        self.deviations = 0           # times the agent picked a non-nearest robot

    def choose_robot(self, request, robots, queue_behind=0, now=0):
        candidates = ranked_candidates(request, robots)
        if not candidates:
            return None               # nothing decided, nothing recorded

        free_count = len(candidates)
        urgency = request.urgency.value
        state = encode_state(urgency, free_count, candidates[0][0], queue_behind)
        valid = valid_actions(free_count)

        self.decisions += 1
        if free_count >= 2:
            self.real_choices += 1

        # Now we can see the "next state" for the previous decision, so update it
        if self.learn and self._pending is not None:
            prev_state, prev_action, prev_reward = self._pending
            self.agent.update(prev_state, prev_action, prev_reward, state, valid)

        action = self.agent.choose_action(state, valid, explore=self.explore)
        distance, _, robot = candidates[action]

        delivery_len = path_length(tuple(request.pickup), tuple(request.destination))
        reward = compute_reward(urgency, now - request.arrival_time, distance + delivery_len)
        self.total_reward += reward
        if action != 0:
            self.deviations += 1
        self._pending = (state, action, reward)
        return robot

    def end_day(self):
        if self.learn and self._pending is not None:
            state, action, reward = self._pending
            self.agent.update(state, action, reward, None, [])
        self._pending = None
        if self.learn:
            self.agent.end_episode()