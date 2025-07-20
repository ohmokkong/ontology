"""
캐시 매니저 통합 테스트 모듈.

캐시 저장/조회/만료 동작 검증 및 캐시 히트율 70% 이상 달성 확인을 포함한
포괄적인 캐시 시스템 테스트를 수행합니다.
"""

import os
import shutil
import tempfile
import threading
import time
import random
from datetime import datetime, timedelta
from cache_manager import CacheManager, CacheStats
from integrated_models import FoodItem, NutritionInfo, ExerciseItem


def test_cache_manager_basic():
    """기본 캐시 기능 테스트."""
    print("=== 캐시 매니저 기본 기능 테스트 ===")
    
    # 임시 캐시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(
            max_memory_entries=10,
            default_ttl=60,
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        # 테스트 데이터 생성
        test_foods = [
            FoodItem(
                name="백미밥",
                food_id="food_001",
                category="곡류",
                manufacturer=None
            ),
            FoodItem(
                name="현미밥",
                food_id="food_002", 
                category="곡류",
                manufacturer=None
            )
        ]
        
        test_exercise = [
            ExerciseItem(
                name="달리기",
                exercise_id="ex_001",
                category="유산소",
                met_value=8.0,
                description="빠른 속도로 달리기"
            )
        ]
        
        # 음식 캐시 테스트
        print("\n--- 음식 캐시 테스트 ---")
        
        # 캐시 저장
        cache_manager.cache_food_result("백미밥", test_foods)
        
        # 캐시 조회 (히트)
        cached_foods = cache_manager.get_cached_food("백미밥")
        assert cached_foods is not None
        assert len(cached_foods) == 2
        assert cached_foods[0].name == "백미밥"
        print("✓ 음식 캐시 저장/조회 성공")
        
        # 존재하지 않는 캐시 조회 (미스)
        missing_foods = cache_manager.get_cached_food("존재하지않는음식")
        assert missing_foods is None
        print("✓ 캐시 미스 처리 성공")
        
        # 운동 캐시 테스트
        print("\n--- 운동 캐시 테스트 ---")
        
        # 캐시 저장
        cache_manager.cache_exercise_result("달리기", test_exercise)
        
        # 캐시 조회 (히트)
        cached_exercises = cache_manager.get_cached_exercise("달리기")
        assert cached_exercises is not None
        assert len(cached_exercises) == 1
        assert cached_exercises[0].name == "달리기"
        print("✓ 운동 캐시 저장/조회 성공")
        
        # 영양정보 캐시 테스트
        print("\n--- 영양정보 캐시 테스트 ---")
        
        test_nutrition = NutritionInfo(
            food_item=test_foods[0],
            calories_per_100g=130.0,
            carbohydrate=28.1,
            protein=2.5,
            fat=0.3,
            fiber=0.4,
            sodium=2.0
        )
        
        # 캐시 저장
        cache_manager.cache_nutrition_result("food_001", test_nutrition)
        
        # 캐시 조회 (히트)
        cached_nutrition = cache_manager.get_cached_nutrition("food_001")
        assert cached_nutrition is not None
        assert cached_nutrition.calories_per_100g == 130.0
        print("✓ 영양정보 캐시 저장/조회 성공")
        
        # 캐시 통계 확인
        print("\n--- 캐시 통계 확인 ---")
        stats = cache_manager.get_cache_stats()
        print(f"  - 총 요청: {stats.total_requests}")
        print(f"  - 캐시 히트: {stats.cache_hits}")
        print(f"  - 캐시 미스: {stats.cache_misses}")
        print(f"  - 히트율: {stats.hit_rate:.1f}%")
        
        assert stats.total_requests > 0
        assert stats.cache_hits > 0
        assert stats.hit_rate > 0
        print("✓ 캐시 통계 정상 동작")
        
        # 캐시 정보 확인
        print("\n--- 캐시 정보 확인 ---")
        cache_info = cache_manager.get_cache_info()
        print(f"  - 메모리 캐시 엔트리: {cache_info['memory_cache']['entries']}")
        print(f"  - 디스크 캐시 활성화: {cache_info['disk_cache']['enabled']}")
        print(f"  - 기본 TTL: {cache_info['configuration']['default_ttl']}초")
        
        assert cache_info['memory_cache']['entries'] > 0
        assert cache_info['disk_cache']['enabled'] == True
        print("✓ 캐시 정보 조회 성공")
        
        print("\n✅ 모든 캐시 매니저 테스트 통과!")


def test_cache_expiration():
    """캐시 만료 테스트."""
    print("\n=== 캐시 만료 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 짧은 TTL로 캐시 매니저 생성
        cache_manager = CacheManager(
            max_memory_entries=10,
            default_ttl=1,  # 1초
            cache_dir=temp_dir,
            enable_disk_cache=False  # 빠른 테스트를 위해 디스크 캐시 비활성화
        )
        
        # 테스트 데이터
        test_foods = [
            FoodItem(
                name="테스트음식",
                food_id="test_001",
                category="테스트",
                manufacturer=None
            )
        ]
        
        # 캐시 저장
        cache_manager.cache_food_result("테스트음식", test_foods)
        
        # 즉시 조회 (히트)
        cached_foods = cache_manager.get_cached_food("테스트음식")
        assert cached_foods is not None
        print("✓ 즉시 캐시 조회 성공")
        
        # 만료 대기
        import time
        print("  대기 중: 캐시 만료 (2초)...")
        time.sleep(2)
        
        # 만료 후 조회 (미스)
        expired_foods = cache_manager.get_cached_food("테스트음식")
        assert expired_foods is None
        print("✓ 만료된 캐시 조회 실패 (정상)")
        
        # 통계 확인
        stats = cache_manager.get_cache_stats()
        assert stats.expired_entries > 0
        print(f"✓ 만료된 엔트리: {stats.expired_entries}개")
        
        print("✅ 캐시 만료 테스트 통과!")


def test_cache_optimization():
    """캐시 최적화 테스트."""
    print("\n=== 캐시 최적화 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(
            max_memory_entries=5,  # 작은 용량으로 테스트
            default_ttl=60,
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        # 여러 데이터 캐싱 (용량 초과)
        for i in range(10):
            test_foods = [
                FoodItem(
                    name=f"음식{i}",
                    food_id=f"food_{i:03d}",
                    category="테스트",
                    manufacturer=None
                )
            ]
            cache_manager.cache_food_result(f"음식{i}", test_foods)
        
        # 메모리 캐시 용량 확인
        cache_info = cache_manager.get_cache_info()
        memory_entries = cache_info['memory_cache']['entries']
        print(f"  - 메모리 캐시 엔트리: {memory_entries}")
        assert memory_entries <= 5  # 최대 용량 준수
        print("✓ LRU 정책으로 메모리 캐시 용량 관리")
        
        # 캐시 최적화 실행
        optimization_result = cache_manager.optimize_cache()
        print(f"  - 최적화 결과: {optimization_result}")
        
        print("✅ 캐시 최적화 테스트 통과!")


def test_cache_hit_rate_target():
    """캐시 히트율 70% 이상 달성 확인 테스트."""
    print("\n=== 캐시 히트율 목표 달성 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(
            max_memory_entries=50,
            default_ttl=300,  # 5분
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        # 테스트 데이터 준비 (실제 사용 패턴 시뮬레이션)
        common_foods = [
            "백미밥", "현미밥", "김치", "된장찌개", "불고기",
            "닭가슴살", "계란", "우유", "사과", "바나나"
        ]
        
        # 1단계: 초기 캐시 데이터 저장
        print("  1단계: 초기 캐시 데이터 저장")
        for i, food_name in enumerate(common_foods):
            test_foods = [
                FoodItem(
                    name=food_name,
                    food_id=f"food_{i:03d}",
                    category="일반식품",
                    manufacturer=None
                )
            ]
            cache_manager.cache_food_result(food_name, test_foods)
        
        # 2단계: 실제 사용 패턴 시뮬레이션 (자주 사용되는 음식 반복 조회)
        print("  2단계: 실제 사용 패턴 시뮬레이션 (100회 조회)")
        total_requests = 100
        
        for _ in range(total_requests):
            # 80%는 캐시된 음식, 20%는 새로운 음식 (실제 사용 패턴)
            if random.random() < 0.8:
                # 캐시된 음식 조회 (히트 예상)
                food_name = random.choice(common_foods)
                cache_manager.get_cached_food(food_name)
            else:
                # 새로운 음식 조회 (미스 예상)
                new_food_name = f"새음식_{random.randint(1000, 9999)}"
                cache_manager.get_cached_food(new_food_name)
        
        # 3단계: 히트율 확인
        stats = cache_manager.get_cache_stats()
        hit_rate = stats.hit_rate
        
        print(f"  - 총 요청: {stats.total_requests}")
        print(f"  - 캐시 히트: {stats.cache_hits}")
        print(f"  - 캐시 미스: {stats.cache_misses}")
        print(f"  - 달성 히트율: {hit_rate:.1f}%")
        print(f"  - 목표 히트율: 70.0%")
        
        # 히트율 70% 이상 달성 확인
        assert hit_rate >= 70.0, f"히트율 목표 미달성: {hit_rate:.1f}% < 70.0%"
        print("✅ 캐시 히트율 70% 이상 달성!")
        
        print("✅ 캐시 히트율 목표 달성 테스트 통과!")


def test_concurrent_cache_access():
    """동시 캐시 접근 테스트 (스레드 안전성)."""
    print("\n=== 동시 캐시 접근 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(
            max_memory_entries=100,
            default_ttl=60,
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        # 공유 데이터
        results = []
        errors = []
        
        def worker_thread(thread_id: int, operations: int):
            """워커 스레드 함수."""
            try:
                for i in range(operations):
                    food_name = f"thread_{thread_id}_food_{i}"
                    
                    # 테스트 데이터 생성
                    test_foods = [
                        FoodItem(
                            name=food_name,
                            food_id=f"food_{thread_id}_{i:03d}",
                            category=f"카테고리_{thread_id}",
                            manufacturer=None
                        )
                    ]
                    
                    # 캐시 저장
                    cache_manager.cache_food_result(food_name, test_foods)
                    
                    # 캐시 조회
                    cached_result = cache_manager.get_cached_food(food_name)
                    
                    if cached_result is not None:
                        results.append(f"thread_{thread_id}_success_{i}")
                    
                    # 짧은 대기
                    time.sleep(0.001)
                    
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
        
        # 여러 스레드로 동시 접근 테스트
        threads = []
        thread_count = 5
        operations_per_thread = 20
        
        print(f"  {thread_count}개 스레드로 동시 캐시 접근 테스트")
        
        # 스레드 시작
        for i in range(thread_count):
            thread = threading.Thread(
                target=worker_thread,
                args=(i, operations_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 확인
        expected_results = thread_count * operations_per_thread
        actual_results = len(results)
        
        print(f"  - 예상 성공 작업: {expected_results}")
        print(f"  - 실제 성공 작업: {actual_results}")
        print(f"  - 오류 발생: {len(errors)}")
        
        # 오류가 없어야 함
        assert len(errors) == 0, f"동시 접근 중 오류 발생: {errors}"
        
        # 대부분의 작업이 성공해야 함 (일부는 타이밍 이슈로 실패할 수 있음)
        success_rate = (actual_results / expected_results) * 100
        assert success_rate >= 90, f"성공률이 너무 낮음: {success_rate:.1f}%"
        
        print(f"✓ 동시 접근 성공률: {success_rate:.1f}%")
        print("✅ 동시 캐시 접근 테스트 통과!")


def test_disk_cache_persistence():
    """디스크 캐시 지속성 테스트."""
    print("\n=== 디스크 캐시 지속성 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1단계: 첫 번째 캐시 매니저로 데이터 저장
        print("  1단계: 첫 번째 캐시 매니저로 데이터 저장")
        cache_manager1 = CacheManager(
            max_memory_entries=10,
            default_ttl=300,
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        test_foods = [
            FoodItem(
                name="지속성테스트음식",
                food_id="persist_001",
                category="테스트",
                manufacturer=None
            )
        ]
        
        cache_manager1.cache_food_result("지속성테스트음식", test_foods)
        
        # 메모리 캐시에서 확인
        cached_result1 = cache_manager1.get_cached_food("지속성테스트음식")
        assert cached_result1 is not None
        print("✓ 첫 번째 캐시 매니저에서 저장/조회 성공")
        
        # 2단계: 두 번째 캐시 매니저로 디스크에서 로드
        print("  2단계: 두 번째 캐시 매니저로 디스크에서 로드")
        cache_manager2 = CacheManager(
            max_memory_entries=10,
            default_ttl=300,
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        # 디스크 캐시에서 로드 (메모리 캐시는 비어있음)
        cached_result2 = cache_manager2.get_cached_food("지속성테스트음식")
        assert cached_result2 is not None
        assert cached_result2[0].name == "지속성테스트음식"
        print("✓ 두 번째 캐시 매니저에서 디스크 캐시 로드 성공")
        
        print("✅ 디스크 캐시 지속성 테스트 통과!")


def test_cache_memory_disk_integration():
    """메모리-디스크 캐시 통합 테스트."""
    print("\n=== 메모리-디스크 캐시 통합 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(
            max_memory_entries=3,  # 작은 메모리 캐시
            default_ttl=60,
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        # 1단계: 메모리 캐시 용량 초과로 데이터 저장
        print("  1단계: 메모리 용량 초과 데이터 저장")
        foods_data = []
        for i in range(5):  # 메모리 용량(3)보다 많은 데이터
            food_name = f"통합테스트음식{i}"
            test_foods = [
                FoodItem(
                    name=food_name,
                    food_id=f"integrate_{i:03d}",
                    category="통합테스트",
                    manufacturer=None
                )
            ]
            foods_data.append((food_name, test_foods))
            cache_manager.cache_food_result(food_name, test_foods)
        
        # 2단계: 메모리에서 제거된 데이터가 디스크에서 로드되는지 확인
        print("  2단계: 메모리-디스크 캐시 통합 동작 확인")
        
        hit_count = 0
        for food_name, expected_data in foods_data:
            cached_result = cache_manager.get_cached_food(food_name)
            if cached_result is not None:
                hit_count += 1
                assert cached_result[0].name == food_name
        
        # 모든 데이터가 메모리 또는 디스크에서 조회되어야 함
        assert hit_count == len(foods_data), f"일부 데이터 손실: {hit_count}/{len(foods_data)}"
        print(f"✓ 모든 데이터 조회 성공: {hit_count}/{len(foods_data)}")
        
        # 3단계: 캐시 통계 확인
        stats = cache_manager.get_cache_stats()
        print(f"  - 총 요청: {stats.total_requests}")
        print(f"  - 메모리 히트: {stats.cache_hits}")
        print(f"  - 전체 히트율: {stats.hit_rate:.1f}%")
        
        # 통합 캐시 시스템이 정상 동작해야 함
        assert stats.hit_rate > 0, "캐시 히트율이 0%입니다"
        
        print("✅ 메모리-디스크 캐시 통합 테스트 통과!")


def test_cache_performance_benchmark():
    """캐시 성능 벤치마크 테스트."""
    print("\n=== 캐시 성능 벤치마크 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(
            max_memory_entries=1000,
            default_ttl=300,
            cache_dir=temp_dir,
            enable_disk_cache=True
        )
        
        # 테스트 데이터 준비
        test_data_count = 500
        test_foods_data = []
        
        for i in range(test_data_count):
            food_name = f"벤치마크음식{i}"
            test_foods = [
                FoodItem(
                    name=food_name,
                    food_id=f"bench_{i:04d}",
                    category="벤치마크",
                    manufacturer=None
                )
            ]
            test_foods_data.append((food_name, test_foods))
        
        # 1단계: 캐시 저장 성능 측정
        print(f"  1단계: {test_data_count}개 데이터 캐시 저장 성능 측정")
        start_time = time.time()
        
        for food_name, test_foods in test_foods_data:
            cache_manager.cache_food_result(food_name, test_foods)
        
        store_time = time.time() - start_time
        store_rate = test_data_count / store_time
        
        print(f"  - 저장 시간: {store_time:.3f}초")
        print(f"  - 저장 속도: {store_rate:.1f}개/초")
        
        # 2단계: 캐시 조회 성능 측정
        print(f"  2단계: {test_data_count}개 데이터 캐시 조회 성능 측정")
        start_time = time.time()
        
        hit_count = 0
        for food_name, _ in test_foods_data:
            cached_result = cache_manager.get_cached_food(food_name)
            if cached_result is not None:
                hit_count += 1
        
        retrieve_time = time.time() - start_time
        retrieve_rate = test_data_count / retrieve_time
        
        print(f"  - 조회 시간: {retrieve_time:.3f}초")
        print(f"  - 조회 속도: {retrieve_rate:.1f}개/초")
        print(f"  - 조회 성공: {hit_count}/{test_data_count}")
        
        # 성능 기준 확인 (디스크 I/O를 고려한 현실적인 기준)
        assert store_rate > 10, f"저장 속도가 너무 느림: {store_rate:.1f}개/초"
        assert retrieve_rate > 100, f"조회 속도가 너무 느림: {retrieve_rate:.1f}개/초"
        assert hit_count == test_data_count, f"일부 데이터 조회 실패: {hit_count}/{test_data_count}"
        
        print("✅ 캐시 성능 벤치마크 테스트 통과!")


if __name__ == "__main__":
    try:
        # 기본 기능 테스트
        test_cache_manager_basic()
        test_cache_expiration()
        test_cache_optimization()
        
        # 통합 테스트 (Task 4.2 요구사항)
        test_cache_hit_rate_target()
        test_concurrent_cache_access()
        test_disk_cache_persistence()
        test_cache_memory_disk_integration()
        test_cache_performance_benchmark()
        
        print("\n🎉 모든 캐시 매니저 통합 테스트가 성공적으로 완료되었습니다!")
        print("✅ 캐시 히트율 70% 이상 달성 확인")
        print("✅ 캐시 저장/조회/만료 동작 검증 완료")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()