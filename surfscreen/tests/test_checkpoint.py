"""
Test Checkpoint Module
"""

import pytest
import json
from pathlib import Path

from surfscreen.checkpoint import (
    CheckpointManager,
    ScreeningCheckpoint,
    MDCheckpoint,
    TaskStatus
)


@pytest.fixture
def checkpoint_dir(tmp_path):
    """체크포인트 디렉토리"""
    return tmp_path / "checkpoint_test"


def test_checkpoint_manager_create(checkpoint_dir):
    """체크포인트 생성 테스트"""
    manager = CheckpointManager(str(checkpoint_dir), job_type="screening")
    
    assert manager.checkpoint_path.exists()
    assert manager.state.job_type == "screening"


def test_checkpoint_register_tasks(checkpoint_dir):
    """작업 등록 테스트"""
    manager = CheckpointManager(str(checkpoint_dir))
    manager.register_tasks(["task1", "task2", "task3"], {"engine": "mace"})
    
    assert manager.state.total_tasks == 3
    assert len(manager.get_pending_tasks()) == 3


def test_checkpoint_task_lifecycle(checkpoint_dir):
    """작업 라이프사이클 테스트"""
    manager = CheckpointManager(str(checkpoint_dir))
    manager.register_tasks(["task1"])
    
    # 시작
    manager.start_task("task1")
    assert manager.state.tasks["task1"]["status"] == TaskStatus.RUNNING.value
    
    # 완료
    manager.complete_task("task1", {"energy": -1.5})
    assert manager.state.tasks["task1"]["status"] == TaskStatus.COMPLETED.value
    assert manager.state.completed_tasks == 1


def test_checkpoint_fail_task(checkpoint_dir):
    """작업 실패 테스트"""
    manager = CheckpointManager(str(checkpoint_dir))
    manager.register_tasks(["task1"])
    manager.start_task("task1")
    manager.fail_task("task1", "Calculation error")
    
    assert manager.state.tasks["task1"]["status"] == TaskStatus.FAILED.value
    assert manager.state.failed_tasks == 1
    assert len(manager.get_failed_tasks()) == 1


def test_checkpoint_reset_failed(checkpoint_dir):
    """실패 작업 리셋 테스트"""
    manager = CheckpointManager(str(checkpoint_dir))
    manager.register_tasks(["task1"])
    manager.fail_task("task1", "Error")
    
    manager.reset_failed_tasks()
    
    assert len(manager.get_failed_tasks()) == 0
    assert len(manager.get_pending_tasks()) == 1


def test_checkpoint_progress(checkpoint_dir):
    """진행률 테스트"""
    manager = CheckpointManager(str(checkpoint_dir))
    manager.register_tasks(["t1", "t2", "t3", "t4"])
    manager.complete_task("t1")
    manager.complete_task("t2")
    
    progress = manager.get_progress()
    
    assert progress["total"] == 4
    assert progress["completed"] == 2
    assert progress["progress_pct"] == 50.0


def test_screening_checkpoint(checkpoint_dir):
    """스크리닝 체크포인트 테스트"""
    cp = ScreeningCheckpoint(str(checkpoint_dir))
    cp.register_configurations(
        ["config1.xyz", "config2.xyz"],
        {"engine": "mace", "temperature": 300}
    )
    
    assert cp.state.total_tasks == 2
    assert cp.state.config["engine"] == "mace"


def test_md_checkpoint(checkpoint_dir):
    """MD 체크포인트 테스트"""
    cp = MDCheckpoint(str(checkpoint_dir))
    cp.register_steps(5000, {"checkpoint_interval": 1000})
    
    assert cp.state.total_tasks == 5  # 5000 / 1000
    
    cp.complete_task("step_0")
    cp.complete_task("step_1000")
    
    assert cp.get_last_completed_step() == 1000


def test_checkpoint_persistence(checkpoint_dir):
    """체크포인트 영속성 테스트"""
    # 첫 번째 세션
    manager1 = CheckpointManager(str(checkpoint_dir))
    manager1.register_tasks(["task1", "task2"])
    manager1.complete_task("task1")
    
    # 두 번째 세션 (재로드)
    manager2 = CheckpointManager(str(checkpoint_dir))
    
    assert manager2.state.total_tasks == 2
    assert manager2.state.completed_tasks == 1
    assert len(manager2.get_pending_tasks()) == 1
