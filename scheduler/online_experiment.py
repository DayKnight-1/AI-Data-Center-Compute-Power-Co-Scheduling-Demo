# scheduler/online_experiment.py
import numpy as np
import copy
import pandas as pd
from scheduler.model import Schedule
from scheduler.metrics import calc_metrics
from scheduler.greedy import run_greedy


def simulate_error(problem, error_level, seed):
    """
    Simulate forecast-error scenarios:
    1. Generate a noisy price forecast.
    2. Schedule using the forecast price.
    3. Evaluate the schedule against the true prices for real cost and carbon.
    """
    rng = np.random.default_rng(seed)
    T = int(problem.horizon / problem.dt)

    true_price = problem.curves.grid_price
    # Noise uniformly distributed in [-error_level, +error_level]
    if error_level == 0:
        noise = np.ones(T)
    else:
        noise = rng.uniform(1 - error_level, 1 + error_level, size=T)

    pred_price = true_price * noise

    # 1. Run greedy scheduling with forecast prices
    temp_problem = copy.deepcopy(problem)
    temp_problem.curves.grid_price = pred_price
    sched = run_greedy(temp_problem)

    # 2. Evaluate against true prices
    load = problem.curves.rigid_load.copy()
    for tid, blocks in sched.assignment.items():
        task = next(t for t in problem.tasks if t.id == tid)
        for (t, tier) in blocks:
            load[t] += task.p[tier]

    grid = np.zeros(T);
    green = np.zeros(T)
    charge = np.zeros(T);
    discharge = np.zeros(T);
    soc = np.zeros(T)
    current_soc = problem.batt_init

    # Battery is real-time: reacts to true prices
    for t in range(T):
        rem = load[t]
        use_g = min(rem, problem.curves.green_avail[t])
        green[t] = use_g
        rem -= use_g

        if true_price[t] > 1.0 and current_soc > 0:
            d = min(problem.batt_power, current_soc, rem)
            discharge[t] = d;
            current_soc -= d;
            rem -= d
        elif true_price[t] < 0.4 and current_soc < problem.batt_cap:
            c = min(problem.batt_power, problem.batt_cap - current_soc)
            charge[t] = c;
            current_soc += c

        grid[t] = rem + charge[t]
        soc[t] = current_soc

    true_sched = Schedule(assignment=sched.assignment, interrupt_count=sched.interrupt_count,
                          grid_power=grid, green_power=green, charge=charge,
                          discharge=discharge, soc=soc)
    true_sched.metrics = calc_metrics(true_sched, problem)

    return true_sched, true_price, pred_price


def run_all_experiments(problem, error_levels=[0.0, 0.1, 0.2, 0.3], seeds=[42, 100]):
    """
    Run simulations for all error levels; return a summary DataFrame and example curves per level.
    """
    results = []
    curves_dict = {}

    # Get baseline for perfect forecast (0%)
    base_sched, _, _ = simulate_error(problem, error_level=0.0, seed=42)

    for err in error_levels:
        costs = []
        carbons = []
        slas = []

        for s in seeds:
            sched, true_p, pred_p = simulate_error(problem, error_level=err, seed=s)
            costs.append(sched.metrics['cost'])
            carbons.append(sched.metrics['carbon'])
            slas.append(sched.metrics['sla'])

            # Save example curves per error level (first seed)
            if s == seeds[0]:
                curves_dict[err] = {
                    "true": true_p.tolist(),
                    "pred": pred_p.tolist()
                }

        avg_cost = sum(costs) / len(costs)
        avg_carbon = sum(carbons) / len(carbons)
        avg_sla = sum(slas) / len(slas)

        # Compute degradation vs perfect forecast
        cost_deg = (avg_cost - base_sched.metrics['cost']) / base_sched.metrics['cost'] if base_sched.metrics[
            'cost'] else 0
        carbon_deg = (avg_carbon - base_sched.metrics['carbon']) / base_sched.metrics['carbon'] if base_sched.metrics[
            'carbon'] else 0

        results.append({
            "error_level": err,
            "avg_cost": avg_cost,
            "cost_degradation": cost_deg,
            "avg_carbon": avg_carbon,
            "carbon_degradation": carbon_deg,
            "avg_sla": avg_sla,
            "sla_increase": avg_sla - base_sched.metrics['sla']
        })

    return pd.DataFrame(results), curves_dict