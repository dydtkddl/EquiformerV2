#!/bin/bash
# ============================================================
# Example 20: 전체 파이프라인 데모
# ============================================================
# 테스트: 전체 워크플로우
# 설명: 표면 생성 → 분자 준비 → 스크리닝 → MD → 분석 → 리포트
# ============================================================

set -e

echo "========================================================"
echo "Example 20: Complete SurfScreen Pipeline Demo"
echo "========================================================"

mkdir -p output/20_pipeline
cd output/20_pipeline

echo ""
echo "🚀 Starting complete pipeline..."
echo ""

# Step 1: 표면 생성
echo "========================================="
echo "Step 1/7: Surface Creation"
echo "========================================="
surfscreen surface create Pt --miller 111 --layers 4 --supercell 3x3x1 --fix 2 -o Pt111.xyz
surfscreen surface sites Pt111.xyz
echo "✓ Pt(111) surface created"

# Step 2: 분자 준비
echo ""
echo "========================================="
echo "Step 2/7: Molecule Preparation"
echo "========================================="
surfscreen molecule from-pubchem CO -o CO.xyz
surfscreen molecule analyze CO.xyz
echo "✓ CO molecule ready"

# Step 3: 흡착 구성 생성
echo ""
echo "========================================="
echo "Step 3/7: Adsorption Config Generation"
echo "========================================="
surfscreen adsorb generate -s Pt111.xyz -m CO.xyz -r 0,45,90 -H 1.8,2.0,2.2 -o configs/
echo "✓ Configs generated: $(ls configs/*.xyz | wc -l) structures"

# Step 4: 흡착 스크리닝
echo ""
echo "========================================="
echo "Step 4/7: Adsorption Screening"
echo "========================================="
surfscreen screen run -s Pt111.xyz -m CO.xyz \
    --engine mace --device cpu --max-configs 10 \
    -o screening/
echo "✓ Screening completed"

# Step 5: 스크리닝 결과 확인
echo ""
echo "========================================="
echo "Step 5/7: Screening Results"
echo "========================================="
surfscreen screen results screening/results.json --top 5
surfscreen screen report screening/ -o screen_report.html
echo "✓ Report: screen_report.html"

# Step 6: 최적 구조에서 MD
echo ""
echo "========================================="
echo "Step 6/7: MD on Best Structure"
echo "========================================="
# 최적 구조 파일 (첫 번째 optimized 구조)
best_structure=$(ls screening/optimized/*.xyz 2>/dev/null | head -1)
if [ -n "$best_structure" ]; then
    surfscreen md run "$best_structure" \
        --ensemble nvt --temperature 300 --steps 50 \
        --engine mace --device cpu \
        -o md_best/
    surfscreen md report md_best/ -o md_report.html
    echo "✓ MD completed on best structure"
else
    echo "⚠️ No optimized structures found, skipping MD"
fi

# Step 7: 분석 및 정리
echo ""
echo "========================================="
echo "Step 7/7: Analysis & Summary"
echo "========================================="
if [ -d "md_best" ]; then
    surfscreen analysis msd md_best/trajectory.traj -s Pt -o msd.html 2>/dev/null || true
fi

echo ""
echo "========================================================"
echo "✅ Pipeline Demo Completed!"
echo "========================================================"
echo ""
echo "📁 Output Structure:"
echo "├── Pt111.xyz           - Surface"
echo "├── CO.xyz              - Molecule"
echo "├── configs/            - Adsorption configs"
echo "├── screening/          - Screening results"
echo "├── screen_report.html  - Screening report"
echo "├── md_best/            - MD trajectory"
echo "└── md_report.html      - MD report"
echo ""
echo "🌐 Open in browser:"
echo "   firefox screen_report.html"
echo "   firefox md_report.html"
echo "========================================================"
