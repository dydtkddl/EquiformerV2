#!/bin/bash
# ============================================================
# Template 시스템 테스트
# ============================================================
# DESC: 워크플로우 템플릿 기능 테스트
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p output/template_test

echo "🧪 Testing Template System"
echo "=========================="

# ----------------------------------------
# 1. 기본 템플릿 설치
# ----------------------------------------
echo ""
echo "📦 Step 1: Installing default templates..."

surfscreen template install-defaults

echo "   ✅ Default templates installed"

# ----------------------------------------
# 2. 템플릿 목록 확인
# ----------------------------------------
echo ""
echo "📋 Step 2: Listing templates..."

surfscreen template list

# ----------------------------------------
# 3. 드라이런 테스트
# ----------------------------------------
echo ""
echo "🔍 Step 3: Dry-run basic_screening template..."

surfscreen template run basic_screening \
    -v element=Cu \
    -v miller=111 \
    -v molecule=water \
    --dry-run

echo ""
echo "   ✅ Dry-run completed (no actual execution)"

# ----------------------------------------
# 4. 사용자 정의 템플릿 생성
# ----------------------------------------
echo ""
echo "📝 Step 4: Creating custom template..."

mkdir -p ~/.surfscreen/templates

cat > ~/.surfscreen/templates/custom_workflow.yaml << 'EOF'
name: custom_workflow
description: Custom test workflow
version: "1.0"
author: SurfScreen User
variables:
  element: Pt
  output_dir: results
steps:
  - name: Create surface
    command: echo "Creating ${element} surface..."
  - name: Run optimization
    command: echo "Optimizing in ${output_dir}..."
  - name: Done
    command: echo "Workflow complete!"
EOF

echo "   ✅ Custom template created"

# ----------------------------------------
# 5. 사용자 정의 템플릿 실행
# ----------------------------------------
echo ""
echo "🚀 Step 5: Running custom template..."

surfscreen template run custom_workflow -v element=Au

echo ""
echo "========================================"
echo "📊 Template Test Summary"
echo "========================================"
echo "✅ Template system tests completed!"
