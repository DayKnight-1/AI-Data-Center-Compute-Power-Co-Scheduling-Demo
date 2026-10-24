# tests/generate_test_report.py
"""
Generate the results table used in TEST_EVIDENCE.md.

Usage:
    python tests/generate_test_report.py
    python tests/generate_test_report.py --seeds 3
"""
import sys
import os
import argparse

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.generator import build_problem
from scheduler.baseline import run_no_schedule, run_rule_based, calc_lower_bound
from scheduler.local_search import run_local_search


SCENARIOS = [
    "☀️ Sunny Baseline",
    "☁️ Cloudy (Low Solar)",
    "📈 Demand Surge",
    "⚡ Price Spike",
]


def run_once(scenario, lam=0.5, seed=42):
    p = build_problem(scenario, lam=lam, seed=seed)
    base = run_no_schedule(p)
    rule = run_rule_based(p)
    smart = run_local_search(p)
    lb = calc_lower_bound(p)
    return {
        "Baseline (FCFS)": {
            "cost": base.metrics["cost"],
            "carbon": base.metrics["carbon"],
            "missed": base.metrics["sla"],
            "cycles": base.metrics["batt_cycles"],
        },
        "Simple Off-Peak": {
            "cost": rule.metrics["cost"],
            "carbon": rule.metrics["carbon"],
            "missed": rule.metrics["sla"],
            "cycles": rule.metrics["batt_cycles"],
        },
        "Smart Scheduling": {
            "cost": smart.metrics["cost"],
            "carbon": smart.metrics["carbon"],
            "missed": smart.metrics["sla"],
            "cycles": smart.metrics["batt_cycles"],
        },
        "Lower Bound": {
            "cost": lb["lb_cost"],
            "carbon": lb["lb_carbon"],
            "missed": None,
            "cycles": None,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3, help="number of random seeds to average")
    args = ap.parse_args()

    print(f"\n# Test Report\n")
    print(f"Averaged over {args.seeds} seeds for stochastic methods.\n")
    print("| Scenario | Strategy | Cost (¥) | Carbon (kg) | Missed | Battery cycles |")
    print("|---|---|---|---|---|---|")

    for scenario in SCENARIOS:
        # For stochastic methods, average over multiple seeds
        acc = {}
        for s in range(args.seeds):
            r = run_once(scenario, seed=42 + s)
            for strat, m in r.items():
                if strat not in acc:
                    acc[strat] = {k: [] for k in m}
                for k, v in m.items():
                    if v is not None:
                        acc[strat][k].append(v)

        for strat in ["Baseline (FCFS)", "Simple Off-Peak", "Smart Scheduling", "Lower Bound"]:
            m = {k: (sum(v) / len(v) if v else None) for k, v in acc[strat].items()}
            cost = f"¥{m['cost']:.0f}" if m['cost'] is not None else "—"
            carbon = f"{m['carbon']:.0f}" if m['carbon'] is not None else "—"
            missed = f"{int(m['missed'])}" if m['missed'] is not None else "—"
            cycles = f"{m['cycles']:.2f}" if m['cycles'] is not None else "—"
            print(f"| {scenario} | {strat} | {cost} | {carbon} | {missed} | {cycles} |")

    print("\n> Note: Lower Bound is a relaxed analytic bound, not a MILP optimum.\n")


if __name__ == "__main__":
    main()