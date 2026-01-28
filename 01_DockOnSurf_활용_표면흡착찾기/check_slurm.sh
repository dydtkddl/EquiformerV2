#!/bin/bash
# ============================================
# SLURM 환경 확인
# ============================================

echo "=== Checking SLURM availability ==="
which sbatch 2>/dev/null && echo "sbatch: Found" || echo "sbatch: NOT FOUND"
which squeue 2>/dev/null && echo "squeue: Found" || echo "squeue: NOT FOUND"
which sinfo 2>/dev/null && echo "sinfo: Found" || echo "sinfo: NOT FOUND"

echo ""
echo "=== SLURM version ==="
sbatch --version 2>/dev/null || echo "SLURM not available"

echo ""
echo "=== Available partitions ==="
sinfo 2>/dev/null || echo "Cannot query SLURM info"

echo ""
echo "=== Current queue ==="
squeue -u $USER 2>/dev/null || echo "Cannot query queue"
