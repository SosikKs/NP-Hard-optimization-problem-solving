import time
from gurobipy import *
import csv
import argparse

# Add argument -complex 1 / 2 / 3 / 4 / 5 for different dataset sizes
parser = argparse.ArgumentParser(description="Elden Ring Gauntlet Optimization Engine")
parser.add_argument(
    '-complex', 
    type=int, 
    choices=[1, 2, 3, 4, 5], 
    default=1, 
    help="Select the boss complexity list profile (1, 2, 3, 4 or 5)"
)
args = parser.parse_args()
weapons_filename=f"Datasets/weapons{args.complex}.csv"
bosses_filename = f"Datasets/bosses{args.complex}.csv"

# --- Sets and Parameters ---
damage_types = ["Standard", "Strike", "Slash", "Piercing", "Magic", "Fire", "Lightning", "Holy"]
D = range(len(damage_types))

weapons_data = {}
with open(weapons_filename, mode='r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        dmg_vector = [float(row[dt]) for dt in damage_types]
        
        weapons_data[row['WeaponName']] = (
            float(row['Weight']), 
            dmg_vector, 
            float(row['BaseSwingTime'])
        )

weapons = list(weapons_data.keys())
I = range(len(weapons))
W = [weapons_data[w][0] for w in weapons]
M = [weapons_data[w][1] for w in weapons]
T_base = [weapons_data[w][2] for w in weapons]

bosses_data = {}
with open(bosses_filename, mode='r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        res_vector = [float(row[dt]) for dt in damage_types]
        
        bosses_data[row['BossName']] = (
            int(row['HP']), 
            res_vector
        )

bosses = list(bosses_data.keys())
J = range(len(bosses))

HP = [bosses_data[b][0] for b in bosses]
R = [bosses_data[b][1] for b in bosses]

s = 100
e = 10
B = 999999  




# --- Model Initialization ---
'''
wls_config = {
    "WLSACCESSID": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "WLSSECRET": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "LICENSEID": xxxxxxx,
}
wls_env = Env(params=wls_config)

start_real_time = time.perf_counter()
problem = Model("Elden_Ring_Combat_Time_Optimization", env=wls_env)
'''

start_real_time = time.perf_counter()
problem = Model("Elden_Ring_Combat_Time_Optimization")

# Suppress standard Gurobi terminal spam
problem.setParam('OutputFlag', 0) 
# Enable non-convex engine handling for bilinear/quadratic terms
problem.setParam('NonConvex', 2)  

# --- Decision Variables ---
x = problem.addVar(vtype=GRB.INTEGER, lb=1, ub=s, name="offensive_stats") 
# New variable representing sqrt(x)
w = problem.addVar(vtype=GRB.CONTINUOUS, lb=1.0, ub=10.0, name="sqrt_offensive_stats")

y = problem.addVars(len(I), vtype=GRB.BINARY, name="equip_weapon")
h = problem.addVars(len(I), len(J), vtype=GRB.INTEGER, lb=0, name="hits_per_weapon_per_boss")

# --- Constraints ---
problem.addConstr(x <= s, name="Resource_allocation_bound")
# Link w to x mathematically so that w = sqrt(x) -> w^2 = x
problem.addConstr(w * w == x, name="link_sqrt_x")

problem.addConstr(quicksum(y[i] for i in I) == 1, name="Weapon_selection_constraint")
problem.addConstr(quicksum(y[i] * W[i] for i in I) + x <= s + e, name="Weight_requirement")

for j in J:
    for i in I:
        dmg_expr = quicksum((w * M[i][k]) * (1 - R[j][k]) for k in D)
        
        problem.addConstr(dmg_expr >= 1 - B * (1 - y[i]), name=f"Damage_Bounding_{i}_{j}")
        problem.addConstr(h[i, j] * dmg_expr >= HP[j] - B * (1 - y[i]), name=f"Hits_ceiling_{i}_{j}")
        problem.addConstr(h[i, j] <= B * y[i], name=f"Force_zero_hits_{i}_{j}")

# --- Objective Definition ---
problem.setObjective(
    quicksum(h[i, j] * T_base[i] * (1.0 - 0.5 * ((s - x + e) / 100.0))
    for i in I for j in J), GRB.MINIMIZE)

# --- Execute Solver Optimization ---
problem.optimize()

end_real_time = time.perf_counter()
execution_duration_ms = (end_real_time - start_real_time) * 1000.0

# --- Display Output ---
# Catch both optimal and suboptimal pool structures
if problem.status in [GRB.OPTIMAL, GRB.SUBOPTIMAL]:
    selected_idx = [i for i in I if y[i].X > 0.5][0]
    opt_x = int(x.X)
    opt_w = w.X
    opt_e = s - opt_x + e  
    dynamic_endurance = s - opt_x
    
    final_swing_time = T_base[selected_idx] * (1.0 - 0.5 * ((s - opt_x + e) / 100.0))

    # --- Console Output ---
    print("=" * 75)
    if problem.status == GRB.SUBOPTIMAL:
        print("     MIP GAUNTLET RUN COMPLETED (Feasible Strategy Found)")
    else:
        print("       OPTIMAL ELDEN RING TIME-MINIMIZATION COMPLETED")
    print("=" * 75)
    print(f"Chosen Weapon             : {weapons[selected_idx]}")
    print(f"Base Swing Velocity       : {T_base[selected_idx]:.2f} seconds")
    print(f"Allocated Stats (x)       : {opt_x} points (Effective sqrt(x) scaling value: {opt_w:.2f})")
    print(f"Dynamic Endurance Pool (e): {dynamic_endurance} (+ {e} Base) -> {opt_e} Total")
    print(f"Actual Swing Duration     : {final_swing_time:.3f} seconds / attack")
    print(f"Load Limit Integrity      : {W[selected_idx]} / {opt_e} units")
    print("-" * 75)
    print("Combat Breakdown vs. Boss Gauntlet:")

    total_hits = 0
    for j in J:
        # Display the real output using the optimal square-root scaling factor
        boss_dmg = sum((opt_w * M[selected_idx][k]) * (1 - R[j][k]) for k in D)
        boss_hits = int(h[selected_idx, j].X)
        total_hits += boss_hits
        boss_time = boss_hits * final_swing_time
        print(f" - {bosses[j]:<28} | Output: {boss_dmg:<5.1f} dmg | Hits: {boss_hits:<4} | Time: {boss_time:.2f}s")

    print("-" * 75)
    print(f"TOTAL RUN PERFORMANCE : {problem.ObjVal:.2f} COMBAT SECONDS CLEAR ({total_hits} total hits)")
    print(f"ALGORITHM SOLVE TIME  : {execution_duration_ms:.2f} ms (Gurobi Engine Global MIP)")
    print("=" * 75)
else:
    print(f"Solver stopped with status code: {problem.status}. Check constraints or attribute limits.")