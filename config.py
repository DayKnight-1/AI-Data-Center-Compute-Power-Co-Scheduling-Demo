# config.py
DT = 1.0               # Time step (hours)
HORIZON = 24           # Planning horizon
SEED = 42              # Random seed
CAPACITY = 500.0       # Data center total compute capacity (kW)
BATTERY_CAPACITY = 1000.0
BATTERY_POWER = 250.0
BATTERY_INIT_SOC = 500.0
C_BATT = 0.60          # Battery cycling cost
LAMBDA_DEFAULT = 0.5   # Default carbon price
N_GPU = 400            # Number of GPUs in 3D view