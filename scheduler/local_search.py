# scheduler/local_search.py
import numpy as np
import copy
import random
from scheduler.model import Problem, Schedule
from scheduler.metrics import calc_metrics
from scheduler.greedy import run_greedy


def _evaluate_schedule(p: Problem, assignment: dict, interrupt_count: dict) -> Schedule:
    T = int(p.horizon / p.dt)
    load = p.curves.rigid_load.copy()
    for tid, blocks in assignment.items():
        tsk = next(t for t in p.tasks if t.id == tid)
        for (t, tier) in blocks: load[t] += tsk.p[tier]

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
            d = min(p.batt_power, current_soc, rem);
            discharge[t] = d;
            current_soc -= d;
            rem -= d
        elif p.curves.grid_price[t] < 0.4 and current_soc < p.batt_cap:
            c = min(p.batt_power, p.batt_cap - current_soc);
            charge[t] = c;
            current_soc += c
        grid[t] = rem + charge[t];
        soc[t] = current_soc

    sched = Schedule(assignment=assignment, interrupt_count=interrupt_count,
                     grid_power=grid, green_power=green, charge=charge,
                     discharge=discharge, soc=soc)
    sched.metrics = calc_metrics(sched, p)
    return sched


def run_local_search(p: Problem, max_iter=2000) -> Schedule:
    init_sched = run_greedy(p)
    if not init_sched.assignment: return init_sched

    best_sched = copy.deepcopy(init_sched)
    current_sched = copy.deepcopy(init_sched)
    T = int(p.horizon / p.dt)

    for _ in range(max_iter):
        valid_tasks = [t for t in p.tasks if current_sched.assignment.get(t.id)]
        if not valid_tasks: break
        task = random.choice(valid_tasks)

        new_assign = copy.deepcopy(current_sched.assignment)
        new_interrupts = copy.deepcopy(current_sched.interrupt_count)

        old_blocks = new_assign[task.id]
        start_t = old_blocks[0][0]
        old_tier = old_blocks[0][1]

        actions = ["tier", "shift"]
        if task.interruptible and new_interrupts.get(task.id, 0) < task.max_interrupt:
            actions.append("split")
        action = random.choice(actions)

        if action == "tier":
            new_tier = random.choice(["slow", "std", "fast"])
            if new_tier == old_tier: continue
            new_dur = task.duration_slots(new_tier, p.dt)
            if start_t + new_dur > p.horizon: continue
            new_assign[task.id] = [(t, new_tier) for t in range(start_t, start_t + new_dur)]

        elif action == "shift":
            shift = random.randint(-4, 4)
            new_start = start_t + shift
            dur = len(old_blocks)
            if new_start < int(task.arrival / p.dt) or new_start + dur > int(task.deadline / p.dt): continue
            new_assign[task.id] = [(t, old_tier) for t in range(new_start, new_start + dur)]

        elif action == "split":
            dur = len(old_blocks)
            if dur > 2:  # Need at least 3 hours to allow a split
                split_point = random.randint(1, dur - 2)
                head = old_blocks[:split_point]
                tail_dur = dur - split_point
                start_idx = int(task.arrival / p.dt)
                best_tail = None

                for t in range(start_idx, T - tail_dur + 1):
                    if t + tail_dur > int(task.deadline / p.dt): break
                    # Force a gap of at least 2 hours!
                    if t < head[-1][0] + 2: continue
                    if any(k in [b[0] for b in head] for k in range(t, t + tail_dur)): continue

                    load = p.curves.rigid_load.copy()
                    for tid, blocks in new_assign.items():
                        if tid == task.id: continue
                        tsk = next(x for x in p.tasks if x.id == tid)
                        for (b_t, tier) in blocks: load[b_t] += tsk.p[tier]
                    for b_t, tier in head: load[b_t] += task.p[tier]

                    if any(load[k] + task.p[old_tier] > p.capacity for k in range(t, t + tail_dur)): continue

                    best_tail = [(k, old_tier) for k in range(t, t + tail_dur)]
                    break

                if best_tail:
                    new_assign[task.id] = head + best_tail
                    new_interrupts[task.id] = new_interrupts.get(task.id, 0) + 1

        new_sched = _evaluate_schedule(p, new_assign, new_interrupts)

        # Since interrupt cost is lower, tighten the tolerance for degradation
        if new_sched.metrics["objective"] < current_sched.metrics["objective"] * 1.05:
            current_sched = new_sched
            if new_sched.metrics["objective"] < best_sched.metrics["objective"]:
                best_sched = new_sched

    best_sched.method = "Greedy + Local Search"
    return best_sched