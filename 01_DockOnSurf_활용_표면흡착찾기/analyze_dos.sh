#!/bin/bash
# ============================================
# DockOnSurf 소스 코드 분석
# ============================================

echo "=== DockOnSurf batch_q_sys supported values ==="
grep -r "batch_q_sys" ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/src/dockonsurf/*.py | head -50

echo ""
echo "=== isolated.py main function ==="
head -100 ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/src/dockonsurf/isolated.py

echo ""
echo "=== Checking for 'local' support ==="
grep -r "local" ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/src/dockonsurf/*.py | grep -i batch | head -20
