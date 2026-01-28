(equiformer*v2) [yongsang@ga00 01_DockOnSurf*활용*표면흡착찾기]$ which dockonsurf.py
~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/dockonsurf.py
(equiformer_v2) [yongsang@ga00 01_DockOnSurf*활용*표면흡착찾기]$ ^C
(equiformer_v2) [yongsang@ga00 01_DockOnSurf*활용*표면흡착찾기]$ ^C
(equiformer_v2) [yongsang@ga00 01_DockOnSurf*활용\_표면흡착찾기]$ tree -L 4 ~/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/
/home/yongsang/PSID_SIMULATION_TOOLS/DockOnSurf/dockonsurf/
├── dockonsurf.py
├── docs
│   ├── make.bat
│   ├── Makefile
│   ├── requirements.txt
│   └── source
│   ├── about.rst
│   ├── autodoc.rst
│   ├── BadSurface.png
│   ├── conf.py
│   ├── contact.rst
│   ├── dihedral_angle1.png
│   ├── dockonsurf-step2-en2.png
│   ├── faqs.rst
│   ├── index.rst
│   ├── inp_ref_manual.rst
│   ├── installation.rst
│   ├── internal_angles_centers.png
│   ├── isopropanol.png
│   ├── license.rst
│   ├── logo-transp.png
│   ├── logo-white.png
│   ├── refined_structure.png
│   ├── release_notes.rst
│   ├── tips_and_tricks.rst
│   └── tutorials.rst
├── examples
│   ├── dftb
│   │   ├── isolated
│   │   │   ├── dftb_in.hsd
│   │   │   └── dockonsurf_isolated_dftb.inp
│   │   ├── README.md
│   │   ├── refinement
│   │   │   ├── dftb_in.hsd
│   │   │   └── dockonsurf_euler_ref.inp
│   │   └── screening
│   │   ├── dftb_in.hsd
│   │   └── dockonsurf_screening_dftb.inp
│   ├── dockonsurf.inp
│   ├── dockonsurf.yml
│   ├── mace
│   │   ├── isolated
│   │   │   ├── dockonsurf_isolated_mace.inp
│   │   │   └── mace_input.yaml
│   │   ├── README.md
│   │   ├── refinement
│   │   │   ├── dockonsurf_refinement_mace.inp
│   │   │   └── mace_input.yaml
│   │   ├── run_opt.py
│   │   └── screening
│   │   ├── dockonsurf_screening_mace.inp
│   │   └── mace_input.yaml
│   └── mace.tar
├── **init**.py
├── LICENSE
├── MANIFEST.in
├── pyproject.toml
├── README.md
├── requirements.txt
├── setup.cfg
├── setup.py
├── src
│   ├── dockonsurf
│   │   ├── ASANN.py
│   │   ├── calculation.py
│   │   ├── clustering.py
│   │   ├── config_arg.py
│   │   ├── config_log.py
│   │   ├── dos_input.py
│   │   ├── formats.py
│   │   ├── **init**.py
│   │   ├── internal_rotate.py
│   │   ├── isolated.py
│   │   ├── **pycache**
│   │   │   ├── config_arg.cpython-38.pyc
│   │   │   ├── config_log.cpython-38.pyc
│   │   │   ├── dos_input.cpython-38.pyc
│   │   │   ├── formats.cpython-38.pyc
│   │   │   ├── **init**.cpython-38.pyc
│   │   │   ├── isolated.cpython-38.pyc
│   │   │   ├── refinement.cpython-38.pyc
│   │   │   ├── screening.cpython-38.pyc
│   │   │   └── utilities.cpython-38.pyc
│   │   ├── refinement.py
│   │   ├── screening.py
│   │   ├── utilities.py
│   │   └── xyz2mol.py
│   ├── **init**.py
│   └── **pycache**
│   └── **init**.cpython-38.pyc
├── tests
│   ├── acetic.mol
│   ├── acetic.xyz
│   ├── confs_cp2k
│   │   └── conf_0
│   │   ├── cp2k_isolated-1.restart
│   │   ├── isolated.inp
│   │   └── isolated.out
│   ├── confs_VASP
│   │   ├── conf_0
│   │   │   ├── good_vasp.inp
│   │   │   ├── INCAR
│   │   │   ├── KPOINTS
│   │   │   ├── OUTCAR
│   │   │   ├── POSCAR
│   │   │   └── POTCAR
│   │   ├── conf_1
│   │   │   └── OUTCAR
│   │   ├── conf_2
│   │   │   └── OUTCAR
│   │   └── conf_missing_potcar
│   │   ├── INCAR
│   │   └── KPOINTS
│   ├── cp2k.inp
│   ├── cp2k.sub
│   ├── expected_exemplars.npy
│   ├── expected_rmsd_matrix.npy
│   ├── good.inp
│   ├── good_vasp.inp
│   ├── hematite.xyz
│   ├── INCAR
│   ├── isolated.inp
│   ├── isopropanol.xyz
│   ├── KPOINTS
│   ├── POSCAR
│   ├── README
│   ├── refine.inp
│   ├── run_all_tests.py
│   ├── screen.inp
│   ├── setup_tests.py
│   ├── test_calculation.py
│   ├── test_dos_input.py
│   ├── test_formats.py
│   ├── test_isolated.py
│   ├── test_refinement.py
│   ├── test_screening.py
│   ├── vasp.sh
│   └── wrong.inp
└── tutorial
├── prep_isolated
│   ├── dockonsurf_isolated_vasp.inp
│   ├── INCAR
│   ├── KPOINTS
│   └── POSCAR
├── prep_refinement
│   ├── dockonsurf_euler_refinement.inp
│   ├── INCAR
│   └── KPOINTS
├── prep_screening
│   ├── dockonsurf_euler_screening.inp
│   ├── INCAR
│   ├── KPOINTS
│   └── POSCAR
└── tools
├── extract_CPU.sh
├── extract_energy.sh
└── extract_lowest_diff.py

28 directories, 129 files
(equiformer_v2) [yongsang@ga00
