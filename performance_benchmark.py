"""
성능 벤치마크 도구

이 모듈은 시스템의 다양한 구성 요소에 대한 성능 벤치마크를 실행합니다.
- 대량 데이터 처리 성능 측정
- API 호출 성능 테스트
- 메모리 사용량 분석
- 온톨로지 처리 성능 측정
"""

import time
import asyncio
import logging
import statistics
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures
import json
import csv
from pathlib import Path

from performance_monitor import performance_monitor, PerformanceMonitor
from api_optimizer import api_optimizer, APIRequest
from food_models import FoodItem, NutritionInfo
from integrated_models import ExerciseItem, ExerciseSession
from rdf_data_converter import RDFDataConverter
from ontology_manager import OntologyManager

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """벤치마크 결과 데이터 클래스"""
    test_name: str
    data_size: int
    execution_time: float
    memory_used: float
    throughput: float  # 처리량 (items/second)
    success_rate: float
    error_count: int
    additional_metrics: Dict[str, Any]


class PerformanceBenchmark:
    """성능 벤치마크 실행기"""
    
    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.monitor = PerformanceMonitor()
        self.results: List[BenchmarkResult] = []
    
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """모든 벤치마크 실행"""
        logger.info("Starting comprehensive performance benchmark...")
        
        benchmark_suite = [
            ("Data Processing", self.benchmark_data_processing),
            ("API Calls", self.benchmark_api_calls),
            ("Memory Usage", self.benchmark_memory_usage),
            ("RDF Conversion", self.benchmark_rdf_conversion),
            ("Ontology Operations", self.benchmark_ontology_operations),
            ("Concurrent Processing", self.benchmark_concurrent_processing),
            ("Batch Operations", self.benchmark_batch_operations)
        ]
        
        all_results = {}
        
        for suite_name, benchmark_func in benchmark_suite:
            logger.info(f"Running {suite_name} benchmark...")
            try:
                results = benchmark_func()
                all_results[suite_name] = results
                logger.info(f"Completed {suite_name} benchmark")
            except Exception as e:
                logger.error(f"Failed to run {suite_name} benchmark: {e}")
                all_results[suite_name] = {"error": str(e)}
        
        # 결과 저장
        self._save_results(all_results)
        
        # 종합 리포트 생성
        summary = self._generate_summary_report(all_results)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "detailed_results": all_results
        }
    
    def benchmark_data_processing(self) -> Dict[str, Any]:
        """데이터 처리 성능 벤치마크"""
        test_sizes = [100, 500, 1000, 5000, 10000]
        results = []
        
        for size in test_sizes:
            # 음식 데이터 생성
            food_data = self._generate_test_food_data(size)
            
            @self.monitor.measure_performance(f"data_processing_{size}")
            def process_food_data(data):
                processed = []
                for item in data:
                    # 데이터 검증 및 처리 시뮬레이션
                    if item.get('name') and item.get('calories'):
                        nutrition = NutritionInfo(
                            food_item=FoodItem(
                                name=item['name'],
                                food_id=str(item.get('id', 0)),
                                category=item.get('category'),
                                manufacturer=item.get('manufacturer')
                            ),
                            calories_per_100g=float(item['calories']),
                            carbohydrate=float(item.get('carbs', 0)),
                            protein=float(item.get('protein', 0)),
                            fat=float(item.get('fat', 0))
                        )
                        processed.append(nutrition)
                return processed
            
            start_time = time.time()
            processed_data = process_food_data(food_data)
            execution_time = time.time() - start_time
            
            # 메트릭 수집
            metrics = self.monitor.get_operation_statistics(f"data_processing_{size}")
            
            result = BenchmarkResult(
                test_name=f"data_processing_{size}",
                data_size=size,
                execution_time=execution_time,
                memory_used=0,  # 실제 구현에서는 메모리 모니터링 결과 사용
                throughput=size / execution_time if execution_time > 0 else 0,
                success_rate=len(processed_data) / size * 100,
                error_count=size - len(processed_data),
                additional_metrics=metrics or {}
            )
            
            results.append(result)
            logger.info(f"Processed {size} items in {execution_time:.2f}s (throughput: {result.throughput:.2f} items/s)")
        
        return {
            "test_type": "data_processing",
            "results": [result.__dict__ for result in results],
            "summary": {
                "max_throughput": max(r.throughput for r in results),
                "avg_success_rate": statistics.mean(r.success_rate for r in results),
                "total_items_processed": sum(r.data_size for r in results)
            }
        }
    
    def benchmark_api_calls(self) -> Dict[str, Any]:
        """API 호출 성능 벤치마크"""
        # Mock API 엔드포인트들
        test_endpoints = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/2",
            "https://httpbin.org/json",
            "https://httpbin.org/status/200"
        ]
        
        results = []
        
        # 순차 호출 테스트
        sequential_times = []
        for endpoint in test_endpoints:
            start_time = time.time()
            try:
                request = APIRequest(endpoint=endpoint, timeout=10.0)
                # 실제 구현에서는 API 호출 실행
                time.sleep(0.5)  # 시뮬레이션
                execution_time = time.time() - start_time
                sequential_times.append(execution_time)
            except Exception as e:
                logger.error(f"API call failed: {e}")
                sequential_times.append(10.0)  # 타임아웃으로 간주
        
        # 동시 호출 테스트
        concurrent_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for endpoint in test_endpoints:
                future = executor.submit(self._simulate_api_call, endpoint)
                futures.append(future)
            
            concurrent.futures.wait(futures, timeout=15.0)
        
        concurrent_time = time.time() - concurrent_start
        
        # 결과 분석
        sequential_total = sum(sequential_times)
        speedup = sequential_total / concurrent_time if concurrent_time > 0 else 0
        
        return {
            "test_type": "api_calls",
            "sequential_time": sequential_total,
            "concurrent_time": concurrent_time,
            "speedup_factor": speedup,
            "avg_response_time": statistics.mean(sequential_times),
            "max_response_time": max(sequential_times),
            "min_response_time": min(sequential_times),
            "endpoints_tested": len(test_endpoints)
        }
    
    def benchmark_memory_usage(self) -> Dict[str, Any]:
        """메모리 사용량 벤치마크"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_tests = [
            ("Small Dataset", 1000),
            ("Medium Dataset", 10000),
            ("Large Dataset", 100000)
        ]
        
        results = []
        
        for test_name, size in memory_tests:
            gc.collect()  # 가비지 컬렉션
            start_memory = process.memory_info().rss / 1024 / 1024
            
            # 메모리 집약적 작업 시뮬레이션
            @self.monitor.measure_performance(f"memory_test_{size}")
            def memory_intensive_task():
                # 대량 데이터 생성
                data = []
                for i in range(size):
                    item = {
                        'id': i,
                        'name': f'item_{i}',
                        'data': list(range(10)),  # 작은 리스트
                        'metadata': {'created': datetime.now().isoformat()}
                    }
                    data.append(item)
                
                # 데이터 처리
                processed = [item for item in data if item['id'] % 2 == 0]
                return len(processed)
            
            result_count = memory_intensive_task()
            
            end_memory = process.memory_info().rss / 1024 / 1024
            memory_used = end_memory - start_memory
            
            results.append({
                "test_name": test_name,
                "data_size": size,
                "memory_used_mb": memory_used,
                "memory_per_item_kb": (memory_used * 1024) / size if size > 0 else 0,
                "items_processed": result_count
            })
            
            logger.info(f"{test_name}: {memory_used:.2f}MB for {size} items")
        
        return {
            "test_type": "memory_usage",
            "initial_memory_mb": initial_memory,
            "results": results,
            "peak_memory_usage": max(r["memory_used_mb"] for r in results)
        }
    
    def benchmark_rdf_conversion(self) -> Dict[str, Any]:
        """RDF 변환 성능 벤치마크"""
        converter = RDFDataConverter()
        test_sizes = [10, 50, 100, 500]
        results = []
        
        for size in test_sizes:
            # 테스트 데이터 생성
            food_items = []
            for i in range(size):
                food_item = FoodItem(
                    name=f"테스트음식_{i}",
                    food_id=str(i),
                    category="테스트카테고리",
                    manufacturer="테스트제조사"
                )
                nutrition = NutritionInfo(
                    food_item=food_item,
                    calories_per_100g=100.0 + i,
                    carbohydrate=20.0 + i,
                    protein=10.0 + i,
                    fat=5.0 + i
                )
                food_items.append((food_item, nutrition))
            
            @self.monitor.measure_performance(f"rdf_conversion_{size}")
            def convert_to_rdf():
                graphs = []
                for food_item, nutrition in food_items:
                    try:
                        graph = converter.convert_food_to_rdf(food_item, nutrition)
                        graphs.append(graph)
                    except Exception as e:
                        logger.error(f"RDF conversion error: {e}")
                
                # 그래프 병합
                if graphs:
                    merged_graph = converter.merge_graphs(graphs)
                    return len(merged_graph), len(graphs)
                return 0, 0
            
            start_time = time.time()
            triples_count, graphs_count = convert_to_rdf()
            execution_time = time.time() - start_time
            
            result = {
                "data_size": size,
                "execution_time": execution_time,
                "triples_generated": triples_count,
                "graphs_processed": graphs_count,
                "triples_per_second": triples_count / execution_time if execution_time > 0 else 0,
                "conversion_rate": graphs_count / size * 100 if size > 0 else 0
            }
            
            results.append(result)
            logger.info(f"RDF conversion: {size} items -> {triples_count} triples in {execution_time:.2f}s")
        
        return {
            "test_type": "rdf_conversion",
            "results": results,
            "max_triples_per_second": max(r["triples_per_second"] for r in results),
            "avg_conversion_rate": statistics.mean(r["conversion_rate"] for r in results)
        }
    
    def benchmark_ontology_operations(self) -> Dict[str, Any]:
        """온톨로지 작업 성능 벤치마크"""
        ontology_manager = OntologyManager()
        results = []
        
        # 온톨로지 로드 테스트
        load_start = time.time()
        try:
            # 기존 온톨로지 파일이 있다면 로드
            if Path("diet-ontology.ttl").exists():
                graph = ontology_manager.load_existing_ontology("diet-ontology.ttl")
                load_time = time.time() - load_start
                triples_count = len(graph) if graph else 0
            else:
                load_time = 0
                triples_count = 0
        except Exception as e:
            logger.error(f"Ontology load error: {e}")
            load_time = 0
            triples_count = 0
        
        results.append({
            "operation": "load_ontology",
            "execution_time": load_time,
            "triples_loaded": triples_count,
            "load_rate": triples_count / load_time if load_time > 0 else 0
        })
        
        # 온톨로지 저장 테스트
        if triples_count > 0:
            save_start = time.time()
            try:
                # 임시 파일로 저장 테스트
                temp_file = self.output_dir / "test_ontology.ttl"
                success = ontology_manager.save_ontology(graph, str(temp_file))
                save_time = time.time() - save_start
                
                # 파일 크기 확인
                file_size = temp_file.stat().st_size if temp_file.exists() else 0
                
                results.append({
                    "operation": "save_ontology",
                    "execution_time": save_time,
                    "triples_saved": triples_count,
                    "file_size_bytes": file_size,
                    "save_rate": triples_count / save_time if save_time > 0 else 0,
                    "success": success
                })
                
                # 임시 파일 삭제
                if temp_file.exists():
                    temp_file.unlink()
                    
            except Exception as e:
                logger.error(f"Ontology save error: {e}")
        
        return {
            "test_type": "ontology_operations",
            "results": results,
            "total_triples": triples_count
        }
    
    def benchmark_concurrent_processing(self) -> Dict[str, Any]:
        """동시 처리 성능 벤치마크"""
        test_data = self._generate_test_food_data(1000)
        worker_counts = [1, 2, 4, 8, 16]
        results = []
        
        def process_chunk(chunk):
            """데이터 청크 처리"""
            processed = []
            for item in chunk:
                if item.get('name') and item.get('calories'):
                    # 처리 시뮬레이션
                    time.sleep(0.001)  # 1ms 처리 시간
                    processed.append({
                        'name': item['name'],
                        'calories': item['calories'],
                        'processed_at': time.time()
                    })
            return processed
        
        for worker_count in worker_counts:
            chunk_size = len(test_data) // worker_count
            chunks = [test_data[i:i + chunk_size] for i in range(0, len(test_data), chunk_size)]
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
                results_list = []
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        results_list.extend(result)
                    except Exception as e:
                        logger.error(f"Concurrent processing error: {e}")
            
            execution_time = time.time() - start_time
            throughput = len(results_list) / execution_time if execution_time > 0 else 0
            
            results.append({
                "worker_count": worker_count,
                "execution_time": execution_time,
                "items_processed": len(results_list),
                "throughput": throughput,
                "efficiency": throughput / worker_count if worker_count > 0 else 0
            })
            
            logger.info(f"Concurrent processing with {worker_count} workers: {throughput:.2f} items/s")
        
        return {
            "test_type": "concurrent_processing",
            "results": results,
            "optimal_worker_count": max(results, key=lambda x: x["efficiency"])["worker_count"],
            "max_throughput": max(r["throughput"] for r in results)
        }
    
    def benchmark_batch_operations(self) -> Dict[str, Any]:
        """배치 작업 성능 벤치마크"""
        total_items = 10000
        batch_sizes = [10, 50, 100, 500, 1000]
        results = []
        
        test_data = self._generate_test_food_data(total_items)
        
        for batch_size in batch_sizes:
            batches = [test_data[i:i + batch_size] for i in range(0, len(test_data), batch_size)]
            
            start_time = time.time()
            processed_count = 0
            
            for batch in batches:
                # 배치 처리 시뮬레이션
                batch_start = time.time()
                
                # 배치 내 아이템 처리
                for item in batch:
                    if item.get('name') and item.get('calories'):
                        processed_count += 1
                
                batch_time = time.time() - batch_start
                
                # 배치 간 지연 시뮬레이션 (API 호출 등)
                time.sleep(0.01)  # 10ms
            
            total_time = time.time() - start_time
            throughput = processed_count / total_time if total_time > 0 else 0
            
            results.append({
                "batch_size": batch_size,
                "total_batches": len(batches),
                "execution_time": total_time,
                "items_processed": processed_count,
                "throughput": throughput,
                "avg_batch_time": total_time / len(batches) if batches else 0
            })
            
            logger.info(f"Batch processing (size {batch_size}): {throughput:.2f} items/s")
        
        return {
            "test_type": "batch_operations",
            "results": results,
            "optimal_batch_size": max(results, key=lambda x: x["throughput"])["batch_size"],
            "total_items": total_items
        }
    
    def _generate_test_food_data(self, size: int) -> List[Dict[str, Any]]:
        """테스트용 음식 데이터 생성"""
        foods = [
            {"name": "백미밥", "calories": 130, "carbs": 28.1, "protein": 2.5, "fat": 0.3, "category": "곡류"},
            {"name": "닭가슴살", "calories": 165, "carbs": 0, "protein": 31, "fat": 3.6, "category": "육류"},
            {"name": "사과", "calories": 52, "carbs": 13.8, "protein": 0.3, "fat": 0.2, "category": "과일"},
            {"name": "브로콜리", "calories": 34, "carbs": 7, "protein": 2.8, "fat": 0.4, "category": "채소"},
            {"name": "연어", "calories": 208, "carbs": 0, "protein": 25, "fat": 12, "category": "어류"}
        ]
        
        test_data = []
        for i in range(size):
            base_food = foods[i % len(foods)]
            test_item = {
                **base_food,
                "id": i,
                "name": f"{base_food['name']}_{i}",
                "manufacturer": f"제조사_{i % 10}"
            }
            test_data.append(test_item)
        
        return test_data
    
    def _simulate_api_call(self, endpoint: str) -> float:
        """API 호출 시뮬레이션"""
        # 실제 구현에서는 실제 API 호출
        delay = 0.5 + (hash(endpoint) % 100) / 100  # 0.5-1.5초 랜덤 지연
        time.sleep(delay)
        return delay
    
    def _save_results(self, results: Dict[str, Any]):
        """결과를 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 형태로 저장
        json_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # CSV 형태로 요약 저장
        csv_file = self.output_dir / f"benchmark_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Test Type', 'Metric', 'Value', 'Unit'])
            
            for test_type, test_results in results.items():
                if isinstance(test_results, dict) and 'summary' in test_results:
                    for metric, value in test_results['summary'].items():
                        writer.writerow([test_type, metric, value, ''])
        
        logger.info(f"Results saved to {json_file} and {csv_file}")
    
    def _generate_summary_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """종합 요약 리포트 생성"""
        summary = {
            "total_tests_run": len(results),
            "test_completion_rate": len([r for r in results.values() if not isinstance(r, dict) or 'error' not in r]) / len(results) * 100,
            "key_findings": [],
            "recommendations": []
        }
        
        # 주요 발견사항 추출
        for test_type, test_result in results.items():
            if isinstance(test_result, dict) and 'error' not in test_result:
                if test_type == "Data Processing":
                    max_throughput = test_result.get('summary', {}).get('max_throughput', 0)
                    if max_throughput > 0:
                        summary["key_findings"].append(f"최대 데이터 처리 속도: {max_throughput:.2f} items/sec")
                
                elif test_type == "API Calls":
                    speedup = test_result.get('speedup_factor', 0)
                    if speedup > 1:
                        summary["key_findings"].append(f"동시 API 호출로 {speedup:.2f}배 성능 향상")
                
                elif test_type == "Concurrent Processing":
                    optimal_workers = test_result.get('optimal_worker_count', 0)
                    if optimal_workers > 0:
                        summary["key_findings"].append(f"최적 동시 처리 워커 수: {optimal_workers}")
        
        # 권장사항 생성
        if any("API Calls" in r for r in results.keys()):
            summary["recommendations"].append("API 호출 최적화를 위해 동시 처리 및 배치 처리 활용 권장")
        
        if any("Memory" in r for r in results.keys()):
            summary["recommendations"].append("대량 데이터 처리 시 메모리 사용량 모니터링 및 가비지 컬렉션 최적화 필요")
        
        return summary


def run_performance_benchmark(output_dir: str = "benchmark_results") -> Dict[str, Any]:
    """성능 벤치마크 실행 (편의 함수)"""
    benchmark = PerformanceBenchmark(output_dir)
    return benchmark.run_all_benchmarks()


if __name__ == "__main__":
    # 벤치마크 실행
    logging.basicConfig(level=logging.INFO)
    results = run_performance_benchmark()
    
    print("\n=== 성능 벤치마크 완료 ===")
    print(f"총 {results['summary']['total_tests_run']}개 테스트 실행")
    print(f"완료율: {results['summary']['test_completion_rate']:.1f}%")
    
    if results['summary']['key_findings']:
        print("\n주요 발견사항:")
        for finding in results['summary']['key_findings']:
            print(f"- {finding}")
    
    if results['summary']['recommendations']:
        print("\n권장사항:")
        for recommendation in results['summary']['recommendations']:
            print(f"- {recommendation}")