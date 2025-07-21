"""
진행 상황 표시 기능 통합 예제

이 모듈은 기존 시스템에 진행률 표시 기능을 통합하는 방법을 보여줍니다.
- 음식 데이터 배치 처리
- API 호출 진행률 표시
- 온톨로지 생성 진행률
- 대량 데이터 처리 모니터링
"""

import time
import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from progress_manager import (
    progress_context, create_progress_task, start_progress_task,
    update_progress, increment_progress, complete_progress_task,
    cancel_progress_task, is_task_cancelled, wait_if_task_paused,
    ProgressStyle, progress_manager
)
from performance_monitor import measure_performance
from food_models import FoodItem, NutritionInfo
from integrated_models import ExerciseItem, ExerciseSession

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProgressIntegratedFoodProcessor:
    """진행률 표시가 통합된 음식 데이터 프로세서"""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
    
    @measure_performance("batch_food_processing")
    def process_food_batch(self, food_data: List[Dict[str, Any]], 
                          task_id: str = "food_batch_processing") -> List[NutritionInfo]:
        """음식 데이터 배치 처리 (진행률 표시 포함)"""
        
        # 진행률 작업 생성
        task = create_progress_task(
            task_id=task_id,
            name="음식 데이터 배치 처리",
            total_items=len(food_data),
            style=ProgressStyle.DETAILED
        )
        
        start_progress_task(task_id)
        processed_items = []
        
        try:
            for i, food_item_data in enumerate(food_data):
                # 취소 확인
                if is_task_cancelled(task_id):
                    logger.info(f"Food batch processing cancelled at item {i}")
                    break
                
                # 일시정지 확인
                wait_if_task_paused(task_id)
                
                try:
                    # 음식 아이템 처리
                    nutrition_info = self._process_single_food_item(food_item_data)
                    if nutrition_info:
                        processed_items.append(nutrition_info)
                        self.processed_count += 1
                    
                    # 진행률 업데이트
                    current_operation = f"처리 중: {food_item_data.get('name', 'Unknown')}"
                    update_progress(
                        task_id, 
                        i + 1, 
                        current_operation,
                        processed_count=len(processed_items),
                        error_count=self.error_count
                    )
                    
                    # 처리 시간 시뮬레이션
                    time.sleep(0.01)
                    
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error processing food item {i}: {e}")
                    
                    # 오류가 있어도 진행률은 업데이트
                    update_progress(
                        task_id, 
                        i + 1, 
                        f"오류 발생: {food_item_data.get('name', 'Unknown')}",
                        processed_count=len(processed_items),
                        error_count=self.error_count
                    )
            
            # 완료 처리
            if not is_task_cancelled(task_id):
                complete_progress_task(task_id)
                logger.info(f"Food batch processing completed: {len(processed_items)} items processed")
            
        except Exception as e:
            progress_manager.fail_task(task_id, str(e))
            logger.error(f"Food batch processing failed: {e}")
            raise
        
        return processed_items
    
    def _process_single_food_item(self, food_data: Dict[str, Any]) -> NutritionInfo:
        """단일 음식 아이템 처리"""
        if not food_data.get('name') or not food_data.get('calories'):
            return None
        
        food_item = FoodItem(
            name=food_data['name'],
            food_id=str(food_data.get('id', 0)),
            category=food_data.get('category'),
            manufacturer=food_data.get('manufacturer')
        )
        
        nutrition_info = NutritionInfo(
            food_item=food_item,
            calories_per_100g=float(food_data['calories']),
            carbohydrate=float(food_data.get('carbs', 0)),
            protein=float(food_data.get('protein', 0)),
            fat=float(food_data.get('fat', 0))
        )
        
        return nutrition_info


class ProgressIntegratedAPIClient:
    """진행률 표시가 통합된 API 클라이언트"""
    
    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
    
    async def batch_api_requests(self, requests: List[Dict[str, Any]], 
                                task_id: str = "api_batch_requests") -> List[Dict[str, Any]]:
        """배치 API 요청 (진행률 표시 포함)"""
        
        # 진행률 작업 생성
        task = create_progress_task(
            task_id=task_id,
            name="API 배치 요청 처리",
            total_items=len(requests),
            style=ProgressStyle.DETAILED
        )
        
        start_progress_task(task_id)
        results = []
        
        try:
            for i, request_data in enumerate(requests):
                # 취소 확인
                if is_task_cancelled(task_id):
                    logger.info(f"API batch requests cancelled at request {i}")
                    break
                
                # 일시정지 확인
                wait_if_task_paused(task_id)
                
                try:
                    # API 요청 시뮬레이션
                    result = await self._make_api_request(request_data)
                    results.append(result)
                    self.success_count += 1
                    
                    # 진행률 업데이트
                    current_operation = f"요청 완료: {request_data.get('endpoint', 'Unknown')}"
                    update_progress(
                        task_id,
                        i + 1,
                        current_operation,
                        success_count=self.success_count,
                        error_count=self.error_count,
                        response_time=result.get('response_time', 0)
                    )
                    
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"API request {i} failed: {e}")
                    
                    # 오류 결과 추가
                    results.append({
                        'error': str(e),
                        'request': request_data
                    })
                    
                    # 진행률 업데이트 (오류 포함)
                    update_progress(
                        task_id,
                        i + 1,
                        f"요청 실패: {request_data.get('endpoint', 'Unknown')}",
                        success_count=self.success_count,
                        error_count=self.error_count
                    )
                
                self.request_count += 1
            
            # 완료 처리
            if not is_task_cancelled(task_id):
                complete_progress_task(task_id)
                logger.info(f"API batch requests completed: {self.success_count}/{len(requests)} successful")
            
        except Exception as e:
            progress_manager.fail_task(task_id, str(e))
            logger.error(f"API batch requests failed: {e}")
            raise
        
        return results
    
    async def _make_api_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """단일 API 요청 시뮬레이션"""
        # 요청 시간 시뮬레이션
        delay = request_data.get('delay', 0.1)
        await asyncio.sleep(delay)
        
        # 가끔 오류 시뮬레이션
        if request_data.get('simulate_error', False):
            raise Exception("Simulated API error")
        
        return {
            'status': 'success',
            'endpoint': request_data.get('endpoint', 'unknown'),
            'response_time': delay,
            'data': {'result': 'success'}
        }


class ProgressIntegratedOntologyBuilder:
    """진행률 표시가 통합된 온톨로지 빌더"""
    
    def __init__(self):
        self.triples_generated = 0
        self.files_processed = 0
    
    def build_ontology_from_data(self, data_sources: List[str], 
                                task_id: str = "ontology_building") -> Dict[str, Any]:
        """데이터로부터 온톨로지 구축 (진행률 표시 포함)"""
        
        # 총 단계 계산 (데이터 로드 + 변환 + 병합 + 저장)
        total_steps = len(data_sources) * 3 + 2  # 각 소스당 3단계 + 병합 + 저장
        
        task = create_progress_task(
            task_id=task_id,
            name="온톨로지 구축",
            total_items=total_steps,
            style=ProgressStyle.DETAILED
        )
        
        start_progress_task(task_id)
        current_step = 0
        
        try:
            ontology_data = []
            
            # 1단계: 데이터 소스 처리
            for i, source in enumerate(data_sources):
                if is_task_cancelled(task_id):
                    break
                
                wait_if_task_paused(task_id)
                
                # 데이터 로드
                current_step += 1
                update_progress(
                    task_id,
                    current_step,
                    f"데이터 로드 중: {source}",
                    current_source=source,
                    files_processed=self.files_processed
                )
                
                data = self._load_data_source(source)
                time.sleep(0.1)  # 로드 시간 시뮬레이션
                
                # 데이터 변환
                current_step += 1
                update_progress(
                    task_id,
                    current_step,
                    f"RDF 변환 중: {source}",
                    current_source=source,
                    triples_generated=self.triples_generated
                )
                
                rdf_data = self._convert_to_rdf(data)
                time.sleep(0.2)  # 변환 시간 시뮬레이션
                
                # 검증
                current_step += 1
                update_progress(
                    task_id,
                    current_step,
                    f"데이터 검증 중: {source}",
                    current_source=source
                )
                
                validated_data = self._validate_rdf_data(rdf_data)
                ontology_data.append(validated_data)
                self.files_processed += 1
                time.sleep(0.05)  # 검증 시간 시뮬레이션
            
            if not is_task_cancelled(task_id):
                # 2단계: 온톨로지 병합
                current_step += 1
                update_progress(
                    task_id,
                    current_step,
                    "온톨로지 병합 중...",
                    merge_phase=True,
                    total_sources=len(ontology_data)
                )
                
                merged_ontology = self._merge_ontologies(ontology_data)
                time.sleep(0.3)  # 병합 시간 시뮬레이션
                
                # 3단계: 온톨로지 저장
                current_step += 1
                update_progress(
                    task_id,
                    current_step,
                    "온톨로지 저장 중...",
                    save_phase=True,
                    total_triples=self.triples_generated
                )
                
                result = self._save_ontology(merged_ontology)
                time.sleep(0.1)  # 저장 시간 시뮬레이션
                
                complete_progress_task(task_id)
                logger.info(f"Ontology building completed: {self.triples_generated} triples, {self.files_processed} files")
                
                return result
            
        except Exception as e:
            progress_manager.fail_task(task_id, str(e))
            logger.error(f"Ontology building failed: {e}")
            raise
        
        return {}
    
    def _load_data_source(self, source: str) -> List[Dict[str, Any]]:
        """데이터 소스 로드 시뮬레이션"""
        # 실제 구현에서는 파일이나 API에서 데이터 로드
        return [{'id': i, 'name': f'item_{i}', 'source': source} for i in range(10)]
    
    def _convert_to_rdf(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """RDF 변환 시뮬레이션"""
        self.triples_generated += len(data) * 3  # 각 아이템당 3개 트리플
        return {'triples': len(data) * 3, 'data': data}
    
    def _validate_rdf_data(self, rdf_data: Dict[str, Any]) -> Dict[str, Any]:
        """RDF 데이터 검증 시뮬레이션"""
        return {'validated': True, **rdf_data}
    
    def _merge_ontologies(self, ontology_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """온톨로지 병합 시뮬레이션"""
        total_triples = sum(data.get('triples', 0) for data in ontology_data)
        return {'merged_triples': total_triples, 'sources': len(ontology_data)}
    
    def _save_ontology(self, ontology: Dict[str, Any]) -> Dict[str, Any]:
        """온톨로지 저장 시뮬레이션"""
        return {
            'saved': True,
            'file_path': 'generated_ontology.ttl',
            'triples': ontology.get('merged_triples', 0),
            'timestamp': datetime.now().isoformat()
        }


def demo_progress_integration():
    """진행률 통합 데모"""
    print("=== 진행률 표시 기능 통합 데모 ===\n")
    
    # 1. 음식 데이터 배치 처리 데모
    print("1. 음식 데이터 배치 처리 데모")
    food_processor = ProgressIntegratedFoodProcessor()
    
    # 테스트 음식 데이터
    test_food_data = [
        {'id': i, 'name': f'음식_{i}', 'calories': 100 + i, 'carbs': 20 + i, 
         'protein': 10 + i, 'fat': 5 + i, 'category': '테스트'}
        for i in range(50)
    ]
    
    try:
        with progress_context("food_demo", "음식 데이터 처리 데모", len(test_food_data)):
            processed_foods = food_processor.process_food_batch(test_food_data, "food_demo")
            print(f"처리 완료: {len(processed_foods)}개 음식 아이템")
    except Exception as e:
        print(f"음식 데이터 처리 오류: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 2. API 배치 요청 데모
    print("2. API 배치 요청 데모")
    api_client = ProgressIntegratedAPIClient()
    
    # 테스트 API 요청들
    test_requests = [
        {'endpoint': f'/api/food/{i}', 'delay': 0.05, 'simulate_error': i % 10 == 0}
        for i in range(30)
    ]
    
    async def api_demo():
        try:
            results = await api_client.batch_api_requests(test_requests, "api_demo")
            success_count = sum(1 for r in results if 'error' not in r)
            print(f"API 요청 완료: {success_count}/{len(results)} 성공")
        except Exception as e:
            print(f"API 요청 오류: {e}")
    
    asyncio.run(api_demo())
    
    print("\n" + "="*50 + "\n")
    
    # 3. 온톨로지 구축 데모
    print("3. 온톨로지 구축 데모")
    ontology_builder = ProgressIntegratedOntologyBuilder()
    
    # 테스트 데이터 소스들
    test_sources = ['food_data.json', 'exercise_data.json', 'nutrition_data.json']
    
    try:
        result = ontology_builder.build_ontology_from_data(test_sources, "ontology_demo")
        print(f"온톨로지 구축 완료: {result}")
    except Exception as e:
        print(f"온톨로지 구축 오류: {e}")
    
    print("\n=== 데모 완료 ===")
    
    # 최종 통계
    all_tasks = progress_manager.get_all_tasks()
    print(f"\n총 실행된 작업: {len(all_tasks)}개")
    
    for task_id, task in all_tasks.items():
        print(f"- {task.name}: {task.status.value} ({task.progress_percentage:.1f}%)")


def demo_cancellation_and_restart():
    """취소 및 재시작 데모"""
    print("\n=== 작업 취소 및 재시작 데모 ===")
    
    # 장시간 실행 작업 시뮬레이션
    task_id = "long_running_demo"
    task = create_progress_task(task_id, "장시간 실행 작업", 1000, ProgressStyle.DETAILED)
    start_progress_task(task_id)
    
    import threading
    
    def long_running_worker():
        for i in range(1000):
            if is_task_cancelled(task_id):
                print(f"작업이 {i}번째 아이템에서 취소되었습니다.")
                break
            
            wait_if_task_paused(task_id)
            time.sleep(0.01)
            increment_progress(task_id, 1, f"처리 중: 아이템 {i+1}")
    
    # 워커 스레드 시작
    worker_thread = threading.Thread(target=long_running_worker)
    worker_thread.start()
    
    # 잠시 후 취소
    time.sleep(0.5)
    print("작업을 취소합니다...")
    cancel_progress_task(task_id)
    
    worker_thread.join(timeout=2.0)
    
    # 작업 상태 확인
    task = progress_manager.get_task_progress(task_id)
    print(f"취소된 작업 상태: {task.status.value}, 진행률: {task.progress_percentage:.1f}%")
    
    # 재시작
    print("작업을 재시작합니다...")
    progress_manager.restart_task(task_id)
    start_progress_task(task_id)
    
    # 짧은 작업으로 완료
    for i in range(10):
        increment_progress(task_id, 1, f"재시작 후 처리: 아이템 {i+1}")
        time.sleep(0.05)
    
    complete_progress_task(task_id)
    
    final_task = progress_manager.get_task_progress(task_id)
    print(f"재시작 후 작업 상태: {final_task.status.value}, 진행률: {final_task.progress_percentage:.1f}%")


if __name__ == "__main__":
    try:
        # 메인 데모 실행
        demo_progress_integration()
        
        # 취소/재시작 데모 실행
        demo_cancellation_and_restart()
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    finally:
        # 진행률 관리자 정리
        progress_manager.stop()
        print("진행률 관리자가 종료되었습니다.")