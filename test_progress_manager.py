"""
진행 상황 표시 기능 테스트

이 모듈은 진행률 관리 및 표시 기능을 테스트합니다.
"""

import unittest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from progress_manager import (
    ProgressManager, TaskProgress, TaskStatus, ProgressStyle, ProgressDisplay,
    create_progress_task, start_progress_task, update_progress, 
    increment_progress, complete_progress_task, cancel_progress_task,
    is_task_cancelled, progress_context
)


class TestTaskProgress(unittest.TestCase):
    """TaskProgress 클래스 테스트"""
    
    def test_task_progress_creation(self):
        """작업 진행 상황 생성 테스트"""
        progress = TaskProgress(
            task_id="test_task",
            name="Test Task",
            total_items=100
        )
        
        self.assertEqual(progress.task_id, "test_task")
        self.assertEqual(progress.name, "Test Task")
        self.assertEqual(progress.total_items, 100)
        self.assertEqual(progress.completed_items, 0)
        self.assertEqual(progress.status, TaskStatus.PENDING)
        self.assertEqual(progress.progress_percentage, 0.0)
    
    def test_progress_percentage_calculation(self):
        """진행률 백분율 계산 테스트"""
        progress = TaskProgress("test", "Test", 100)
        
        progress.completed_items = 25
        self.assertEqual(progress.progress_percentage, 25.0)
        
        progress.completed_items = 50
        self.assertEqual(progress.progress_percentage, 50.0)
        
        progress.completed_items = 100
        self.assertEqual(progress.progress_percentage, 100.0)
    
    def test_time_calculations(self):
        """시간 계산 테스트"""
        progress = TaskProgress("test", "Test", 100)
        progress.start_time = datetime.now() - timedelta(seconds=10)
        progress.completed_items = 50
        
        # 경과 시간 확인
        elapsed = progress.elapsed_time
        self.assertGreaterEqual(elapsed.total_seconds(), 9)
        self.assertLessEqual(elapsed.total_seconds(), 11)
        
        # 초당 처리량 확인
        rate = progress.items_per_second
        self.assertGreater(rate, 4)
        self.assertLess(rate, 6)
        
        # 예상 남은 시간 확인
        eta = progress.estimated_remaining_time
        self.assertGreater(eta.total_seconds(), 8)
        self.assertLess(eta.total_seconds(), 12)
    
    def test_to_dict_conversion(self):
        """딕셔너리 변환 테스트"""
        progress = TaskProgress("test", "Test Task", 100)
        progress.completed_items = 25
        progress.start_time = datetime.now()
        
        result = progress.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['task_id'], "test")
        self.assertEqual(result['name'], "Test Task")
        self.assertEqual(result['total_items'], 100)
        self.assertEqual(result['completed_items'], 25)
        self.assertEqual(result['progress_percentage'], 25.0)
        self.assertIn('start_time', result)


class TestProgressDisplay(unittest.TestCase):
    """ProgressDisplay 클래스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.progress = TaskProgress("test", "Test Task", 100)
        self.progress.completed_items = 50
        self.progress.start_time = datetime.now() - timedelta(seconds=10)
        self.progress.current_operation = "Processing data"
    
    def test_bar_style_display(self):
        """바 스타일 표시 테스트"""
        display = ProgressDisplay(ProgressStyle.BAR, width=20)
        result = display.format_progress(self.progress)
        
        self.assertIn("[", result)
        self.assertIn("]", result)
        self.assertIn("50.0%", result)
        self.assertIn("█", result)
        self.assertIn("░", result)
    
    def test_percentage_style_display(self):
        """백분율 스타일 표시 테스트"""
        display = ProgressDisplay(ProgressStyle.PERCENTAGE)
        result = display.format_progress(self.progress)
        
        self.assertEqual(result, "50.0%")
    
    def test_spinner_style_display(self):
        """스피너 스타일 표시 테스트"""
        display = ProgressDisplay(ProgressStyle.SPINNER)
        result = display.format_progress(self.progress)
        
        self.assertIn("Processing data", result)
        # 스피너 문자 중 하나가 포함되어야 함
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.assertTrue(any(char in result for char in spinner_chars))
    
    def test_detailed_style_display(self):
        """상세 스타일 표시 테스트"""
        display = ProgressDisplay(ProgressStyle.DETAILED)
        result = display.format_progress(self.progress)
        
        self.assertIn("50.0%", result)
        self.assertIn("(50/100)", result)
        self.assertIn("Rate:", result)
        self.assertIn("ETA:", result)
        self.assertIn("Elapsed:", result)


class TestProgressManager(unittest.TestCase):
    """ProgressManager 클래스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.manager = ProgressManager(update_interval=0.1)
    
    def tearDown(self):
        """테스트 정리"""
        self.manager.stop()
    
    def test_create_task(self):
        """작업 생성 테스트"""
        task = self.manager.create_task("test_task", "Test Task", 100)
        
        self.assertIsInstance(task, TaskProgress)
        self.assertEqual(task.task_id, "test_task")
        self.assertEqual(task.name, "Test Task")
        self.assertEqual(task.total_items, 100)
        self.assertEqual(task.status, TaskStatus.PENDING)
        
        # 관리자에 등록되었는지 확인
        self.assertIn("test_task", self.manager.tasks)
        self.assertIn("test_task", self.manager.displays)
        self.assertIn("test_task", self.manager.cancel_flags)
    
    def test_start_task(self):
        """작업 시작 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        
        success = self.manager.start_task("test_task")
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.RUNNING)
        self.assertIsNotNone(task.start_time)
    
    def test_update_progress(self):
        """진행 상황 업데이트 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        
        success = self.manager.update_progress("test_task", 25, "Processing item 25")
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.completed_items, 25)
        self.assertEqual(task.current_operation, "Processing item 25")
        self.assertEqual(task.progress_percentage, 25.0)
    
    def test_increment_progress(self):
        """진행 상황 증가 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        
        # 10씩 3번 증가
        for i in range(3):
            success = self.manager.increment_progress("test_task", 10, f"Step {i+1}")
            self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.completed_items, 30)
        self.assertEqual(task.current_operation, "Step 3")
    
    def test_complete_task(self):
        """작업 완료 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        
        success = self.manager.complete_task("test_task")
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertEqual(task.completed_items, 100)
        self.assertIsNotNone(task.end_time)
    
    def test_cancel_task(self):
        """작업 취소 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        
        success = self.manager.cancel_task("test_task")
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(task.end_time)
        self.assertTrue(self.manager.is_cancelled("test_task"))
    
    def test_pause_and_resume_task(self):
        """작업 일시정지 및 재개 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        
        # 일시정지
        success = self.manager.pause_task("test_task")
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.PAUSED)
        self.assertTrue(self.manager.is_paused("test_task"))
        
        # 재개
        success = self.manager.resume_task("test_task")
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.RUNNING)
        self.assertFalse(self.manager.is_paused("test_task"))
    
    def test_fail_task(self):
        """작업 실패 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        
        error_message = "Test error occurred"
        success = self.manager.fail_task("test_task", error_message)
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.FAILED)
        self.assertEqual(task.error_message, error_message)
        self.assertIsNotNone(task.end_time)
    
    def test_restart_task(self):
        """작업 재시작 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        self.manager.update_progress("test_task", 50)
        self.manager.cancel_task("test_task")
        
        # 재시작
        success = self.manager.restart_task("test_task")
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.completed_items, 0)
        self.assertIsNone(task.start_time)
        self.assertIsNone(task.end_time)
        self.assertIsNone(task.error_message)
        self.assertFalse(self.manager.is_cancelled("test_task"))
    
    def test_callback_functionality(self):
        """콜백 기능 테스트"""
        callback_events = []
        
        def test_callback(task, event_type):
            callback_events.append((task.task_id, event_type))
        
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.add_callback("test_task", test_callback)
        
        self.manager.start_task("test_task")
        self.manager.update_progress("test_task", 50)
        self.manager.complete_task("test_task")
        
        # 콜백이 호출되었는지 확인
        expected_events = [("test_task", "started"), ("test_task", "updated"), ("test_task", "completed")]
        for expected in expected_events:
            self.assertIn(expected, callback_events)
    
    def test_auto_completion(self):
        """자동 완료 테스트"""
        self.manager.create_task("test_task", "Test Task", 100)
        self.manager.start_task("test_task")
        
        # 100% 진행률로 업데이트하면 자동 완료되어야 함
        success = self.manager.update_progress("test_task", 100)
        self.assertTrue(success)
        
        task = self.manager.get_task_progress("test_task")
        self.assertEqual(task.status, TaskStatus.COMPLETED)
    
    def test_get_all_tasks(self):
        """모든 작업 조회 테스트"""
        # 여러 작업 생성
        for i in range(3):
            self.manager.create_task(f"task_{i}", f"Task {i}", 100)
        
        all_tasks = self.manager.get_all_tasks()
        self.assertEqual(len(all_tasks), 3)
        
        for i in range(3):
            self.assertIn(f"task_{i}", all_tasks)


class TestGlobalFunctions(unittest.TestCase):
    """전역 함수 테스트"""
    
    def test_global_create_progress_task(self):
        """전역 작업 생성 함수 테스트"""
        task = create_progress_task("global_test", "Global Test", 50)
        
        self.assertIsInstance(task, TaskProgress)
        self.assertEqual(task.task_id, "global_test")
        self.assertEqual(task.total_items, 50)
    
    def test_global_progress_operations(self):
        """전역 진행률 조작 함수 테스트"""
        create_progress_task("global_test", "Global Test", 100)
        
        # 시작
        success = start_progress_task("global_test")
        self.assertTrue(success)
        
        # 업데이트
        success = update_progress("global_test", 25, "Processing...")
        self.assertTrue(success)
        
        # 증가
        success = increment_progress("global_test", 25)
        self.assertTrue(success)
        
        # 완료
        success = complete_progress_task("global_test")
        self.assertTrue(success)
    
    def test_progress_context_manager(self):
        """진행률 컨텍스트 매니저 테스트"""
        with progress_context("context_test", "Context Test", 100) as task:
            self.assertIsInstance(task, TaskProgress)
            self.assertEqual(task.task_id, "context_test")
            self.assertEqual(task.status, TaskStatus.RUNNING)
            
            # 진행률 업데이트
            update_progress("context_test", 50)
        
        # 컨텍스트 종료 후 완료 상태 확인
        from progress_manager import progress_manager
        final_task = progress_manager.get_task_progress("context_test")
        self.assertEqual(final_task.status, TaskStatus.COMPLETED)
    
    def test_progress_context_with_exception(self):
        """예외 발생 시 컨텍스트 매니저 테스트"""
        try:
            with progress_context("error_test", "Error Test", 100):
                update_progress("error_test", 25)
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # 예외 발생 후 실패 상태 확인
        from progress_manager import progress_manager
        final_task = progress_manager.get_task_progress("error_test")
        self.assertEqual(final_task.status, TaskStatus.FAILED)
        self.assertIn("Test error", final_task.error_message)


class TestProgressIntegration(unittest.TestCase):
    """통합 진행률 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.manager = ProgressManager(update_interval=0.05)
    
    def tearDown(self):
        """테스트 정리"""
        self.manager.stop()
    
    def test_batch_processing_simulation(self):
        """배치 처리 시뮬레이션 테스트"""
        batch_size = 100
        total_items = 1000
        
        task = self.manager.create_task("batch_test", "Batch Processing", total_items)
        self.manager.start_task("batch_test")
        
        # 배치 단위로 처리 시뮬레이션
        for batch_num in range(0, total_items, batch_size):
            if self.manager.is_cancelled("batch_test"):
                break
            
            # 배치 처리 시뮬레이션
            for i in range(batch_size):
                if batch_num + i >= total_items:
                    break
                
                self.manager.wait_if_paused("batch_test")
                
                if self.manager.is_cancelled("batch_test"):
                    break
                
                time.sleep(0.001)  # 처리 시간 시뮬레이션
                self.manager.increment_progress(
                    "batch_test", 1, 
                    f"Processing item {batch_num + i + 1}"
                )
        
        final_task = self.manager.get_task_progress("batch_test")
        self.assertEqual(final_task.status, TaskStatus.COMPLETED)
        self.assertEqual(final_task.completed_items, total_items)
    
    def test_long_running_task_with_cancellation(self):
        """장시간 실행 작업 취소 테스트"""
        task = self.manager.create_task("long_task", "Long Running Task", 1000)
        self.manager.start_task("long_task")
        
        # 별도 스레드에서 작업 실행
        def worker():
            for i in range(1000):
                if self.manager.is_cancelled("long_task"):
                    break
                
                time.sleep(0.001)
                self.manager.increment_progress("long_task", 1, f"Step {i+1}")
        
        worker_thread = threading.Thread(target=worker)
        worker_thread.start()
        
        # 잠시 후 취소
        time.sleep(0.1)
        self.manager.cancel_task("long_task")
        
        worker_thread.join(timeout=1.0)
        
        final_task = self.manager.get_task_progress("long_task")
        self.assertEqual(final_task.status, TaskStatus.CANCELLED)
        self.assertLess(final_task.completed_items, 1000)  # 완료되지 않았어야 함
    
    def test_multiple_concurrent_tasks(self):
        """다중 동시 작업 테스트"""
        task_count = 3
        items_per_task = 50
        
        # 여러 작업 생성 및 시작
        for i in range(task_count):
            task_id = f"concurrent_task_{i}"
            self.manager.create_task(task_id, f"Concurrent Task {i}", items_per_task)
            self.manager.start_task(task_id)
        
        # 동시 처리
        def worker(task_id):
            for j in range(items_per_task):
                if self.manager.is_cancelled(task_id):
                    break
                
                time.sleep(0.001)
                self.manager.increment_progress(task_id, 1, f"Item {j+1}")
        
        threads = []
        for i in range(task_count):
            thread = threading.Thread(target=worker, args=(f"concurrent_task_{i}",))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join(timeout=2.0)
        
        # 모든 작업이 완료되었는지 확인
        for i in range(task_count):
            task = self.manager.get_task_progress(f"concurrent_task_{i}")
            self.assertEqual(task.status, TaskStatus.COMPLETED)
            self.assertEqual(task.completed_items, items_per_task)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)