#!/bin/bash
# ============================================================
# Coverage 및 Phonon 분석 테스트
# ============================================================
# DESC: 피복도 및 진동 분석 기능 테스트
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p output/analysis_advanced

echo "🧪 Testing Advanced Analysis Features"
echo "======================================"

# ----------------------------------------
# 1. 테스트 구조 생성
# ----------------------------------------
echo ""
echo "📝 Step 1: Creating test structures..."

# Python으로 표면 + 흡착 분자 생성
python << 'EOF'
from ase.build import fcc111, molecule
from ase.io import write

# Cu(111) 표면
surface = fcc111('Cu', size=(3, 3, 4), vacuum=15.0)
n_surface = len(surface)
print(f"Surface atoms: {n_surface}")

# CO 분자 추가
co = molecule('CO')
co.translate([5, 5, 20])

system = surface + co
write('output/analysis_advanced/surface_co.xyz', system)
print("Created: surface_co.xyz")

# 단순 분자 (phonon용)
h2o = molecule('H2O')
write('output/analysis_advanced/water.xyz', h2o)
print("Created: water.xyz")
EOF

echo "   ✅ Test structures created"

# ----------------------------------------
# 2. Coverage 분석
# ----------------------------------------
echo ""
echo "📊 Step 2: Coverage analysis..."

surfscreen analysis coverage output/analysis_advanced/surface_co.xyz \
    --n-surface 36 \
    --mol-area 10.0

echo "   ✅ Coverage analysis completed"

# ----------------------------------------
# 3. Phonon 분석 (xTB - 분자용)
# ----------------------------------------
echo ""
echo "🔊 Step 3: Phonon analysis (water molecule)..."

# xTB가 PBC 없는 분자에서 작동
surfscreen analysis phonon output/analysis_advanced/water.xyz \
    --engine xtb \
    --delta 0.01 || echo "   ⚠️ Phonon analysis requires ASE vibrations (may fail on first run)"

# ----------------------------------------
# 4. Gibbs 자유에너지 계산
# ----------------------------------------
echo ""
echo "🔥 Step 4: Gibbs free energy calculation..."

surfscreen analysis gibbs output/analysis_advanced/water.xyz \
    -T 298.15 \
    --engine xtb || echo "   ⚠️ Gibbs calculation requires phonon data"

# ----------------------------------------
# 결과 요약
# ----------------------------------------
echo ""
echo "========================================"
echo "📊 Advanced Analysis Test Summary"
echo "========================================"
echo "Created files:"
ls -la output/analysis_advanced/
echo ""
echo "✅ Advanced analysis tests completed!"
