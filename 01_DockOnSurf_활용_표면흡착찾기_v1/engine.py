#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ads_pose_enum_enterprise.py

Enterprise-grade adsorption pose enumerator with two engines:
  - native: internal sampling (hemisphere directions + spin + anchors)
  - dockonsurf: call DockOnSurf in dry-run mode (batch_q_sys=False) and collect conf_* structures

Key points (DockOnSurf engine):
  - robust executable resolution (dockonsurf.py on PATH OR absolute path)
  - correct "sites" / "molec_ctrs" formatting (comma-separated tokens)
  - robust output collection via recursive conf_* discovery (no hard-coded screening/ path)
  - reproducible downsampling (seeded) instead of DockOnSurf random max_structures

Outputs:
  - manifest.jsonl
  - all_candidates.extxyz  (multi-frame + cell)
  - optional all_candidates.traj (multi-frame + cell)
  - optional individual files (default CIF)

Dependencies:
  - ase, numpy
  - scikit-learn (optional, only if --cluster)
"""

import os
import sys
import json
import math
import glob
import shutil
import argparse
import logging
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Union

import numpy as np
from ase import Atoms
from ase.io import read, write
from ase.build import bulk, surface
from ase.io.trajectory import Trajectory

# optional
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import OPTICS
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False


# --------------------------
# logging
# --------------------------
def setup_logger(name: str, outdir: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # file handler
    os.makedirs(outdir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(outdir, "run.log"), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ==========================
# Dataclasses
# ==========================
@dataclass(frozen=True)
class Site:
    kind: str                       # atop/bridge/hollow
    xy: Tuple[float, float]         # for native placement
    surf_atoms: Tuple[int, ...]     # indices defining the site (0-based)
    meta: Dict


# ==========================
# Small utils
# ==========================
def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def is_listlike(x) -> bool:
    return isinstance(x, (list, tuple))

def uniq_xy_with_payload(points_xy: List[Tuple[float, float]],
                         payload: List[Tuple[int, ...]],
                         tol: float) -> Tuple[List[Tuple[float, float]], List[Tuple[int, ...]]]:
    """Grid-hash uniqueness filter in XY, keeping first payload for each bin."""
    if not points_xy:
        return [], []
    grid = max(float(tol), 1e-6)
    seen = set()
    out_xy = []
    out_pl = []
    for xy, pl in zip(points_xy, payload):
        k = (int(round(xy[0] / grid)), int(round(xy[1] / grid)))
        if k in seen:
            continue
        seen.add(k)
        out_xy.append(xy)
        out_pl.append(pl)
    return out_xy, out_pl

def top_layer_indices(slab: Atoms, z_tol: float) -> np.ndarray:
    z = slab.positions[:, 2]
    zmax = float(np.max(z))
    return np.where(z >= zmax - z_tol)[0]

def get_z_surface(slab: Atoms, top_idx: np.ndarray) -> float:
    return float(np.mean(slab.positions[top_idx, 2]))

def min_mol_slab_distance(combined: Atoms, n_slab: int) -> float:
    dmat = combined.get_all_distances(mic=True)
    return float(np.min(dmat[n_slab:, :n_slab]))

def min_mol_toplayer_distance(combined: Atoms, n_slab: int, top_idx: np.ndarray) -> float:
    dmat = combined.get_all_distances(mic=True)
    return float(np.min(dmat[n_slab:, top_idx]))

def rotation_matrix_from_axis_angle(axis: np.ndarray, angle_rad: float) -> np.ndarray:
    axis = np.asarray(axis, float)
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    x, y, z = axis
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    C = 1 - c
    return np.array([
        [c + x*x*C,     x*y*C - z*s, x*z*C + y*s],
        [y*x*C + z*s,   c + y*y*C,   y*z*C - x*s],
        [z*x*C - y*s,   z*y*C + x*s, c + z*z*C]
    ], float)

def rotation_align_vectors(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    a = np.asarray(v_from, float)
    b = np.asarray(v_to, float)
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))

    if dot > 1.0 - 1e-10:
        return np.eye(3)
    if dot < -1.0 + 1e-10:
        ortho = np.array([1.0, 0.0, 0.0])
        if abs(a[0]) > 0.9:
            ortho = np.array([0.0, 1.0, 0.0])
        axis = np.cross(a, ortho)
        axis = axis / (np.linalg.norm(axis) + 1e-12)
        return rotation_matrix_from_axis_angle(axis, math.pi)

    axis = np.cross(a, b)
    angle = math.acos(dot)
    return rotation_matrix_from_axis_angle(axis, angle)

def apply_rotation_about_point(pos: np.ndarray, R: np.ndarray, origin: np.ndarray) -> np.ndarray:
    return (pos - origin) @ R.T + origin


# ==========================
# Slab builders
# ==========================
def build_metal_slab(element: str, crystal: str, hkl: Tuple[int, int, int],
                     layers: int, vacuum: float, nx: int, ny: int,
                     a: Optional[float], c: Optional[float]) -> Atoms:
    """
    ASE bulk() can fail for some element/crystal without lattice constants.
    We catch and raise actionable error.
    """
    kw = {}
    if a is not None:
        kw["a"] = float(a)

    crystal_l = crystal.lower()
    if crystal_l == "hcp":
        if c is not None:
            kw["c"] = float(c)
        elif a is not None:
            kw["c"] = 1.633 * float(a)

    try:
        b = bulk(element, crystalstructure=crystal, **kw)
    except Exception as e:
        raise RuntimeError(
            f"ASE bulk() 실패: element={element}, crystal={crystal}, a={a}, c={c}. "
            f"해결: --a (그리고 hcp면 --c) 값을 명시하거나, crystal 구조를 바꾸세요.\n"
            f"원인: {repr(e)}"
        )

    slab = surface(b, hkl, layers=layers, vacuum=vacuum)
    slab = slab.repeat((nx, ny, 1))

    # z PBC False to avoid z-wrap issues in MIC distance checks
    slab.pbc = (True, True, False)
    return slab

def load_slab(args) -> Atoms:
    if args.slab_file:
        slab = read(args.slab_file)
        slab.pbc = (True, True, False) if args.slab_pbc_z_false else (True, True, True)
        return slab

    hkl = tuple(int(x.strip()) for x in args.hkl.split(","))
    if len(hkl) != 3:
        raise ValueError("--hkl은 '1,1,1' 형태여야 합니다.")

    return build_metal_slab(args.element, args.crystal, hkl, args.layers, args.vacuum,
                            args.nx, args.ny, args.a, args.c)


# ==========================
# Site generation (heuristic, keeps indices for DockOnSurf)
# ==========================
def generate_sites_heuristic(slab: Atoms, top_idx: np.ndarray, nn_cut: float,
                             kinds: Optional[List[str]] = None) -> List[Site]:
    """
    kinds: subset of ['atop','bridge','hollow'] (None -> all)
    """
    if kinds is None:
        kinds = ["atop", "bridge", "hollow"]
    kinds = [k.lower() for k in kinds]

    slab = slab.copy()
    slab.pbc = (True, True, False)
    top_idx = np.array(top_idx, int)

    sites: List[Site] = []

    # (1) atop
    if "atop" in kinds:
        for ai in top_idx.tolist():
            x, y = slab.positions[ai, 0], slab.positions[ai, 1]
            sites.append(Site("atop", (float(x), float(y)), (int(ai),), {"source": "top_atom"}))

    # (2) bridge
    if "bridge" in kinds:
        bridge_xy = []
        bridge_pair = []
        for i, ai in enumerate(top_idx):
            for aj in top_idx[i + 1:]:
                dij = slab.get_distance(int(ai), int(aj), mic=True)
                if 1e-6 < dij <= nn_cut:
                    vvec = slab.get_distance(int(ai), int(aj), mic=True, vector=True)
                    mid = slab.positions[int(ai)] + 0.5 * vvec
                    bridge_xy.append((float(mid[0]), float(mid[1])))
                    bridge_pair.append(tuple(sorted((int(ai), int(aj)))))

        bridge_xy, bridge_pair = uniq_xy_with_payload(bridge_xy, bridge_pair, tol=0.20)
        for xy, pair in zip(bridge_xy, bridge_pair):
            sites.append(Site("bridge", xy, pair, {"nn_cut": nn_cut}))

    # (3) hollow
    if "hollow" in kinds:
        hollow_xy = []
        hollow_tri = []
        top_list = top_idx.tolist()

        neigh = {ai: [] for ai in top_list}
        for i, ai in enumerate(top_list):
            for aj in top_list[i + 1:]:
                d = slab.get_distance(ai, aj, mic=True)
                if d <= nn_cut:
                    neigh[ai].append(aj)
                    neigh[aj].append(ai)

        tri_seen = set()
        for ai in top_list:
            nbs = neigh[ai]
            for j in range(len(nbs)):
                for k in range(j + 1, len(nbs)):
                    aj, ak = nbs[j], nbs[k]
                    if ak in neigh[aj]:
                        tri = tuple(sorted((ai, aj, ak)))
                        if tri in tri_seen:
                            continue
                        tri_seen.add(tri)

                        v_ij = slab.get_distance(ai, aj, mic=True, vector=True)
                        v_ik = slab.get_distance(ai, ak, mic=True, vector=True)
                        center = slab.positions[ai] + (v_ij + v_ik) / 3.0
                        hollow_xy.append((float(center[0]), float(center[1])))
                        hollow_tri.append(tri)

        hollow_xy, hollow_tri = uniq_xy_with_payload(hollow_xy, hollow_tri, tol=0.25)
        for xy, tri in zip(hollow_xy, hollow_tri):
            sites.append(Site("hollow", xy, tri, {"nn_cut": nn_cut}))

    return sites


# ==========================
# Molecule handling
# ==========================
def read_molecules(mol_path: str, mol_index: str) -> List[Atoms]:
    """
    mol_index:
      - "0" -> first frame
      - ":" -> all frames (multi-frame xyz/extxyz/traj ...)
    """
    idx: Union[int, str]
    if mol_index.strip() == ":":
        idx = ":"
    else:
        idx = int(mol_index)

    mols = read(mol_path, index=idx)
    if is_listlike(mols):
        out = [m.copy() for m in mols]
    else:
        out = [mols.copy()]
    for m in out:
        m.pbc = (False, False, False)
    return out


# ==========================
# Native pose sampling
# ==========================
def fibonacci_hemisphere(n: int, rng: np.random.Generator, jitter: float = 0.0) -> np.ndarray:
    if n <= 0:
        return np.zeros((0, 3), float)
    golden = (1 + 5 ** 0.5) / 2
    pts = []
    for i in range(n):
        u = (i + 0.5) / n
        if jitter > 0:
            u = np.clip(u + rng.uniform(-jitter, jitter) / n, 0.0, 1.0)
        cos_t = u
        sin_t = math.sqrt(max(0.0, 1 - cos_t * cos_t))
        phi = 2 * math.pi * (i / golden)
        if jitter > 0:
            phi += rng.uniform(-jitter, jitter) * (2 * math.pi / n)
        pts.append([sin_t * math.cos(phi), sin_t * math.sin(phi), cos_t])
    return np.array(pts, float)

def inertia_axes(mol: Atoms) -> np.ndarray:
    pos = mol.positions - mol.get_center_of_mass()
    masses = mol.get_masses()
    I = np.zeros((3, 3), float)
    for r, m in zip(pos, masses):
        x, y, z = r
        I += m * np.array([
            [y*y + z*z, -x*y,     -x*z],
            [-x*y,      x*x + z*z, -y*z],
            [-x*z,      -y*z,      x*x + y*y]
        ], float)
    _, evecs = np.linalg.eigh(I)
    return evecs  # columns are eigenvectors

def select_molecular_axis(evecs: np.ndarray, mode: str) -> np.ndarray:
    if mode == "min":
        v = evecs[:, 0]
    elif mode == "mid":
        v = evecs[:, 1]
    else:
        v = evecs[:, 2]
    return v / (np.linalg.norm(v) + 1e-12)

def anchor_candidates(mol: Atoms, mode: str, lowest_k: int) -> List[int]:
    if mode == "com":
        return [-1]
    Z = mol.get_atomic_numbers()
    pos = mol.positions
    ids = list(range(len(mol)))

    if mode == "all":
        return ids

    nonH = [i for i, z in enumerate(Z) if z != 1]
    if mode == "nonH":
        return nonH if nonH else ids

    if mode == "lowestK":
        pool = nonH if nonH else ids
        rel = pos - mol.get_center_of_mass()
        pool_sorted = sorted(pool, key=lambda i: rel[i, 2])
        return pool_sorted[:max(1, int(lowest_k))]

    return [-1]

def orient_molecule(mol: Atoms, axis_mode: str, target_dir: np.ndarray, spin_deg: float,
                    anchor_idx: int) -> Atoms:
    m = mol.copy()
    evecs = inertia_axes(m)
    v_axis = select_molecular_axis(evecs, axis_mode)
    tdir = np.asarray(target_dir, float)
    tdir = tdir / (np.linalg.norm(tdir) + 1e-12)

    origin = m.positions[anchor_idx].copy() if anchor_idx >= 0 else m.get_center_of_mass()

    R1 = rotation_align_vectors(v_axis, tdir)
    m.positions = apply_rotation_about_point(m.positions, R1, origin)

    R2 = rotation_matrix_from_axis_angle(tdir, math.radians(spin_deg))
    m.positions = apply_rotation_about_point(m.positions, R2, origin)
    return m

def place_on_site(slab: Atoms, mol_oriented: Atoms,
                  site_xy: Tuple[float, float],
                  z_surface: float,
                  height: float,
                  anchor_idx: int,
                  z_clear: float) -> Atoms:
    m = mol_oriented.copy()
    anchor = m.positions[anchor_idx].copy() if anchor_idx >= 0 else m.get_center_of_mass()
    target = np.array([site_xy[0], site_xy[1], z_surface + height], float)
    m.translate(target - anchor)

    mol_zmin = float(np.min(m.positions[:, 2]))
    min_allowed = z_surface + z_clear
    if mol_zmin < min_allowed:
        m.translate([0.0, 0.0, (min_allowed - mol_zmin)])

    combined = slab.copy()
    combined += m
    combined.cell = slab.cell
    combined.pbc = slab.pbc
    return combined


# ==========================
# Features for clustering
# ==========================
def pose_features(combined: Atoms, n_slab: int, top_idx: np.ndarray, z_surface: float,
                  site_xy: Tuple[float, float], axis_mode: str,
                  n_hist: int = 12, h_cut: float = 6.0, contact_cut: float = 3.0) -> np.ndarray:
    mol = combined[n_slab:]

    evecs = inertia_axes(mol)
    v_axis = select_molecular_axis(evecs, axis_mode)
    nz = np.array([0.0, 0.0, 1.0])
    cosang = abs(float(np.dot(v_axis, nz)))
    cosang = np.clip(cosang, 0.0, 1.0)
    tilt_deg = math.degrees(math.acos(cosang))

    hz = mol.positions[:, 2] - z_surface
    hmin, hmean, hmax = float(np.min(hz)), float(np.mean(hz)), float(np.max(hz))

    dx = mol.positions[:, 0] - site_xy[0]
    dy = mol.positions[:, 1] - site_xy[1]
    r = np.sqrt(dx*dx + dy*dy)
    rmean, rmax = float(np.mean(r)), float(np.max(r))

    hclip = np.clip(hz, 0.0, float(h_cut))
    hist_h, _ = np.histogram(hclip, bins=n_hist, range=(0.0, float(h_cut)), density=True)
    hist_h = hist_h.astype(float)

    dmat = combined.get_all_distances(mic=True)
    d_near = np.min(dmat[n_slab:, top_idx], axis=1)
    contact = int(np.sum(d_near < float(contact_cut)))

    dclip = np.clip(d_near, 0.0, float(h_cut))
    hist_d, _ = np.histogram(dclip, bins=n_hist, range=(0.0, float(h_cut)), density=True)
    hist_d = hist_d.astype(float)

    feat = np.concatenate([
        np.array([tilt_deg, hmin, hmean, hmax, rmean, rmax, float(contact)], float),
        hist_h, hist_d
    ])
    return feat


# ==========================
# DockOnSurf integration (enterprise)
# ==========================
def resolve_dos_cmd(dos_cmd: str) -> str:
    """
    Resolve DockOnSurf executable.
    - If absolute/relative path exists -> return it
    - Else try PATH via shutil.which
    """
    if os.path.exists(dos_cmd):
        return os.path.abspath(dos_cmd)
    hit = shutil.which(dos_cmd)
    if hit:
        return hit
    return dos_cmd  # keep as is; caller will error with diagnostic

def format_groups_dos(groups: List[Tuple[int, ...]]) -> str:
    """
    DockOnSurf expects comma-separated tokens.
      - singleton: "62"
      - group: "(59 62)" or "(59, 62)" (we use space inside)
    Example: "62, 59, (59 62), (45 54 59)"
    """
    parts = []
    for g in groups:
        if len(g) == 1:
            parts.append(str(int(g[0])))
        else:
            parts.append("(" + " ".join(str(int(x)) for x in g) + ")")
    return ", ".join(parts)

def write_dummy_vasp_inputs(workdir: str) -> Tuple[str, str, str]:
    """
    Some DockOnSurf versions insist screen_inp_file exists.
    Provide minimal placeholders: INCAR, KPOINTS, POTCAR.
    """
    incar = os.path.join(workdir, "INCAR")
    kpts = os.path.join(workdir, "KPOINTS")
    potcar = os.path.join(workdir, "POTCAR")
    with open(incar, "w", encoding="utf-8") as f:
        f.write("SYSTEM = DockOnSurf_DRYRUN\nENCUT=350\nISMEAR=0\nSIGMA=0.05\nIBRION=2\nNSW=0\n")
    with open(kpts, "w", encoding="utf-8") as f:
        f.write("KPOINTS\n0\nGamma\n1 1 1\n0 0 0\n")
    with open(potcar, "w", encoding="utf-8") as f:
        f.write("")  # dummy
    return incar, kpts, potcar

def collect_conf_dirs(workdir: str) -> Tuple[str, List[str]]:
    """
    Robustly discover conf_* directories produced by DockOnSurf.
    Returns: (best_parent_dir, conf_dirs_in_that_parent)
    """
    conf_dirs = sorted(glob.glob(os.path.join(workdir, "**", "conf_*"), recursive=True))
    if not conf_dirs:
        return "", []

    parent_count: Dict[str, int] = {}
    for cd in conf_dirs:
        parent = os.path.dirname(cd)
        parent_count[parent] = parent_count.get(parent, 0) + 1

    best_parent = max(parent_count.items(), key=lambda kv: kv[1])[0]
    in_parent = sorted(glob.glob(os.path.join(best_parent, "conf_*")))
    return best_parent, in_parent

def read_first_geometry_in_conf(conf_dir: str) -> Tuple[Optional[Atoms], Optional[str]]:
    """
    Try typical filenames then fallback to any readable file.
    """
    candidates = [
        os.path.join(conf_dir, "POSCAR"),
        os.path.join(conf_dir, "CONTCAR"),
        os.path.join(conf_dir, "POSCAR.vasp"),
        os.path.join(conf_dir, "CONTCAR.vasp"),
    ]
    # fallback common extensions
    candidates += sorted(glob.glob(os.path.join(conf_dir, "*.vasp")))
    candidates += sorted(glob.glob(os.path.join(conf_dir, "*.cif")))
    candidates += sorted(glob.glob(os.path.join(conf_dir, "*.xyz")))
    candidates += sorted(glob.glob(os.path.join(conf_dir, "*.extxyz")))
    candidates += sorted(glob.glob(os.path.join(conf_dir, "*.*")))

    for fp in candidates:
        if not os.path.isfile(fp):
            continue
        try:
            atoms = read(fp)
            return atoms, fp
        except Exception:
            continue
    return None, None

def run_dockonsurf_screening_dryrun(
    args,
    logger: logging.Logger,
    slab: Atoms,
    sites: List[Site],
    anchors: List[int],
    mol_file: str,
    project_suffix: str = ""
) -> Tuple[str, List[Tuple[Atoms, Dict]]]:
    """
    Execute DockOnSurf screening in dry-run mode and collect structures.
    Returns:
      - workdir used
      - list of (Atoms, extra_meta)
    """
    dos_cmd_resolved = resolve_dos_cmd(args.dos_cmd)
    if (not shutil.which(dos_cmd_resolved)) and (not os.path.exists(dos_cmd_resolved)):
        raise RuntimeError(
            f"DockOnSurf 실행 파일을 못 찾음: --dos_cmd {args.dos_cmd}\n"
            f"해결: `which dockonsurf.py` 결과를 --dos_cmd로 넣거나, 절대경로를 넣어라."
        )

    # per-conformer workdir to avoid collisions
    workdir = os.path.join(args.outdir, "_dockonsurf_work" + project_suffix)
    ensure_dir(workdir)

    # Write surface POSCAR
    surf_file = os.path.join(workdir, "SURF_POSCAR")
    slab_for_vasp = slab.copy()
    slab_for_vasp.pbc = (True, True, True)
    write(surf_file, slab_for_vasp, format="vasp")

    # VASP inputs placeholders (or user-provided)
    if args.dos_screen_inp_files:
        # user gave list
        files = args.dos_screen_inp_files
        # ensure in workdir
        basenames = []
        for fp in files:
            if not os.path.isfile(fp):
                raise RuntimeError(f"--dos_screen_inp_files 파일 없음: {fp}")
            dst = os.path.join(workdir, os.path.basename(fp))
            if os.path.abspath(fp) != os.path.abspath(dst):
                shutil.copy2(fp, dst)
            basenames.append(os.path.basename(dst))
        screen_inp_str = " ".join(basenames)
    else:
        incar, kpts, potcar = write_dummy_vasp_inputs(workdir)
        screen_inp_str = f"{os.path.basename(incar)} {os.path.basename(kpts)} {os.path.basename(potcar)}"

    inp_path = os.path.join(workdir, "dockonsurf_screening.inp")

    # DockOnSurf sites/molec_ctrs formatting
    dos_sites = [s.surf_atoms for s in sites]
    dos_molec_ctrs = [(int(aidx),) for aidx in anchors if aidx >= 0] or [(0,)]

    # IMPORTANT: for reproducibility, we default max_structures to False and downsample ourselves later
    max_structures = "False" if args.dos_max_structures <= 0 else str(int(args.dos_max_structures))
    if args.dos_reproducible:
        max_structures = "False"

    project_name = args.dos_project_name + project_suffix

    with open(inp_path, "w", encoding="utf-8") as f:
        f.write("[Global]\n")
        f.write(f"project_name = {project_name}\n")
        f.write("batch_q_sys = False\n")       # dry-run
        f.write("code = VASP\n")
        f.write("run_type = Screening\n\n")

        f.write("[Screening]\n")
        f.write(f"surf_file = {os.path.basename(surf_file)}\n")
        f.write("surf_normal_vect = z\n")
        f.write(f"use_molec_file = {os.path.abspath(mol_file)}\n")
        f.write(f"adsorption_height = {float(args.height)}\n")
        f.write(f"min_coll_height = {float(args.dos_min_coll_height)}\n")
        f.write(f"set_angles = {args.dos_set_angles}\n")
        f.write(f"sample_points_per_angle = {int(args.dos_sample_points_per_angle)}\n")
        f.write(f"select_magns = {args.dos_select_magns}\n")
        f.write(f"confs_per_magn = {int(args.dos_confs_per_magn)}\n")
        f.write(f"max_structures = {max_structures}\n")
        f.write(f"screen_inp_file = {screen_inp_str}\n")
        f.write(f"sites = {format_groups_dos(dos_sites)}\n")
        f.write(f"molec_ctrs = {format_groups_dos(dos_molec_ctrs)}\n")

    # run command: if dos_cmd is .py, run via python for safety
    cmd = [dos_cmd_resolved, "-i", inp_path]
    if str(dos_cmd_resolved).endswith(".py"):
        cmd = [sys.executable, dos_cmd_resolved, "-i", inp_path]

    logger.info(f"[DockOnSurf] CMD: {' '.join(cmd)} (cwd={workdir})")
    subprocess.run(cmd, cwd=workdir, check=True)

    # locate conf dirs robustly
    best_parent, conf_dirs = collect_conf_dirs(workdir)
    if not conf_dirs:
        logp = os.path.join(workdir, "dockonsurf.log")
        raise RuntimeError(
            "DockOnSurf가 conf_*를 생성하지 못했음.\n"
            f"1) DockOnSurf 로그 확인: {logp}\n"
            f"2) sites/molec_ctrs 문법 오류 가능성이 큼 (콤마 구분 필수)\n"
            f"3) workdir 내 conf_* 탐색: find {workdir} -type d -name 'conf_*'\n"
        )

    logger.info(f"[DockOnSurf] conf dirs = {len(conf_dirs)} @ {best_parent}")

    out: List[Tuple[Atoms, Dict]] = []
    for cd in conf_dirs:
        atoms, src = read_first_geometry_in_conf(cd)
        if atoms is None:
            continue
        atoms.pbc = (True, True, True)

        meta = {
            "engine": "dockonsurf",
            "dockonsurf_project": project_name,
            "dockonsurf_conf_dir": os.path.relpath(cd, args.outdir),
            "dockonsurf_geom_file": os.path.relpath(src, args.outdir) if src else None,
            "dockonsurf_best_parent": os.path.relpath(best_parent, args.outdir),
            "dockonsurf_workdir": os.path.relpath(workdir, args.outdir),
        }
        out.append((atoms, meta))

    return workdir, out


# ==========================
# Selection / downsampling
# ==========================
def downsample_records(rng: np.random.Generator, items: List[Tuple[Atoms, Dict]],
                       max_n: int, mode: str = "seeded_random") -> List[Tuple[Atoms, Dict]]:
    if max_n <= 0 or len(items) <= max_n:
        return items
    if mode == "first":
        return items[:max_n]
    # seeded_random: deterministic given seed
    idx = np.arange(len(items))
    rng.shuffle(idx)
    idx = idx[:max_n]
    return [items[i] for i in idx]


# ==========================
# Main
# ==========================
def main():
    ap = argparse.ArgumentParser()

    # general
    ap.add_argument("--engine", choices=["native", "dockonsurf"], default="native",
                    help="후보 생성 엔진: native / dockonsurf")
    ap.add_argument("--log_level", default="INFO", help="DEBUG/INFO/WARN/ERROR")

    # slab: build or load
    ap.add_argument("--slab_file", default=None, help="미리 만든 slab 파일(cif/vasp/extxyz/...)")
    ap.add_argument("--slab_pbc_z_false", action="store_true",
                    help="slab_file 로딩 시 z PBC를 False로 강제")
    ap.add_argument("--element", default="Zn", help="원소(예: Zn, Cu, Ni, Fe...)")
    ap.add_argument("--crystal", default="hcp", help="fcc/bcc/hcp/sc/diamond 등 (ASE 지원)")
    ap.add_argument("--hkl", default="0,0,1", help="Miller index: 1,1,1 형태")
    ap.add_argument("--a", type=float, default=None, help="격자상수 a (ASE bulk 실패 시 필수)")
    ap.add_argument("--c", type=float, default=None, help="hcp 격자상수 c")
    ap.add_argument("--nx", type=int, default=4)
    ap.add_argument("--ny", type=int, default=4)
    ap.add_argument("--layers", type=int, default=6)
    ap.add_argument("--vacuum", type=float, default=15.0)
    ap.add_argument("--z_tol", type=float, default=0.6)
    ap.add_argument("--nn_cut", type=float, default=3.2)
    ap.add_argument("--site_kinds", default="atop,bridge,hollow",
                    help="site 종류 subset. 예: atop,bridge 또는 atop 만")

    # molecule
    ap.add_argument("--mol", required=True, help="흡착 분자 파일(xyz/extxyz/traj/...)")
    ap.add_argument("--mol_index", default="0", help="':'면 모든 프레임을 conformer로 처리 (native는 완전 지원, dockonsurf도 반복 실행 지원)")

    # placement + filters (native + optional post-filter for dockonsurf)
    ap.add_argument("--height", type=float, default=2.5, help="anchor 기준 초기 높이(Å)")
    ap.add_argument("--z_clear", type=float, default=0.8, help="분자 원자 z 최소 clearance(Å) (native only)")
    ap.add_argument("--min_dist", type=float, default=1.9, help="전체 슬랩-분자 최소거리 컷(Å) (native + post-filter)")
    ap.add_argument("--min_top_dist", type=float, default=1.8, help="top-layer 최소거리 컷(Å) (native + post-filter)")
    ap.add_argument("--apply_post_filter_dos", action="store_true",
                    help="DockOnSurf 결과에도 min_dist/min_top_dist post-filter 적용")

    # pose sampling (native)
    ap.add_argument("--axis_mode", choices=["min", "mid", "max"], default="max")
    ap.add_argument("--n_dir", type=int, default=24, help="반구 방향 샘플 개수")
    ap.add_argument("--n_spin", type=int, default=6, help="각 방향당 spin 샘플 개수")
    ap.add_argument("--spin_jitter", type=float, default=0.0)
    ap.add_argument("--anchor_mode", choices=["com", "nonH", "lowestK", "all"], default="lowestK")
    ap.add_argument("--lowest_k", type=int, default=3)

    # output
    ap.add_argument("--outdir", default="out_candidates")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_configs", type=int, default=500, help="최종 저장 구조 수 (다운샘플은 wrapper에서 seed 기반)")
    ap.add_argument("--select_mode", choices=["seeded_random", "first"], default="seeded_random")
    ap.add_argument("--no_individual", action="store_true", help="개별 파일 저장 끄기")
    ap.add_argument("--individual_format", default="cif",
                    choices=["cif", "vasp", "extxyz", "xyz", "traj"],
                    help="개별 저장 포맷(기본 cif)")
    ap.add_argument("--bundle_extxyz", default="all_candidates.extxyz",
                    help="셀정보 포함 멀티프레임 extxyz (항상 생성)")
    ap.add_argument("--bundle_traj", default=None,
                    help="추가로 ASE Trajectory(.traj) 번들도 저장 (옵션)")
    ap.add_argument("--write_slab_cif", action="store_true", help="slab만 따로 slab.cif 저장")

    # clustering
    ap.add_argument("--cluster", action="store_true", help="생성 후 포즈 군집화 실행(OPTICS)")
    ap.add_argument("--optics_min_samples", type=int, default=10)
    ap.add_argument("--optics_xi", type=float, default=0.05)
    ap.add_argument("--rep_per_cluster", type=int, default=3)

    # DockOnSurf options
    ap.add_argument("--dos_cmd", default="dockonsurf.py", help="DockOnSurf 실행 커맨드/경로 (예: dockonsurf.py 또는 /abs/path/dockonsurf.py)")
    ap.add_argument("--dos_project_name", default="dos_project", help="DockOnSurf project_name")
    ap.add_argument("--dos_set_angles", default="Euler", choices=["Euler", "Internal"], help="DockOnSurf set_angles")
    ap.add_argument("--dos_sample_points_per_angle", type=int, default=3, help="DockOnSurf sample_points_per_angle")
    ap.add_argument("--dos_select_magns", default="energy", choices=["energy", "MOI"], help="DockOnSurf select_magns")
    ap.add_argument("--dos_confs_per_magn", type=int, default=1, help="DockOnSurf confs_per_magn")
    ap.add_argument("--dos_max_structures", type=int, default=-1,
                    help="DockOnSurf max_structures (<=0이면 False). 재현성 원하면 wrapper가 다운샘플링하도록 -1 추천.")
    ap.add_argument("--dos_min_coll_height", type=float, default=1.5, help="DockOnSurf min_coll_height")
    ap.add_argument("--dos_keep_workdir", action="store_true", help="DockOnSurf workdir 유지")
    ap.add_argument("--dos_reuse_existing", action="store_true",
                    help="DockOnSurf workdir에 conf_*가 이미 있으면 실행 스킵하고 회수만")
    ap.add_argument("--dos_reproducible", action="store_true",
                    help="재현성 모드: DockOnSurf max_structures를 강제로 False로 두고 wrapper에서만 다운샘플")

    ap.add_argument("--dos_screen_inp_files", nargs="*", default=None,
                    help="DockOnSurf screen_inp_file에 넣을 실제 입력 파일들 (예: INCAR KPOINTS POTCAR). 없으면 dummy 생성.")

    args = ap.parse_args()
    ensure_dir(args.outdir)
    logger = setup_logger("ads_pose_enum_enterprise", args.outdir, args.log_level)

    rng = np.random.default_rng(args.seed)

    # save run config
    with open(os.path.join(args.outdir, "run_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)

    # slab
    slab = load_slab(args)
    if args.write_slab_cif:
        write(os.path.join(args.outdir, "slab.cif"), slab, format="cif")

    top_idx = top_layer_indices(slab, z_tol=args.z_tol)
    zsurf = get_z_surface(slab, top_idx)
    logger.info(f"Top layer atoms={len(top_idx)} | z_surface≈{zsurf:.3f} Å")

    # sites
    kinds = [x.strip() for x in args.site_kinds.split(",") if x.strip()]
    sites = generate_sites_heuristic(slab, top_idx, nn_cut=args.nn_cut, kinds=kinds)
    logger.info(f"Generated sites: {len(sites)} | kinds={kinds}")

    # output paths
    bundle_extxyz_path = args.bundle_extxyz
    if not os.path.isabs(bundle_extxyz_path):
        bundle_extxyz_path = os.path.join(args.outdir, bundle_extxyz_path)
    if os.path.exists(bundle_extxyz_path):
        os.remove(bundle_extxyz_path)

    traj_writer: Optional[Trajectory] = None
    bundle_traj_path = None
    if args.bundle_traj:
        bundle_traj_path = args.bundle_traj
        if not os.path.isabs(bundle_traj_path):
            bundle_traj_path = os.path.join(args.outdir, bundle_traj_path)
        if os.path.exists(bundle_traj_path):
            os.remove(bundle_traj_path)
        traj_writer = Trajectory(bundle_traj_path, mode="w")

    manifest_path = os.path.join(args.outdir, "manifest.jsonl")
    n_slab = len(slab)

    feat_list = []
    rec_list = []

    written = 0

    def write_one(atoms: Atoms, rec: Dict):
        nonlocal written
        individual_file = None

        if not args.no_individual:
            ext = args.individual_format
            individual_file = f"cand_{written:06d}.{ext}"
            write(os.path.join(args.outdir, individual_file), atoms, format=ext)

        write(bundle_extxyz_path, atoms, format="extxyz", append=True)
        if traj_writer is not None:
            traj_writer.write(atoms)

        rec2 = dict(rec)
        rec2["id"] = written
        rec2["frame_index"] = written
        rec2["individual_file"] = individual_file
        rec2["bundle_extxyz"] = os.path.basename(bundle_extxyz_path)
        rec2["bundle_traj"] = os.path.basename(bundle_traj_path) if bundle_traj_path else None

        with open(manifest_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec2, ensure_ascii=False) + "\n")

        if args.cluster:
            # for dockonsurf: site_xy unknown -> use mol COM xy as proxy
            mol_part = atoms[n_slab:]
            com = mol_part.get_center_of_mass()
            pseudo_xy = (float(com[0]), float(com[1]))
            feat = pose_features(atoms, n_slab, top_idx, zsurf, pseudo_xy, args.axis_mode)
            feat_list.append(feat)
            rec_list.append(rec2)

        written += 1

    try:
        # reset manifest
        if os.path.exists(manifest_path):
            os.remove(manifest_path)

        # ========= DockOnSurf engine =========
        if args.engine == "dockonsurf":
            mols = read_molecules(args.mol, args.mol_index)

            all_items: List[Tuple[Atoms, Dict]] = []

            for mi, mol in enumerate(mols):
                # per-conformer molecule file (DockOnSurf reads a file)
                mol_file = os.path.join(args.outdir, f"_dos_mol_frame_{mi:03d}.xyz")
                write(mol_file, mol, format="xyz")

                anchors = anchor_candidates(mol, args.anchor_mode, args.lowest_k)
                anchors = [a for a in anchors if a >= 0]  # DockOnSurf needs atom indices
                if not anchors:
                    anchors = [0]

                suffix = f"_mf{mi:03d}" if len(mols) > 1 else ""

                workdir = os.path.join(args.outdir, "_dockonsurf_work" + suffix)
                if args.dos_reuse_existing:
                    best_parent, conf_dirs = collect_conf_dirs(workdir)
                    if conf_dirs:
                        logger.info(f"[DockOnSurf] reuse_existing=True: found existing conf_* ({len(conf_dirs)}) @ {workdir}")
                        items = []
                        for cd in conf_dirs:
                            atoms, src = read_first_geometry_in_conf(cd)
                            if atoms is None:
                                continue
                            atoms.pbc = (True, True, True)
                            meta = {
                                "engine": "dockonsurf",
                                "dockonsurf_project": args.dos_project_name + suffix,
                                "dockonsurf_conf_dir": os.path.relpath(cd, args.outdir),
                                "dockonsurf_geom_file": os.path.relpath(src, args.outdir) if src else None,
                                "dockonsurf_best_parent": os.path.relpath(best_parent, args.outdir) if best_parent else None,
                                "dockonsurf_workdir": os.path.relpath(workdir, args.outdir),
                                "mol_frame": mi,
                            }
                            items.append((atoms, meta))
                    else:
                        _, items = run_dockonsurf_screening_dryrun(args, logger, slab, sites, anchors, mol_file, suffix)
                        # attach mol_frame
                        items = [(a, {**m, "mol_frame": mi}) for a, m in items]
                else:
                    _, items = run_dockonsurf_screening_dryrun(args, logger, slab, sites, anchors, mol_file, suffix)
                    items = [(a, {**m, "mol_frame": mi}) for a, m in items]

                logger.info(f"[DockOnSurf] collected structures: {len(items)} (mol_frame={mi})")
                all_items.extend(items)

            # optional post-filter
            if args.apply_post_filter_dos:
                logger.info("[DockOnSurf] applying post distance filters...")
                filtered = []
                for atoms, meta in all_items:
                    try:
                        mind = min_mol_slab_distance(atoms, n_slab=n_slab)
                        mind_top = min_mol_toplayer_distance(atoms, n_slab=n_slab, top_idx=top_idx)
                    except Exception:
                        continue
                    if mind < args.min_dist:
                        continue
                    if mind_top < args.min_top_dist:
                        continue
                    meta2 = dict(meta)
                    meta2["min_dist"] = float(mind)
                    meta2["min_top_dist"] = float(mind_top)
                    filtered.append((atoms, meta2))
                all_items = filtered
                logger.info(f"[DockOnSurf] after post-filter: {len(all_items)}")

            # reproducible downsample
            all_items = downsample_records(rng, all_items, args.max_configs, args.select_mode)

            # write
            for atoms, meta in all_items:
                if written >= args.max_configs:
                    break
                write_one(atoms, meta)

            if not args.dos_keep_workdir:
                # keep workdir by default because it contains logs; user can clean later
                pass

        # ========= Native engine =========
        else:
            mols = read_molecules(args.mol, args.mol_index)

            dirs = fibonacci_hemisphere(args.n_dir, rng=rng, jitter=0.0)
            spins = np.linspace(0.0, 360.0, num=args.n_spin, endpoint=False)
            if args.spin_jitter > 0:
                spins = np.array([s + rng.uniform(-args.spin_jitter, args.spin_jitter) for s in spins], float)

            for mol_frame, mol in enumerate(mols):
                anchors = anchor_candidates(mol, args.anchor_mode, args.lowest_k)
                logger.info(f"[Native] mol_frame={mol_frame} | anchors={len(anchors)} | n_dir={len(dirs)} | n_spin={len(spins)}")

                for site in sites:
                    for anchor_idx in anchors:
                        for di, dvec in enumerate(dirs):
                            for sp in spins:
                                if written >= args.max_configs:
                                    break

                                mol_oriented = orient_molecule(mol, args.axis_mode, dvec, float(sp), anchor_idx)
                                combined = place_on_site(slab, mol_oriented, site.xy, zsurf, args.height, anchor_idx, args.z_clear)

                                mind = min_mol_slab_distance(combined, n_slab=n_slab)
                                if mind < args.min_dist:
                                    continue
                                mind_top = min_mol_toplayer_distance(combined, n_slab=n_slab, top_idx=top_idx)
                                if mind_top < args.min_top_dist:
                                    continue

                                rec = {
                                    "engine": "native",
                                    "site_kind": site.kind,
                                    "site_xy": [site.xy[0], site.xy[1]],
                                    "site_surf_atoms": list(site.surf_atoms),
                                    "anchor_idx": int(anchor_idx),
                                    "mol_frame": int(mol_frame),
                                    "dir_vec": [float(dvec[0]), float(dvec[1]), float(dvec[2])],
                                    "spin_deg": float(sp),
                                    "height": float(args.height),
                                    "z_surface": float(zsurf),
                                    "min_dist": float(mind),
                                    "min_top_dist": float(mind_top),
                                    "site_meta": site.meta,
                                }
                                write_one(combined, rec)

                            if written >= args.max_configs:
                                break
                        if written >= args.max_configs:
                            break
                    if written >= args.max_configs:
                        break
                if written >= args.max_configs:
                    break

    finally:
        if traj_writer is not None:
            traj_writer.close()

    logger.info(f"Done. wrote={written}")
    logger.info(f"Manifest: {manifest_path}")
    logger.info(f"Bundle EXTXYZ (multi-frame, with cell): {bundle_extxyz_path}")
    if bundle_traj_path:
        logger.info(f"Bundle TRAJ (multi-frame, with cell): {bundle_traj_path}")

    # ========= Clustering =========
    if args.cluster:
        if not SKLEARN_OK:
            logger.error("scikit-learn이 없어서 --cluster 실행 불가. (pip install scikit-learn)")
            return

        if len(feat_list) < max(args.optics_min_samples, 5):
            logger.warning("Not enough samples for clustering (or all filtered). Skipping clustering.")
            return

        X = np.vstack(feat_list)
        Xs = StandardScaler().fit_transform(X)

        optics = OPTICS(min_samples=int(args.optics_min_samples), xi=float(args.optics_xi), metric="minkowski")
        labels = optics.fit_predict(Xs)

        cluster_path = os.path.join(args.outdir, "clusters.json")
        clusters: Dict[str, List[int]] = {}
        for i, lab in enumerate(labels):
            clusters.setdefault(str(int(lab)), []).append(int(i))

        with open(cluster_path, "w", encoding="utf-8") as g:
            json.dump({
                "n_samples": int(len(labels)),
                "n_clusters_excluding_noise": int(len([k for k in clusters.keys() if k != "-1"])),
                "labels": [int(x) for x in labels.tolist()],
                "clusters": clusters
            }, g, ensure_ascii=False, indent=2)

        logger.info(f"Clustering done. clusters.json written: {cluster_path}")

        rep_dir = os.path.join(args.outdir, "cluster_representatives")
        ensure_dir(rep_dir)

        # representatives: closest to cluster mean
        for clab, idxs in clusters.items():
            if clab == "-1":
                continue
            idxs = np.array(idxs, int)
            Xc = Xs[idxs]
            mu = np.mean(Xc, axis=0, keepdims=True)
            d2 = np.sum((Xc - mu) ** 2, axis=1)
            order = idxs[np.argsort(d2)]
            take = order[:max(1, int(args.rep_per_cluster))]

            for rank, frame_i in enumerate(take):
                atoms = read(bundle_extxyz_path, index=int(frame_i))
                fname = os.path.join(rep_dir, f"cluster_{clab}_rep{rank:02d}_frame{int(frame_i):06d}.cif")
                write(fname, atoms, format="cif")

        logger.info(f"Representatives saved to: {rep_dir}")


if __name__ == "__main__":
    main()

