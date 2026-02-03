import subprocess
import sys
import logging
from tqdm import tqdm

# Logging 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("/home/yongsang/20260129_Equiformer/surfscreen/logs/test.20260203.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_tests():
    cmd = [
        "python", "-m", "pytest", "/home/yongsang/20260129_Equiformer/surfscreen/tests/unit",
        "-v", "--tb=short", "-n", "auto",
        "--timeout=120", "--cov=surfscreen",
        "--cov-report=term-missing",
        "--cov-report=html:/home/yongsang/20260129_Equiformer/surfscreen/test_outputs/coverage_unit",
        "--junitxml=/home/yongsang/20260129_Equiformer/surfscreen/test_outputs/junit_unit.xml"
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
