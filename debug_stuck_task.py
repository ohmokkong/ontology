"""
정지된 작업 디버깅 및 복구 도구
"""

import time
import threading
import logging
from progress_manager import progress_manager, TaskStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def diagnose_stuck_task():
    """정지된 작업 진단"""
    print("=== 정지된 작업 진단 ===")
    
    # 모든 작업 상태 확인
    all_tasks = progress_manager.get_all_tasks()
    
    if not all_tasks:
        print("❌ 등록된 작업이 없습니다.")
        return
    
    for task_id, task in all_tasks.items():
        print(f"\n📋 작업 ID: {task_id}")
        print(f"   이름: {task.name}")
        print(f"   상태: {task.status.value}")
        print(f"   진행률: {task.progress_percentage:.1f}% ({task.completed_items}/{task.total_items})")
        print(f"   경과 시간: {task.elapsed_time}")
        
        if task.start_time:
            print(f"   시작 시간: {task.start_time}")
        if task.error_message:
            print(f"   오류 메시지: {task.error_message}")
        
        # 작업 상태별 진단
        if task.status == TaskStatus.RUNNING:
            if task.completed_items == 0 and task.elapsed_time.total_seconds() > 60:
                print("   🚨 경고: 작업이 1분 이상 진행되지 않음")
                print("   💡 권장: 작업 재시작 또는 취소")
            elif task.items_per_second < 0.1:
                print("   ⚠️  주의: 처리 속도가 매우 느림")
                print("   💡 권장: 리소스 확인 또는 배치 크기 조정")
        
        elif task.status == TaskStatus.PENDING:
            print("   ℹ️  정보: 작업이 시작되지 않음")
            print("   💡 권장: start_progress_task() 호출 필요")
        
        elif task.status == TaskStatus.CANCELLED:
            print("   🛑 정보: 작업이 취소됨")
            print("   💡 권장: restart_task()로 재시작 가능")
        
        elif task.status == TaskStatus.FAILED:
            print("   ❌ 정보: 작업이 실패함")
            print("   💡 권장: 오류 해결 후 재시작")
        
        # 플래그 상태 확인
        is_cancelled = progress_manager.is_cancelled(task_id)
        is_paused = progress_manager.is_paused(task_id)
        
        print(f"   취소 플래그: {'설정됨' if is_cancelled else '해제됨'}")
        print(f"   일시정지 플래그: {'설정됨' if is_paused else '해제됨'}")


def force_restart_stuck_tasks():
    """정지된 작업 강제 재시작"""
    print("\n=== 정지된 작업 강제 재시작 ===")
    
    all_tasks = progress_manager.get_all_tasks()
    stuck_tasks = []
    
    for task_id, task in all_tasks.items():
        # 정지된 작업 조건
        is_stuck = (
            (task.status == TaskStatus.RUNNING and 
             task.completed_items == 0 and 
             task.elapsed_time.total_seconds() > 300) or  # 5분 이상 진행 없음
            task.status == TaskStatus.CANCELLED or
            task.status == TaskStatus.FAILED
        )
        
        if is_stuck:
            stuck_tasks.append(task_id)
    
    if not stuck_tasks:
        print("✅ 재시작이 필요한 작업이 없습니다.")
        return
    
    for task_id in stuck_tasks:
        print(f"🔄 작업 재시작 중: {task_id}")
        
        # 작업 재시작
        success = progress_manager.restart_task(task_id)
        if success:
            print(f"   ✅ {task_id} 재시작 성공")
        else:
            print(f"   ❌ {task_id} 재시작 실패")


def create_test_batch_task():
    """테스트용 배치 작업 생성"""
    print("\n=== 테스트 배치 작업 생성 ===")
    
    task_id = "test_batch_recovery"
    
    # 기존 작업이 있으면 정리
    existing_task = progress_manager.get_task_progress(task_id)
    if existing_task:
        progress_manager.cancel_task(task_id)
        time.sleep(0.1)
    
    # 새 작업 생성
    task = progress_manager.create_task(
        task_id=task_id,
        name="복구 테스트 배치 작업",
        total_items=100
    )
    
    print(f"✅ 테스트 작업 생성됨: {task_id}")
    
    # 작업 시작
    progress_manager.start_task(task_id)
    print(f"🚀 테스트 작업 시작됨")
    
    # 워커 스레드로 작업 실행
    def test_worker():
        try:
            for i in range(100):
                if progress_manager.is_cancelled(task_id):
                    print(f"   작업이 {i}에서 취소됨")
                    break
                
                progress_manager.wait_if_paused(task_id)
                
                # 작업 시뮬레이션
                time.sleep(0.05)  # 50ms 처리 시간
                
                progress_manager.increment_progress(
                    task_id, 1, f"테스트 아이템 {i+1} 처리 중"
                )
                
                # 진행 상황 출력 (10개마다)
                if (i + 1) % 10 == 0:
                    task = progress_manager.get_task_progress(task_id)
                    print(f"   진행률: {task.progress_percentage:.1f}% ({task.completed_items}/{task.total_items})")
            
            # 완료되지 않았다면 완료 처리
            task = progress_manager.get_task_progress(task_id)
            if task.status == TaskStatus.RUNNING:
                progress_manager.complete_task(task_id)
                print("   ✅ 테스트 작업 완료")
                
        except Exception as e:
            progress_manager.fail_task(task_id, str(e))
            print(f"   ❌ 테스트 작업 실패: {e}")
    
    # 워커 스레드 시작
    worker_thread = threading.Thread(target=test_worker, daemon=True)
    worker_thread.start()
    
    return task_id, worker_thread


def monitor_task_recovery(task_id: str, worker_thread: threading.Thread):
    """작업 복구 모니터링"""
    print(f"\n=== 작업 복구 모니터링: {task_id} ===")
    
    start_time = time.time()
    last_progress = 0
    
    while worker_thread.is_alive() and time.time() - start_time < 30:  # 최대 30초 모니터링
        task = progress_manager.get_task_progress(task_id)
        
        if task:
            current_progress = task.completed_items
            
            # 진행 상황 변화 확인
            if current_progress > last_progress:
                print(f"📈 진행률 업데이트: {task.progress_percentage:.1f}% "
                      f"(속도: {task.items_per_second:.1f} items/s)")
                last_progress = current_progress
            
            # 완료 확인
            if task.status == TaskStatus.COMPLETED:
                print("🎉 작업이 성공적으로 완료되었습니다!")
                break
            elif task.status == TaskStatus.FAILED:
                print(f"❌ 작업이 실패했습니다: {task.error_message}")
                break
            elif task.status == TaskStatus.CANCELLED:
                print("🛑 작업이 취소되었습니다.")
                break
        
        time.sleep(1)
    
    # 최종 상태 확인
    final_task = progress_manager.get_task_progress(task_id)
    if final_task:
        print(f"\n📊 최종 상태:")
        print(f"   상태: {final_task.status.value}")
        print(f"   진행률: {final_task.progress_percentage:.1f}%")
        print(f"   처리 속도: {final_task.items_per_second:.1f} items/s")
        print(f"   경과 시간: {final_task.elapsed_time}")


def main():
    """메인 진단 및 복구 프로세스"""
    print("🔧 정지된 작업 진단 및 복구 도구")
    print("=" * 50)
    
    # 1. 현재 상태 진단
    diagnose_stuck_task()
    
    # 2. 정지된 작업 재시작 시도
    force_restart_stuck_tasks()
    
    # 3. 테스트 작업으로 시스템 확인
    task_id, worker_thread = create_test_batch_task()
    
    # 4. 복구 모니터링
    monitor_task_recovery(task_id, worker_thread)
    
    print("\n" + "=" * 50)
    print("🏁 진단 및 복구 프로세스 완료")
    
    # 최종 권장사항
    print("\n💡 권장사항:")
    print("1. 시스템 리소스 확인 (메모리, CPU)")
    print("2. 로그 파일 확인으로 오류 원인 파악")
    print("3. 배치 크기 조정으로 성능 최적화")
    print("4. 정기적인 작업 상태 모니터링")


if __name__ == "__main__":
    main()