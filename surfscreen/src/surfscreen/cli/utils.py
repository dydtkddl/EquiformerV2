"""
SurfScreen CLI - Common Utilities

공통 유틸리티, console 객체, CPU 스레드 설정
"""

import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


# ============ CPU Thread Configuration ============

def _set_cpu_threads():
    """전역 CPU 스레드 제한 (80% 기본)"""
    if "SURFSCREEN_NCPUS" in os.environ:
        ncpus = os.environ["SURFSCREEN_NCPUS"]
    else:
        total = os.cpu_count() or 1
        ncpus = str(max(1, int(total * 0.8)))
    
    os.environ.setdefault("OMP_NUM_THREADS", ncpus)
    os.environ.setdefault("MKL_NUM_THREADS", ncpus)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", ncpus)
    os.environ.setdefault("NUMEXPR_NUM_THREADS", ncpus)


# 모듈 로드 시 CPU 설정 적용
_set_cpu_threads()


# ============ Shared Console Object ============

console = Console()


# ============ Verbose Setup ============

def _setup_verbose(ctx, param, value):
    """Verbose 레벨 설정 콜백"""
    from surfscreen.logging_utils import set_verbose
    set_verbose(value)
    return value


# ============ Common Decorators ============

def handle_errors(func):
    """공통 에러 핸들러 데코레이터"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] File not found: {e}")
            raise SystemExit(1)
        except ValueError as e:
            console.print(f"[red]Error:[/red] Invalid value: {e}")
            raise SystemExit(1)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
    
    return wrapper


# ============ Common Options ============

def common_engine_options(func):
    """공통 계산 엔진 옵션"""
    func = click.option(
        "--engine", "-e",
        type=click.Choice(["mace", "chgnet", "matgl", "xtb", "emt"], case_sensitive=False),
        default="mace",
        help="Calculation engine"
    )(func)
    func = click.option(
        "--device", "-d",
        type=click.Choice(["auto", "cpu", "cuda"], case_sensitive=False),
        default="auto",
        help="Computation device"
    )(func)
    return func


# ============ Helper Functions ============

def print_table(title: str, columns: list, rows: list):
    """표 형식으로 출력"""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) for v in row])
    console.print(table)


def confirm_action(message: str, default: bool = False) -> bool:
    """사용자 확인"""
    return click.confirm(message, default=default)


def format_energy(energy: float, unit: str = "eV") -> str:
    """에너지 포맷팅"""
    return f"{energy:.4f} {unit}"


def format_time(seconds: float) -> str:
    """시간 포맷팅"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


__all__ = [
    "console",
    "handle_errors",
    "common_engine_options",
    "print_table",
    "confirm_action",
    "format_energy",
    "format_time",
    "_setup_verbose",
    "_set_cpu_threads",
    "Progress",
    "SpinnerColumn",
    "TextColumn",
    "Table",
]
