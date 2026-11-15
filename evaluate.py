"""
Compare the Q-learning dispatcher with the rule-based baseline on test days.

Run:   python3 evaluate.py
       python3 evaluate.py --scenarios normal emergency_heavy

For every scenario that has a saved table (q_table_<scenario>.json, made by
train_q.py), both dispatchers run on TEST_SEEDS: days the agent never trained
on. Here the agent explores nothing and learns nothing. Both dispatchers get
exactly the same requests, so any difference comes from the dispatcher.
"""

import argparse
import csv
import os

from data_generator import SCENARIOS, TEST_SEEDS
from q_agent import QAgent
from q_dispatcher import QDispatcher, NearestDispatcher

from simulation import run_simulation

def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def fmt(value, digits=1):
    return "n/a" if value is None else f"{value:.{digits}f}"


def evaluate_scenario(scenario, table_path):
    """Run baseline and agent on every test seed. Returns one dict per seed."""
    agent = QAgent(seed=0)
    agent.load(table_path)

    rows = []
    for seed in TEST_SEEDS:
        baseline_result = run_simulation(scenario, seed, NearestDispatcher(), verbose=False)

        dispatcher = QDispatcher(agent, explore=False, learn=False)
        agent_result = run_simulation(scenario, seed, dispatcher, verbose=False)

        rows.append({
            "scenario": scenario,
            "seed": seed,
            "base": baseline_result,
            "q": agent_result,
            "decisions": dispatcher.decisions,
            "real_choices": dispatcher.real_choices,
            "deviations": dispatcher.deviations,
        })
    return rows


def compare(rows, key):
    """
    Count the days where the agent was better, the same, or worse (lower is better).
    Days where either dispatcher left requests unfinished are skipped, because the
    averages only cover finished requests and would not be comparable.
    """
    better = same = worse = skipped = 0

    for row in rows:
        base, q = row["base"], row["q"]
        both_finished = (base["completed"] == base["total"]
                         and q["completed"] == q["total"])

        if not both_finished or base[key] is None or q[key] is None:
            skipped += 1
            continue

        difference = q[key] - base[key]
        if abs(difference) < 1e-9:
            same += 1
        elif difference < 0:
            better += 1
        else:
            worse += 1

    return better, same, worse, skipped


def report(scenario, rows):
    print(f"\n=== {scenario}: {len(rows)} test days ===")
    print(f"{'':16}{'completed':>12}{'avg delivery':>15}{'avg RED response':>20}")

    for name, key in (("nearest robot", "base"), ("Q-learning", "q")):
        results = [row[key] for row in rows]
        completed = sum(r["completed"] for r in results)
        total = sum(r["total"] for r in results)

        done = f"{completed}/{total}"
        delivery = fmt(mean([r["avg_delivery_time"] for r in results]))
        red = fmt(mean([r["avg_red_response_time"] for r in results]))
        print(f"{name:16}{done:>12}{delivery:>15}{red:>20}")

    print()
    for label, key in (("avg delivery time", "avg_delivery_time"),
                       ("avg RED response", "avg_red_response_time")):
        better, same, worse, skipped = compare(rows, key)
        print(f"Q-learning vs nearest, {label}: better on {better} days, "
              f"same on {same}, worse on {worse} "
              f"({skipped} skipped: unfinished requests or no data)")

    decisions = sum(row["decisions"] for row in rows)
    real = sum(row["real_choices"] for row in rows)
    deviations = sum(row["deviations"] for row in rows)
    print(f"Agent had a real choice (2+ eligible robots) in {real} of {decisions} "
          f"decisions and picked a non-nearest robot {deviations} times.")


def main():
    parser = argparse.ArgumentParser(description="Evaluate Q-learning against the baseline.")
    parser.add_argument("--scenarios", nargs="+", default=list(SCENARIOS),
                        choices=list(SCENARIOS))
    parser.add_argument("--out", default="evaluation_results.csv")
    args = parser.parse_args()

    csv_rows = []

    for scenario in args.scenarios:
        table_path = f"q_table_{scenario}.json"
        if not os.path.exists(table_path):
            print(f"\n=== {scenario}: skipped (no {table_path}; run train_q.py first) ===")
            continue

        rows = evaluate_scenario(scenario, table_path)
        report(scenario, rows)

        for row in rows:
            for name, key in (("nearest", "base"), ("q_learning", "q")):
                result = row[key]
                csv_rows.append({
                    "scenario": scenario,
                    "seed": row["seed"],
                    "dispatcher": name,
                    "completed": result["completed"],
                    "total": result["total"],
                    "avg_delivery_time": result["avg_delivery_time"],
                    "avg_red_response_time": result["avg_red_response_time"],
                })

    if csv_rows:
        with open(args.out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\nSaved per-day results to {args.out}")


if __name__ == "__main__":
    main()