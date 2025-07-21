"""
성능 모니터링 시스템 테스트

이 모듈은 성능 측정 및 최적화 기능을 테스트합니다.
"""

import unittest
import time
import asyncio
import threading
from unittest.mock import patch, MagicMock
from performance_monitor import (
    PerformanceMonitor, PerformanceMetrics, APICallMetrics,
    measure_performance, measure_async_performance, 
    record_api_call, get_performance_report, optimize_memory
)


class TestPerformanceMetrics(unittest.TestCase):
    """PerformanceMetrics 클래스 테스트"""
    
    def test_performance_metrics_creation(self):
        """성능 메트릭 생성 테스트"""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=1000.0,
            end_time=1001.5,
            duration=1.5,
            memory_before=100.0,
            memory_after=120.0,
            memory_peak=125.0,
            cpu_percent=50.0,
            success=True
        )
        
        self.assertEqual(metrics.operation_name, "test_operation")
        self.assertEqual(metrics.duration, 1.5)
        self.assertEqual(metrics.memory_used, 20.0)
        self.assertTrue(metrics.success)
    
    def test_metrics_to_dict(self):
        """메트릭 딕셔너리 변환 테스트"""
        metrics = PerformanceMetrics(
            operation_name="test_operation",
            start_time=1000.0,
            end_time=1001.5,
            duration=1.5,
            memory_before=100.0,
            memory_after=120.0,
            memory_peak=125.0,
            cpu_percent=50.0,
            success=True
        )
        
        result = metrics.to_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result['operation_name'], "test_operation")
        self.assertEqual(result['memory_used'], 20.0)


class TestPerformanceMonitor(unittest.TestCase):
    """PerformanceMonitor 클래스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.monitor = PerformanceMonitor(max_history=100)
    
    def test_monitor_initialization(self):
        """모니터 초기화 테스트"""
        self.assertEqual(self.monitor.max_history, 100)
        self.assertEqual(len(self.monitor.metrics_history), 0)
        self.assertEqual(len(self.monitor.api_metrics), 0)
        self.assertIn('api_response_time', self.monitor.thresholds)
    
    @patch('psutil.Process')
    def test_sync_performance_measurement(self, mock_process):
        """동기 성능 측정 테스트"""
        # Mock 설정
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        mock_process_instance.cpu_percent.return_value = 50.0
        
        @self.monitor.measure_performance("test_operation")
        def test_function():
            time.sleep(0.1)  # 100ms 대기
            return "test_result"
        
        result = test_function()
        
        self.assertEqual(result, "test_result")
        self.assertEqual(len(self.monitor.metrics_history), 1)
        
        metrics = self.monitor.metrics_history[0]
        self.assertEqual(metrics.operation_name, "test_operation")
        self.assertTrue(metrics.success)
        self.assertGreaterEqual(metrics.duration, 0.1)
    
    @patch('psutil.Process')
    def test_sync_performance_measurement_with_exception(self, mock_process):
        """예외 발생 시 성능 측정 테스트"""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_instance.cpu_percent.return_value = 50.0
        
        @self.monitor.measure_performance("test_operation_error")
        def test_function_with_error():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            test_function_with_error()
        
        self.assertEqual(len(self.monitor.metrics_history), 1)
        metrics = self.monitor.metrics_history[0]
        self.assertFalse(metrics.success)
        self.assertEqual(metrics.error_message, "Test error")
    
    @patch('psutil.Process')
    def test_async_performance_measurement(self, mock_process):
        """비동기 성능 측정 테스트"""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_instance.cpu_percent.return_value = 50.0
        
        @self.monitor.measure_async_performance("async_test_operation")
        async def async_test_function():
            await asyncio.sleep(0.1)
            return "async_result"
        
        async def run_test():
            result = await async_test_function()
            return result
        
        result = asyncio.run(run_test())
        
        self.assertEqual(result, "async_result")
        self.assertEqual(len(self.monitor.metrics_history), 1)
        
        metrics = self.monitor.metrics_history[0]
        self.assertEqual(metrics.operation_name, "async_test_operation")
        self.assertTrue(metrics.success)
    
    def test_api_call_recording(self):
        """API 호출 기록 테스트"""
        self.monitor.record_api_call(
            endpoint="/api/food/search",
            method="GET",
            response_time=1.5,
            status_code=200,
            payload_size=100,
            response_size=500
        )
        
        self.assertEqual(len(self.monitor.api_metrics), 1)
        
        api_metric = self.monitor.api_metrics[0]
        self.assertEqual(api_metric.endpoint, "/api/food/search")
        self.assertEqual(api_metric.method, "GET")
        self.assertEqual(api_metric.response_time, 1.5)
        self.assertEqual(api_metric.status_code, 200)
        self.assertTrue(api_metric.success)
    
    def test_operation_statistics(self):
        """작업 통계 테스트"""
        # 테스트 데이터 추가
        self.monitor.operation_stats["test_op"] = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        stats = self.monitor.get_operation_statistics("test_op")
        
        self.assertEqual(stats["operation_name"], "test_op")
        self.assertEqual(stats["total_calls"], 5)
        self.assertEqual(stats["avg_duration"], 3.0)
        self.assertEqual(stats["min_duration"], 1.0)
        self.assertEqual(stats["max_duration"], 5.0)
        self.assertEqual(stats["total_duration"], 15.0)
    
    def test_api_statistics(self):
        """API 통계 테스트"""
        # 테스트 API 호출 데이터 추가
        from datetime import datetime
        
        for i in range(5):
            api_metric = APICallMetrics(
                endpoint="/api/test",
                method="GET",
                response_time=1.0 + i * 0.5,
                status_code=200,
                payload_size=100,
                response_size=200,
                timestamp=datetime.now(),
                success=True
            )
            self.monitor.api_metrics.append(api_metric)
        
        stats = self.monitor.get_api_statistics("/api/test")
        
        self.assertEqual(stats["total_calls"], 5)
        self.assertEqual(stats["successful_calls"], 5)
        self.assertEqual(stats["success_rate"], 100.0)
        self.assertEqual(stats["avg_response_time"], 3.0)  # (1.0+1.5+2.0+2.5+3.0)/5
        self.assertEqual(stats["min_response_time"], 1.0)
        self.assertEqual(stats["max_response_time"], 3.0)
    
    @patch('psutil.Process')
    def test_memory_statistics(self, mock_process):
        """메모리 통계 테스트"""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024
        
        # 테스트 메트릭 추가
        for i in range(3):
            metrics = PerformanceMetrics(
                operation_name=f"test_op_{i}",
                start_time=1000.0,
                end_time=1001.0,
                duration=1.0,
                memory_before=100.0 + i * 10,
                memory_after=120.0 + i * 10,
                memory_peak=125.0 + i * 10,
                cpu_percent=50.0,
                success=True
            )
            self.monitor.metrics_history.append(metrics)
        
        stats = self.monitor.get_memory_statistics()
        
        self.assertEqual(stats["avg_memory_usage"], 20.0)  # (20+20+20)/3
        self.assertEqual(stats["max_memory_usage"], 20.0)
        self.assertEqual(stats["min_memory_usage"], 20.0)
        self.assertIn("current_memory", stats)
    
    def test_threshold_setting(self):
        """임계값 설정 테스트"""
        original_threshold = self.monitor.thresholds['api_response_time']
        
        self.monitor.set_threshold('api_response_time', 5.0)
        self.assertEqual(self.monitor.thresholds['api_response_time'], 5.0)
        
        # 존재하지 않는 메트릭
        self.monitor.set_threshold('nonexistent_metric', 10.0)
        self.assertNotIn('nonexistent_metric', self.monitor.thresholds)
    
    @patch('gc.collect')
    def test_memory_optimization(self, mock_gc_collect):
        """메모리 최적화 테스트"""
        mock_gc_collect.return_value = 42  # 수집된 객체 수
        
        # 테스트 데이터 추가
        for i in range(10):
            metrics = PerformanceMetrics(
                operation_name=f"old_op_{i}",
                start_time=1000.0 - 7200,  # 2시간 전
                end_time=1001.0 - 7200,
                duration=1.0,
                memory_before=100.0,
                memory_after=120.0,
                memory_peak=125.0,
                cpu_percent=50.0,
                success=True
            )
            self.monitor.metrics_history.append(metrics)
        
        result = self.monitor.optimize_memory()
        
        self.assertEqual(result["objects_collected"], 42)
        self.assertIn("current_memory_mb", result)
        mock_gc_collect.assert_called_once()
    
    def test_performance_report_generation(self):
        """성능 리포트 생성 테스트"""
        # 테스트 데이터 추가
        self.monitor.operation_stats["test_op"] = [1.0, 2.0, 3.0]
        
        report = self.monitor.generate_performance_report()
        
        self.assertIn("timestamp", report)
        self.assertIn("system_info", report)
        self.assertIn("operation_statistics", report)
        self.assertIn("api_statistics", report)
        self.assertIn("memory_statistics", report)
        self.assertIn("performance_thresholds", report)
        self.assertIn("total_metrics_recorded", report)
    
    def test_clear_metrics(self):
        """메트릭 초기화 테스트"""
        # 테스트 데이터 추가
        self.monitor.operation_stats["test_op"] = [1.0, 2.0, 3.0]
        metrics = PerformanceMetrics(
            operation_name="test_op",
            start_time=1000.0,
            end_time=1001.0,
            duration=1.0,
            memory_before=100.0,
            memory_after=120.0,
            memory_peak=125.0,
            cpu_percent=50.0,
            success=True
        )
        self.monitor.metrics_history.append(metrics)
        
        self.monitor.clear_metrics()
        
        self.assertEqual(len(self.monitor.metrics_history), 0)
        self.assertEqual(len(self.monitor.api_metrics), 0)
        self.assertEqual(len(self.monitor.operation_stats), 0)


class TestGlobalFunctions(unittest.TestCase):
    """전역 함수 테스트"""
    
    @patch('psutil.Process')
    def test_global_measure_performance(self, mock_process):
        """전역 성능 측정 함수 테스트"""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_instance.cpu_percent.return_value = 50.0
        
        @measure_performance("global_test")
        def test_function():
            return "global_result"
        
        result = test_function()
        self.assertEqual(result, "global_result")
    
    def test_global_record_api_call(self):
        """전역 API 호출 기록 함수 테스트"""
        record_api_call("/api/test", "GET", 1.5, 200)
        # 전역 모니터에 기록되었는지 확인은 실제 구현에서 수행
    
    def test_global_get_performance_report(self):
        """전역 성능 리포트 함수 테스트"""
        report = get_performance_report()
        self.assertIsInstance(report, dict)
        self.assertIn("timestamp", report)
    
    @patch('gc.collect')
    def test_global_optimize_memory(self, mock_gc_collect):
        """전역 메모리 최적화 함수 테스트"""
        mock_gc_collect.return_value = 10
        result = optimize_memory()
        self.assertIsInstance(result, dict)
        self.assertIn("objects_collected", result)


class TestPerformanceIntegration(unittest.TestCase):
    """통합 성능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.monitor = PerformanceMonitor()
    
    @patch('psutil.Process')
    def test_batch_data_processing_performance(self, mock_process):
        """대량 데이터 처리 성능 테스트"""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_process_instance.cpu_percent.return_value = 50.0
        
        @self.monitor.measure_performance("batch_processing")
        def process_batch_data(data_size: int):
            # 대량 데이터 처리 시뮬레이션
            data = list(range(data_size))
            processed = [x * 2 for x in data]
            return len(processed)
        
        # 다양한 크기의 배치 처리 테스트
        sizes = [1000, 5000, 10000]
        results = []
        
        for size in sizes:
            result = process_batch_data(size)
            results.append(result)
        
        # 성능 통계 확인
        stats = self.monitor.get_operation_statistics("batch_processing")
        self.assertEqual(stats["total_calls"], 3)
        self.assertGreater(stats["avg_duration"], 0)
        
        # 모든 처리가 성공했는지 확인
        for metrics in self.monitor.metrics_history:
            if metrics.operation_name == "batch_processing":
                self.assertTrue(metrics.success)
    
    def test_api_call_optimization_simulation(self):
        """API 호출 최적화 시뮬레이션 테스트"""
        # 최적화 전 - 느린 API 호출들
        slow_calls = [
            ("/api/food/search", "GET", 4.5, 200),
            ("/api/food/search", "GET", 3.8, 200),
            ("/api/exercise/search", "GET", 5.2, 200),
        ]
        
        for endpoint, method, response_time, status_code in slow_calls:
            self.monitor.record_api_call(endpoint, method, response_time, status_code)
        
        # 최적화 후 - 빠른 API 호출들
        fast_calls = [
            ("/api/food/search", "GET", 1.2, 200),
            ("/api/food/search", "GET", 0.8, 200),
            ("/api/exercise/search", "GET", 1.5, 200),
        ]
        
        for endpoint, method, response_time, status_code in fast_calls:
            self.monitor.record_api_call(endpoint, method, response_time, status_code)
        
        # 통계 확인
        stats = self.monitor.get_api_statistics()
        self.assertEqual(stats["total_calls"], 6)
        self.assertEqual(stats["success_rate"], 100.0)
        
        # 임계값 초과 호출 확인
        self.assertEqual(stats["calls_exceeding_threshold"], 3)  # 처음 3개 호출
    
    @patch('psutil.Process')
    def test_memory_usage_monitoring(self, mock_process):
        """메모리 사용량 모니터링 테스트"""
        mock_process_instance = MagicMock()
        mock_process.return_value = mock_process_instance
        
        # 메모리 사용량이 점진적으로 증가하는 시뮬레이션
        memory_values = [100, 150, 200, 180, 160]  # MB
        memory_iter = iter(memory_values)
        
        def mock_memory_info():
            mock_info = MagicMock()
            mock_info.rss = next(memory_iter, 160) * 1024 * 1024
            return mock_info
        
        mock_process_instance.memory_info = mock_memory_info
        mock_process_instance.cpu_percent.return_value = 50.0
        
        @self.monitor.measure_performance("memory_intensive_task")
        def memory_intensive_task():
            # 메모리 집약적 작업 시뮬레이션
            large_list = [i for i in range(10000)]
            return len(large_list)
        
        # 여러 번 실행하여 메모리 패턴 확인
        for _ in range(3):
            memory_intensive_task()
        
        # 메모리 통계 확인
        memory_stats = self.monitor.get_memory_statistics()
        self.assertIn("avg_memory_usage", memory_stats)
        self.assertIn("max_memory_usage", memory_stats)
        self.assertIn("current_memory", memory_stats)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)