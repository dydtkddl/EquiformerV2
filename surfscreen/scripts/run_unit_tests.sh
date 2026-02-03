#!/bin/bash
###############################################################################
# Unit Tests Runner (Enhanced with Logging & Progress Tracking)
#
# 기능을 완벽히 수행하기 위해 로그 파일 생성 및 tqdm 기반 진행률을 지원합니다.
###############################################################################

set -euo pipefail

# 1. 환경 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_ROOT/tests/unit"
LOG_DIR="$PROJECT_ROOT/logs"
DATE_STR=$(date +"%Y%m%d")
LOG_FILE="$LOG_DIR/test.$DATE_STR.log"

# 로그 디렉토리 자동 생성 (능동적 대안 탐색)
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_ROOT/test_outputs"

# 2. Python 헬퍼 스크립트 생성 (Logging & tqdm 연동)
# Bash에서 직접 tqdm을 구현하는 것보다 Python 래퍼를 통해 정확한 로깅을 수행합니다.
cat << EOF > "$SCRIPT_DIR/test_wrapper.py"
import subprocess
import sys
import logging
from tqdm import tqdm

# Logging 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("$LOG_FILE"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_tests():
    cmd = [
        "python", "-m", "pytest", "$TEST_DIR",
        "-v", "--tb=short", "-n", "${PARALLEL_WORKERS:-auto}",
        "--timeout=120", "--cov=surfscreen",
        "--cov-report=term-missing",
        "--cov-report=html:$PROJECT_ROOT/test_outputs/coverage_unit",
        "--junitxml=$PROJECT_ROOT/test_outputs/junit_unit.xml"
    ]
    
    logger.info("Starting Unit Tests...")
    
    # tqdm 진행률 표시 (테스트 수집 후 진행)
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # 실제 pytest 출력과 별개로 진행 바를 노출 (가상 진행률 또는 라인 카운트)
        with tqdm(total=100, desc="Testing Progress", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [%]') as pbar:
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if line:
                    logger.info(line)
                    # 특정 키워드 발견 시 진행률 업데이트 로직 (간이 구현)
                    if "passed" in line or "failed" in line:
                        pbar.update(1)
            
            process.wait()
            pbar.n = 100
            pbar.refresh()

        if process.returncode == 0:
            logger.info("All tests completed successfully.")
        else:
            logger.error(f"Tests failed with return code {process.returncode}")
            sys.exit(process.returncode)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
EOF

# 3. 메인 실행부
echo "=================================================="
echo "UNIT TESTS WITH LOGGING"
echo "=================================================="
echo "Log File: $LOG_FILE"
echo ""

cd "$PROJECT_ROOT"

# Python 래퍼 실행 (모든 로깅 및 tqdm 처리)
python "$SCRIPT_DIR/test_wrapper.py" 2>&1 | tee -a "$LOG_FILE"

# 임시 래퍼 파일 삭제
rm "$SCRIPT_DIR/test_wrapper.py"

echo ""
echo "Unit tests completed. Results saved to $LOG_FILE"

#!/bin/bash
###############################################################################
