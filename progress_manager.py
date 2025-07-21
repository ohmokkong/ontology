"""
진행 상황 표시 및 관리 모듈

이 모듈은 장시간 실행되는 작업의 진행 상황을 표시하고 관리합니다.
- 배치 처리 시 진행률 표시
- 장시간 작업에 대한 사용자 피드백
- 작업 취소 및 재시작 기능
- 실시간 상태 업데이트
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import sys
from collections import deque
import signal

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """작업 상태 열거형"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProgressStyle(Enum):
    """진행률 표시 스타일"""
    BAR = "bar"              # [████████████████████] 100%
    PERCENTAGE = "percentage" # 75%
    SPINNER = "spinner"       # ⠋ Processing...
    DETAILED = "detailed"     # [████████████████████] 75% (750/1000) ETA: 00:05:23


@dataclass
class TaskProgress:
    """작업 진행 상황 데이터 클래스"""
    task_id: str
    name: str
    total_items: int
    completed_items: int = 0
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    current_operation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> float:
        """진행률 백분율"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def elapsed_time(self) -> timedelta:
        """경과 시간"""
        if not self.start_time:
            return timedelta(0)
        end_time = self.end_time or datetime.now()
        return end_time - self.start_time
    
    @property
    def estimated_remaining_time(self) -> timedelta:
        """예상 남은 시간"""
        if self.completed_items == 0 or not self.start_time:
            return timedelta(0)
        
        elapsed = self.elapsed_time.total_seconds()
        rate = self.completed_items / elapsed if elapsed > 0 else 0
        
        if rate == 0:
            return timedelta(0)
        
        remaining_items = self.total_items - self.completed_items
        remaining_seconds = remaining_items / rate
        return timedelta(seconds=remaining_seconds)
    
    @property
    def items_per_second(self) -> float:
        """초당 처리 아이템 수"""
        if not self.start_time or self.completed_items == 0:
            return 0.0
        
        elapsed = self.elapsed_time.total_seconds()
        return self.completed_items / elapsed if elapsed > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'status': self.status.value,
            'progress_percentage': self.progress_percentage,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'elapsed_time': str(self.elapsed_time),
            'estimated_remaining_time': str(self.estimated_remaining_time),
            'items_per_second': self.items_per_second,
            'current_operation': self.current_operation,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


class ProgressDisplay:
    """진행률 표시 클래스"""
    
    def __init__(self, style: ProgressStyle = ProgressStyle.DETAILED, width: int = 50):
        self.style = style
        self.width = width
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_index = 0
    
    def format_progress(self, progress: TaskProgress) -> str:
        """진행률을 포맷팅하여 문자열로 반환"""
        if self.style == ProgressStyle.BAR:
            return self._format_bar(progress)
        elif self.style == ProgressStyle.PERCENTAGE:
            return self._format_percentage(progress)
        elif self.style == ProgressStyle.SPINNER:
            return self._format_spinner(progress)
        elif self.style == ProgressStyle.DETAILED:
            return self._format_detailed(progress)
        else:
            return f"{progress.name}: {progress.progress_percentage:.1f}%"
    
    def _format_bar(self, progress: TaskProgress) -> str:
        """바 형태 진행률"""
        filled = int(self.width * progress.progress_percentage / 100)
        bar = "█" * filled + "░" * (self.width - filled)
        return f"[{bar}] {progress.progress_percentage:.1f}%"
    
    def _format_percentage(self, progress: TaskProgress) -> str:
        """백분율 형태 진행률"""
        return f"{progress.progress_percentage:.1f}%"
    
    def _format_spinner(self, progress: TaskProgress) -> str:
        """스피너 형태 진행률"""
        spinner = self.spinner_chars[self.spinner_index % len(self.spinner_chars)]
        self.spinner_index += 1
        return f"{spinner} {progress.current_operation or progress.name}..."
    
    def _format_detailed(self, progress: TaskProgress) -> str:
        """상세 정보 포함 진행률"""
        filled = int(self.width * progress.progress_percentage / 100)
        bar = "█" * filled + "░" * (self.width - filled)
        
        # 시간 정보 포맷팅
        eta = self._format_time(progress.estimated_remaining_time)
        elapsed = self._format_time(progress.elapsed_time)
        rate = progress.items_per_second
        
        return (f"[{bar}] {progress.progress_percentage:.1f}% "
                f"({progress.completed_items}/{progress.total_items}) "
                f"Rate: {rate:.1f}/s ETA: {eta} Elapsed: {elapsed}")
    
    def _format_time(self, td: timedelta) -> str:
        """시간 포맷팅"""
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class ProgressManager:
    """진행 상황 관리자"""
    
    def __init__(self, update_interval: float = 0.5):
        self.update_interval = update_interval
        self.tasks: Dict[str, TaskProgress] = {}
        self.displays: Dict[str, ProgressDisplay] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.cancel_flags: Dict[str, threading.Event] = {}
        self.pause_flags: Dict[str, threading.Event] = {}
        
        self._lock = threading.Lock()
        self._display_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 시그널 핸들러 설정 (Ctrl+C 처리)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def create_task(self, task_id: str, name: str, total_items: int, 
                   style: ProgressStyle = ProgressStyle.DETAILED) -> TaskProgress:
        """새 작업 생성"""
        with self._lock:
            progress = TaskProgress(
                task_id=task_id,
                name=name,
                total_items=total_items,
                status=TaskStatus.PENDING
            )
            
            self.tasks[task_id] = progress
            self.displays[task_id] = ProgressDisplay(style)
            self.callbacks[task_id] = []
            self.cancel_flags[task_id] = threading.Event()
            self.pause_flags[task_id] = threading.Event()
            
            logger.info(f"Created task: {task_id} ({name}) with {total_items} items")
            
        return progress
    
    def start_task(self, task_id: str) -> bool:
        """작업 시작"""
        with self._lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False
            
            task = self.tasks[task_id]
            if task.status != TaskStatus.PENDING:
                logger.warning(f"Task {task_id} is not in pending state")
                return False
            
            task.status = TaskStatus.RUNNING
            task.start_time = datetime.now()
            
            # 표시 스레드 시작
            if not self._running:
                self._running = True
                self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
                self._display_thread.start()
            
            logger.info(f"Started task: {task_id}")
            self._notify_callbacks(task_id, "started")
            
        return True
    
    def update_progress(self, task_id: str, completed_items: int, 
                       current_operation: str = "", **metadata) -> bool:
        """진행 상황 업데이트"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != TaskStatus.RUNNING:
                return False
            
            task.completed_items = min(completed_items, task.total_items)
            task.current_operation = current_operation
            task.metadata.update(metadata)
            
            # 완료 확인
            if task.completed_items >= task.total_items:
                self.complete_task(task_id)
            
            self._notify_callbacks(task_id, "updated")
            
        return True
    
    def increment_progress(self, task_id: str, increment: int = 1, 
                          current_operation: str = "", **metadata) -> bool:
        """진행 상황 증가"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            new_completed = task.completed_items + increment
            
        return self.update_progress(task_id, new_completed, current_operation, **metadata)
    
    def pause_task(self, task_id: str) -> bool:
        """작업 일시정지"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != TaskStatus.RUNNING:
                return False
            
            task.status = TaskStatus.PAUSED
            self.pause_flags[task_id].set()
            
            logger.info(f"Paused task: {task_id}")
            self._notify_callbacks(task_id, "paused")
            
        return True
    
    def resume_task(self, task_id: str) -> bool:
        """작업 재개"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != TaskStatus.PAUSED:
                return False
            
            task.status = TaskStatus.RUNNING
            self.pause_flags[task_id].clear()
            
            logger.info(f"Resumed task: {task_id}")
            self._notify_callbacks(task_id, "resumed")
            
        return True
    
    def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.end_time = datetime.now()
            self.cancel_flags[task_id].set()
            
            logger.info(f"Cancelled task: {task_id}")
            self._notify_callbacks(task_id, "cancelled")
            
        return True
    
    def complete_task(self, task_id: str) -> bool:
        """작업 완료"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()
            task.completed_items = task.total_items
            
            logger.info(f"Completed task: {task_id}")
            self._notify_callbacks(task_id, "completed")
            
        return True
    
    def fail_task(self, task_id: str, error_message: str) -> bool:
        """작업 실패 처리"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.end_time = datetime.now()
            task.error_message = error_message
            
            logger.error(f"Failed task: {task_id} - {error_message}")
            self._notify_callbacks(task_id, "failed")
            
        return True
    
    def restart_task(self, task_id: str) -> bool:
        """작업 재시작"""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = TaskStatus.PENDING
            task.completed_items = 0
            task.start_time = None
            task.end_time = None
            task.error_message = None
            task.current_operation = ""
            
            # 플래그 초기화
            self.cancel_flags[task_id].clear()
            self.pause_flags[task_id].clear()
            
            logger.info(f"Restarted task: {task_id}")
            self._notify_callbacks(task_id, "restarted")
            
        return True
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """작업 진행 상황 조회"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, TaskProgress]:
        """모든 작업 진행 상황 조회"""
        with self._lock:
            return self.tasks.copy()
    
    def is_cancelled(self, task_id: str) -> bool:
        """작업 취소 여부 확인"""
        return self.cancel_flags.get(task_id, threading.Event()).is_set()
    
    def is_paused(self, task_id: str) -> bool:
        """작업 일시정지 여부 확인"""
        return self.pause_flags.get(task_id, threading.Event()).is_set()
    
    def wait_if_paused(self, task_id: str):
        """일시정지 상태면 대기"""
        if task_id in self.pause_flags:
            self.pause_flags[task_id].wait()
    
    def add_callback(self, task_id: str, callback: Callable[[TaskProgress, str], None]):
        """콜백 함수 추가"""
        with self._lock:
            if task_id not in self.callbacks:
                self.callbacks[task_id] = []
            self.callbacks[task_id].append(callback)
    
    def remove_callback(self, task_id: str, callback: Callable):
        """콜백 함수 제거"""
        with self._lock:
            if task_id in self.callbacks and callback in self.callbacks[task_id]:
                self.callbacks[task_id].remove(callback)
    
    def _notify_callbacks(self, task_id: str, event_type: str):
        """콜백 함수 호출"""
        if task_id in self.callbacks:
            task = self.tasks[task_id]
            for callback in self.callbacks[task_id]:
                try:
                    callback(task, event_type)
                except Exception as e:
                    logger.error(f"Callback error for task {task_id}: {e}")
    
    def _display_loop(self):
        """진행률 표시 루프"""
        while self._running:
            try:
                with self._lock:
                    active_tasks = {
                        tid: task for tid, task in self.tasks.items()
                        if task.status == TaskStatus.RUNNING
                    }
                
                if active_tasks:
                    # 콘솔 클리어 (Windows/Linux 호환)
                    if sys.platform.startswith('win'):
                        import os
                        os.system('cls')
                    else:
                        print('\033[2J\033[H', end='')
                    
                    print("=== 작업 진행 상황 ===")
                    print(f"업데이트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print()
                    
                    for task_id, task in active_tasks.items():
                        display = self.displays[task_id]
                        progress_str = display.format_progress(task)
                        print(f"{task.name}: {progress_str}")
                        
                        if task.current_operation:
                            print(f"  현재 작업: {task.current_operation}")
                        print()
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Display loop error: {e}")
                time.sleep(1)
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 처리)"""
        print("\n\n작업 취소 요청을 받았습니다...")
        
        with self._lock:
            running_tasks = [
                tid for tid, task in self.tasks.items()
                if task.status == TaskStatus.RUNNING
            ]
        
        if running_tasks:
            print(f"{len(running_tasks)}개의 실행 중인 작업을 취소합니다...")
            for task_id in running_tasks:
                self.cancel_task(task_id)
        
        self.stop()
        sys.exit(0)
    
    def stop(self):
        """진행률 관리자 중지"""
        self._running = False
        if self._display_thread and self._display_thread.is_alive():
            self._display_thread.join(timeout=2.0)
        
        logger.info("Progress manager stopped")
    
    def export_progress_report(self, file_path: str):
        """진행 상황 리포트 내보내기"""
        with self._lock:
            report = {
                'timestamp': datetime.now().isoformat(),
                'tasks': {tid: task.to_dict() for tid, task in self.tasks.items()}
            }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Progress report exported to {file_path}")


# 전역 진행률 관리자 인스턴스
progress_manager = ProgressManager()


# 편의 함수들
def create_progress_task(task_id: str, name: str, total_items: int, 
                        style: ProgressStyle = ProgressStyle.DETAILED) -> TaskProgress:
    """진행률 작업 생성 (전역 관리자 사용)"""
    return progress_manager.create_task(task_id, name, total_items, style)


def start_progress_task(task_id: str) -> bool:
    """진행률 작업 시작 (전역 관리자 사용)"""
    return progress_manager.start_task(task_id)


def update_progress(task_id: str, completed_items: int, current_operation: str = "", **metadata) -> bool:
    """진행 상황 업데이트 (전역 관리자 사용)"""
    return progress_manager.update_progress(task_id, completed_items, current_operation, **metadata)


def increment_progress(task_id: str, increment: int = 1, current_operation: str = "", **metadata) -> bool:
    """진행 상황 증가 (전역 관리자 사용)"""
    return progress_manager.increment_progress(task_id, increment, current_operation, **metadata)


def complete_progress_task(task_id: str) -> bool:
    """진행률 작업 완료 (전역 관리자 사용)"""
    return progress_manager.complete_task(task_id)


def cancel_progress_task(task_id: str) -> bool:
    """진행률 작업 취소 (전역 관리자 사용)"""
    return progress_manager.cancel_task(task_id)


def is_task_cancelled(task_id: str) -> bool:
    """작업 취소 여부 확인 (전역 관리자 사용)"""
    return progress_manager.is_cancelled(task_id)


def wait_if_task_paused(task_id: str):
    """작업 일시정지 시 대기 (전역 관리자 사용)"""
    progress_manager.wait_if_paused(task_id)


# 컨텍스트 매니저
class ProgressContext:
    """진행률 컨텍스트 매니저"""
    
    def __init__(self, task_id: str, name: str, total_items: int, 
                 style: ProgressStyle = ProgressStyle.DETAILED):
        self.task_id = task_id
        self.name = name
        self.total_items = total_items
        self.style = style
        self.task = None
    
    def __enter__(self) -> TaskProgress:
        self.task = create_progress_task(self.task_id, self.name, self.total_items, self.style)
        start_progress_task(self.task_id)
        return self.task
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            complete_progress_task(self.task_id)
        else:
            progress_manager.fail_task(self.task_id, str(exc_val))
        return False


def progress_context(task_id: str, name: str, total_items: int, 
                    style: ProgressStyle = ProgressStyle.DETAILED) -> ProgressContext:
    """진행률 컨텍스트 매니저 생성"""
    return ProgressContext(task_id, name, total_items, style)