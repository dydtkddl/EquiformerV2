#!/bin/bash
# ============================================================
# Example 14: RDF (Radial Distribution Function) 분석
# ============================================================
# 테스트: surfscreen analysis rdf
# 설명: 궤적에서 원자 쌍의 RDF 계산
# ============================================================

set -e

echo "========================================"
echo "Example 14: RDF Analysis"
echo "========================================"

mkdir -p output/14_rdf
cd output/14_rdf

# MD 실행
echo ""
echo "[1/3] Running MD for trajectory..."
surfscreen surface create Cu --miller 111 --layers 2 --supercell 2x2x1 -o Cu111.xyz
surfscreen md run Cu111.xyz \
    --ensemble nvt \
    --temperature 300 \
    --steps 100 \
    --engine mace \
    --device cpu \
    -o md_output/
echo "✓ MD completed"

# RDF 계산 (Cu-Cu)
echo ""
echo "[2/3] Calculating Cu-Cu RDF..."
surfscreen analysis rdf md_output/trajectory.traj -p Cu-Cu --rmax 8.0 -o rdf_CuCu.html
echo "✓ RDF calculated"

# 결과
echo ""
echo "[3/3] Results..."
echo "RDF Plot: rdf_CuCu.html"

echo ""
echo "========================================"
echo "✅ Example 14 completed!"
echo "========================================"
