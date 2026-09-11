import random
import math
import time
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

# --- Helper Function: Calculate Total Clear Time for a State ---
def evaluate_state(weapon_idx, x_val):
    if (s - x_val + e) < W[weapon_idx]:
        return float('inf') 
        
    total_time = 0.0
    swing_time = T_base[weapon_idx] * (1.0 - 0.5 * ((s - x_val + e) / 100.0))
    
    for b_idx in J:
        dmg_per_hit = 0.0
        for d_idx in D:
            dmg_per_hit += (math.sqrt(x_val) * M[weapon_idx][d_idx]) * (1.0 - R[b_idx][d_idx])
            
        if dmg_per_hit < 1.0:
            return float('inf') 
            
        hits_needed = math.ceil(HP[b_idx] / dmg_per_hit)
        total_time += hits_needed * swing_time
        
    return total_time

# --- Simulated Annealing Configurations ---
temperature = 100.0
temperatureMin = 0.001

total_iterations = len(weapons) * s

cooling_rate = (temperatureMin / temperature) ** (1.0 / total_iterations)

p_swap = 0.15

currWeapon = random.randint(0, len(weapons) - 1)
currX = random.randint(1, s)
currTime = evaluate_state(currWeapon, currX)

while currTime == float('inf'):
    currWeapon = random.randint(0, len(weapons) - 1)
    currX = random.randint(1, s)
    currTime = evaluate_state(currWeapon, currX)

bestWeapon = currWeapon
bestX = currX
bestTime = currTime

start_real_time = time.perf_counter()

# --- Optimization Engine ---
while temperature > temperatureMin:
    if random.random() < p_swap:
        neighborWeapon = random.choice([w for w in I if w != currWeapon])
        neighborX = currX
    else:
        neighborWeapon = currWeapon
        step = random.choice([-2, -1, 1, 2])
        neighborX = max(1, min(s, currX + step))
        
    neighborTime = evaluate_state(neighborWeapon, neighborX)
    
    if neighborTime == float('inf'):
        continue
        
    if neighborTime < currTime:
        currWeapon = neighborWeapon
        currX = neighborX
        currTime = neighborTime
    else:
        delta_energy = neighborTime - currTime
        acceptance_prob = math.exp(-delta_energy / temperature)
        
        if random.random() < acceptance_prob:
            currWeapon = neighborWeapon
            currX = neighborX
            currTime = neighborTime
            
    if currTime < bestTime:
        bestTime = currTime
        bestWeapon = currWeapon
        bestX = currX
        
    temperature *= cooling_rate

end_real_time = time.perf_counter()
execution_duration_ms = (end_real_time - start_real_time) * 1000.0

# --- Post-Processing: Compute Metrics for the Final Summary ---
final_swing_duration = T_base[bestWeapon] * (1.0 - 0.5 * ((s - bestX + e) / 100.0))
dynamic_endurance = (s - bestX)
total_hits_gauntlet = 0

combat_breakdown_lines = []
for b_idx in J:
    dmg_per_hit = 0.0
    for d_idx in D:
        dmg_per_hit += (math.sqrt(bestX) * M[bestWeapon][d_idx]) * (1.0 - R[b_idx][d_idx])
    
    hits_needed = math.ceil(HP[b_idx] / dmg_per_hit)
    total_hits_gauntlet += hits_needed
    boss_clear_time = hits_needed * final_swing_duration
    
    line = f" - {bosses[b_idx]:<28} | Output: {dmg_per_hit:<5.1f} dmg | Hits: {hits_needed:<4} | Time: {boss_clear_time:.2f}s"
    combat_breakdown_lines.append(line)

# --- Console Output ---
print("=" * 75)
print("     OPTIMAL ELDEN RING TIME-MINIMIZATION COMPLETED")
print("=" * 75)
print(f"Chosen Weapon             : {weapons[bestWeapon]}")
print(f"Base Swing Velocity       : {T_base[bestWeapon]:.2f} seconds")
print(f"Allocated Stats (x)       : {bestX} points")
print(f"Dynamic Endurance Pool (e): {dynamic_endurance} (+ {e} Base) -> {dynamic_endurance + e} Total")
print(f"Actual Swing Duration     : {final_swing_duration:.3f} seconds / attack")
print(f"Load Limit Integrity     : {W[bestWeapon]} / {dynamic_endurance + e} units")
print("-" * 75)
print("Combat Breakdown vs. Boss Gauntlet:")
for line in combat_breakdown_lines:
    print(line)
print("-" * 75)
print(f"TOTAL RUN PERFORMANCE : {bestTime:.2f} COMBAT SECONDS CLEAR ({total_hits_gauntlet} total hits)")
print(f"ALGORITHM SOLVE TIME  : {execution_duration_ms:.2f} ms ({total_iterations} iterations tracked)")
print("=" * 75)