# data/generator.py
import numpy as np
from scheduler.model import Problem, Task, Curves
import config


def build_problem(scenario: str, lam: float, seed: int = 42) -> Problem:
    rng = np.random.default_rng(seed)

    # 1. Baseline data
    grid_price = np.array([0.3] * 6 + [0.5] * 2 + [0.9] * 3 + [0.6] * 3 + [0.9] * 3 + [1.2] * 4 + [0.6] * 3)
    green_avail = np.array([20] * 6 + [50] * 2 + [150] * 3 + [300] * 3 + [180] * 3 + [80] * 2 + [60] * 5)
    carbon = np.array([0.85] * 6 + [0.75] * 2 + [0.6] * 3 + [0.3] * 3 + [0.55] * 3 + [0.8] * 4 + [0.75] * 3)
    rigid_load = np.array([50] * 6 + [100] * 3 + [150] * 4 + [180] * 5 + [120] * 6)

    num_deadline = 12
    num_elastic = 6

    # 2. Scenario overrides
    if scenario == "☁️ Cloudy (Low Solar)":
        # Cloudy day: midday solar drops sharply
        green_avail = np.array([20] * 6 + [50] * 2 + [100] * 3 + [100] * 3 + [100] * 3 + [80] * 2 + [60] * 5)
    elif scenario == "📈 Demand Surge":
        # Load +30%, task count +50%
        rigid_load = (rigid_load * 1.3).astype(int)
        num_deadline = 18
        num_elastic = 9
    elif scenario == "⚡ Price Spike":
        # Evening peak price spikes to 1.8, carbon rises
        grid_price = np.array([0.3] * 6 + [0.5] * 2 + [0.9] * 3 + [0.6] * 3 + [0.9] * 3 + [1.8] * 4 + [0.6] * 3)
        carbon = np.array([0.85] * 6 + [0.75] * 2 + [0.6] * 3 + [0.3] * 3 + [0.55] * 3 + [1.0] * 4 + [0.75] * 3)

    # Green price tracks grid price
    green_price = np.clip(grid_price * 0.8 - 0.05, 0.15, 0.5)

    tasks = []
    task_id = 1

    # Deadline tasks
    for _ in range(num_deadline):
        arr = rng.uniform(0, 16)
        dur = rng.uniform(4, 8)
        p_std = rng.uniform(40, 80)
        w_std = p_std * dur
        deadline = min(24.0, arr + dur + rng.uniform(6, 12))

        tasks.append(Task(
            id=task_id, arrival=arr, deadline=deadline,
            p={"slow": p_std * 0.6, "std": p_std, "fast": p_std * 1.5},
            w={"slow": w_std * 0.9, "std": w_std, "fast": w_std * 1.1},
            length={"slow": (w_std * 0.9) / (p_std * 0.6), "std": dur, "fast": (w_std * 1.1) / (p_std * 1.5)},
            kind="deadline", interruptible=rng.random() > 0.5,
            interrupt_cost=0.5, max_interrupt=2, delay_penalty=100.0
        ))
        task_id += 1

    # Elastic tasks
    for _ in range(num_elastic):
        arr = rng.uniform(0, 10)
        dur = rng.uniform(3, 6)
        p_std = rng.uniform(20, 50)
        w_std = p_std * dur

        tasks.append(Task(
            id=task_id, arrival=arr, deadline=24.0,
            p={"slow": p_std * 0.6, "std": p_std, "fast": p_std * 1.5},
            w={"slow": w_std * 0.9, "std": w_std, "fast": w_std * 1.1},
            length={"slow": (w_std * 0.9) / (p_std * 0.6), "std": dur, "fast": (w_std * 1.1) / (p_std * 1.5)},
            kind="elastic", interruptible=True,
            interrupt_cost=0.2, max_interrupt=3, delay_penalty=0.0
        ))
        task_id += 1

    rng.shuffle(tasks)
    curves = Curves(grid_price=grid_price, green_price=green_price,
                    green_avail=green_avail, carbon=carbon, rigid_load=rigid_load)
    return Problem(dt=config.DT, horizon=config.HORIZON, capacity=config.CAPACITY,
                   curves=curves, tasks=tasks, lam=lam)