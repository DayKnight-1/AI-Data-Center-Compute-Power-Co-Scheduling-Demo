# scheduler/baseline.py
import numpy as np
from scheduler.model import Problem, Schedule
from scheduler.metrics import calc_metrics


def _build_arrays(p: Problem, assignment: dict):
    T = int(p.horizon / p.dt)
    load = p.curves.rigid_load.copy()
    for tid, blocks in assignment.items():
        task = next(t for t in p.tasks if t.id == tid)
        for (t, tier) in blocks:
            if t < T: load[t] += task.p[tier]

    grid = np.zeros(T);
    green = np.zeros(T)
    for t in range(T):
        use_g = min(load[t], p.curves.green_avail[t])
        green[t] = use_g
        grid[t] = load[t] - use_g
    return grid, green


def run_no_schedule(p: Problem) -> Schedule:
    T = int(p.horizon / p.dt)
    assignment = {}
    avail_cap = p.capacity - p.curves.rigid_load

    # Truly no scheduling: queue on arrival, defer if no room
    for task in sorted(p.tasks, key=lambda x: x.arrival):
        start = int(task.arrival / p.dt)
        dur = task.duration_slots("std", p.dt)
        placed = False
        for t in range(start, T - dur + 1):
            if np.all(avail_cap[t:t + dur] >= task.p["std"]):
                assignment[task.id] = [(k, "std") for k in range(t, t + dur)]
                for k in range(t, t + dur): avail_cap[k] -= task.p["std"]
                placed = True
                break
        if not placed: assignment[task.id] = []

    grid, green = _build_arrays(p, assignment)
    sched = Schedule(assignment=assignment, interrupt_count={}, grid_power=grid,
                     green_power=green, charge=np.zeros(T), discharge=np.zeros(T), soc=np.zeros(T))
    sched.metrics = calc_metrics(sched, p)
    sched.method = "Baseline (No Scheduling)"
    return sched


def run_rule_based(p: Problem) -> Schedule:
    T = int(p.horizon / p.dt)
    assignment = {}
    avail_cap = p.capacity - p.curves.rigid_load

    for task in sorted(p.tasks, key=lambda x: (x.deadline, x.arrival)):
        start = int(task.arrival / p.dt)
        dur = task.duration_slots("std", p.dt)
        placed = False
        # Rule: prefer cheaper grid price
        for t in range(start, T - dur + 1):
            if t + dur > int(task.deadline / p.dt): break
            if np.any(avail_cap[t:t + dur] < task.p["std"]): continue
            if p.curves.grid_price[t] <= 0.6:
                assignment[task.id] = [(k, "std") for k in range(t, t + dur)]
                for k in range(t, t + dur): avail_cap[k] -= task.p["std"]
                placed = True
                break
        if not placed:
            # Fallback: queue at arrival
            for t in range(start, T - dur + 1):
                if np.all(avail_cap[t:t + dur] >= task.p["std"]):
                    assignment[task.id] = [(k, "std") for k in range(t, t + dur)]
                    for k in range(t, t + dur): avail_cap[k] -= task.p["std"]
                    placed = True
                    break
            if not placed: assignment[task.id] = []

    grid, green = _build_arrays(p, assignment)
    sched = Schedule(assignment=assignment, interrupt_count={}, grid_power=grid,
                     green_power=green, charge=np.zeros(T), discharge=np.zeros(T), soc=np.zeros(T))
    sched.metrics = calc_metrics(sched, p)
    sched.method = "Rule-based"
    return sched


# scheduler/baseline.py (replaces the original calc_lower_bound)


def calc_lower_bound(p: Problem) -> dict:
    """
    Compute the "task-feasible-window lower bound" (a theoretical optimum):
    1. Keep each task's arrival and deadline;
    2. Allow free switching among the three tiers;
    3. Relax the capacity constraint;
    4. Add the battery's theoretical maximum net arbitrage (net of losses).
    """
    min_total_cost = 0.0
    min_total_carbon = 0.0

    # 1. Minimum cost for rigid load
    for t in range(int(p.horizon / p.dt)):
        rigid_load = p.curves.rigid_load[t]
        if rigid_load > 0:
            green_used = min(rigid_load, p.curves.green_avail[t])
            grid_used = rigid_load - green_used

            min_total_cost += grid_used * p.curves.grid_price[t] + green_used * p.curves.green_price[t]
            min_total_carbon += grid_used * p.curves.carbon[t]

    # 2. Theoretical minimum cost for schedulable tasks
    for task in p.tasks:
        best_task_cost = float('inf')
        best_task_carbon = float('inf')

        start_idx = int(task.arrival / p.dt)
        end_idx = int(task.deadline / p.dt) if task.deadline < 999 else int(p.horizon / p.dt)

        for tier in ["slow", "std", "fast"]:
            dur = task.duration_slots(tier, p.dt)
            power = task.p[tier]

            for t in range(start_idx, end_idx - dur + 1):
                cost = 0.0
                carbon = 0.0
                for k in range(t, t + dur):
                    green_used = min(power, p.curves.green_avail[k])
                    grid_used = power - green_used
                    cost += grid_used * p.curves.grid_price[k] + green_used * p.curves.green_price[k]
                    carbon += grid_used * p.curves.carbon[k]

                total_obj = cost + p.lam * carbon
                if total_obj < best_task_cost + p.lam * best_task_carbon:
                    best_task_cost = cost
                    best_task_carbon = carbon

        if best_task_cost != float('inf'):
            min_total_cost += best_task_cost
            min_total_carbon += best_task_carbon

    # 3. [Key fix] Maximum theoretical net battery arbitrage (net of cycling cost)
    max_price = np.max(p.curves.grid_price)
    min_price = np.min(p.curves.grid_price)

    # Arbitrage only pays off when price spread exceeds cycling cost
    max_price_diff = max_price - min_price
    net_arbitrage_per_kwh = max(0, max_price_diff - p.c_batt)

    # Battery can move at most one full capacity per day
    max_net_arbitrage = net_arbitrage_per_kwh * p.batt_cap

    # Subtract maximum net battery gain
    min_total_cost = max(0, min_total_cost - max_net_arbitrage)

    return {
        "lb_cost": min_total_cost,
        "lb_carbon": min_total_carbon
    }