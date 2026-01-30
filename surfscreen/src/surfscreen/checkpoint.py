"""
SurfScreen Checkpoint Module

대규모 스크리닝/MD 작업의 체크포인트 및 재개 기능
"""

import json
import time
import fcntl
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskRecord:
    """개별 작업 기록"""
    task_id: str
    status: str = "pending"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict] = None
    
    def mark_running(self):
        self.status = TaskStatus.RUNNING.value
        self.start_time = datetime.now().isoformat()
        
    def mark_completed(self, result: Optional[Dict] = None):
        self.status = TaskStatus.COMPLETED.value
        self.end_time = datetime.now().isoformat()
        self.result = result
        
    def mark_failed(self, error: str):
        self.status = TaskStatus.FAILED.value
        self.end_time = datetime.now().isoformat()
        self.error = error


@dataclass
class CheckpointState:
    """체크포인트 상태"""
    job_id: str
    job_type: str  # "screening" or "md"
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    start_time: str = ""
    last_update: str = ""
    config: Dict = field(default_factory=dict)
    tasks: Dict[str, Dict] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now().isoformat()
        self.last_update = datetime.now().isoformat()


class CheckpointManager:
    """체크포인트 관리자"""
    
    CHECKPOINT_FILE = "checkpoint.json"
    
    def __init__(self, output_dir: str, job_type: str = "screening"):
        """
        Args:
            output_dir: 출력 디렉토리
            job_type: 작업 유형 ("screening" or "md")
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_path = self.output_dir / self.CHECKPOINT_FILE
        
        # 기존 체크포인트 로드 또는 새로 생성
        if self.checkpoint_path.exists():
            self.state = self._load_checkpoint()
        else:
            job_id = f"{job_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.state = CheckpointState(job_id=job_id, job_type=job_type)
            
    def _load_checkpoint(self) -> CheckpointState:
        """체크포인트 로드"""
        with open(self.checkpoint_path) as f:
            data = json.load(f)
        return CheckpointState(**data)
    
    def save(self):
        """체크포인트 저장 (파일 락 사용)"""
        self.state.last_update = datetime.now().isoformat()
        try:
            with open(self.checkpoint_path, "w") as f:
                # 파일 락 (UNIX only, Windows에서는 무시)
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (AttributeError, OSError):
                    pass  # Windows 또는 락 실패
                json.dump(asdict(self.state), f, indent=2)
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except (AttributeError, OSError):
                    pass
            logger.debug(f"Checkpoint saved: {self.checkpoint_path}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
            
    def register_tasks(self, task_ids: List[str], config: Optional[Dict] = None):
        """작업 등록
        
        Args:
            task_ids: 작업 ID 목록
            config: 작업 설정
        """
        self.state.total_tasks = len(task_ids)
        self.state.config = config or {}
        
        for task_id in task_ids:
            if task_id not in self.state.tasks:
                self.state.tasks[task_id] = asdict(TaskRecord(task_id=task_id))
                
        self.save()
        
    def get_pending_tasks(self) -> List[str]:
        """대기 중인 작업 ID 목록"""
        return [
            task_id for task_id, task in self.state.tasks.items()
            if task.get("status") == TaskStatus.PENDING.value
        ]
    
    def get_failed_tasks(self) -> List[str]:
        """실패한 작업 ID 목록"""
        return [
            task_id for task_id, task in self.state.tasks.items()
            if task.get("status") == TaskStatus.FAILED.value
        ]
    
    def get_completed_tasks(self) -> List[str]:
        """완료된 작업 ID 목록"""
        return [
            task_id for task_id, task in self.state.tasks.items()
            if task.get("status") == TaskStatus.COMPLETED.value
        ]
    
    def start_task(self, task_id: str):
        """작업 시작 표시"""
        if task_id in self.state.tasks:
            self.state.tasks[task_id]["status"] = TaskStatus.RUNNING.value
            self.state.tasks[task_id]["start_time"] = datetime.now().isoformat()
            self.save()
            
    def complete_task(self, task_id: str, result: Optional[Dict] = None):
        """작업 완료 표시"""
        if task_id in self.state.tasks:
            self.state.tasks[task_id]["status"] = TaskStatus.COMPLETED.value
            self.state.tasks[task_id]["end_time"] = datetime.now().isoformat()
            self.state.tasks[task_id]["result"] = result
            self.state.completed_tasks += 1
            self.save()
            
    def fail_task(self, task_id: str, error: str):
        """작업 실패 표시"""
        if task_id in self.state.tasks:
            self.state.tasks[task_id]["status"] = TaskStatus.FAILED.value
            self.state.tasks[task_id]["end_time"] = datetime.now().isoformat()
            self.state.tasks[task_id]["error"] = error
            self.state.failed_tasks += 1
            self.save()
            
    def reset_failed_tasks(self):
        """실패한 작업을 대기 상태로 리셋"""
        for task_id in self.get_failed_tasks():
            self.state.tasks[task_id]["status"] = TaskStatus.PENDING.value
            self.state.tasks[task_id]["error"] = None
            self.state.tasks[task_id]["start_time"] = None
            self.state.tasks[task_id]["end_time"] = None
            
        self.state.failed_tasks = 0
        self.save()
        
    def get_progress(self) -> Dict[str, Any]:
        """진행 상황 반환"""
        total = self.state.total_tasks
        completed = self.state.completed_tasks
        failed = self.state.failed_tasks
        pending = len(self.get_pending_tasks())
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress_pct": (completed / total * 100) if total > 0 else 0,
            "is_finished": pending == 0 and total > 0,
        }
        
    def print_status(self):
        """상태 출력"""
        progress = self.get_progress()
        print(f"\n📊 Checkpoint Status: {self.state.job_id}")
        print(f"   Job Type: {self.state.job_type}")
        print(f"   Total: {progress['total']}")
        print(f"   Completed: {progress['completed']} ✅")
        print(f"   Failed: {progress['failed']} ❌")
        print(f"   Pending: {progress['pending']} ⏳")
        print(f"   Progress: {progress['progress_pct']:.1f}%")
        print(f"   Last Update: {self.state.last_update}")


class ScreeningCheckpoint(CheckpointManager):
    """스크리닝 전용 체크포인트"""
    
    def __init__(self, output_dir: str):
        super().__init__(output_dir, job_type="screening")
        
    def register_configurations(self, config_files: List[str], screening_config: Dict):
        """스크리닝 구성 등록
        
        Args:
            config_files: 구성 파일 경로 목록
            screening_config: 스크리닝 설정
        """
        task_ids = [Path(f).stem for f in config_files]
        self.register_tasks(task_ids, screening_config)
        
        # 파일 경로 저장
        for task_id, config_file in zip(task_ids, config_files):
            self.state.tasks[task_id]["config_file"] = config_file


class MDCheckpoint(CheckpointManager):
    """MD 전용 체크포인트"""
    
    def __init__(self, output_dir: str):
        super().__init__(output_dir, job_type="md")
        
    def register_steps(self, total_steps: int, md_config: Dict):
        """MD 스텝 등록
        
        Args:
            total_steps: 총 스텝 수
            md_config: MD 설정
        """
        # 체크포인트 간격으로 작업 분할
        checkpoint_interval = md_config.get("checkpoint_interval", 1000)
        n_checkpoints = (total_steps + checkpoint_interval - 1) // checkpoint_interval
        
        task_ids = [f"step_{i * checkpoint_interval}" for i in range(n_checkpoints)]
        self.register_tasks(task_ids, md_config)
        
    def get_last_completed_step(self) -> int:
        """마지막 완료된 스텝 번호"""
        completed = self.get_completed_tasks()
        if not completed:
            return 0
            
        steps = [int(t.replace("step_", "")) for t in completed]
        return max(steps) if steps else 0
