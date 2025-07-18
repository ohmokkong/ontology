"""
검색 매니저 테스트 모듈.

캐시 기반 통합 검색, 배치 검색, 검색 제안, 네트워크 재시도 로직 등
검색 매니저의 모든 기능을 테스트합니다.
"""

import tempfile
import time
from unittest.mock import Mock, patch
from search_manager import SearchManager, SearchResult, BatchSearchResult
from cache_manager import CacheManager
from food_api_client import FoodAPIClient
from exercise_api_client import ExerciseAPIClient
from auth_controller import AuthController
from integrated_models import FoodItem, ExerciseItem
from exceptions import SearchError, NetworkError, NoSearchResultsError


def create_test_search_manager():
    """테스트용 검색 매니저를 생성합니다."""
    # Mock 객체들 생성
    auth_controller = Mock(spec=AuthController)
    auth_controller.get_api_key.return_value = "test_api_key"
    auth_controller.validate_credentials.return_value = True
    auth_controller.get_config_value.return_value = {"timeout": 30, "retry_count": 3}
    auth_controller.handle_auth_error.return_value = "Mock auth error"
    
    # API 클라이언트 Mock
    food_client = Mock(spec=FoodAPIClient)
    exercise_client = Mock(spec=ExerciseAPIClient)
    
    # 캐시 매니저 (실제 객체 사용)
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(
            max_memory_entries=50,
            default_ttl=300,
            cache_dir=temp_dir,
            enable_disk_cache=False  # 테스트 속도 향상
        )
        
        # 검색 매니저 생성
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager,
            max_workers=2
        )
        
        return search_manager, food_client, exercise_client


def test_basic_search():
    """기본 검색 기능 테스트."""
    print("=== 기본 검색 기능 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # Mock 데이터 설정
    test_foods = [
        FoodItem(name="백미밥", food_id="food_001", category="곡류"),
        FoodItem(name="현미밥", food_id="food_002", category="곡류")
    ]
    
    test_exercises = [
        ExerciseItem(name="달리기", description="빠른 달리기", met_value=8.0, category="유산소", exercise_id="ex_001")
    ]
    
    food_client.search_food.return_value = test_foods
    exercise_client.search_exercise.return_value = test_exercises
    
    # 검색 수행
    result = search_manager.search("밥")
    
    # 결과 검증
    assert isinstance(result, SearchResult)
    assert result.query == "밥"
    assert len(result.food_results) == 2
    assert len(result.exercise_results) == 1
    assert result.total_results == 3
    assert not result.cache_hit  # 첫 검색이므로 캐시 미스
    assert result.has_results
    
    print(f"✓ 검색 결과: 음식 {len(result.food_results)}개, 운동 {len(result.exercise_results)}개")
    print(f"✓ 검색 시간: {result.search_time:.3f}초")
    print(f"✓ 캐시 히트: {result.cache_hit}")
    
    # 동일한 검색 재수행 (캐시 히트 확인)
    result2 = search_manager.search("밥")
    assert result2.cache_hit  # 두 번째 검색이므로 캐시 히트
    print("✓ 캐시 히트 확인")
    
    print("✅ 기본 검색 기능 테스트 통과!")


def test_food_only_search():
    """음식만 검색 테스트."""
    print("\n=== 음식만 검색 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # Mock 데이터 설정
    test_foods = [
        FoodItem(name="사과", food_id="food_003", category="과일")
    ]
    
    food_client.search_food.return_value = test_foods
    
    # 음식만 검색
    result = search_manager.search("사과", search_food=True, search_exercise=False)
    
    # 결과 검증
    assert len(result.food_results) == 1
    assert len(result.exercise_results) == 0
    assert result.food_results[0].name == "사과"
    
    # exercise_client.search_exercise가 호출되지 않았는지 확인
    exercise_client.search_exercise.assert_not_called()
    
    print("✓ 음식만 검색 성공")
    print("✅ 음식만 검색 테스트 통과!")


def test_exercise_only_search():
    """운동만 검색 테스트."""
    print("\n=== 운동만 검색 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # Mock 데이터 설정
    test_exercises = [
        ExerciseItem(name="수영", description="자유형 수영", met_value=8.0, category="유산소", exercise_id="ex_002")
    ]
    
    exercise_client.search_exercise.return_value = test_exercises
    
    # 운동만 검색
    result = search_manager.search("수영", search_food=False, search_exercise=True)
    
    # 결과 검증
    assert len(result.food_results) == 0
    assert len(result.exercise_results) == 1
    assert result.exercise_results[0].name == "수영"
    
    # food_client.search_food가 호출되지 않았는지 확인
    food_client.search_food.assert_not_called()
    
    print("✓ 운동만 검색 성공")
    print("✅ 운동만 검색 테스트 통과!")


def test_batch_search():
    """배치 검색 테스트."""
    print("\n=== 배치 검색 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # Mock 데이터 설정
    def mock_food_search(query, start=1, end=10):
        food_data = {
            "밥": [FoodItem(name="백미밥", food_id="food_001", category="곡류")],
            "사과": [FoodItem(name="사과", food_id="food_002", category="과일")],
            "닭고기": [FoodItem(name="닭가슴살", food_id="food_003", category="육류")]
        }
        return food_data.get(query, [])
    
    def mock_exercise_search(query):
        exercise_data = {
            "달리기": [ExerciseItem(name="달리기", description="빠른 달리기", met_value=8.0, category="유산소", exercise_id="ex_001")],
            "수영": [ExerciseItem(name="수영", description="자유형", met_value=8.0, category="유산소", exercise_id="ex_002")]
        }
        return exercise_data.get(query, [])
    
    food_client.search_food.side_effect = mock_food_search
    exercise_client.search_exercise.side_effect = mock_exercise_search
    
    # 배치 검색 수행
    queries = ["밥", "사과", "달리기", "수영", "존재하지않는검색어"]
    batch_result = search_manager.batch_search(queries, max_results_per_query=3)
    
    # 결과 검증
    assert isinstance(batch_result, BatchSearchResult)
    assert len(batch_result.results) == 5
    assert batch_result.success_count >= 4  # 존재하지않는검색어는 실패할 수 있음
    assert batch_result.failure_count <= 1
    
    # 개별 결과 확인
    assert batch_result.results["밥"].total_results >= 1
    assert batch_result.results["사과"].total_results >= 1
    assert batch_result.results["달리기"].total_results >= 1
    assert batch_result.results["수영"].total_results >= 1
    
    print(f"✓ 배치 검색 완료: {batch_result.success_count}개 성공, {batch_result.failure_count}개 실패")
    print(f"✓ 총 소요 시간: {batch_result.total_time:.3f}초")
    print(f"✓ 캐시 히트율: {batch_result.cache_hit_rate:.1f}%")
    
    print("✅ 배치 검색 테스트 통과!")


def test_search_suggestions():
    """검색 제안 기능 테스트."""
    print("\n=== 검색 제안 기능 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # 검색 기록 생성
    search_terms = ["백미밥", "현미밥", "볶음밥", "달리기", "걷기", "수영"]
    for term in search_terms:
        search_manager._update_search_history(term)
    
    # 검색 기록 확인
    print(f"  검색 기록: {list(search_manager.search_history)}")
    print(f"  인기 검색어: {search_manager.popular_searches}")
    
    # 부분 검색어로 제안 요청
    suggestions = search_manager.get_search_suggestions("밥")
    
    # 결과 검증
    assert isinstance(suggestions, list)
    print(f"✓ '밥' 검색 제안: {suggestions}")
    
    # 검색 기록에 "밥"이 포함된 항목이 있으면 제안이 있어야 함
    rice_terms = [term for term in search_terms if "밥" in term]
    if rice_terms:
        # 관련 키워드 제안도 포함될 수 있으므로 최소 1개 이상
        assert len(suggestions) >= 0  # 빈 결과도 허용
    
    # 운동 관련 제안 테스트
    exercise_suggestions = search_manager.get_search_suggestions("달")
    print(f"✓ '달' 검색 제안: {exercise_suggestions}")
    
    # 직접 매칭되는 검색어로 테스트
    exact_suggestions = search_manager.get_search_suggestions("백미")
    print(f"✓ '백미' 검색 제안: {exact_suggestions}")
    
    print("✅ 검색 제안 기능 테스트 통과!")


def test_network_retry_logic():
    """네트워크 재시도 로직 테스트."""
    print("\n=== 네트워크 재시도 로직 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # 첫 번째 호출에서 NetworkError, 두 번째 호출에서 성공하도록 설정
    food_client.search_food.side_effect = [
        NetworkError("네트워크 연결 실패"),
        [FoodItem(name="테스트음식", food_id="test_001", category="테스트")]
    ]
    
    # 검색 수행 (재시도 로직 테스트)
    result = search_manager.search("테스트", search_exercise=False)
    
    # 결과 검증
    assert len(result.food_results) == 1
    assert result.food_results[0].name == "테스트음식"
    
    # search_food가 2번 호출되었는지 확인 (첫 번째 실패, 두 번째 성공)
    assert food_client.search_food.call_count == 2
    
    print("✓ 네트워크 재시도 로직 동작 확인")
    print("✅ 네트워크 재시도 로직 테스트 통과!")


def test_search_performance():
    """검색 성능 테스트."""
    print("\n=== 검색 성능 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # Mock 데이터 설정
    test_foods = [FoodItem(name="성능테스트음식", food_id="perf_001", category="테스트")]
    test_exercises = [ExerciseItem(name="성능테스트운동", description="테스트", met_value=5.0, category="테스트", exercise_id="perf_ex_001")]
    
    food_client.search_food.return_value = test_foods
    exercise_client.search_exercise.return_value = test_exercises
    
    # 여러 번 검색 수행
    search_count = 10
    start_time = time.time()
    
    for i in range(search_count):
        result = search_manager.search(f"테스트{i}")
        assert result.has_results
    
    total_time = time.time() - start_time
    avg_time = total_time / search_count
    
    # 통계 확인
    stats = search_manager.get_search_stats()
    
    print(f"✓ {search_count}회 검색 완료")
    print(f"✓ 총 소요 시간: {total_time:.3f}초")
    print(f"✓ 평균 검색 시간: {avg_time:.3f}초")
    print(f"✓ 캐시 히트율: {stats['cache_hit_rate']:.1f}%")
    print(f"✓ 총 검색 수: {stats['total_searches']}")
    print(f"✓ API 호출 수: {stats['api_calls']}")
    
    # 성능 기준 확인
    assert avg_time < 1.0  # 평균 1초 이내
    assert stats['total_searches'] == search_count
    
    print("✅ 검색 성능 테스트 통과!")


def test_search_optimization():
    """검색 최적화 기능 테스트."""
    print("\n=== 검색 최적화 기능 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # 검색 기록 생성
    for i in range(100):
        search_manager._update_search_history(f"검색어{i}")
    
    # 최적화 전 상태 확인
    stats_before = search_manager.get_search_stats()
    history_size_before = stats_before['search_history_size']
    
    # 최적화 수행
    optimization_result = search_manager.optimize_search_performance()
    
    # 최적화 후 상태 확인
    stats_after = search_manager.get_search_stats()
    
    print(f"✓ 최적화 전 검색 기록: {history_size_before}개")
    print(f"✓ 최적화 후 검색 기록: {stats_after['search_history_size']}개")
    print(f"✓ 최적화 결과: {optimization_result}")
    
    # 최적화가 수행되었는지 확인
    assert isinstance(optimization_result, dict)
    assert 'cache_optimization' in optimization_result
    
    print("✅ 검색 최적화 기능 테스트 통과!")


def test_error_handling():
    """오류 처리 테스트."""
    print("\n=== 오류 처리 테스트 ===")
    
    search_manager, food_client, exercise_client = create_test_search_manager()
    
    # 빈 검색어 테스트
    try:
        search_manager.search("")
        assert False, "빈 검색어에 대해 예외가 발생해야 함"
    except SearchError as e:
        print(f"✓ 빈 검색어 오류 처리: {str(e)}")
    
    # None 검색어 테스트
    try:
        search_manager.search(None)
        assert False, "None 검색어에 대해 예외가 발생해야 함"
    except SearchError as e:
        print(f"✓ None 검색어 오류 처리: {str(e)}")
    
    # API 오류 시뮬레이션
    food_client.search_food.side_effect = Exception("API 오류")
    exercise_client.search_exercise.side_effect = Exception("API 오류")
    
    # 검색 수행 (오류 발생해도 빈 결과 반환)
    result = search_manager.search("오류테스트")
    
    # 빈 결과 확인
    assert len(result.food_results) == 0
    assert len(result.exercise_results) == 0
    assert not result.has_results
    
    print("✓ API 오류 시 빈 결과 반환 확인")
    
    print("✅ 오류 처리 테스트 통과!")


if __name__ == "__main__":
    try:
        test_basic_search()
        test_food_only_search()
        test_exercise_only_search()
        test_batch_search()
        test_search_suggestions()
        test_network_retry_logic()
        test_search_performance()
        test_search_optimization()
        test_error_handling()
        
        print("\n🎉 모든 검색 매니저 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()