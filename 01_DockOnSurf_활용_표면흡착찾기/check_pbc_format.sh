#!/bin/bash
# pbc_cell 형식 확인

echo "=== DockOnSurf pbc_cell parser ==="
grep -A 30 "def get_pbc_cell" ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/src/dockonsurf/dos_input.py

echo ""
echo "=== Examples from DockOnSurf ==="
find ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf -name "*.inp" -exec grep -l "pbc_cell" {} \; | head -5 | while read f; do
    echo "--- $f ---"
    grep -A 3 "pbc_cell" "$f" | head -10
done
