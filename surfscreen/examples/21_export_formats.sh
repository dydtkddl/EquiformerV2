#!/bin/bash
# ============================================================
# Export 기능 테스트
# ============================================================
# DESC: CSV, JSON, Excel, ZIP 내보내기 테스트
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p output/export_test

echo "🧪 Testing Export Features"
echo "=========================="

# ----------------------------------------
# 1. 테스트 데이터 생성
# ----------------------------------------
echo ""
echo "📝 Step 1: Creating sample results..."

mkdir -p output/export_test/results
cat > output/export_test/results/results.json << 'EOF'
{
    "results": [
        {"name": "config1", "e_ads": -1.5, "height": 2.0, "site": "top"},
        {"name": "config2", "e_ads": -1.2, "height": 2.5, "site": "bridge"},
        {"name": "config3", "e_ads": -1.8, "height": 1.8, "site": "hollow"},
        {"name": "config4", "e_ads": -0.9, "height": 3.0, "site": "top"},
        {"name": "config5", "e_ads": -2.1, "height": 1.5, "site": "hollow"}
    ],
    "summary": {
        "best_energy": -2.1,
        "best_config": "config5",
        "total_configs": 5
    },
    "metadata": {
        "surface": "Cu111",
        "molecule": "acetone",
        "engine": "mace"
    }
}
EOF

echo "   ✅ Sample results.json created"

# ----------------------------------------
# 2. CSV 내보내기
# ----------------------------------------
echo ""
echo "📊 Step 2: Exporting to CSV..."

surfscreen export csv output/export_test/results -o output/export_test/results.csv

if [ -f "output/export_test/results.csv" ]; then
    echo "   ✅ CSV export successful"
    echo "   Preview:"
    head -3 output/export_test/results.csv
else
    echo "   ❌ CSV export failed"
    exit 1
fi

# ----------------------------------------
# 3. JSON 내보내기
# ----------------------------------------
echo ""
echo "📋 Step 3: Exporting to JSON..."

surfscreen export json output/export_test/results -o output/export_test/results_export.json

if [ -f "output/export_test/results_export.json" ]; then
    echo "   ✅ JSON export successful"
else
    echo "   ❌ JSON export failed"
    exit 1
fi

# ----------------------------------------
# 4. ZIP 내보내기
# ----------------------------------------
echo ""
echo "📦 Step 4: Exporting to ZIP..."

surfscreen export zip output/export_test/results -o output/export_test/results.zip --no-structures --no-trajectories

if [ -f "output/export_test/results.zip" ]; then
    echo "   ✅ ZIP export successful"
    echo "   Contents:"
    unzip -l output/export_test/results.zip 2>/dev/null | head -10 || echo "   (unzip not available)"
else
    echo "   ❌ ZIP export failed"
    exit 1
fi

# ----------------------------------------
# 5. Excel 내보내기 (pandas 필요)
# ----------------------------------------
echo ""
echo "📈 Step 5: Exporting to Excel..."

if python -c "import pandas; import openpyxl" 2>/dev/null; then
    surfscreen export excel output/export_test/results -o output/export_test/results.xlsx
    
    if [ -f "output/export_test/results.xlsx" ]; then
        echo "   ✅ Excel export successful"
    else
        echo "   ❌ Excel export failed"
    fi
else
    echo "   ⚠️ Skipped (pandas/openpyxl not installed)"
fi

# ----------------------------------------
# 결과 요약
# ----------------------------------------
echo ""
echo "========================================"
echo "📊 Export Test Summary"
echo "========================================"
ls -la output/export_test/
echo ""
echo "✅ Export tests completed!"
