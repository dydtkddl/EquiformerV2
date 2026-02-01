"""
SurfScreen CLI

Click 기반 명령행 인터페이스 - 하위 호환성 유지용 래퍼

실제 구현은 surfscreen.cli 패키지에 있습니다.
"""

# Re-export from modular CLI package
from surfscreen.cli import cli, main

__all__ = ["cli", "main"]

if __name__ == "__main__":
    cli()
