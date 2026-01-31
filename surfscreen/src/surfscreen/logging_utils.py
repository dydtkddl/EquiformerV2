"""
SurfScreen Logging Utilities

중앙화된 로깅 시스템으로 모든 모듈에서 일관된 verbose 출력 지원

Verbosity Levels:
    0 (SILENT): 오류만 출력
    1 (LOW): 주요 단계만 출력
    2 (MEDIUM): 중간 수준 진행상황
    3 (HIGH): 상세 진행상황 및 계산값
    4 (DEBUG): 모든 내부 동작 추적
"""

from __future__ import annotations

import logging
import sys
from enum import IntEnum
from typing import Optional, Any, Dict
from datetime import datetime
from pathlib import Path
from functools import wraps
import time


class VerboseLevel(IntEnum):
    """Verbose 레벨 정의"""
    SILENT = 0   # 오류만
    LOW = 1      # 주요 단계
    MEDIUM = 2   # 중간 수준
    HIGH = 3     # 상세 정보
    DEBUG = 4    # 디버그 정보


# 전역 verbose 레벨
_VERBOSE_LEVEL: VerboseLevel = VerboseLevel.MEDIUM


def set_verbose(level: int) -> None:
    """전역 verbose 레벨 설정
    
    Args:
        level: 0-4 사이의 정수 또는 VerboseLevel
    """
    global _VERBOSE_LEVEL
    if isinstance(level, str):
        level_map = {
            'silent': 0, 'low': 1, 'medium': 2, 'high': 3, 'debug': 4
        }
        level = level_map.get(level.lower(), 2)
    _VERBOSE_LEVEL = VerboseLevel(min(max(int(level), 0), 4))


def get_verbose() -> VerboseLevel:
    """현재 verbose 레벨 반환"""
    return _VERBOSE_LEVEL


class SurfScreenLogger:
    """SurfScreen 전용 로거
    
    Examples:
        logger = SurfScreenLogger("Calculator")
        logger.info("Optimizing structure...")
        logger.debug("Force residual: 0.0234 eV/Å")
        logger.detail("Iteration 45: E=-1234.5678 eV")
    """
    
    # ANSI 색상 코드
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'CYAN': '\033[96m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'ENDC': '\033[0m',
        'BOLD': '\033[1m',
        'DIM': '\033[2m',
    }
    
    # 아이콘 매핑
    ICONS = {
        'start': '🚀',
        'done': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'progress': '⏳',
        'calc': '🔬',
        'file': '📁',
        'config': '⚙️',
        'data': '📊',
        'time': '⏱️',
        'atom': '⚛️',
        'energy': '⚡',
    }
    
    def __init__(self, 
                 name: str,
                 color: bool = True,
                 file_log: Optional[str] = None):
        """
        Args:
            name: 로거 이름 (모듈/클래스명)
            color: 콘솔 컬러 사용 여부
            file_log: 파일 로그 경로 (None이면 파일 로그 없음)
        """
        self.name = name
        self.use_color = color and sys.stdout.isatty()
        self.file_log = file_log
        self._indent_level = 0
        self._file_handler = None
        
        if file_log:
            self._setup_file_log(file_log)
    
    def _setup_file_log(self, path: str):
        """파일 로그 설정"""
        log_path = Path(path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handler = open(log_path, 'a', encoding='utf-8')
        self._file_handler.write(f"\n{'='*60}\n")
        self._file_handler.write(f"Session started: {datetime.now().isoformat()}\n")
        self._file_handler.write(f"Module: {self.name}\n")
        self._file_handler.write(f"{'='*60}\n\n")
    
    def _colorize(self, text: str, color: str) -> str:
        """텍스트에 색상 적용"""
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['ENDC']}"
    
    def _format_message(self, 
                        level_name: str,
                        message: str, 
                        icon: Optional[str] = None,
                        color: str = 'ENDC') -> str:
        """메시지 포맷팅"""
        indent = "  " * self._indent_level
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        icon_str = self.ICONS.get(icon, '') + ' ' if icon else ''
        level_str = f"[{level_name:7s}]"
        name_str = f"[{self.name}]"
        
        formatted = f"{timestamp} {level_str} {name_str} {indent}{icon_str}{message}"
        
        return self._colorize(formatted, color)
    
    def _log(self, 
             level: VerboseLevel, 
             level_name: str,
             message: str, 
             icon: Optional[str] = None,
             color: str = 'ENDC',
             **kwargs):
        """내부 로깅 함수"""
        if _VERBOSE_LEVEL < level:
            return
            
        formatted = self._format_message(level_name, message, icon, color)
        
        # 추가 데이터 포맷팅 (HIGH 이상)
        if kwargs and _VERBOSE_LEVEL >= VerboseLevel.HIGH:
            data_lines = []
            for key, value in kwargs.items():
                if isinstance(value, float):
                    data_lines.append(f"    {key}: {value:.6f}")
                elif isinstance(value, (list, tuple)) and len(value) <= 10:
                    data_lines.append(f"    {key}: {value}")
                else:
                    data_lines.append(f"    {key}: {value}")
            if data_lines:
                formatted += "\n" + "\n".join(data_lines)
        
        print(formatted)
        
        if self._file_handler:
            # 파일에는 색상 코드 없이 저장
            plain = self._format_message(level_name, message, icon, 'ENDC')
            self._file_handler.write(plain + "\n")
            if kwargs:
                for key, value in kwargs.items():
                    self._file_handler.write(f"    {key}: {value}\n")
            self._file_handler.flush()
    
    # === Level 1: LOW === 
    def info(self, message: str, icon: Optional[str] = None, **kwargs):
        """일반 정보 (LOW 레벨 이상에서 표시)"""
        self._log(VerboseLevel.LOW, "INFO", message, icon or 'info', 'CYAN', **kwargs)
    
    def success(self, message: str, **kwargs):
        """성공 메시지 (LOW 레벨 이상에서 표시)"""
        self._log(VerboseLevel.LOW, "SUCCESS", message, 'done', 'GREEN', **kwargs)
    
    def warning(self, message: str, **kwargs):
        """경고 메시지 (항상 표시)"""
        self._log(VerboseLevel.SILENT, "WARNING", message, 'warning', 'YELLOW', **kwargs)
    
    def error(self, message: str, **kwargs):
        """오류 메시지 (항상 표시)"""
        self._log(VerboseLevel.SILENT, "ERROR", message, 'error', 'RED', **kwargs)
    
    # === Level 2: MEDIUM ===
    def progress(self, message: str, current: int = 0, total: int = 0, **kwargs):
        """진행 상황 (MEDIUM 레벨 이상에서 표시)"""
        if total > 0:
            pct = current / total * 100
            message = f"{message} [{current}/{total}] ({pct:.1f}%)"
        self._log(VerboseLevel.MEDIUM, "PROGRESS", message, 'progress', 'BLUE', **kwargs)
    
    def step(self, message: str, **kwargs):
        """단계 표시 (MEDIUM 레벨 이상)"""
        self._log(VerboseLevel.MEDIUM, "STEP", message, 'config', 'HEADER', **kwargs)
    
    # === Level 3: HIGH ===
    def detail(self, message: str, **kwargs):
        """상세 정보 (HIGH 레벨 이상에서 표시)"""
        self._log(VerboseLevel.HIGH, "DETAIL", message, None, 'DIM', **kwargs)
    
    def calc(self, message: str, **kwargs):
        """계산 정보 (HIGH 레벨 이상)"""
        self._log(VerboseLevel.HIGH, "CALC", message, 'calc', 'CYAN', **kwargs)
    
    def data(self, message: str, **kwargs):
        """데이터 정보 (HIGH 레벨 이상)"""
        self._log(VerboseLevel.HIGH, "DATA", message, 'data', 'BLUE', **kwargs)
    
    def energy(self, message: str, **kwargs):
        """에너지 관련 (HIGH 레벨 이상)"""
        self._log(VerboseLevel.HIGH, "ENERGY", message, 'energy', 'YELLOW', **kwargs)
    
    # === Level 4: DEBUG ===
    def debug(self, message: str, **kwargs):
        """디버그 정보 (DEBUG 레벨에서만 표시)"""
        self._log(VerboseLevel.DEBUG, "DEBUG", message, None, 'DIM', **kwargs)
    
    def trace(self, message: str, **kwargs):
        """추적 정보 (DEBUG 레벨에서만)"""
        self._log(VerboseLevel.DEBUG, "TRACE", message, None, 'DIM', **kwargs)
    
    # === Context Managers ===
    def section(self, title: str):
        """섹션 컨텍스트 매니저"""
        return _SectionContext(self, title)
    
    def indent(self):
        """들여쓰기 증가"""
        self._indent_level += 1
        return self
    
    def dedent(self):
        """들여쓰기 감소"""
        self._indent_level = max(0, self._indent_level - 1)
        return self
    
    # === Decorators ===
    def timer(self, message: str = "Operation"):
        """함수 실행 시간 측정 데코레이터"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                self.step(f"{message} started...")
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start
                    self.success(f"{message} completed in {elapsed:.2f}s")
                    return result
                except Exception as e:
                    elapsed = time.time() - start
                    self.error(f"{message} failed after {elapsed:.2f}s: {e}")
                    raise
            return wrapper
        return decorator
    
    def __del__(self):
        """파일 핸들러 정리"""
        if self._file_handler:
            self._file_handler.close()


class _SectionContext:
    """섹션 컨텍스트 매니저"""
    
    def __init__(self, logger: SurfScreenLogger, title: str):
        self.logger = logger
        self.title = title
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        if _VERBOSE_LEVEL >= VerboseLevel.LOW:
            print()
            print(f"{'─' * 60}")
            self.logger.info(f"▶ {self.title}", icon='start')
            print(f"{'─' * 60}")
        self.logger.indent()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.dedent()
        elapsed = time.time() - self.start_time
        if _VERBOSE_LEVEL >= VerboseLevel.LOW:
            if exc_type is None:
                self.logger.success(f"◀ {self.title} completed ({elapsed:.2f}s)")
            else:
                self.logger.error(f"◀ {self.title} failed ({elapsed:.2f}s): {exc_val}")
            print(f"{'─' * 60}")
            print()
        return False


# === 편의 함수 ===

def get_logger(name: str, **kwargs) -> SurfScreenLogger:
    """로거 인스턴스 생성 편의 함수"""
    return SurfScreenLogger(name, **kwargs)


def log_function_call(logger: SurfScreenLogger):
    """함수 호출 로깅 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__}()")
            logger.trace(f"  args: {args[:3]}...")  # 처음 3개만
            logger.trace(f"  kwargs: {list(kwargs.keys())}")
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__}() returned")
            return result
        return wrapper
    return decorator


# === 물리 상수 검증 로깅 ===

class PhysicsLogger(SurfScreenLogger):
    """물리 계산 전용 로거"""
    
    def __init__(self, name: str = "Physics"):
        super().__init__(name)
    
    def log_unit_conversion(self, 
                           value: float, 
                           from_unit: str, 
                           to_unit: str, 
                           result: float,
                           factor: float):
        """단위 변환 로깅"""
        self.debug(
            f"Unit conversion: {value} {from_unit} → {result} {to_unit}",
            factor=factor
        )
    
    def log_formula(self, name: str, formula: str, inputs: Dict[str, float], result: float):
        """물리 공식 계산 로깅"""
        self.calc(f"{name}: {formula}")
        self.indent()
        for key, val in inputs.items():
            self.detail(f"{key} = {val}")
        self.detail(f"Result = {result}")
        self.dedent()


# === 모듈 로거 인스턴스 ===

# 각 모듈에서 사용할 수 있는 기본 로거들
cli_logger = get_logger("CLI")
calc_logger = get_logger("Calculator")
md_logger = get_logger("MD")
analysis_logger = get_logger("Analysis")
adsorption_logger = get_logger("Adsorption")
molecule_logger = get_logger("Molecule")
surface_logger = get_logger("Surface")
physics_logger = PhysicsLogger()
