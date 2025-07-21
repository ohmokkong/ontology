"""
성능 최적화 시스템 간단 테스트
"""

import time
import logging
from performance_monitor import performance_monitor, measure_performance, get_performance_report, optimize_memory
from api_optimizer import APIRequest, api_optimizer

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_performance_monitoring():
    """성능 모니터링 테스트"""
    print("=== 성능 모니터링 테스트 ===")
    
    @measure_performance("test_data_processing")
    def process_test_data():
        # 데이터 처리 시뮬레이션
        data = list(range(10000))
        processed = [x * 2 for x in data if x % 2 == 0]
        time.sleep(0.1)  # 처리 시간 시뮬레이션
        return len(processed)
    
    # 여러 번 실행하여 통계 수집
    for i in range(3):
        result = process_test_data()
        print(f"처리 {i+1}: {result}개 아이템 처리됨")
    
    # 통계 조회
    stats = performance_monitor.get_operation_statistics("test_data_processing")
    print(f"평균 실행 시간: {stats['avg_duration']:.3f}초")
    print(f"총 호출 횟수: {stats['total_calls']}")
    
    return True


def test_memory_optimization():
    """메모리 최적화 테스트"""
    print("\n=== 메모리 최적화 테스트 ===")
    
    # 메모리 집약적 작업
    @measure_performance("memory_intensive_task")
    def memory_task():
        # 큰 리스트 생성
        large_data = [list(range(1000)) for _ in range(100)]
        # 처리
        processed = [sum(sublist) for sublist in large_data]
        return len(processed)
    
    result = memory_task()
    print(f"메모리 집약적 작업 완료: {result}개 처리")
    
    # 메모리 최적화 실행
    optimization_result = optimize_memory()
    print(f"가비지 컬렉션: {optimization_result['objects_collected']}개 객체 정리")
    print(f"현재 메모리 사용량: {optimization_result['current_memory_mb']:.2f}MB")
    
    return True


def test_api_optimization():
    """API 최적화 테스트"""
    print("\n=== API 최적화 테스트 ===")
    
    # API 최적화 엔진 시작
    api_optimizer.start()
    
    try:
        # 테스트 요청들 추가
        requests = [
            APIRequest(endpoint="https://httpbin.org/json", method="GET", priority=1),
            APIRequest(endpoint="https://httpbin.org/status/200", method="GET", priority=2),
            APIRequest(endpoint="https://httpbin.org/delay/1", method="GET", priority=3)
        ]
        
        request_ids = []
        for req in requests:
            req_id = api_optimizer.add_request(req)
            request_ids.append(req_id)
            print(f"요청 추가됨: {req_id}")
        
        # 잠시 대기하여 처리 시간 확보
        time.sleep(2)
        
        # 통계 조회
        stats = api_optimizer.get_statistics()
        print(f"총 요청 수: {stats['total_requests']}")
        print(f"성공한 요청 수: {stats['successful_requests']}")
        print(f"실패한 요청 수: {stats['failed_requests']}")
        print(f"평균 응답 시간: {stats['avg_response_time']:.3f}초")
        
    finally:
        # API 최적화 엔진 중지
        api_optimizer.stop()
    
    return True


def test_performance_report():
    """성능 리포트 테스트"""
    print("\n=== 성능 리포트 테스트 ===")
    
    report = get_performance_report()
    
    print("시스템 정보:")
    system_info = report.get("system_info", {})
    print(f"  CPU 코어 수: {system_info.get('cpu_count', 'N/A')}")
    print(f"  총 메모리: {system_info.get('memory_total_gb', 'N/A'):.2f}GB")
    print(f"  사용 가능 메모리: {system_info.get('memory_available_gb', 'N/A'):.2f}GB")
    print(f"  CPU 사용률: {system_info.get('cpu_percent', 'N/A'):.1f}%")
    
    print(f"\n총 기록된 메트릭 수: {report.get('total_metrics_recorded', 0)}")
    
    return True


def main():
    """메인 테스트 함수"""
    print("성능 최적화 시스템 테스트 시작\n")
    
    tests = [
        ("성능 모니터링", test_performance_monitoring),
        ("메모리 최적화", test_memory_optimization),
        ("API 최적화", test_api_optimization),
        ("성능 리포트", test_performance_report)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"테스트 실행 중: {test_name}")
            if test_func():
                print(f"✓ {test_name} 테스트 통과")
                passed += 1
            else:
                print(f"✗ {test_name} 테스트 실패")
        except Exception as e:
            print(f"✗ {test_name} 테스트 오류: {e}")
    
    print(f"\n=== 테스트 결과 ===")
    print(f"통과: {passed}/{total}")
    print(f"성공률: {passed/total*100:.1f}%")
    
    if passed == total:
        print("모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("일부 테스트가 실패했습니다. 로그를 확인해주세요.")


if __name__ == "__main__":
    main()