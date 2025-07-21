"""
성능 최적화 시스템 실행 스크립트

이 스크립트는 성능 측정, 최적화, 벤치마크를 통합 실행합니다.
"""

import argparse
import logging
import json
import time
from pathlib import Path
from datetime import datetime

from performance_monitor import performance_monitor, get_performance_report, optimize_memory
from api_optimizer import api_optimizer, start_api_optimizer, stop_api_optimizer, get_api_optimizer_stats
from performance_benchmark import run_performance_benchmark

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_performance_monitoring(duration: int = 60):
    """성능 모니터링 실행"""
    logger.info(f"Starting performance monitoring for {duration} seconds...")
    
    # API 최적화 엔진 시작
    start_api_optimizer()
    
    try:
        # 모니터링 기간 동안 대기
        start_time = time.time()
        while time.time() - start_time < duration:
            # 주기적으로 메모리 최적화 실행
            if int(time.time() - start_time) % 30 == 0:  # 30초마다
                optimize_memory()
            
            time.sleep(1)
        
        # 성능 리포트 생성
        report = get_performance_report()
        
        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"performance_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Performance monitoring completed. Report saved to {report_file}")
        
        return report
        
    finally:
        # API 최적화 엔진 중지
        stop_api_optimizer()


def run_optimization_analysis():
    """최적화 분석 실행"""
    logger.info("Running optimization analysis...")
    
    # 현재 성능 통계 수집
    performance_stats = get_performance_report()
    api_stats = get_api_optimizer_stats()
    
    # 분석 결과
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "performance_analysis": analyze_performance_metrics(performance_stats),
        "api_optimization_analysis": analyze_api_metrics(api_stats),
        "recommendations": generate_optimization_recommendations(performance_stats, api_stats)
    }
    
    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_file = f"optimization_analysis_{timestamp}.json"
    
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Optimization analysis completed. Results saved to {analysis_file}")
    
    return analysis


def analyze_performance_metrics(stats: dict) -> dict:
    """성능 메트릭 분석"""
    analysis = {
        "system_health": "good",
        "bottlenecks": [],
        "performance_trends": {}
    }
    
    # 시스템 정보 분석
    system_info = stats.get("system_info", {})
    if system_info.get("cpu_percent", 0) > 80:
        analysis["bottlenecks"].append("High CPU usage detected")
        analysis["system_health"] = "warning"
    
    memory_available = system_info.get("memory_available_gb", 0)
    if memory_available < 1.0:  # 1GB 미만
        analysis["bottlenecks"].append("Low memory availability")
        analysis["system_health"] = "critical"
    
    # 작업 통계 분석
    operation_stats = stats.get("operation_statistics", {})
    if operation_stats:
        slow_operations = []
        for op_name, op_stats in operation_stats.items():
            avg_duration = op_stats.get("avg_duration", 0)
            if avg_duration > 5.0:  # 5초 이상
                slow_operations.append(f"{op_name}: {avg_duration:.2f}s")
        
        if slow_operations:
            analysis["bottlenecks"].extend(slow_operations)
            analysis["performance_trends"]["slow_operations"] = slow_operations
    
    # API 통계 분석
    api_stats = stats.get("api_statistics", {})
    if api_stats and not api_stats.get("error"):
        avg_response_time = api_stats.get("avg_response_time", 0)
        if avg_response_time > 3.0:  # 3초 이상
            analysis["bottlenecks"].append(f"Slow API responses: {avg_response_time:.2f}s average")
        
        success_rate = api_stats.get("success_rate", 100)
        if success_rate < 95:  # 95% 미만
            analysis["bottlenecks"].append(f"Low API success rate: {success_rate:.1f}%")
            analysis["system_health"] = "warning"
    
    return analysis


def analyze_api_metrics(stats: dict) -> dict:
    """API 메트릭 분석"""
    analysis = {
        "optimization_status": "optimal",
        "efficiency_metrics": {},
        "recommendations": []
    }
    
    if stats.get("is_running"):
        # 큐 크기 분석
        total_queue_size = sum(
            stats.get(f"priority_{i}_queue", 0) for i in [1, 2, 3]
        )
        
        if total_queue_size > 100:
            analysis["optimization_status"] = "overloaded"
            analysis["recommendations"].append("Consider increasing concurrent request limit")
        
        # 속도 제한 분석
        rate_limit_wait = stats.get("rate_limiter_wait_time", 0)
        if rate_limit_wait > 1.0:
            analysis["optimization_status"] = "throttled"
            analysis["recommendations"].append("API rate limiting is active - consider optimizing request patterns")
        
        # 효율성 메트릭
        total_requests = stats.get("total_requests", 0)
        successful_requests = stats.get("successful_requests", 0)
        
        if total_requests > 0:
            success_rate = successful_requests / total_requests * 100
            analysis["efficiency_metrics"]["success_rate"] = success_rate
            
            if success_rate < 90:
                analysis["optimization_status"] = "suboptimal"
                analysis["recommendations"].append("High failure rate detected - review error handling")
        
        # 배치 처리 효율성
        batched_requests = stats.get("batched_requests", 0)
        if total_requests > 0:
            batch_ratio = batched_requests / total_requests * 100
            analysis["efficiency_metrics"]["batch_ratio"] = batch_ratio
            
            if batch_ratio < 20:  # 20% 미만
                analysis["recommendations"].append("Consider using more batch processing for better efficiency")
    
    else:
        analysis["optimization_status"] = "inactive"
        analysis["recommendations"].append("API optimizer is not running")
    
    return analysis


def generate_optimization_recommendations(performance_stats: dict, api_stats: dict) -> list:
    """최적화 권장사항 생성"""
    recommendations = []
    
    # 성능 기반 권장사항
    system_info = performance_stats.get("system_info", {})
    cpu_percent = system_info.get("cpu_percent", 0)
    memory_available = system_info.get("memory_available_gb", 0)
    
    if cpu_percent > 70:
        recommendations.append({
            "category": "CPU Optimization",
            "priority": "high",
            "description": "High CPU usage detected",
            "actions": [
                "Consider reducing concurrent operations",
                "Optimize CPU-intensive algorithms",
                "Implement caching for frequently computed results"
            ]
        })
    
    if memory_available < 2.0:
        recommendations.append({
            "category": "Memory Optimization",
            "priority": "high",
            "description": "Low memory availability",
            "actions": [
                "Run memory optimization more frequently",
                "Reduce data retention periods",
                "Implement data streaming for large datasets"
            ]
        })
    
    # API 최적화 권장사항
    if api_stats.get("avg_response_time", 0) > 2.0:
        recommendations.append({
            "category": "API Performance",
            "priority": "medium",
            "description": "Slow API response times",
            "actions": [
                "Implement request caching",
                "Use connection pooling",
                "Consider API endpoint optimization"
            ]
        })
    
    # 일반적인 최적화 권장사항
    recommendations.append({
        "category": "General Optimization",
        "priority": "low",
        "description": "Continuous improvement suggestions",
        "actions": [
            "Regular performance monitoring",
            "Periodic benchmark testing",
            "Update performance thresholds based on usage patterns"
        ]
    })
    
    return recommendations


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="성능 최적화 시스템")
    parser.add_argument("--mode", choices=["monitor", "benchmark", "analyze", "all"], 
                       default="all", help="실행 모드 선택")
    parser.add_argument("--duration", type=int, default=60, 
                       help="모니터링 지속 시간 (초)")
    parser.add_argument("--output-dir", default="performance_results", 
                       help="결과 출력 디렉토리")
    
    args = parser.parse_args()
    
    # 출력 디렉토리 생성
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    logger.info(f"Starting performance optimization system in {args.mode} mode")
    
    results = {}
    
    try:
        if args.mode in ["monitor", "all"]:
            logger.info("=== Performance Monitoring ===")
            monitoring_results = run_performance_monitoring(args.duration)
            results["monitoring"] = monitoring_results
        
        if args.mode in ["benchmark", "all"]:
            logger.info("=== Performance Benchmark ===")
            benchmark_results = run_performance_benchmark(str(output_dir))
            results["benchmark"] = benchmark_results
        
        if args.mode in ["analyze", "all"]:
            logger.info("=== Optimization Analysis ===")
            analysis_results = run_optimization_analysis()
            results["analysis"] = analysis_results
        
        # 종합 결과 저장
        if results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = output_dir / f"performance_optimization_summary_{timestamp}.json"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Performance optimization completed. Summary saved to {summary_file}")
            
            # 주요 결과 출력
            print("\n" + "="*50)
            print("성능 최적화 시스템 실행 완료")
            print("="*50)
            
            if "monitoring" in results:
                print(f"모니터링 기간: {args.duration}초")
                print(f"기록된 메트릭 수: {results['monitoring'].get('total_metrics_recorded', 0)}")
            
            if "benchmark" in results:
                summary = results["benchmark"].get("summary", {})
                print(f"벤치마크 테스트: {summary.get('total_tests_run', 0)}개 실행")
                print(f"완료율: {summary.get('test_completion_rate', 0):.1f}%")
            
            if "analysis" in results:
                analysis = results["analysis"]
                perf_analysis = analysis.get("performance_analysis", {})
                print(f"시스템 상태: {perf_analysis.get('system_health', 'unknown')}")
                
                bottlenecks = perf_analysis.get("bottlenecks", [])
                if bottlenecks:
                    print("발견된 병목점:")
                    for bottleneck in bottlenecks[:3]:  # 상위 3개만 표시
                        print(f"  - {bottleneck}")
                
                recommendations = analysis.get("recommendations", [])
                high_priority_recs = [r for r in recommendations if r.get("priority") == "high"]
                if high_priority_recs:
                    print("우선순위 높은 권장사항:")
                    for rec in high_priority_recs:
                        print(f"  - {rec.get('description', '')}")
            
            print(f"\n상세 결과는 {summary_file}에서 확인하세요.")
    
    except KeyboardInterrupt:
        logger.info("Performance optimization interrupted by user")
    except Exception as e:
        logger.error(f"Error during performance optimization: {e}")
        raise
    
    logger.info("Performance optimization system finished")


if __name__ == "__main__":
    main()