# scheduler/metrics.py
import numpy as np
from scheduler.model import Problem, Schedule


def calc_metrics(schedule: Schedule, p: Problem) -> dict:
    cost = np.sum(p.curves.grid_price * schedule.grid_power * p.dt) + \
           np.sum(p.curves.green_price * schedule.green_power * p.dt)
    carbon = np.sum(p.curves.carbon * schedule.grid_power * p.dt)
    batt_cost = p.c_batt * np.sum(schedule.discharge * p.dt)

    # Fix: build ID→Task dict to avoid index misalignment after shuffle
    task_dict = {t.id: t for t in p.tasks}

    # Correctly compute interrupt cost
    interrupt_cost = sum(task_dict[j].interrupt_cost * c for j, c in schedule.interrupt_count.items() if j in task_dict)

    # Robust SLA check: iterate p.tasks instead of relying on ID continuity
    sla_violations = sum(1 for t in p.tasks if t.id not in schedule.assignment or not schedule.assignment[t.id])

    # SLA penalty: 1000 CNY per unscheduled task
    sla_penalty = sla_violations * 1000.0

    return {
        "cost": cost,
        "carbon": carbon,
        "sla": sla_violations,
        "batt_cycles": np.sum(schedule.discharge * p.dt) / p.batt_cap,
        "objective": cost + p.lam * carbon + batt_cost + interrupt_cost + sla_penalty
    }