#!/bin/bash
# ============================================
# DockOnSurf 상세 분석 및 분자 파일 테스트
# ============================================

echo "=== Check calculation.py local handling ==="
grep -A 20 "batch_q_sys.*local" ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/src/dockonsurf/calculation.py

echo ""
echo "=== Check molecule file parsing in formats.py ==="
grep -A 10 "def.*read\|\.xyz\|\.gen" ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/src/dockonsurf/formats.py | head -50

echo ""
echo "=== Test reading molecule with RDKit ==="
python << 'EOF'
from rdkit import Chem
from rdkit.Chem import AllChem

# XYZ 파일 읽기 시도
mol_file = "work/dockonsurf_test2/molecule.xyz"
print(f"Reading: {mol_file}")

try:
    mol = Chem.MolFromXYZFile(mol_file)
    if mol:
        print(f"Success! Atoms: {mol.GetNumAtoms()}")
        print(f"Formula: {Chem.rdMolDescriptors.CalcMolFormula(mol)}")
    else:
        print("Failed to read molecule")
except Exception as e:
    print(f"Error: {e}")

# MOL 파일로 변환 테스트
print("\n=== Try from SMILES instead ===")
mol = Chem.MolFromSmiles("CO")  # Methanol
mol = Chem.AddHs(mol)
AllChem.EmbedMolecule(mol)
AllChem.MMFFOptimizeMolecule(mol)
print(f"Methanol from SMILES: {mol.GetNumAtoms()} atoms")
EOF

echo ""
echo "=== Check if .xyz is supported in DockOnSurf ==="
grep -r "\.xyz\|XYZ\|xyz_file" ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/src/dockonsurf/*.py | head -20
