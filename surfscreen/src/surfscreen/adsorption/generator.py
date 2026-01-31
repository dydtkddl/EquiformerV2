"""
Adsorption Configuration Generator

흡착 구성을 미리 생성하고 관리하는 모듈
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from ase import Atoms
from ase.io import write, read
from ase.build import add_adsorbate
import json

from ..surface.builder import Surface
from surfscreen.logging_utils import adsorption_logger as logger


@dataclass
class AdsorptionConfig:
    """흡착 구성 데이터 클래스"""
    name: str
    site_index: int
    site_type: str
    site_position: Tuple[float, float, float]
    rotation: float
    height: float
    center_atom: int
    atoms: Atoms
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "site_index": self.site_index,
            "site_type": self.site_type,
            "site_position": list(self.site_position),
            "rotation": self.rotation,
            "height": self.height,
            "center_atom": self.center_atom
        }


class AdsorptionGenerator:
    """흡착 구성 생성기"""
    
    def __init__(self, surface: Surface, molecule: Atoms):
        """
        Args:
            surface: Surface 객체
            molecule: 분자 Atoms 객체
        """
        self.surface = surface
        self.molecule = molecule
        self.configs: List[AdsorptionConfig] = []
        logger.debug(f"AdsorptionGenerator initialized: surface={len(surface.atoms)} atoms, molecule={len(molecule)} atoms")
        
    def detect_adsorption_sites(self, 
                                 site_types: List[str] = ["top", "bridge", "hollow"],
                                 symmetry_reduce: bool = True) -> List[Dict]:
        """표면의 흡착 사이트 감지
        
        Args:
            site_types: 감지할 사이트 유형 리스트
            symmetry_reduce: 대칭성으로 중복 제거
            
        Returns:
            사이트 정보 리스트
        """
        from pymatgen.io.ase import AseAtomsAdaptor
        from pymatgen.analysis.adsorption import AdsorbateSiteFinder
        
        logger.step(f"Detecting adsorption sites: types={site_types}, symmetry_reduce={symmetry_reduce}")
        
        try:
            adaptor = AseAtomsAdaptor()
            structure = adaptor.get_structure(self.surface.atoms)
            
            asf = AdsorbateSiteFinder(structure)
            sites = []
            
            for site_type in site_types:
                if site_type == "top":
                    site_positions = asf.find_adsorption_sites()["ontop"]
                elif site_type == "bridge":
                    site_positions = asf.find_adsorption_sites()["bridge"]
                elif site_type == "hollow":
                    site_positions = asf.find_adsorption_sites()["hollow"]
                else:
                    continue
                
                logger.detail(f"  {site_type}: {len(site_positions)} sites")
                    
                for i, pos in enumerate(site_positions):
                    sites.append({
                        "index": len(sites),
                        "type": site_type,
                        "position": (pos[0], pos[1], pos[2])
                    })
            
            logger.success(f"Found {len(sites)} adsorption sites")
            return sites
            
        except Exception as e:
            logger.warning(f"PyMatGen failed, using fallback: {e}")
            # Fallback: 표면 원자 위 top 사이트만
            return self._detect_top_sites_simple()
    
    def _detect_top_sites_simple(self) -> List[Dict]:
        """간단한 top 사이트 감지 (fallback)"""
        surface_atoms = self.surface.atoms
        positions = surface_atoms.get_positions()
        
        # 표면 원자 (z 좌표가 가장 높은 원자들)
        z_coords = positions[:, 2]
        z_max = z_coords.max()
        surface_mask = z_coords > z_max - 1.0  # 최상위 1Å 이내
        
        sites = []
        for i, (is_surface, pos) in enumerate(zip(surface_mask, positions)):
            if is_surface:
                sites.append({
                    "index": len(sites),
                    "type": "top",
                    "position": (pos[0], pos[1], pos[2])
                })
                
        return sites
    
    def detect_molecule_centers(self) -> List[int]:
        """분자의 흡착 중심 원자 자동 감지
        
        Returns:
            중심 원자 인덱스 리스트
        """
        mol = self.molecule
        symbols = mol.get_chemical_symbols()
        
        # 우선순위: O, N, S > C (sp2) > 기타
        centers = []
        
        # 헤테로 원자 우선
        for i, sym in enumerate(symbols):
            if sym in ['O', 'N', 'S', 'P']:
                centers.append(i)
                
        # 헤테로 원자가 없으면 탄소 사용
        if not centers:
            for i, sym in enumerate(symbols):
                if sym == 'C':
                    centers.append(i)
                    break
                    
        # 그래도 없으면 첫 번째 원자
        if not centers:
            centers = [0]
            
        return centers
    
    def generate_configurations(self,
                                sites: Optional[List[Dict]] = None,
                                rotations: List[float] = [0, 45, 90, 135],
                                heights: List[float] = [2.0],
                                center_atoms: Optional[List[int]] = None,
                                max_configs: int = 100) -> List[AdsorptionConfig]:
        """흡착 구성 생성
        
        Args:
            sites: 사이트 리스트 (None이면 자동 감지)
            rotations: 회전 각도 리스트 (도)
            heights: 흡착 높이 리스트 (Å)
            center_atoms: 중심 원자 인덱스 (None이면 자동 감지)
            max_configs: 최대 구성 수
            
        Returns:
            AdsorptionConfig 리스트
        """
        if sites is None:
            sites = self.detect_adsorption_sites()
            
        if center_atoms is None:
            center_atoms = self.detect_molecule_centers()
            
        self.configs = []
        config_count = 0
        
        for site in sites:
            for rotation in rotations:
                for height in heights:
                    for center_atom in center_atoms:
                        if config_count >= max_configs:
                            break
                            
                        config = self._create_config(
                            site=site,
                            rotation=rotation,
                            height=height,
                            center_atom=center_atom
                        )
                        
                        if config is not None:
                            self.configs.append(config)
                            config_count += 1
                            
        return self.configs
    
    def _create_config(self, 
                       site: Dict,
                       rotation: float,
                       height: float,
                       center_atom: int) -> Optional[AdsorptionConfig]:
        """단일 흡착 구성 생성"""
        try:
            # 표면 복사
            system = self.surface.atoms.copy()
            
            # 분자 복사 및 회전
            mol = self.molecule.copy()
            
            # 중심 원자를 원점으로 이동
            center_pos = mol.positions[center_atom].copy()
            mol.positions -= center_pos
            
            # Z축 기준 회전
            angle_rad = np.radians(rotation)
            rot_matrix = np.array([
                [np.cos(angle_rad), -np.sin(angle_rad), 0],
                [np.sin(angle_rad), np.cos(angle_rad), 0],
                [0, 0, 1]
            ])
            mol.positions = mol.positions @ rot_matrix.T
            
            # 사이트 위치로 이동
            site_x, site_y, site_z = site["position"]
            mol.positions[:, 0] += site_x
            mol.positions[:, 1] += site_y
            mol.positions[:, 2] += site_z + height
            
            # 표면과 결합
            system = system + mol
            
            # Cell과 PBC 복사
            system.set_cell(self.surface.atoms.get_cell())
            system.set_pbc(self.surface.atoms.get_pbc())
            
            # 이름 생성
            name = f"site{site['index']}_rot{int(rotation)}"
            
            return AdsorptionConfig(
                name=name,
                site_index=site["index"],
                site_type=site["type"],
                site_position=site["position"],
                rotation=rotation,
                height=height,
                center_atom=center_atom,
                atoms=system
            )
            
        except Exception as e:
            print(f"Warning: Failed to create config: {e}")
            return None
    
    def filter_overlapping(self, min_distance: float = 1.5) -> List[AdsorptionConfig]:
        """원자 겹침이 있는 구성 필터링
        
        Args:
            min_distance: 최소 허용 거리 (Å)
            
        Returns:
            유효한 구성 리스트
        """
        valid_configs = []
        
        for config in self.configs:
            if self._check_no_overlap(config.atoms, min_distance):
                valid_configs.append(config)
                
        self.configs = valid_configs
        return valid_configs
    
    def _check_no_overlap(self, atoms: Atoms, min_distance: float) -> bool:
        """원자 겹침 확인"""
        from scipy.spatial.distance import pdist
        
        positions = atoms.get_positions()
        distances = pdist(positions)
        
        return distances.min() >= min_distance
    
    def save_configs(self, 
                     output_dir: str,
                     format: str = "extxyz") -> List[str]:
        """구성을 파일로 저장
        
        Args:
            output_dir: 출력 디렉토리
            format: 파일 포맷
            
        Returns:
            저장된 파일 경로 리스트
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        # 메타데이터
        metadata = {
            "surface": self.surface.name,
            "molecule": "molecule",
            "n_configs": len(self.configs),
            "configs": []
        }
        
        for config in self.configs:
            ext = "xyz" if format == "xyz" else "extxyz"
            file_path = output_path / f"{config.name}.{ext}"
            write(str(file_path), config.atoms, format=format)
            saved_files.append(str(file_path))
            
            metadata["configs"].append(config.to_dict())
            
        # 메타데이터 저장
        meta_path = output_path / "configs_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        return saved_files
    
    def visualize_html(self, output_path: str = "configs_preview.html") -> str:
        """구성들을 HTML로 시각화
        
        Args:
            output_path: 출력 HTML 파일 경로
            
        Returns:
            HTML 파일 경로
        """
        html_content = self._generate_preview_html()
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        return output_path
    
    def _generate_preview_html(self) -> str:
        """미리보기 HTML 생성"""
        # XYZ 데이터 준비
        xyz_data = {}
        for config in self.configs:
            xyz_lines = [str(len(config.atoms)), config.name]
            for atom in config.atoms:
                xyz_lines.append(
                    f"{atom.symbol} {atom.position[0]:.6f} "
                    f"{atom.position[1]:.6f} {atom.position[2]:.6f}"
                )
            xyz_data[config.name] = "\n".join(xyz_lines)
        
        # 구성 목록
        config_items = ""
        for config in self.configs:
            config_items += f"""
            <div class="config-item" onclick="showConfig('{config.name}')">
                <strong>{config.name}</strong><br>
                Site: {config.site_type} | Rot: {config.rotation}° | H: {config.height}Å
            </div>
            """
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Adsorption Configurations Preview</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
        }}
        .header {{
            background: rgba(0,0,0,0.3);
            padding: 20px;
            text-align: center;
        }}
        .container {{
            display: flex;
            height: calc(100vh - 80px);
        }}
        .sidebar {{
            width: 300px;
            background: rgba(0,0,0,0.2);
            overflow-y: auto;
            padding: 10px;
        }}
        .config-item {{
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin: 5px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .config-item:hover {{
            background: rgba(100,200,255,0.3);
            transform: translateX(5px);
        }}
        .config-item.active {{
            background: rgba(100,200,255,0.5);
            border-left: 3px solid #00ff88;
        }}
        .viewer-container {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}
        #viewer {{
            flex: 1;
            background: #1a1a2e;
        }}
        .info-bar {{
            background: rgba(0,0,0,0.3);
            padding: 10px;
            text-align: center;
        }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            color: #00ff88;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 Adsorption Configurations Preview</h1>
        <p>Surface: {self.surface.name} | Total Configs: {len(self.configs)}</p>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <h3 style="padding: 10px;">Configurations</h3>
            {config_items}
        </div>
        
        <div class="viewer-container">
            <div id="viewer"></div>
            <div class="info-bar">
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value" id="siteName">-</div>
                        <div>Site</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="rotation">-</div>
                        <div>Rotation</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="height">-</div>
                        <div>Height</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const xyzData = {json.dumps(xyz_data)};
        const configInfo = {json.dumps([c.to_dict() for c in self.configs])};
        
        let viewer = null;
        
        document.addEventListener('DOMContentLoaded', function() {{
            viewer = $3Dmol.createViewer('viewer', {{
                backgroundColor: '#1a1a2e'
            }});
            
            // Show first config
            if (Object.keys(xyzData).length > 0) {{
                showConfig(Object.keys(xyzData)[0]);
            }}
        }});
        
        function showConfig(name) {{
            if (!viewer) return;
            
            const xyz = xyzData[name];
            if (!xyz) return;
            
            // Update active state
            document.querySelectorAll('.config-item').forEach(item => {{
                item.classList.remove('active');
                if (item.textContent.includes(name)) {{
                    item.classList.add('active');
                }}
            }});
            
            // Update viewer
            viewer.removeAllModels();
            viewer.addModel(xyz, 'xyz');
            viewer.setStyle({{}}, {{
                stick: {{ radius: 0.12, colorscheme: 'Jmol' }},
                sphere: {{ scale: 0.25, colorscheme: 'Jmol' }}
            }});
            viewer.zoomTo();
            viewer.render();
            
            // Update info
            const info = configInfo.find(c => c.name === name);
            if (info) {{
                document.getElementById('siteName').textContent = info.site_type;
                document.getElementById('rotation').textContent = info.rotation + '°';
                document.getElementById('height').textContent = info.height + 'Å';
            }}
        }}
    </script>
</body>
</html>"""
        return html
