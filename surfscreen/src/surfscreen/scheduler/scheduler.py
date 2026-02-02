"""
Job Scheduler

APScheduler-based job scheduling with cron, interval, and dependency support.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

from .schedule_models import (
    ScheduleType,
    ScheduleStatus,
    ScheduledJob,
)

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Job scheduler supporting cron, interval, one-time, and dependency-based scheduling.
    
    Uses APScheduler when available, falls back to basic implementation.
    """
    
    def __init__(
        self,
        executor_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
        storage_dir: Optional[Path] = None,
    ):
        """
        Initialize scheduler.
        
        Args:
            executor_fn: Function to execute scheduled jobs
            storage_dir: Directory for persistent storage
        """
        self.executor_fn = executor_fn or self._default_executor
        self.storage_dir = storage_dir or Path.cwd() / "schedules"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.schedules: Dict[str, ScheduledJob] = {}
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = Lock()
        self._apscheduler = None
        self._running = False
        
        # Try to initialize APScheduler
        self._init_apscheduler()
        
        # Load persisted schedules
        self._load_schedules()
    
    def _init_apscheduler(self):
        """Initialize APScheduler if available."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.triggers.date import DateTrigger
            
            self._apscheduler = BackgroundScheduler()
            logger.info("APScheduler initialized")
            
        except ImportError:
            logger.warning("APScheduler not installed. Using basic scheduling.")
            self._apscheduler = None
    
    def start(self):
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        
        if self._apscheduler:
            self._apscheduler.start()
            logger.info("Scheduler started")
        
        # Register existing schedules
        for schedule in self.schedules.values():
            if schedule.status == ScheduleStatus.ACTIVE:
                self._register_job(schedule)
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        
        if self._apscheduler:
            self._apscheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
    
    def create_schedule(
        self,
        name: str,
        schedule_type: ScheduleType,
        job_type: str,
        job_config: Dict[str, Any],
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_at: Optional[str] = None,
        depends_on: Optional[str] = None,
        max_runs: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> ScheduledJob:
        """
        Create a new scheduled job.
        
        Args:
            name: Schedule name
            schedule_type: Type of schedule
            job_type: Type of job to execute
            job_config: Job configuration
            cron_expression: Cron expression (for CRON type)
            interval_seconds: Interval in seconds (for INTERVAL type)
            run_at: ISO datetime (for ONCE type)
            depends_on: Job ID to wait for (for DEPENDENCY type)
            max_runs: Maximum number of runs
            created_by: User who created the schedule
            
        Returns:
            Created ScheduledJob
        """
        schedule_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        schedule = ScheduledJob(
            schedule_id=schedule_id,
            name=name,
            schedule_type=schedule_type,
            status=ScheduleStatus.ACTIVE,
            job_config={
                "job_type": job_type,
                **job_config,
            },
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            run_at=run_at,
            depends_on=depends_on,
            max_runs=max_runs,
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )
        
        # Calculate next run time
        schedule.next_run = self._calculate_next_run(schedule)
        
        with self._lock:
            self.schedules[schedule_id] = schedule
            self.history[schedule_id] = []
        
        # Register with scheduler
        if self._running:
            self._register_job(schedule)
        
        # Persist
        self._save_schedules()
        
        logger.info(f"Created schedule: {schedule_id} ({name})")
        
        return schedule
    
    def get_schedule(self, schedule_id: str) -> Optional[ScheduledJob]:
        """Get schedule by ID."""
        with self._lock:
            return self.schedules.get(schedule_id)
    
    def list_schedules(
        self,
        status: Optional[ScheduleStatus] = None,
        schedule_type: Optional[ScheduleType] = None,
    ) -> List[ScheduledJob]:
        """List schedules with optional filtering."""
        with self._lock:
            schedules = list(self.schedules.values())
        
        if status:
            schedules = [s for s in schedules if s.status == status]
        
        if schedule_type:
            schedules = [s for s in schedules if s.schedule_type == schedule_type]
        
        return schedules
    
    def update_schedule(
        self,
        schedule_id: str,
        name: Optional[str] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_at: Optional[str] = None,
        max_runs: Optional[int] = None,
        job_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[ScheduledJob]:
        """Update a schedule."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            
            if not schedule:
                return None
            
            if name:
                schedule.name = name
            if cron_expression:
                schedule.cron_expression = cron_expression
            if interval_seconds:
                schedule.interval_seconds = interval_seconds
            if run_at:
                schedule.run_at = run_at
            if max_runs:
                schedule.max_runs = max_runs
            if job_config:
                schedule.job_config.update(job_config)
            
            schedule.updated_at = datetime.utcnow().isoformat()
            schedule.next_run = self._calculate_next_run(schedule)
        
        # Re-register with scheduler
        self._unregister_job(schedule_id)
        if schedule.status == ScheduleStatus.ACTIVE:
            self._register_job(schedule)
        
        self._save_schedules()
        
        return schedule
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        with self._lock:
            if schedule_id not in self.schedules:
                return False
            
            del self.schedules[schedule_id]
            self.history.pop(schedule_id, None)
        
        self._unregister_job(schedule_id)
        self._save_schedules()
        
        logger.info(f"Deleted schedule: {schedule_id}")
        
        return True
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a schedule."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return False
            
            schedule.status = ScheduleStatus.PAUSED
            schedule.updated_at = datetime.utcnow().isoformat()
        
        self._unregister_job(schedule_id)
        self._save_schedules()
        
        return True
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule."""
        with self._lock:
            schedule = self.schedules.get(schedule_id)
            if not schedule:
                return False
            
            schedule.status = ScheduleStatus.ACTIVE
            schedule.updated_at = datetime.utcnow().isoformat()
            schedule.next_run = self._calculate_next_run(schedule)
        
        self._register_job(schedule)
        self._save_schedules()
        
        return True
    
    def get_history(
        self,
        schedule_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get execution history for a schedule."""
        with self._lock:
            history = self.history.get(schedule_id, [])
            return history[-limit:]
    
    def _register_job(self, schedule: ScheduledJob):
        """Register job with APScheduler."""
        if not self._apscheduler:
            return
        
        try:
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.triggers.date import DateTrigger
            
            trigger = None
            
            if schedule.schedule_type == ScheduleType.CRON:
                trigger = CronTrigger.from_crontab(schedule.cron_expression)
                
            elif schedule.schedule_type == ScheduleType.INTERVAL:
                trigger = IntervalTrigger(seconds=schedule.interval_seconds)
                
            elif schedule.schedule_type == ScheduleType.ONCE:
                run_time = datetime.fromisoformat(schedule.run_at)
                trigger = DateTrigger(run_date=run_time)
            
            if trigger:
                self._apscheduler.add_job(
                    self._execute_scheduled_job,
                    trigger,
                    args=[schedule.schedule_id],
                    id=schedule.schedule_id,
                    replace_existing=True,
                )
                
        except Exception as e:
            logger.error(f"Failed to register job {schedule.schedule_id}: {e}")
    
    def _unregister_job(self, schedule_id: str):
        """Unregister job from APScheduler."""
        if not self._apscheduler:
            return
        
        try:
            self._apscheduler.remove_job(schedule_id)
        except Exception:
            pass  # Job may not exist
    
    def _execute_scheduled_job(self, schedule_id: str):
        """Execute a scheduled job."""
        schedule = self.get_schedule(schedule_id)
        
        if not schedule or schedule.status != ScheduleStatus.ACTIVE:
            return
        
        execution_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow().isoformat()
        
        logger.info(f"Executing scheduled job: {schedule_id} ({schedule.name})")
        
        try:
            result = self.executor_fn(schedule.job_config)
            
            # Update schedule
            with self._lock:
                schedule.last_run = started_at
                schedule.run_count += 1
                schedule.last_result = result
                schedule.last_error = None
                schedule.next_run = self._calculate_next_run(schedule)
                
                # Record history
                self.history.setdefault(schedule_id, []).append({
                    "execution_id": execution_id,
                    "started_at": started_at,
                    "completed_at": datetime.utcnow().isoformat(),
                    "status": "completed",
                    "result": result,
                })
                
                # Check max runs
                if schedule.max_runs and schedule.run_count >= schedule.max_runs:
                    schedule.status = ScheduleStatus.COMPLETED
                    self._unregister_job(schedule_id)
            
            self._save_schedules()
            
            # Trigger dependent jobs
            self._trigger_dependents(schedule_id)
            
        except Exception as e:
            with self._lock:
                schedule.last_run = started_at
                schedule.last_error = str(e)
                
                self.history.setdefault(schedule_id, []).append({
                    "execution_id": execution_id,
                    "started_at": started_at,
                    "completed_at": datetime.utcnow().isoformat(),
                    "status": "failed",
                    "error": str(e),
                })
            
            logger.error(f"Scheduled job failed: {schedule_id} - {e}")
            self._save_schedules()
    
    def _trigger_dependents(self, completed_job_id: str):
        """Trigger jobs that depend on the completed job."""
        for schedule in self.schedules.values():
            if (schedule.schedule_type == ScheduleType.DEPENDENCY and
                schedule.depends_on == completed_job_id and
                schedule.status == ScheduleStatus.ACTIVE):
                
                logger.info(f"Triggering dependent job: {schedule.schedule_id}")
                self._execute_scheduled_job(schedule.schedule_id)
    
    def _calculate_next_run(self, schedule: ScheduledJob) -> Optional[str]:
        """Calculate next run time for a schedule."""
        now = datetime.utcnow()
        
        if schedule.schedule_type == ScheduleType.ONCE:
            return schedule.run_at
        
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            if schedule.last_run:
                last = datetime.fromisoformat(schedule.last_run)
                next_run = last + timedelta(seconds=schedule.interval_seconds)
            else:
                next_run = now + timedelta(seconds=schedule.interval_seconds)
            return next_run.isoformat()
        
        elif schedule.schedule_type == ScheduleType.CRON:
            try:
                from croniter import croniter
                cron = croniter(schedule.cron_expression, now)
                return cron.get_next(datetime).isoformat()
            except ImportError:
                # Fallback: return None if croniter not available
                return None
        
        return None
    
    def _save_schedules(self):
        """Persist schedules to disk."""
        try:
            data = {
                "schedules": {
                    sid: s.to_dict()
                    for sid, s in self.schedules.items()
                },
                "history": self.history,
            }
            
            path = self.storage_dir / "schedules.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save schedules: {e}")
    
    def _load_schedules(self):
        """Load schedules from disk."""
        path = self.storage_dir / "schedules.json"
        
        if not path.exists():
            return
        
        try:
            with open(path) as f:
                data = json.load(f)
            
            for sid, sdata in data.get("schedules", {}).items():
                self.schedules[sid] = ScheduledJob(
                    schedule_id=sdata["schedule_id"],
                    name=sdata["name"],
                    schedule_type=ScheduleType(sdata["schedule_type"]),
                    status=ScheduleStatus(sdata["status"]),
                    job_config=sdata["job_config"],
                    cron_expression=sdata.get("cron_expression"),
                    interval_seconds=sdata.get("interval_seconds"),
                    run_at=sdata.get("run_at"),
                    depends_on=sdata.get("depends_on"),
                    next_run=sdata.get("next_run"),
                    last_run=sdata.get("last_run"),
                    run_count=sdata.get("run_count", 0),
                    max_runs=sdata.get("max_runs"),
                    last_error=sdata.get("last_error"),
                    created_at=sdata.get("created_at", ""),
                    updated_at=sdata.get("updated_at", ""),
                )
            
            self.history = data.get("history", {})
            
            logger.info(f"Loaded {len(self.schedules)} schedules")
            
        except Exception as e:
            logger.warning(f"Failed to load schedules: {e}")
    
    def _default_executor(self, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Default job executor (placeholder)."""
        import time
        time.sleep(0.1)
        return {"status": "completed", "config": job_config}


# Global scheduler instance
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = Scheduler()
    
    return _scheduler
