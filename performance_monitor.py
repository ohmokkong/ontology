"""
성능 측정 및 최적화 모듈

이 모듈은 시스템의 성능을 측정하고 최적화하는 기능을 제공합니다.
- 대량 데이터 처리 성능 측정
- API 호출 최적화 및 지연 시간 조절
- 메모리 사용량 모니터링 및 최적화
"""

import time
import psutil
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import functools
import gc
import sys

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 클래스"""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cpu_percent: float
    success: bool
    error_message: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def memory_used(self) -> float:
        """사용된 메모리 양 (MB)"""
        return self.memory_after - self.memory_before

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'operation_name': self.operation_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'memory_before': self.memory_before,
            'memory_after': self.memory_after,
            'memory_peak': self.memory_peak,
            'memory_used': self.memory_used,
            'cpu_percent': self.cpu_percent,
            'success': self.success,
            'error_message': self.error_message,
            'additional_data': self.additional_data
        }


@dataclass
class APICallMetrics:
    """API 호출 메트릭"""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    payload_size: int
    response_size: int
    timestamp: datetime
    success: bool
    retry_count: int = 0


class PerformanceMonitor:
    """성능 모니터링 및 최적화 클래스"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.api_metrics: deque = deque(maxlen=max_history)
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.memory_monitor_active = False
        self.memory_samples: deque = deque(maxlen=100)
        self._lock = threading.Lock()
        
        # 성능 임계값 설정
        self.thresholds = {
            'api_response_time': 3.0,  # 3초
            'memory_usage_mb': 500,    # 500MB
            'cpu_usage_percent': 80,   # 80%
            'operation_duration': 10.0  # 10초
        }
        
    def measure_performance(self, operation_name: str):
        """성능 측정 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return self._measure_sync_operation(operation_name, func, *args, **kwargs)
            return wrapper
        return decorator
    
    def measure_async_performance(self, operation_name: str):
        """비동기 성능 측정 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await self._measure_async_operation(operation_name, func, *args, **kwargs)
            return wrapper
        return decorator
    
    def _measure_sync_operation(self, operation_name: str, func: Callable, *args, **kwargs) -> Any:
        """동기 작업 성능 측정"""
        # 시작 시점 메트릭 수집
        start_time = time.time()
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        cpu_before = process.cpu_percent()
        
        success = True
        error_message = None
        result = None
        memory_peak = memory_before
        
        try:
            # 메모리 모니터링 시작
            memory_monitor_thread = threading.Thread(
                target=self._monitor_memory_usage,
                args=(process,),
                daemon=True
            )
            memory_monitor_thread.start()
            
            # 함수 실행
            result = func(*args, **kwargs)
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Operation {operation_name} failed: {error_message}")
            raise
        finally:
            # 종료 시점 메트릭 수집
            end_time = time.time()
            duration = end_time - start_time
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            cpu_after = process.cpu_percent()
            
            # 메모리 피크 값 계산
            if self.memory_samples:
                memory_peak = max(self.memory_samples)
                self.memory_samples.clear()
            
            # 메트릭 저장
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_peak=memory_peak,
                cpu_percent=(cpu_before + cpu_after) / 2,
                success=success,
                error_message=error_message
            )
            
            self._store_metrics(metrics)
            self._check_performance_thresholds(metrics)
            
        return result
    
    async def _measure_async_operation(self, operation_name: str, func: Callable, *args, **kwargs) -> Any:
        """비동기 작업 성능 측정"""
        start_time = time.time()
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024
        
        success = True
        error_message = None
        result = None
        
        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Async operation {operation_name} failed: {error_message}")
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            memory_after = process.memory_info().rss / 1024 / 1024
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_peak=memory_after,  # 비동기에서는 간단히 처리
                cpu_percent=process.cpu_percent(),
                success=success,
                error_message=error_message
            )
            
            self._store_metrics(metrics)
            
        return result
    
    def _monitor_memory_usage(self, process: psutil.Process):
        """메모리 사용량 실시간 모니터링"""
        try:
            while True:
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.memory_samples.append(memory_mb)
                time.sleep(0.1)  # 100ms 간격으로 샘플링
        except:
            pass  # 프로세스 종료 시 예외 무시
    
    def _store_metrics(self, metrics: PerformanceMetrics):
        """메트릭 저장"""
        with self._lock:
            self.metrics_history.append(metrics)
            self.operation_stats[metrics.operation_name].append(metrics.duration)
    
    def _check_performance_thresholds(self, metrics: PerformanceMetrics):
        """성능 임계값 확인 및 경고"""
        warnings = []
        
        if metrics.duration > self.thresholds['operation_duration']:
            warnings.append(f"Operation duration ({metrics.duration:.2f}s) exceeds threshold")
        
        if metrics.memory_peak > self.thresholds['memory_usage_mb']:
            warnings.append(f"Memory usage ({metrics.memory_peak:.2f}MB) exceeds threshold")
        
        if metrics.cpu_percent > self.thresholds['cpu_usage_percent']:
            warnings.append(f"CPU usage ({metrics.cpu_percent:.1f}%) exceeds threshold")
        
        if warnings:
            logger.warning(f"Performance warnings for {metrics.operation_name}: {'; '.join(warnings)}")
    
    def record_api_call(self, endpoint: str, method: str, response_time: float, 
                       status_code: int, payload_size: int = 0, response_size: int = 0,
                       retry_count: int = 0):
        """API 호출 메트릭 기록"""
        api_metrics = APICallMetrics(
            endpoint=endpoint,
            method=method,
            response_time=response_time,
            status_code=status_code,
            payload_size=payload_size,
            response_size=response_size,
            timestamp=datetime.now(),
            success=200 <= status_code < 300,
            retry_count=retry_count
        )
        
        with self._lock:
            self.api_metrics.append(api_metrics)
        
        # API 응답 시간 임계값 확인
        if response_time > self.thresholds['api_response_time']:
            logger.warning(f"API call to {endpoint} took {response_time:.2f}s (exceeds {self.thresholds['api_response_time']}s threshold)")
    
    def get_operation_statistics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """작업별 통계 조회"""
        with self._lock:
            if operation_name:
                durations = self.operation_stats.get(operation_name, [])
                if not durations:
                    return {"error": f"No data for operation: {operation_name}"}
                
                return {
                    "operation_name": operation_name,
                    "total_calls": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "total_duration": sum(durations)
                }
            else:
                # 모든 작업 통계
                stats = {}
                for op_name, durations in self.operation_stats.items():
                    if durations:
                        stats[op_name] = {
                            "total_calls": len(durations),
                            "avg_duration": sum(durations) / len(durations),
                            "min_duration": min(durations),
                            "max_duration": max(durations),
                            "total_duration": sum(durations)
                        }
                return stats
    
    def get_api_statistics(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """API 호출 통계 조회"""
        with self._lock:
            api_calls = list(self.api_metrics)
            
            if endpoint:
                api_calls = [call for call in api_calls if call.endpoint == endpoint]
            
            if not api_calls:
                return {"error": "No API call data available"}
            
            response_times = [call.response_time for call in api_calls]
            success_calls = [call for call in api_calls if call.success]
            
            return {
                "total_calls": len(api_calls),
                "successful_calls": len(success_calls),
                "success_rate": len(success_calls) / len(api_calls) * 100,
                "avg_response_time": sum(response_times) / len(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "calls_exceeding_threshold": len([t for t in response_times if t > self.thresholds['api_response_time']])
            }
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """메모리 사용 통계"""
        with self._lock:
            if not self.metrics_history:
                return {"error": "No performance data available"}
            
            memory_usage = [m.memory_used for m in self.metrics_history]
            memory_peaks = [m.memory_peak for m in self.metrics_history]
            
            return {
                "avg_memory_usage": sum(memory_usage) / len(memory_usage),
                "max_memory_usage": max(memory_usage),
                "min_memory_usage": min(memory_usage),
                "avg_memory_peak": sum(memory_peaks) / len(memory_peaks),
                "max_memory_peak": max(memory_peaks),
                "current_memory": psutil.Process().memory_info().rss / 1024 / 1024
            }
    
    def optimize_memory(self):
        """메모리 최적화 수행"""
        logger.info("Starting memory optimization...")
        
        # 가비지 컬렉션 강제 실행
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
        
        # 메트릭 히스토리 정리 (오래된 데이터 제거)
        current_time = time.time()
        cutoff_time = current_time - 3600  # 1시간 이전 데이터 제거
        
        with self._lock:
            # 성능 메트릭 정리
            self.metrics_history = deque(
                [m for m in self.metrics_history if m.end_time > cutoff_time],
                maxlen=self.max_history
            )
            
            # API 메트릭 정리
            cutoff_datetime = datetime.now() - timedelta(hours=1)
            self.api_metrics = deque(
                [m for m in self.api_metrics if m.timestamp > cutoff_datetime],
                maxlen=self.max_history
            )
        
        # 현재 메모리 사용량 확인
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(f"Memory optimization completed. Current memory usage: {current_memory:.2f}MB")
        
        return {
            "objects_collected": collected,
            "current_memory_mb": current_memory,
            "metrics_count": len(self.metrics_history),
            "api_metrics_count": len(self.api_metrics)
        }
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """종합 성능 리포트 생성"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "memory_available_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024,
                "cpu_percent": psutil.cpu_percent(interval=1)
            },
            "operation_statistics": self.get_operation_statistics(),
            "api_statistics": self.get_api_statistics(),
            "memory_statistics": self.get_memory_statistics(),
            "performance_thresholds": self.thresholds,
            "total_metrics_recorded": len(self.metrics_history)
        }
    
    def set_threshold(self, metric_name: str, value: float):
        """성능 임계값 설정"""
        if metric_name in self.thresholds:
            self.thresholds[metric_name] = value
            logger.info(f"Updated threshold for {metric_name}: {value}")
        else:
            logger.warning(f"Unknown threshold metric: {metric_name}")
    
    def clear_metrics(self):
        """모든 메트릭 데이터 초기화"""
        with self._lock:
            self.metrics_history.clear()
            self.api_metrics.clear()
            self.operation_stats.clear()
            self.memory_samples.clear()
        logger.info("All performance metrics cleared")


# 전역 성능 모니터 인스턴스
performance_monitor = PerformanceMonitor()


# 편의 함수들
def measure_performance(operation_name: str):
    """성능 측정 데코레이터 (전역 모니터 사용)"""
    return performance_monitor.measure_performance(operation_name)


def measure_async_performance(operation_name: str):
    """비동기 성능 측정 데코레이터 (전역 모니터 사용)"""
    return performance_monitor.measure_async_performance(operation_name)


def record_api_call(endpoint: str, method: str, response_time: float, status_code: int, **kwargs):
    """API 호출 기록 (전역 모니터 사용)"""
    return performance_monitor.record_api_call(endpoint, method, response_time, status_code, **kwargs)


def get_performance_report():
    """성능 리포트 조회 (전역 모니터 사용)"""
    return performance_monitor.generate_performance_report()


def optimize_memory():
    """메모리 최적화 (전역 모니터 사용)"""
    return performance_monitor.optimize_memory()