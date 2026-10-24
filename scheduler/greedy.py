# scheduler/greedy.py
import numpy as np
from scheduler.model import Problem, Schedule
from scheduler.metrics import calc_metrics


def run_greedy(p: Problem) -> Schedule:
    T = int(p.horizon / p.dt)
    assignment = {}
    avail_cap = p.capacity - p.curves.rigid_load

    for task in sorted(p.tasks, key=lambda x: (x.deadline, x.arrival)):
        best_slot = -1
        best_tier = "std"
        min_cost = float('inf')
        start_idx = int(task.arrival / p.dt)

        for tier in ["slow", "std", "fast"]:
            dur = task.duration_slots(tier, p.dt)
            for t in range(start_idx, T - dur + 1):
                if t + dur > int(task.deadline / p.dt) + 1: break
                if np.any(avail_cap[t:t + dur] < task.p[tier]): continue

                cost = 0
                for k in range(t, t + dur):
                    cost += p.curves.grid_price[k] * task.p[tier] * p.dt
                    # Combined cost including carbon price and green power
                    cost += p.lam * p.curves.carbon[k] * task.p[tier] * p.dt

                if cost < min_cost:
                    min_cost = cost
                    best_slot = t
                    best_tier = tier

        if best_slot != -1:
            dur = task.duration_slots(best_tier, p.dt)
            assignment[task.id] = [(k, best_tier) for k in range(best_slot, best_slot + dur)]
            for k in range(best_slot, best_slot + dur):
                avail_cap[k] -= task.p[best_tier]
        else:
            assignment[task.id] = []

    # Simple battery follow (discharge at evening peak, charge at night)
    load = p.curves.rigid_load.copy()
    for tid, blocks in assignment.items():
        task = next(t for t in p.tasks if t.id == tid)
        for (t, tier) in blocks: load[t] += task.p[tier]

    grid = np.zeros(T);
    green = np.zeros(T)
    charge = np.zeros(T);
    discharge = np.zeros(T);
    soc = np.zeros(T)
    current_soc = p.batt_init

    for t in range(T):
        rem = load[t]
        use_g = min(rem, p.curves.green_avail[t])
        green[t] = use_g
        rem -= use_g

        if p.curves.grid_price[t] > 1.0 and current_soc > 0:
            d = min(p.batt_power, current_soc, rem)
            discharge[t] = d;
            current_soc -= d;
            rem -= d
        elif p.curves.grid_price[t] < 0.4 and current_soc < p.batt_cap:
            c = min(p.batt_power, p.batt_cap - current_soc)
            charge[t] = c;
            current_soc += c

        grid[t] = rem + charge[t]
        soc[t] = current_soc

    sched = Schedule(assignment=assignment, interrupt_count={}, grid_power=grid,
                     green_power=green, charge=charge, discharge=discharge, soc=soc)
    sched.metrics = calc_metrics(sched, p)
    sched.method = "Greedy Scheduling"
    return sched