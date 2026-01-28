#!/usr/bin/env python3
import os
import time
import numpy as np
import torch
from ase.io import read, write
from ase.optimize import BFGS
from mace.calculators import MACECalculator

EV_TO_KCAL_MOL = 23.0605
MODEL_PATH = "/home/yongsang/.cache/mace/20231203mace128L1_epoch199model"
LOG_FILE = "opt_log.out"

# Ensure MODEL_PATH is valid
if MODEL_PATH is None or MODEL_PATH.lower() == "false":
    raise FileNotFoundError("Error: MODEL_PATH is not set correctly! Please provide a valid model file.")

# Load structure
atoms = read("struct_0.gen")

#  Check SLURM-assigned GPU
slurm_gpu = os.getenv("CUDA_VISIBLE_DEVICES")
if slurm_gpu is not None and torch.cuda.is_available():
    device = f"cuda:{slurm_gpu}"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

print(f"Running on assigned device: {device}")

#  Flush GPU memory before starting
if "cuda" in device and torch.cuda.is_available():
    print("Flushing GPU memory before starting...")
    torch.cuda.empty_cache()

#  Load MACE model with correct device
calc = MACECalculator(model_paths=[MODEL_PATH], default_dtype="float32", device=device)
atoms.calc = calc

# Define optimizer
optimizer = BFGS(atoms, trajectory="opt_trajectory.traj")

# Optimization settings
fmax = 0.05
max_steps = 60

# Open log file with header
with open(LOG_FILE, "w") as log_file:
    log_file.write("Step\tEnergy (eV)\tEnergy (kcal/mol)\tMax Force (eV/Å)\n")

step_numbers, energies_eV, energies_kcal_mol, max_forces = [], [], [], []

def log_optimization():
    step_number = len(step_numbers) + 1
    energy_eV = atoms.get_potential_energy()
    energy_kcal_mol = energy_eV * EV_TO_KCAL_MOL
    max_force = np.max(np.abs(atoms.get_forces()))

    step_numbers.append(step_number)
    energies_eV.append(energy_eV)
    energies_kcal_mol.append(energy_kcal_mol)
    max_forces.append(max_force)

    # Append properly formatted output to opt_log.out
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"{step_number}\t{energy_eV:.6f}\t{energy_kcal_mol:.2f}\t{max_force:.6f}\n")

    # Print formatted output for tracking
    print(f"Step {step_number}\tEnergy = {energy_eV:.6f} eV\t({energy_kcal_mol:.2f} kcal/mol)\tMax Force = {max_force:.6f} eV/Å", flush=True)

optimizer.attach(log_optimization, interval=1)

# Run optimization
t0 = time.time()
converged = optimizer.run(fmax=fmax, steps=max_steps)  # Capture convergence status
t1 = time.time()

final_message = ""

if converged:
    final_message = "\nOptimization finished successfully\n"
else:
    final_message = "\nWARNING: Optimization did NOT converge!\n"

with open(LOG_FILE, "a") as log_file:
    log_file.write(final_message)

print(final_message.strip())

# Save the optimized structure
write("optimized_structure.xyz", atoms)
write("optimized_structure.gen", atoms, format="gen")
