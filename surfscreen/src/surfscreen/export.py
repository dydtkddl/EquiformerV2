"""
SurfScreen Export Module

스크리닝 및 MD 결과를 다양한 포맷으로 내보내기
- CSV: 간단한 테이블 형식
- JSON: 전체 데이터 (구조 포함)
- Excel: 다중 시트
- ZIP: 전체 아카이브
"""

import json
import csv
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict

import numpy as np

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


@dataclass
class ExportConfig:
    """내보내기 설정"""
    include_structures: bool = False  # xyz 파일 포함
    include_trajectories: bool = False  # 궤적 파일 포함
    include_plots: bool = True  # HTML 플롯 포함
    include_logs: bool = True  # 로그 파일 포함
    compress: bool = True  # ZIP 압축 여부
    decimal_places: int = 6  # 소수점 자릿수


class ExportManager:
    """결과 내보내기 관리자"""
    
    def __init__(self, results_dir: str, config: Optional[ExportConfig] = None):
        """
        Args:
            results_dir: 스크리닝/MD 결과 디렉토리
            config: 내보내기 설정
        """
        self.results_dir = Path(results_dir)
        self.config = config or ExportConfig()
        
        # 데이터 로드
        self.data = self._load_results()
        
    def _load_results(self) -> Dict[str, Any]:
        """결과 데이터 로드"""
        data = {
            "metadata": {
                "source_dir": str(self.results_dir),
                "export_time": datetime.now().isoformat(),
            },
            "results": [],
            "summary": {}
        }
        
        # results.json 로드
        results_json = self.results_dir / "results.json"
        if results_json.exists():
            with open(results_json) as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    data["results"] = loaded
                elif isinstance(loaded, dict):
                    data["results"] = loaded.get("results", [])
                    data["summary"] = loaded.get("summary", {})
                    data["metadata"].update(loaded.get("metadata", {}))
        
        # summary.json 로드 (MD용)
        summary_json = self.results_dir / "summary.json"
        if summary_json.exists():
            with open(summary_json) as f:
                data["summary"] = json.load(f)
                
        return data
    
    def to_csv(self, output_path: str, include_header: bool = True) -> str:
        """CSV로 내보내기
        
        Args:
            output_path: 출력 파일 경로
            include_header: 헤더 포함 여부
            
        Returns:
            출력 파일 경로
        """
        output = Path(output_path)
        results = self.data.get("results", [])
        
        if not results:
            # 빈 파일 생성
            output.write_text("")
            return str(output)
        
        # 컬럼 추출 (첫 번째 결과에서)
        columns = list(results[0].keys())
        
        # 구조 데이터 제외
        exclude_cols = ["atoms", "structure", "cell", "positions", "forces"]
        columns = [c for c in columns if c not in exclude_cols]
        
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            if include_header:
                writer.writerow(columns)
            
            for result in results:
                row = []
                for col in columns:
                    val = result.get(col, "")
                    if isinstance(val, float):
                        val = round(val, self.config.decimal_places)
                    elif isinstance(val, (list, dict)):
                        val = json.dumps(val)
                    row.append(val)
                writer.writerow(row)
                
        return str(output)
    
    def to_json(self, output_path: str, indent: int = 2) -> str:
        """JSON으로 내보내기
        
        Args:
            output_path: 출력 파일 경로
            indent: 들여쓰기
            
        Returns:
            출력 파일 경로
        """
        output = Path(output_path)
        
        # numpy 배열 처리
        def convert(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, Path):
                return str(obj)
            return obj
        
        # 깊은 복사 및 변환
        export_data = json.loads(json.dumps(self.data, default=convert))
        
        with open(output, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=indent, ensure_ascii=False)
            
        return str(output)
    
    def to_excel(self, output_path: str) -> str:
        """Excel로 내보내기 (다중 시트)
        
        Args:
            output_path: 출력 파일 경로
            
        Returns:
            출력 파일 경로
        """
        if not HAS_PANDAS:
            raise ImportError("pandas가 필요합니다: pip install pandas")
        if not HAS_OPENPYXL:
            raise ImportError("openpyxl이 필요합니다: pip install openpyxl")
        
        output = Path(output_path)
        results = self.data.get("results", [])
        summary = self.data.get("summary", {})
        
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Sheet 1: 요약
            summary_df = pd.DataFrame([summary]) if summary else pd.DataFrame()
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            
            # Sheet 2: 결과
            if results:
                # 구조 데이터 제외
                exclude_cols = ["atoms", "structure", "cell", "positions", "forces"]
                clean_results = []
                for r in results:
                    clean = {k: v for k, v in r.items() if k not in exclude_cols}
                    # 복잡한 객체 문자열화
                    for k, v in clean.items():
                        if isinstance(v, (list, dict)):
                            clean[k] = json.dumps(v)
                    clean_results.append(clean)
                
                results_df = pd.DataFrame(clean_results)
                results_df.to_excel(writer, sheet_name="Results", index=False)
            
            # Sheet 3: 통계
            if results:
                energies = [r.get("e_ads", r.get("energy", 0)) for r in results if isinstance(r.get("e_ads", r.get("energy")), (int, float))]
                if energies:
                    stats = {
                        "count": len(energies),
                        "min": min(energies),
                        "max": max(energies),
                        "mean": np.mean(energies),
                        "std": np.std(energies),
                    }
                    stats_df = pd.DataFrame([stats])
                    stats_df.to_excel(writer, sheet_name="Statistics", index=False)
            
            # Sheet 4: 메타데이터
            meta_df = pd.DataFrame([self.data.get("metadata", {})])
            meta_df.to_excel(writer, sheet_name="Metadata", index=False)
            
        return str(output)
    
    def to_zip(self, output_path: str) -> str:
        """ZIP 아카이브로 내보내기
        
        Args:
            output_path: 출력 파일 경로
            
        Returns:
            출력 파일 경로
        """
        output = Path(output_path)
        
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            # 결과 JSON
            json_content = json.dumps(self.data, indent=2, default=str)
            zf.writestr("results.json", json_content)
            
            # CSV
            csv_content = self._generate_csv_string()
            zf.writestr("results.csv", csv_content)
            
            # 구조 파일
            if self.config.include_structures:
                for pattern in ["*.xyz", "*.extxyz", "*.cif"]:
                    for f in self.results_dir.glob(pattern):
                        zf.write(f, f"structures/{f.name}")
                        
                # optimized 폴더
                opt_dir = self.results_dir / "optimized"
                if opt_dir.exists():
                    for f in opt_dir.glob("*.xyz"):
                        zf.write(f, f"optimized/{f.name}")
            
            # 궤적 파일
            if self.config.include_trajectories:
                for pattern in ["*.traj", "trajectory.*"]:
                    for f in self.results_dir.glob(pattern):
                        zf.write(f, f"trajectories/{f.name}")
            
            # 플롯/리포트
            if self.config.include_plots:
                for f in self.results_dir.glob("*.html"):
                    zf.write(f, f"reports/{f.name}")
                    
            # 로그
            if self.config.include_logs:
                for f in self.results_dir.glob("*.log"):
                    zf.write(f, f"logs/{f.name}")
                    
        return str(output)
    
    def _generate_csv_string(self) -> str:
        """CSV 문자열 생성"""
        import io
        buffer = io.StringIO()
        
        results = self.data.get("results", [])
        if not results:
            return ""
        
        columns = list(results[0].keys())
        exclude_cols = ["atoms", "structure", "cell", "positions", "forces"]
        columns = [c for c in columns if c not in exclude_cols]
        
        writer = csv.writer(buffer)
        writer.writerow(columns)
        
        for result in results:
            row = []
            for col in columns:
                val = result.get(col, "")
                if isinstance(val, float):
                    val = round(val, self.config.decimal_places)
                elif isinstance(val, (list, dict)):
                    val = json.dumps(val)
                row.append(val)
            writer.writerow(row)
            
        return buffer.getvalue()


def export_to_csv(results_dir: str, output: str) -> str:
    """편의 함수: CSV 내보내기"""
    return ExportManager(results_dir).to_csv(output)


def export_to_json(results_dir: str, output: str) -> str:
    """편의 함수: JSON 내보내기"""
    return ExportManager(results_dir).to_json(output)


def export_to_excel(results_dir: str, output: str) -> str:
    """편의 함수: Excel 내보내기"""
    return ExportManager(results_dir).to_excel(output)


def export_to_zip(results_dir: str, output: str, 
                  include_structures: bool = True,
                  include_trajectories: bool = True) -> str:
    """편의 함수: ZIP 내보내기"""
    config = ExportConfig(
        include_structures=include_structures,
        include_trajectories=include_trajectories
    )
    return ExportManager(results_dir, config).to_zip(output)
