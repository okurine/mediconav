"""
Train the Q-learning dispatcher on simulated days.

Run:   python3 train_q.py --scenario normal --episodes 500

One episode is one simulated day. The training seeds (TRAIN_SEEDS) are cycled
in order, so every block of 50 episodes sees the same 50 days and the blocks
can be compared with each other. The trained Q-table is saved so that
evaluate.py can load it.
"""

import argparse
import csv
import time

from data_generator import SCENARIOS, TRAIN_SEEDS
from q_agent import QAgent
from q_dispatcher import QDispatcher

from simulation import run_simulation

def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else float("nan")


def print_block(rows, agent, elapsed):
    """Print one summary line for a block of episodes."""
    reward = mean([r["reward_per_decision"] for r in rows])
    delivery = mean([r["avg_delivery_time"] for r in rows])
    completed = mean([r["completed"] / r["total"] for r in rows]) * 100
    real = sum(r["real_choices"] for r in rows)
    decisions = sum(r["decisions"] for r in rows)

    print(
        f"episodes {rows[0]['episode']:>4}-{rows[-1]['episode']:<4} | "
        f"epsilon {rows[-1]['epsilon']:.2f} | "
        f"reward/decision {reward:8.1f} | "
        f"avg delivery {delivery:6.1f} | "
        f"completed {completed:5.1f}% | "
        f"real choices {real}/{decisions} | "
        f"states seen {len(agent.q)} | "
        f"{elapsed:.0f}s"
    )


def train(scenario, episodes, block=50, agent_seed=0):
    """Run `episodes` simulated days with exploration and learning switched on."""
    agent = QAgent(seed=agent_seed)
    history = []
    started = time.time()

    for episode in range(episodes):
        day_seed = TRAIN_SEEDS[episode % len(TRAIN_SEEDS)]
        epsilon = agent.epsilon

        # A fresh dispatcher per day (its counters restart), the same agent throughout
        dispatcher = QDispatcher(agent, explore=True, learn=True)
        results = run_simulation(scenario, day_seed, dispatcher, verbose=False)

        # end_day() shrinks epsilon. If it did not, the simulation never called it.
        if agent.epsilon >= epsilon and epsilon > agent.epsilon_min:
            raise RuntimeError(
                "epsilon did not decrease: the simulation must call "
                "dispatcher.end_day() once at the end of each day"
            )

        history.append({
            "episode": episode + 1,
            "seed": day_seed,
            "epsilon": epsilon,
            "completed": results["completed"],
            "total": results["total"],
            "avg_delivery_time": results["avg_delivery_time"],
            "avg_red_response_time": results["avg_red_response_time"],
            "reward_per_decision": dispatcher.total_reward / max(dispatcher.decisions, 1),
            "decisions": dispatcher.decisions,
            "real_choices": dispatcher.real_choices,
        })

        if episode == 0:
            first = time.time() - started
            print(
                f"First episode took {first:.1f}s, so {episodes} episodes "
                f"will take about {first * episodes / 60:.1f} minutes.\n"
            )

        if (episode + 1) % block == 0:
            print_block(history[-block:], agent, time.time() - started)

    leftover = len(history) % block
    if leftover:
        print_block(history[-leftover:], agent, time.time() - started)

    return agent, history


def main():
    parser = argparse.ArgumentParser(description="Train the Q-learning dispatcher.")
    parser.add_argument("--scenario", default="normal", choices=list(SCENARIOS))
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--block", type=int, default=50,
                        help="print a summary line every this many episodes")
    parser.add_argument("--agent-seed", type=int, default=0)
    args = parser.parse_args()

    print(f"Training on '{args.scenario}' for {args.episodes} episodes "
          f"(seeds {TRAIN_SEEDS[0]}-{TRAIN_SEEDS[-1]}, cycled)\n")

    agent, history = train(args.scenario, args.episodes, args.block, args.agent_seed)

    table_path = f"q_table_{args.scenario}.json"
    agent.save(table_path)
    print(f"\nSaved Q-table ({len(agent.q)} states) to {table_path}")

    history_path = f"training_{args.scenario}.csv"
    with open(history_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)
    print(f"Saved the per-episode history to {history_path}")


if __name__ == "__main__":
    main()