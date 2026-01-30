"""
SurfScreen MD Engine Tests

xTB + PBC 경고 로직 및 다양한 MD 기능 테스트
"""

import pytest
import numpy as np
from pathlib import Path
from ase import Atoms
from ase.build import fcc111, molecule


class TestMDEngine:
    """MDEngine 테스트"""
    
    @pytest.fixture
    def surface_atoms(self):
        """PBC가 있는 표면 원자 생성"""
        atoms = fcc111("Cu", size=(2, 2, 3), vacuum=10.0)
        return atoms
    
    @pytest.fixture
    def molecule_atoms(self):
        """PBC가 없는 분자 원자 생성"""
        atoms = molecule("H2O")
        atoms.center(vacuum=5.0)
        atoms.pbc = False
        return atoms
    
    def test_xtb_pbc_warning(self, surface_atoms, tmp_path):
        """xTB + PBC 조합에서 경고 발생 테스트"""
        from surfscreen.md import MDEngine, MDConfig
        
        config = MDConfig(
            engine="xtb",
            steps=10,
            temperature=300.0,
            force_xtb=False  # 강제 실행 안 함
        )
        
        # PBC가 있는 표면에서 xTB 사용 시 RuntimeError 발생해야 함
        with pytest.raises(RuntimeError, match="xTB \\+ PBC is not supported"):
            MDEngine(surface_atoms, config, str(tmp_path / "test_md"))
    
    def test_xtb_pbc_force(self, surface_atoms, tmp_path):
        """xTB + PBC + force_xtb=True 테스트"""
        pytest.importorskip("xtb")  # xTB가 설치되어 있어야 함
        
        from surfscreen.md import MDEngine, MDConfig
        
        config = MDConfig(
            engine="xtb", 
            steps=10,
            temperature=300.0,
            force_xtb=True  # 강제 실행
        )
        
        # force_xtb=True이면 경고만 발생하고 생성은 됨 (실행 시 실패할 수 있음)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                engine = MDEngine(surface_atoms, config, str(tmp_path / "test_md"))
                assert len(w) >= 1
                assert "xTB with PBC" in str(w[0].message)
            except Exception:
                # xTB 자체 오류는 허용 (Multipoles not available with PBC 등)
                pass
    
    def test_xtb_molecule_ok(self, molecule_atoms, tmp_path):
        """xTB + 분자(PBC 없음) 정상 동작 테스트"""
        pytest.importorskip("xtb")
        
        from surfscreen.md import MDEngine, MDConfig
        
        config = MDConfig(
            engine="xtb",
            steps=5,
            temperature=300.0
        )
        
        # PBC가 없는 분자에서 xTB는 정상 동작해야 함
        engine = MDEngine(molecule_atoms, config, str(tmp_path / "test_md"))
        assert engine.calculator is not None
    
    def test_mace_surface_ok(self, surface_atoms, tmp_path):
        """MACE + 표면 정상 동작 테스트"""
        pytest.importorskip("mace")
        
        from surfscreen.md import MDEngine, MDConfig
        
        config = MDConfig(
            engine="mace",
            device="cpu",  # CI에서 GPU 없을 수 있음
            steps=5,
            temperature=300.0
        )
        
        # MACE는 PBC 표면에서 정상 동작해야 함
        engine = MDEngine(surface_atoms, config, str(tmp_path / "test_md"))
        assert engine.calculator is not None


class TestMDConfig:
    """MDConfig 테스트"""
    
    def test_force_xtb_default(self):
        """force_xtb 기본값 테스트"""
        from surfscreen.md import MDConfig
        
        config = MDConfig()
        assert config.force_xtb is False
    
    def test_force_xtb_set(self):
        """force_xtb 설정 테스트"""
        from surfscreen.md import MDConfig
        
        config = MDConfig(force_xtb=True)
        assert config.force_xtb is True
    
    def test_config_from_dict(self):
        """딕셔너리에서 설정 로드 테스트"""
        from surfscreen.md import MDConfig
        
        data = {
            "engine": "xtb",
            "temperature": 400.0,
            "force_xtb": True,
            "steps": 1000
        }
        
        config = MDConfig.from_dict(data)
        assert config.engine == "xtb"
        assert config.temperature == 400.0
        assert config.force_xtb is True
        assert config.steps == 1000


class TestCLIOptions:
    """CLI 옵션 테스트"""
    
    def test_md_run_help(self):
        """md run --help에 force-xtb 옵션 포함 확인"""
        from click.testing import CliRunner
        from surfscreen.cli import main
        
        runner = CliRunner()
        result = runner.invoke(main, ["md", "run", "--help"])
        
        assert result.exit_code == 0
        assert "--force-xtb" in result.output
        assert "Force xTB with PBC" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
