"""
API 호출 최적화 모듈

이 모듈은 API 호출을 최적화하여 성능을 향상시킵니다.
- 요청 배치 처리
- 지연 시간 조절
- 재시도 로직
- 연결 풀링
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from performance_monitor import performance_monitor

logger = logging.getLogger(__name__)


@dataclass
class APIRequest:
    """API 요청 데이터 클래스"""
    endpoint: str
    method: str = "GET"
    params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    data: Optional[Dict[str, Any]] = None
    timeout: float = 30.0
    priority: int = 1  # 1=높음, 2=보통, 3=낮음
    callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class APIResponse:
    """API 응답 데이터 클래스"""
    request: APIRequest
    status_code: int
    data: Any
    response_time: float
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0


class RateLimiter:
    """API 호출 속도 제한기"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """호출 허용 여부 확인"""
        with self._lock:
            now = time.time()
            
            # 시간 윈도우 밖의 호출 기록 제거
            while self.calls and self.calls[0] <= now - self.time_window:
                self.calls.popleft()
            
            # 호출 한도 확인
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            
            return False
    
    def wait_time(self) -> float:
        """다음 호출까지 대기 시간"""
        with self._lock:
            if not self.calls:
                return 0.0
            
            oldest_call = self.calls[0]
            wait_time = self.time_window - (time.time() - oldest_call)
            return max(0.0, wait_time)


class ConnectionPool:
    """HTTP 연결 풀 관리"""
    
    def __init__(self, pool_size: int = 10, max_retries: int = 3):
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """최적화된 세션 생성"""
        session = requests.Session()
        
        # 재시도 전략 설정
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        # HTTP 어댑터 설정
        adapter = HTTPAdapter(
            pool_connections=self.pool_size,
            pool_maxsize=self.pool_size,
            max_retries=retry_strategy
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def close(self):
        """연결 풀 종료"""
        if self.session:
            self.session.close()


class APIOptimizer:
    """API 호출 최적화 관리자"""
    
    def __init__(self, 
                 max_concurrent_requests: int = 5,
                 rate_limit_calls: int = 100,
                 rate_limit_window: float = 60.0,
                 batch_size: int = 10,
                 batch_timeout: float = 1.0):
        
        self.max_concurrent_requests = max_concurrent_requests
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # 요청 큐 (우선순위별)
        self.request_queues = {
            1: deque(),  # 높은 우선순위
            2: deque(),  # 보통 우선순위
            3: deque()   # 낮은 우선순위
        }
        
        # 배치 처리 큐
        self.batch_queue = deque()
        self.batch_timer = None
        
        # 속도 제한기
        self.rate_limiter = RateLimiter(rate_limit_calls, rate_limit_window)
        
        # 연결 풀
        self.connection_pool = ConnectionPool()
        
        # 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_requests)
        
        # 통계
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'batched_requests': 0,
            'rate_limited_requests': 0,
            'avg_response_time': 0.0
        }
        
        self._lock = threading.Lock()
        self._running = False
        self._worker_thread = None
    
    def start(self):
        """최적화 엔진 시작"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._process_requests, daemon=True)
            self._worker_thread.start()
            logger.info("API Optimizer started")
    
    def stop(self):
        """최적화 엔진 중지"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
        
        self.executor.shutdown(wait=True)
        self.connection_pool.close()
        logger.info("API Optimizer stopped")
    
    def add_request(self, request: APIRequest) -> str:
        """요청 추가"""
        request_id = f"{request.endpoint}_{int(time.time() * 1000)}"
        
        with self._lock:
            self.request_queues[request.priority].append((request_id, request))
            self.stats['total_requests'] += 1
        
        logger.debug(f"Added request {request_id} with priority {request.priority}")
        return request_id
    
    def add_batch_request(self, requests: List[APIRequest]) -> List[str]:
        """배치 요청 추가"""
        request_ids = []
        
        with self._lock:
            for request in requests:
                request_id = f"batch_{request.endpoint}_{int(time.time() * 1000)}"
                self.batch_queue.append((request_id, request))
                request_ids.append(request_id)
                self.stats['batched_requests'] += 1
        
        # 배치 타이머 시작
        if not self.batch_timer or not self.batch_timer.is_alive():
            self.batch_timer = threading.Timer(self.batch_timeout, self._process_batch)
            self.batch_timer.start()
        
        return request_ids
    
    def _process_requests(self):
        """요청 처리 워커"""
        while self._running:
            try:
                # 우선순위 순으로 요청 처리
                request_item = None
                
                with self._lock:
                    for priority in [1, 2, 3]:
                        if self.request_queues[priority]:
                            request_item = self.request_queues[priority].popleft()
                            break
                
                if request_item:
                    request_id, request = request_item
                    self._execute_request(request_id, request)
                else:
                    time.sleep(0.1)  # 요청이 없으면 잠시 대기
                    
            except Exception as e:
                logger.error(f"Error in request processing: {e}")
    
    def _execute_request(self, request_id: str, request: APIRequest):
        """개별 요청 실행"""
        # 속도 제한 확인
        if not self.rate_limiter.acquire():
            wait_time = self.rate_limiter.wait_time()
            if wait_time > 0:
                logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                self.stats['rate_limited_requests'] += 1
                
                # 재시도
                if self.rate_limiter.acquire():
                    pass
                else:
                    logger.warning(f"Request {request_id} dropped due to rate limiting")
                    return
        
        # 요청 실행
        future = self.executor.submit(self._make_http_request, request)
        
        try:
            response = future.result(timeout=request.timeout)
            self._handle_response(request_id, request, response)
        except Exception as e:
            logger.error(f"Request {request_id} failed: {e}")
            self.stats['failed_requests'] += 1
    
    @performance_monitor.measure_performance("api_http_request")
    def _make_http_request(self, request: APIRequest) -> APIResponse:
        """HTTP 요청 실행"""
        start_time = time.time()
        
        try:
            if request.method.upper() == "GET":
                response = self.connection_pool.session.get(
                    request.endpoint,
                    params=request.params,
                    headers=request.headers,
                    timeout=request.timeout
                )
            elif request.method.upper() == "POST":
                response = self.connection_pool.session.post(
                    request.endpoint,
                    json=request.data,
                    params=request.params,
                    headers=request.headers,
                    timeout=request.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {request.method}")
            
            response_time = time.time() - start_time
            
            # 성능 메트릭 기록
            performance_monitor.record_api_call(
                endpoint=request.endpoint,
                method=request.method,
                response_time=response_time,
                status_code=response.status_code,
                payload_size=len(str(request.data)) if request.data else 0,
                response_size=len(response.content) if response.content else 0
            )
            
            return APIResponse(
                request=request,
                status_code=response.status_code,
                data=response.json() if response.content else None,
                response_time=response_time,
                success=200 <= response.status_code < 300
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return APIResponse(
                request=request,
                status_code=0,
                data=None,
                response_time=response_time,
                success=False,
                error_message=str(e)
            )
    
    def _handle_response(self, request_id: str, request: APIRequest, response: APIResponse):
        """응답 처리"""
        if response.success:
            self.stats['successful_requests'] += 1
            logger.debug(f"Request {request_id} completed successfully in {response.response_time:.2f}s")
        else:
            self.stats['failed_requests'] += 1
            logger.warning(f"Request {request_id} failed: {response.error_message}")
        
        # 평균 응답 시간 업데이트
        total_requests = self.stats['successful_requests'] + self.stats['failed_requests']
        if total_requests > 0:
            self.stats['avg_response_time'] = (
                (self.stats['avg_response_time'] * (total_requests - 1) + response.response_time) / total_requests
            )
        
        # 콜백 실행
        if request.callback:
            try:
                request.callback(response)
            except Exception as e:
                logger.error(f"Callback error for request {request_id}: {e}")
    
    def _process_batch(self):
        """배치 요청 처리"""
        batch_requests = []
        
        with self._lock:
            while self.batch_queue and len(batch_requests) < self.batch_size:
                batch_requests.append(self.batch_queue.popleft())
        
        if batch_requests:
            logger.info(f"Processing batch of {len(batch_requests)} requests")
            
            # 배치 요청을 개별 요청으로 변환하여 처리
            for request_id, request in batch_requests:
                self._execute_request(request_id, request)
    
    async def async_request(self, request: APIRequest) -> APIResponse:
        """비동기 요청 실행"""
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            
            try:
                if request.method.upper() == "GET":
                    async with session.get(
                        request.endpoint,
                        params=request.params,
                        headers=request.headers,
                        timeout=aiohttp.ClientTimeout(total=request.timeout)
                    ) as response:
                        data = await response.json() if response.content_type == 'application/json' else await response.text()
                        
                elif request.method.upper() == "POST":
                    async with session.post(
                        request.endpoint,
                        json=request.data,
                        params=request.params,
                        headers=request.headers,
                        timeout=aiohttp.ClientTimeout(total=request.timeout)
                    ) as response:
                        data = await response.json() if response.content_type == 'application/json' else await response.text()
                else:
                    raise ValueError(f"Unsupported HTTP method: {request.method}")
                
                response_time = time.time() - start_time
                
                return APIResponse(
                    request=request,
                    status_code=response.status,
                    data=data,
                    response_time=response_time,
                    success=200 <= response.status < 300
                )
                
            except Exception as e:
                response_time = time.time() - start_time
                return APIResponse(
                    request=request,
                    status_code=0,
                    data=None,
                    response_time=response_time,
                    success=False,
                    error_message=str(e)
                )
    
    async def async_batch_request(self, requests: List[APIRequest]) -> List[APIResponse]:
        """비동기 배치 요청"""
        tasks = [self.async_request(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                processed_responses.append(APIResponse(
                    request=requests[i],
                    status_code=0,
                    data=None,
                    response_time=0.0,
                    success=False,
                    error_message=str(response)
                ))
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 조회"""
        with self._lock:
            queue_sizes = {
                f"priority_{priority}_queue": len(queue) 
                for priority, queue in self.request_queues.items()
            }
            
            return {
                **self.stats,
                "batch_queue_size": len(self.batch_queue),
                "rate_limiter_calls": len(self.rate_limiter.calls),
                "rate_limiter_wait_time": self.rate_limiter.wait_time(),
                **queue_sizes,
                "is_running": self._running
            }
    
    def optimize_settings(self, response_times: List[float], error_rates: List[float]):
        """설정 자동 최적화"""
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        avg_error_rate = sum(error_rates) / len(error_rates) if error_rates else 0
        
        # 응답 시간이 느리면 동시 요청 수 줄이기
        if avg_response_time > 5.0:
            self.max_concurrent_requests = max(1, self.max_concurrent_requests - 1)
            logger.info(f"Reduced concurrent requests to {self.max_concurrent_requests}")
        
        # 오류율이 높으면 속도 제한 강화
        if avg_error_rate > 0.1:  # 10% 이상
            current_limit = self.rate_limiter.max_calls
            new_limit = max(10, int(current_limit * 0.8))
            self.rate_limiter = RateLimiter(new_limit, self.rate_limiter.time_window)
            logger.info(f"Reduced rate limit to {new_limit} calls per {self.rate_limiter.time_window}s")
        
        # 성능이 좋으면 설정 완화
        if avg_response_time < 1.0 and avg_error_rate < 0.01:
            self.max_concurrent_requests = min(20, self.max_concurrent_requests + 1)
            logger.info(f"Increased concurrent requests to {self.max_concurrent_requests}")


# 전역 API 최적화 인스턴스
api_optimizer = APIOptimizer()


# 편의 함수들
def optimize_api_call(endpoint: str, method: str = "GET", **kwargs) -> str:
    """최적화된 API 호출"""
    request = APIRequest(endpoint=endpoint, method=method, **kwargs)
    return api_optimizer.add_request(request)


def optimize_batch_calls(requests_data: List[Dict[str, Any]]) -> List[str]:
    """최적화된 배치 API 호출"""
    requests = [APIRequest(**data) for data in requests_data]
    return api_optimizer.add_batch_request(requests)


async def async_optimize_call(endpoint: str, method: str = "GET", **kwargs) -> APIResponse:
    """비동기 최적화 API 호출"""
    request = APIRequest(endpoint=endpoint, method=method, **kwargs)
    return await api_optimizer.async_request(request)


def get_api_optimizer_stats() -> Dict[str, Any]:
    """API 최적화 통계 조회"""
    return api_optimizer.get_statistics()


def start_api_optimizer():
    """API 최적화 엔진 시작"""
    api_optimizer.start()


def stop_api_optimizer():
    """API 최적화 엔진 중지"""
    api_optimizer.stop()