"""
간단한 벤치마크 테스트
"""

import time
import logging
from performance_benchmark import PerformanceBenchmark

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_simple_benchmark():
    """간단한 벤치마크 실행"""
    print("=== 간단한 성능 벤치마크 실행 ===")
    
    benchmark = PerformanceBenchmark("simple_benchmark_results")
    
    # 데이터 처리 벤치마크만 실행
    print("데이터 처리 성능 테스트 중...")
    data_processing_results = benchmark.benchmark_data_processing()
    
    print("\n=== 데이터 처리 결과 ===")
    summary = data_processing_results.get("summary", {})
    print(f"최대 처리량: {summary.get('max_throughput', 0):.2f} items/sec")
    print(f"평균 성공률: {summary.get('avg_success_rate', 0):.1f}%")
    print(f"총 처리된 아이템: {summary.get('total_items_processed', 0)}")
    
    # 메모리 사용량 테스트
    print("\n메모리 사용량 테스트 중...")
    memory_results = benchmark.benchmark_memory_usage()
    
    print("\n=== 메모리 사용량 결과 ===")
    print(f"초기 메모리: {memory_results.get('initial_memory_mb', 0):.2f}MB")
    print(f"최대 메모리 사용량: {memory_results.get('peak_memory_usage', 0):.2f}MB")
    
    for result in memory_results.get("results", []):
        print(f"{result['test_name']}: {result['memory_used_mb']:.2f}MB ({result['data_size']} items)")
    
    # 동시 처리 테스트
    print("\n동시 처리 성능 테스트 중...")
    concurrent_results = benchmark.benchmark_concurrent_processing()
    
    print("\n=== 동시 처리 결과 ===")
    print(f"최적 워커 수: {concurrent_results.get('optimal_worker_count', 0)}")
    print(f"최대 처리량: {concurrent_results.get('max_throughput', 0):.2f} items/sec")
    
    for result in concurrent_results.get("results", []):
        print(f"워커 {result['worker_count']}개: {result['throughput']:.2f} items/sec (효율성: {result['efficiency']:.2f})")
    
    return True


if __name__ == "__main__":
    try:
        run_simple_benchmark()
        print("\n벤치마크 테스트가 성공적으로 완료되었습니다!")
    except Exception as e:
        print(f"벤치마크 테스트 중 오류 발생: {e}")
        logger.error(f"Benchmark test error: {e}")