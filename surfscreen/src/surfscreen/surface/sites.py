"""
SiteDetector: 흡착 사이트 자동 감지

표면의 top, bridge, hollow 사이트를 자동으로 감지
"""

from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy.spatial import Delaunay, Voronoi

if TYPE_CHECKING:
    from surfscreen.surface.builder import Surface


class SiteType(Enum):
    """흡착 사이트 유형"""
    TOP = "top"
    BRIDGE = "bridge"
    HOLLOW = "hollow"
    FCC = "fcc"
    HCP = "hcp"


@dataclass
class AdsorptionSite:
    """흡착 사이트"""
    position: np.ndarray  # (x, y, z)
    site_type: SiteType
    atoms: List[int]  # 관련 원자 인덱스
    height: float = 0.0  # 표면으로부터 높이
    symmetry_label: str = ""  # 대칭 라벨
    
    @property
    def xy(self) -> Tuple[float, float]:
        return (self.position[0], self.position[1])
    
    def __repr__(self):
        return f"AdsorptionSite({self.site_type.value}, atoms={self.atoms})"


class SiteDetector:
    """흡착 사이트 감지기
    
    표면 원자 기반으로 가능한 흡착 사이트 분석:
    - top: 단일 원자 위
    - bridge: 두 원자 사이
    - hollow (fcc/hcp): 삼각형 중심
    
    Examples:
        detector = SiteDetector(surface)
        sites = detector.detect_all()
        
        top_sites = detector.detect_top()
        hollow_sites = detector.detect_hollow()
    """
    
    def __init__(self, 
                 surface: "Surface",
                 height: float = 2.0,
                 symmetry_reduce: bool = True):
        """
        Args:
            surface: Surface 객체
            height: 기본 흡착 높이 (Å)
            symmetry_reduce: 대칭 등가 사이트 제거
        """
        self.surface = surface
        self.height = height
        self.symmetry_reduce = symmetry_reduce
        
        # 표면 원자 분석
        self.surface_atoms = surface.get_surface_atoms()
        self.positions = surface.atoms.get_positions()
        self.cell = surface.atoms.get_cell()
        
        # 셀이 유효한지 확인
        cell_array = self.cell.array if hasattr(self.cell, 'array') else np.array(self.cell)
        try:
            self.cell_inv = np.linalg.inv(cell_array[:3, :3])
            self.has_pbc = True
        except np.linalg.LinAlgError:
            # 셀이 singular하면 PBC 비활성화
            self.has_pbc = False
            self.cell_inv = None
        
        # 표면 원자 좌표
        self.surf_positions = self.positions[self.surface_atoms]
        self.z_surface = self.surf_positions[:, 2].max()
    
    def detect_all(self,
                   types: Optional[List[str]] = None) -> List[AdsorptionSite]:
        """모든 흡착 사이트 감지
        
        Args:
            types: 감지할 사이트 유형 (기본: 전체)
            
        Returns:
            AdsorptionSite 목록
        """
        if types is None:
            types = ["top", "bridge", "hollow"]
            
        sites = []
        
        if "top" in types:
            sites.extend(self.detect_top())
        if "bridge" in types:
            sites.extend(self.detect_bridge())
        if "hollow" in types or "fcc" in types or "hcp" in types:
            sites.extend(self.detect_hollow())
            
        if self.symmetry_reduce:
            sites = self._reduce_by_symmetry(sites)
            
        return sites
    
    def detect_top(self) -> List[AdsorptionSite]:
        """Top 사이트 감지 (원자 바로 위)"""
        sites = []
        
        for i, idx in enumerate(self.surface_atoms):
            pos = self.positions[idx].copy()
            pos[2] = self.z_surface + self.height
            
            sites.append(AdsorptionSite(
                position=pos,
                site_type=SiteType.TOP,
                atoms=[idx],
                height=self.height
            ))
            
        return sites
    
    def detect_bridge(self, max_distance: float = 3.5) -> List[AdsorptionSite]:
        """Bridge 사이트 감지 (두 원자 사이)
        
        Args:
            max_distance: 최대 원자간 거리 (Å)
        """
        sites = []
        n = len(self.surface_atoms)
        
        for i in range(n):
            for j in range(i + 1, n):
                idx_i = self.surface_atoms[i]
                idx_j = self.surface_atoms[j]
                
                pos_i = self.positions[idx_i]
                pos_j = self.positions[idx_j]
                
                # 주기적 경계 조건 고려
                diff = self._pbc_diff(pos_i, pos_j)
                dist = np.linalg.norm(diff)
                
                if dist < max_distance:
                    # 중점
                    midpoint = pos_i + diff / 2
                    midpoint[2] = self.z_surface + self.height
                    
                    sites.append(AdsorptionSite(
                        position=midpoint,
                        site_type=SiteType.BRIDGE,
                        atoms=[idx_i, idx_j],
                        height=self.height
                    ))
                    
        return sites
    
    def detect_hollow(self) -> List[AdsorptionSite]:
        """Hollow 사이트 감지 (삼각형 중심)
        
        FCC (111) 표면의 경우 fcc/hcp 구분
        """
        sites = []
        
        # 2D Delaunay 삼각분할
        xy_coords = self.surf_positions[:, :2]
        
        try:
            tri = Delaunay(xy_coords)
        except Exception:
            return sites
        
        for simplex in tri.simplices:
            # 삼각형의 세 꼭짓점
            idx_list = [self.surface_atoms[i] for i in simplex]
            
            # 삼각형 크기 체크 (너무 큰 삼각형 제외)
            p1, p2, p3 = xy_coords[simplex]
            area = 0.5 * abs((p2[0] - p1[0]) * (p3[1] - p1[1]) - 
                            (p3[0] - p1[0]) * (p2[1] - p1[1]))
            
            if area > 20:  # 너무 큰 삼각형 제외
                continue
            
            # 중심점
            centroid = np.mean(self.positions[idx_list], axis=0)
            centroid[2] = self.z_surface + self.height
            
            # FCC vs HCP 구분 (아래에 원자가 있으면 HCP)
            site_type = self._classify_hollow(centroid, idx_list)
            
            sites.append(AdsorptionSite(
                position=centroid,
                site_type=site_type,
                atoms=idx_list,
                height=self.height
            ))
            
        return sites
    
    def _classify_hollow(self, 
                         position: np.ndarray, 
                         surface_atoms: List[int]) -> SiteType:
        """Hollow 사이트를 FCC/HCP로 분류"""
        xy = position[:2]
        
        # 표면 바로 아래 레이어의 원자 확인
        z_surf = self.z_surface
        layer_spacing = 2.5  # 대략적인 레이어 간격
        
        # 두 번째 레이어 원자
        second_layer = []
        for i, pos in enumerate(self.positions):
            if z_surf - layer_spacing * 1.5 < pos[2] < z_surf - layer_spacing * 0.5:
                second_layer.append(i)
        
        if not second_layer:
            return SiteType.HOLLOW
        
        # xy 위치에서 가장 가까운 두 번째 레이어 원자
        min_dist = float('inf')
        for idx in second_layer:
            diff = self._pbc_diff_2d(xy, self.positions[idx, :2])
            dist = np.linalg.norm(diff)
            min_dist = min(min_dist, dist)
        
        # 아래에 원자가 있으면 HCP, 없으면 FCC
        if min_dist < 1.0:
            return SiteType.HCP
        else:
            return SiteType.FCC
    
    def _pbc_diff(self, pos1: np.ndarray, pos2: np.ndarray) -> np.ndarray:
        """주기적 경계 조건을 고려한 거리 벡터"""
        diff = pos2 - pos1
        
        # PBC 비활성화된 경우 단순 거리 반환
        if not self.has_pbc:
            return diff
        
        # 분수 좌표로 변환
        frac = diff @ self.cell_inv
        
        # 최소 이미지
        frac = frac - np.round(frac)
        
        # 직교 좌표로 변환
        cell_array = self.cell.array if hasattr(self.cell, 'array') else np.array(self.cell)
        return frac @ cell_array[:3, :3]
    
    def _pbc_diff_2d(self, xy1: np.ndarray, xy2: np.ndarray) -> np.ndarray:
        """2D 주기적 경계 조건"""
        diff = xy2 - xy1
        
        # PBC 비활성화된 경우 단순 거리 반환
        if not self.has_pbc:
            return diff
        
        cell_array = self.cell.array if hasattr(self.cell, 'array') else np.array(self.cell)
        cell_2d = cell_array[:2, :2]
        
        try:
            cell_inv = np.linalg.inv(cell_2d)
            frac = diff @ cell_inv
            frac = frac - np.round(frac)
            return frac @ cell_2d
        except np.linalg.LinAlgError:
            return diff
    
    def _reduce_by_symmetry(self, 
                            sites: List[AdsorptionSite],
                            tolerance: float = 0.5) -> List[AdsorptionSite]:
        """대칭 등가 사이트 제거"""
        if not sites:
            return sites
        
        unique = []
        
        for site in sites:
            is_unique = True
            
            for existing in unique:
                if site.site_type != existing.site_type:
                    continue
                    
                diff = self._pbc_diff_2d(
                    site.position[:2], 
                    existing.position[:2]
                )
                
                if np.linalg.norm(diff) < tolerance:
                    is_unique = False
                    break
            
            if is_unique:
                unique.append(site)
        
        return unique
    
    def visualize(self, 
                  sites: Optional[List[AdsorptionSite]] = None,
                  show: bool = True):
        """사이트 시각화 (matplotlib)"""
        try:
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D
        except ImportError:
            print("matplotlib required for visualization")
            return
        
        if sites is None:
            sites = self.detect_all()
        
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # 표면 원자
        ax.scatter(
            self.surf_positions[:, 0],
            self.surf_positions[:, 1],
            self.surf_positions[:, 2],
            c='gray', s=200, alpha=0.6, label='Surface atoms'
        )
        
        # 색상 매핑
        colors = {
            SiteType.TOP: 'red',
            SiteType.BRIDGE: 'green',
            SiteType.HOLLOW: 'blue',
            SiteType.FCC: 'blue',
            SiteType.HCP: 'cyan',
        }
        
        # 사이트 표시
        for site_type in SiteType:
            type_sites = [s for s in sites if s.site_type == site_type]
            if type_sites:
                positions = np.array([s.position for s in type_sites])
                ax.scatter(
                    positions[:, 0],
                    positions[:, 1],
                    positions[:, 2],
                    c=colors.get(site_type, 'purple'),
                    s=100, marker='x',
                    label=f'{site_type.value} ({len(type_sites)})'
                )
        
        ax.set_xlabel('X (Å)')
        ax.set_ylabel('Y (Å)')
        ax.set_zlabel('Z (Å)')
        ax.legend()
        ax.set_title('Adsorption Sites')
        
        if show:
            plt.show()
        
        return fig, ax
