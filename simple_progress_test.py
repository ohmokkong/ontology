"""
간단한 진행률 테스트
"""

import time
import logging
from progress_manager import (
    create_progress_task, start_progress_task, update_progress, 
    increment_progress, complete_progress_task, ProgressStyle,
    progress_context, progress_manager
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_simple_progress():
    """간단한 진행률 테스트"""
    print("=== 간단한 진행률 테스트 ===")
    
    # 1. 기본 진행률 테스트
    task_id = "simple_test"
    task = create_progress_task(task_id, "간단한 테스트", 10, ProgressStyle.DETAILED)
    start_progress_task(task_id)
    
    for i in range(10):
        time.sleep(0.2)  # 200ms 대기
        increment_progress(task_id, 1, f"처리 중: 아이템 {i+1}")
        print(f"진행률: {task.progress_percentage:.1f}% - 아이템 {i+1}/10")
    
    complete_progress_task(task_id)
    print("✓ 기본 진행률 테스트 완료")


def test_context_manager():
    """컨텍스트 매니저 테스트"""
    print("\n=== 컨텍스트 매니저 테스트 ===")
    
    with progress_context("context_test", "컨텍스트 테스트", 5) as task:
        for i in range(5):
            time.sleep(0.1)
            update_progress("context_test", i + 1, f"단계 {i+1}")
            print(f"컨텍스트 진행률: {task.progress_percentage:.1f}%")
    
    print("✓ 컨텍스트 매니저 테스트 완료")


def test_batch_processing():
    """배치 처리 테스트"""
    print("\n=== 배치 처리 테스트 ===")
    
    batch_size = 20
    task_id = "batch_test"
    
    task = create_progress_task(task_id, "배치 처리 테스트", batch_size, ProgressStyle.DETAILED)
    start_progress_task(task_id)
    
    # 배치 처리 시뮬레이션
    for i in range(batch_size):
        # 실제 작업 시뮬레이션
        time.sleep(0.05)  # 50ms 처리 시간
        
        # 진행률 업데이트
        increment_progress(
            task_id, 
            1, 
            f"배치 아이템 {i+1} 처리 완료",
            batch_number=i//5 + 1,
            items_in_batch=i%5 + 1
        )
        
        # 5개마다 상태 출력
        if (i + 1) % 5 == 0:
            current_task = progress_manager.get_task_progress(task_id)
            print(f"배치 {(i+1)//5} 완료 - 전체 진행률: {current_task.progress_percentage:.1f}%")
    
    complete_progress_task(task_id)
    print("✓ 배치 처리 테스트 완료")


def test_error_handling():
    """오류 처리 테스트"""
    print("\n=== 오류 처리 테스트 ===")
    
    task_id = "error_test"
    task = create_progress_task(task_id, "오류 처리 테스트", 10)
    start_progress_task(task_id)
    
    try:
        for i in range(10):
            if i == 7:  # 7번째에서 오류 발생
                raise ValueError("테스트 오류 발생")
            
            time.sleep(0.1)
            increment_progress(task_id, 1, f"아이템 {i+1} 처리")
        
        complete_progress_task(task_id)
        
    except Exception as e:
        progress_manager.fail_task(task_id, str(e))
        print(f"오류 발생으로 작업 실패: {e}")
        
        final_task = progress_manager.get_task_progress(task_id)
        print(f"실패한 작업 상태: {final_task.status.value}")
        print(f"실패 시점 진행률: {final_task.progress_percentage:.1f}%")
    
    print("✓ 오류 처리 테스트 완료")


def test_multiple_tasks():
    """다중 작업 테스트"""
    print("\n=== 다중 작업 테스트 ===")
    
    # 3개의 작업 동시 실행
    tasks = []
    for i in range(3):
        task_id = f"multi_task_{i}"
        task = create_progress_task(task_id, f"다중 작업 {i+1}", 8)
        start_progress_task(task_id)
        tasks.append((task_id, task))
    
    # 모든 작업을 동시에 진행
    for step in range(8):
        for task_id, task in tasks:
            time.sleep(0.02)  # 20ms 처리 시간
            increment_progress(task_id, 1, f"단계 {step+1}")
        
        # 진행 상황 출력
        print(f"단계 {step+1} 완료:")
        for task_id, task in tasks:
            current_task = progress_manager.get_task_progress(task_id)
            print(f"  {current_task.name}: {current_task.progress_percentage:.1f}%")
    
    # 모든 작업 완료
    for task_id, task in tasks:
        complete_progress_task(task_id)
    
    print("✓ 다중 작업 테스트 완료")


def main():
    """메인 테스트 함수"""
    print("진행률 표시 기능 테스트 시작\n")
    
    try:
        # 각 테스트 실행
        test_simple_progress()
        test_context_manager()
        test_batch_processing()
        test_error_handling()
        test_multiple_tasks()
        
        print("\n=== 모든 테스트 완료 ===")
        
        # 최종 통계
        all_tasks = progress_manager.get_all_tasks()
        print(f"\n총 실행된 작업: {len(all_tasks)}개")
        
        completed_count = sum(1 for task in all_tasks.values() if task.status.value == "completed")
        failed_count = sum(1 for task in all_tasks.values() if task.status.value == "failed")
        
        print(f"완료된 작업: {completed_count}개")
        print(f"실패한 작업: {failed_count}개")
        
        # 성능 통계
        total_items = sum(task.total_items for task in all_tasks.values())
        total_processed = sum(task.completed_items for task in all_tasks.values())
        
        print(f"총 처리 아이템: {total_processed}/{total_items}")
        
        if all_tasks:
            avg_rate = sum(task.items_per_second for task in all_tasks.values() if task.items_per_second > 0) / len(all_tasks)
            print(f"평균 처리 속도: {avg_rate:.2f} items/sec")
        
    except KeyboardInterrupt:
        print("\n테스트가 사용자에 의해 중단되었습니다.")
    finally:
        # 진행률 관리자 정리
        progress_manager.stop()
        print("진행률 관리자 종료")


if __name__ == "__main__":
    main()