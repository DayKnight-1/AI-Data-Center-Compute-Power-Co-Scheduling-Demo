# scheduler/model.py
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np

@dataclass
class Task:
    id: int
    arrival: float
    deadline: float
    p: Dict[str, float]       # kW
    w: Dict[str, float]       # kWh
    length: Dict[str, float]  # hours
    kind: str                 # "deadline" or "elastic"
    interruptible: bool
    interrupt_cost: float
    max_interrupt: int
    delay_penalty: float

    def duration_slots(self, tier: str, dt: float) -> int:
        return max(1, int(np.ceil(self.length[tier] / dt)))

@dataclass
class Curves:
    grid_price: np.ndarray
    green_price: np.ndarray
    green_avail: np.ndarray
    carbon: np.ndarray
    rigid_load: np.ndarray

@dataclass
class Problem:
    dt: float
    horizon: float
    capacity: float
    curves: Curves
    tasks: List[Task]
    lam: float
    batt_cap: float = 1000.0
    batt_power: float = 250.0
    batt_init: float = 500.0
    c_batt: float = 0.6

@dataclass
class Schedule:
    assignment: Dict[int, List[Tuple[int, str]]] # task_id -> [(slot_idx, tier)]
    interrupt_count: Dict[int, int]
    grid_power: np.ndarray
    green_power: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray
    metrics: Dict[str, float] = field(default_factory=dict)
    method: str = "greedy"