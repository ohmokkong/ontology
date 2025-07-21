"""
빠른 진행률 테스트
"""

import time
import threading
from progress_manager import (
    create_progress_task, start_progress_task, 
    increment_progress, complete_progress_task,
    progress_manager, ProgressStyle
)

def quick_test():
    print("=== 빠른 진행률 테스트 ===")
    
    # 테스트 작업 생성
    task_id = "quick_test"
    task = create_progress_task(
        task_id=task_id,
        name="빠른 테스트 작업",
        total_items=20,
        style=ProgressStyle.DETAILED
    )
    
    print(f"✅ 작업 생성: {task.name}")
    
    # 작업 시작
    start_progress_task(task_id)
    print("🚀 작업 시작")
    
    # 진행률 업데이트
    for i in range(20):
        time.sleep(0.1)  # 100ms 대기
        increment_progress(task_id, 1, f"아이템 {i+1} 처리 중")
        
        # 현재 상태 출력
        current_task = progress_manager.get_task_progress(task_id)
        if current_task:
            print(f"진행률: {current_task.progress_percentage:.1f}% "
                  f"({current_task.completed_items}/{current_task.total_items}) "
                  f"속도: {current_task.items_per_second:.1f}/s")
    
    # 완료
    complete_progress_task(task_id)
    
    # 최종 상태
    final_task = progress_manager.get_task_progress(task_id)
    print(f"\n🎉 작업 완료!")
    print(f"최종 상태: {final_task.status.value}")
    print(f"총 경과 시간: {final_task.elapsed_time}")
    print(f"평균 처리 속도: {final_task.items_per_second:.1f} items/sec")

if __name__ == "__main__":
    quick_test()