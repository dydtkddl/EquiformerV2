"""
PubChem Fetcher: PubChem 데이터베이스에서 분자 가져오기

기존 fetch_pubchem.py 통합 및 확장
"""

from __future__ import annotations

import os
import gzip
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List

import requests


class PubChemFetcher:
    """PubChem 데이터베이스 통합
    
    Features:
        - CID로 3D 구조 다운로드
        - 이름/분자식으로 CID 검색
        - SDF 파일에서 MOL 블록 추출
        
    Examples:
        fetcher = PubChemFetcher()
        
        # CID로 직접 다운로드
        path = fetcher.fetch_by_cid(2244, output_dir=".")
        
        # 이름으로 검색 후 다운로드
        cid = fetcher.search_by_name("aspirin")
        path = fetcher.fetch_by_cid(cid)
    """
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    FTP_3D_URL = "https://ftp.ncbi.nlm.nih.gov/pubchem/Compound_3D/01_conf_per_cmpd/SDF"
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Args:
            cache_dir: SDF 파일 캐시 디렉토리 (기본: 임시 디렉토리)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None
            
    def search_by_name(self, name: str) -> int:
        """화합물 이름으로 CID 검색
        
        Args:
            name: 화합물 이름 (예: "aspirin", "ethanol")
            
        Returns:
            PubChem CID
        """
        url = f"{self.BASE_URL}/compound/name/{name}/cids/JSON"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        
        if not cids:
            raise ValueError(f"No compound found with name: {name}")
            
        return cids[0]
    
    def search_by_formula(self, formula: str) -> int:
        """분자식으로 CID 검색
        
        Args:
            formula: 분자식 (예: "C9H8O4")
            
        Returns:
            PubChem CID (첫 번째 결과)
        """
        url = f"{self.BASE_URL}/compound/formula/{formula}/cids/JSON"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        
        if not cids:
            raise ValueError(f"No compound found with formula: {formula}")
            
        return cids[0]
    
    def search_by_smiles(self, smiles: str) -> int:
        """SMILES로 CID 검색
        
        Args:
            smiles: SMILES 문자열
            
        Returns:
            PubChem CID
        """
        url = f"{self.BASE_URL}/compound/smiles/{smiles}/cids/JSON"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        
        if not cids:
            raise ValueError(f"No compound found with SMILES: {smiles}")
            
        return cids[0]
    
    def get_compound_info(self, cid: int) -> dict:
        """화합물 정보 조회
        
        Args:
            cid: PubChem CID
            
        Returns:
            화합물 정보 딕셔너리
        """
        url = f"{self.BASE_URL}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
        
        return {
            "cid": cid,
            "formula": props.get("MolecularFormula", ""),
            "molecular_weight": props.get("MolecularWeight", 0),
            "iupac_name": props.get("IUPACName", ""),
        }
    
    def fetch_by_cid(self, 
                     cid: int, 
                     output_dir: str = ".",
                     keep_sdf: bool = False) -> str:
        """CID로 3D 구조 다운로드
        
        PubChem FTP에서 압축된 SDF 파일을 다운로드하고
        해당 CID의 MOL 블록을 추출
        
        Args:
            cid: PubChem CID
            output_dir: 출력 디렉토리
            keep_sdf: SDF 파일 유지 여부
            
        Returns:
            저장된 MOL 파일 경로
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # SDF 파일 범위 계산 (25,000개씩)
        range_start = (cid - 1) // 25000 * 25000 + 1
        range_end = range_start + 24999
        
        sdf_filename = f"{range_start:08d}_{range_end:08d}.sdf"
        gz_url = f"{self.FTP_3D_URL}/{sdf_filename}.gz"
        
        # 캐시 확인
        cache_path = None
        if self.cache_dir:
            cache_path = self.cache_dir / sdf_filename
            if cache_path.exists():
                return self._extract_mol(cache_path, cid, output_dir)
        
        # 임시 디렉토리에 다운로드
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            gz_path = tmpdir / f"{sdf_filename}.gz"
            sdf_path = tmpdir / sdf_filename
            
            # 다운로드
            print(f"📦 Downloading: {gz_url}")
            with requests.get(gz_url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(gz_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            
            # 압축 해제
            print("📂 Extracting...")
            with gzip.open(gz_path, 'rb') as f_in:
                with open(sdf_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 캐시에 저장
            if self.cache_dir and keep_sdf:
                shutil.copy(sdf_path, cache_path)
            
            # MOL 블록 추출
            return self._extract_mol(sdf_path, cid, output_dir)
    
    def _extract_mol(self, sdf_path: Path, cid: int, output_dir: Path) -> str:
        """SDF 파일에서 특정 CID의 MOL 블록 추출"""
        mol_path = output_dir / f"{cid}.mol"
        
        print(f"🔍 Searching for CID: {cid}")
        
        block_lines = []
        found = False
        
        with open(sdf_path, 'r') as f:
            buffer = []
            for line in f:
                if line.strip() == "$$$$":
                    # 블록 끝 - CID 확인
                    block_str = ''.join(buffer)
                    if f"> <PUBCHEM_COMPOUND_CID>\n{cid}\n" in block_str:
                        block_lines = buffer
                        found = True
                        break
                    buffer = []
                else:
                    buffer.append(line)
        
        if not found:
            raise ValueError(f"CID {cid} not found in the SDF file")
        
        # MOL 파일 저장
        with open(mol_path, 'w') as f:
            f.writelines(block_lines)
        
        print(f"✓ Saved: {mol_path}")
        return str(mol_path)
    
    def fetch_multiple(self, 
                       cids: List[int], 
                       output_dir: str = ".",
                       progress: bool = True) -> List[str]:
        """여러 CID 일괄 다운로드
        
        Args:
            cids: CID 목록
            output_dir: 출력 디렉토리
            progress: 진행률 표시
            
        Returns:
            저장된 파일 경로 목록
        """
        paths = []
        
        for i, cid in enumerate(cids):
            if progress:
                print(f"[{i+1}/{len(cids)}] Fetching CID {cid}...")
            try:
                path = self.fetch_by_cid(cid, output_dir)
                paths.append(path)
            except Exception as e:
                print(f"  ⚠️ Failed: {e}")
                
        return paths
