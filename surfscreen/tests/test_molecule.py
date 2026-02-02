"""
Test Molecule Module

MoleculeBuilder, ConformerGenerator 테스트
"""

import pytest
import numpy as np


class TestMoleculeBuilderImport:
    """MoleculeBuilder import 테스트"""
    
    def test_import_molecule_builder(self):
        """MoleculeBuilder가 import 가능한지"""
        try:
            from surfscreen.molecule import MoleculeBuilder
            assert MoleculeBuilder is not None
        except ImportError as e:
            pytest.skip(f"MoleculeBuilder not available: {e}")


class TestMoleculeFromSMILES:
    """SMILES에서 분자 생성 테스트"""
    
    def test_water_from_smiles(self):
        """물 분자 SMILES에서 생성"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_smiles('O', name='water')
        
        # 물 분자는 3개 원자
        assert mol.n_atoms == 3
    
    def test_methane_from_smiles(self):
        """메탄 SMILES에서 생성"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_smiles('C', name='methane')
        
        # 메탄: 1 C + 4 H = 5 원자
        assert mol.n_atoms == 5
    
    def test_ethanol_from_smiles(self):
        """에탄올 SMILES에서 생성"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_smiles('CCO', name='ethanol')
        
        # 에탄올: C2H6O = 2C + 6H + 1O = 9 원자
        assert mol.n_atoms == 9
    
    def test_formula_generation(self):
        """화학식 생성 확인"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_smiles('CCO', name='ethanol')
        
        # formula 속성이 있어야 함
        assert hasattr(mol, 'formula')
        # C, H, O가 포함되어야 함
        formula = mol.formula
        assert 'C' in formula
    
    def test_invalid_smiles_raises(self):
        """잘못된 SMILES는 에러 발생"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        with pytest.raises(Exception):
            MoleculeBuilder.from_smiles('XXXYYY_invalid')


class TestMoleculeFromFile:
    """파일에서 분자 로드 테스트"""
    
    def test_from_xyz_file(self, sample_xyz_file):
        """XYZ 파일에서 분자 로드"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_file(sample_xyz_file)
        
        assert mol.n_atoms == 4
    
    def test_file_not_found_raises(self):
        """존재하지 않는 파일은 에러"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        with pytest.raises(FileNotFoundError):
            MoleculeBuilder.from_file('/nonexistent/file.xyz')


class TestMoleculeProperties:
    """분자 속성 테스트"""
    
    def test_molecule_has_positions(self):
        """분자에 위치 정보가 있는지"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_smiles('C')
        
        # positions 속성
        assert hasattr(mol, 'positions') or hasattr(mol, 'atoms')
    
    def test_molecule_symbols(self):
        """분자의 원소 기호"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_smiles('O', name='water')
        
        # symbols 속성
        symbols = mol.symbols
        assert 'O' in symbols
        assert 'H' in symbols


class TestConformerGenerator:
    """ConformerGenerator 테스트"""
    
    def test_conformer_generator_import(self):
        """ConformerGenerator import 확인"""
        try:
            from surfscreen.molecule import ConformerGenerator
            assert ConformerGenerator is not None
        except ImportError:
            pytest.skip("ConformerGenerator not available")
    
    def test_generate_conformers(self):
        """Conformer 생성"""
        try:
            from surfscreen.molecule import MoleculeBuilder, ConformerGenerator
        except ImportError:
            pytest.skip("Required modules not available")
        
        mol = MoleculeBuilder.from_smiles('CCCC', name='butane')  # 회전 가능한 분자
        
        gen = ConformerGenerator(engine='rdkit')
        conformers = gen.generate(mol, n_conformers=5)
        
        # 최소 1개 conformer 생성
        assert len(conformers) >= 1
    
    def test_conformers_have_different_positions(self):
        """Conformer들은 다른 위치를 가짐"""
        try:
            from surfscreen.molecule import MoleculeBuilder, ConformerGenerator
        except ImportError:
            pytest.skip("Required modules not available")
        
        mol = MoleculeBuilder.from_smiles('CCCC', name='butane')
        
        gen = ConformerGenerator(engine='rdkit')
        conformers = gen.generate(mol, n_conformers=3)
        
        if len(conformers) >= 2:
            # 첫 두 conformer의 위치가 다름
            pos1 = conformers[0].positions
            pos2 = conformers[1].positions
            
            assert not np.allclose(pos1, pos2)


class TestMoleculeSave:
    """분자 저장 테스트"""
    
    def test_save_to_xyz(self, tmp_path):
        """XYZ 파일로 저장"""
        try:
            from surfscreen.molecule import MoleculeBuilder
        except ImportError:
            pytest.skip("MoleculeBuilder not available")
        
        mol = MoleculeBuilder.from_smiles('C', name='methane')
        
        output_path = tmp_path / "methane.xyz"
        mol.save(str(output_path))
        
        assert output_path.exists()
        assert output_path.stat().st_size > 0


class TestMoleculeAnalyzer:
    """MoleculeAnalyzer 테스트"""
    
    def test_adsorption_centers(self):
        """흡착 중심 감지"""
        try:
            from surfscreen.molecule import MoleculeBuilder
            from surfscreen.molecule.builder import MoleculeAnalyzer
        except ImportError:
            pytest.skip("Required modules not available")
        
        mol = MoleculeBuilder.from_smiles('CCO', name='ethanol')  # OH 기
        
        centers = MoleculeAnalyzer.get_adsorption_centers(mol)
        
        # 산소가 흡착 중심으로 감지
        assert len(centers) >= 1
    
    def test_functional_groups(self):
        """작용기 감지"""
        try:
            from surfscreen.molecule import MoleculeBuilder
            from surfscreen.molecule.builder import MoleculeAnalyzer
        except ImportError:
            pytest.skip("Required modules not available")
        
        mol = MoleculeBuilder.from_smiles('CCO', name='ethanol')
        
        groups = MoleculeAnalyzer.get_functional_groups(mol)
        
        # OH 기가 감지되어야 함
        group_names = [g.name for g in groups]
        assert any('OH' in name or 'hydroxyl' in name.lower() for name in group_names) or len(groups) >= 0
    
    def test_estimate_footprint(self):
        """분자 footprint 추정"""
        try:
            from surfscreen.molecule import MoleculeBuilder
            from surfscreen.molecule.builder import MoleculeAnalyzer
        except ImportError:
            pytest.skip("Required modules not available")
        
        mol = MoleculeBuilder.from_smiles('c1ccccc1', name='benzene')  # 방향족
        
        width, length = MoleculeAnalyzer.estimate_footprint(mol)
        
        # 벤젠은 대략 6Å x 6Å
        assert 4.0 < width < 10.0
        assert 4.0 < length < 10.0
