"""
검색 매니저 테스트 모듈.

캐시 기반 통합 검색, 배치 검색, 검색 제안, 네트워크 오류 재시도 등의 
기능을 포괄적으로 테스트합니다.
"""

import time
import tempfile
from unittest.mock import Mock, patch, MagicMock
from search_manager import SearchManager, SearchResult, BatchSearchResult, SearchSuggestion
from cache_manager import CacheManager
from integrated_models import FoodItem, NutritionInfo, ExerciseItem
from exceptions import SearchError, NetworkError, NoSearchResultsError


def create_mock_food_client():
    """Mock 음식 API 클라이언트 생성."""
    mock_client = Mock()
    
    # 기본 음식 검색 결과
    mock_foods = [
        FoodItem(name="백미밥", food_id="food_001", category="곡류", manufacturer=None),
        FoodItem(name="현미밥", food_id="food_002", category="곡류", manufacturer=None),
        FoodItem(name="김치", food_id="food_003", category="채소류", manufacturer=None)
    ]
    
    mock_client.search_food.return_value = mock_foods
    return mock_client


def create_mock_exercise_client():
    """Mock 운동 API 클라이언트 생성."""
    mock_client = Mock()
    
    # 기본 운동 검색 결과
    mock_exercises = [
        ExerciseItem(name="달리기", exercise_id="ex_001", category="유산소", met_value=8.0, description="빠른 달리기"),
        ExerciseItem(name="걷기", exercise_id="ex_002", category="유산소", met_value=3.5, description="보통 속도 걷기")
    ]
    
    mock_client.search_exercise.return_value = mock_exercises
    
    # 지원 운동 목록
    mock_client.get_supported_exercises.return_value = {
        "달리기": 8.0,
        "걷기": 3.5,
        "수영": 8.0,
        "자전거타기": 6.8,
        "등산": 6.0
    }
    
    return mock_client


def test_search_manager_initialization():
    """검색 매니저 초기화 테스트."""
    print("=== 검색 매니저 초기화 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        # 검색 매니저 생성
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager,
            max_workers=3,
            suggestion_threshold=0.7
        )
        
        # 초기화 확인
        assert search_manager.food_client == food_client
        assert search_manager.exercise_client == exercise_client
        assert search_manager.cache_manager == cache_manager
        assert search_manager.max_workers == 3
        assert search_manager.suggestion_threshold == 0.7
        
        # 초기 통계 확인
        stats = search_manager.get_search_stats()
        assert stats["search_statistics"]["total_searches"] == 0
        assert stats["search_statistics"]["cache_hits"] == 0
        
        print("✓ 검색 매니저 초기화 성공")
        print(f"  - 최대 워커: {search_manager.max_workers}")
        print(f"  - 제안 임계값: {search_manager.suggestion_threshold}")


def test_food_search_with_cache():
    """캐시 기반 음식 검색 테스트."""
    print("\n=== 캐시 기반 음식 검색 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager
        )
        
        # 1차 검색 (API 호출)
        print("1차 검색 (API 호출 예상)")
        result1 = search_manager.search_food_with_cache("백미밥")
        
        assert result1.query == "백미밥"
        assert result1.search_type == "food"
        assert len(result1.foods) == 3
        assert result1.total_results == 3
        assert result1.cache_hit == False  # 첫 검색은 캐시 미스
        assert result1.search_time > 0
        
        # API 호출 확인
        food_client.search_food.assert_called_with("백미밥")
        
        print(f"✓ 1차 검색 완료: {result1.total_results}개 결과 (캐시 미스)")
        
        # 2차 검색 (캐시 히트)
        print("2차 검색 (캐시 히트 예상)")
        result2 = search_manager.search_food_with_cache("백미밥")
        
        assert result2.query == "백미밥"
        assert len(result2.foods) == 3
        assert result2.cache_hit == True  # 두 번째 검색은 캐시 히트
        
        print(f"✓ 2차 검색 완료: {result2.total_results}개 결과 (캐시 히트)")
        
        # 통계 확인
        stats = search_manager.get_search_stats()
        assert stats["search_statistics"]["total_searches"] == 2
        assert stats["search_statistics"]["cache_hits"] == 1
        assert stats["search_statistics"]["api_calls"] == 1
        
        print("✓ 캐시 기반 음식 검색 테스트 통과")


def test_exercise_search_with_cache():
    """캐시 기반 운동 검색 테스트."""
    print("\n=== 캐시 기반 운동 검색 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager
        )
        
        # 운동 검색
        result = search_manager.search_exercise_with_cache("달리기")
        
        assert result.query == "달리기"
        assert result.search_type == "exercise"
        assert len(result.exercises) == 2
        assert result.total_results == 2
        assert result.cache_hit == False  # 첫 검색은 캐시 미스
        
        # API 호출 확인
        exercise_client.search_exercise.assert_called_with("달리기", None)
        
        print(f"✓ 운동 검색 완료: {result.total_results}개 결과")
        
        # 카테고리 포함 검색
        result_with_category = search_manager.search_exercise_with_cache("달리기", "유산소")
        
        assert result_with_category.query == "달리기"
        assert len(result_with_category.exercises) == 2
        
        # 카테고리 포함 API 호출 확인
        exercise_client.search_exercise.assert_called_with("달리기", "유산소")
        
        print("✓ 카테고리 포함 운동 검색 완료")
        print("✓ 캐시 기반 운동 검색 테스트 통과")


def test_integrated_search():
    """통합 검색 테스트."""
    print("\n=== 통합 검색 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager
        )
        
        # 통합 검색 수행
        result = search_manager.search_both("운동")
        
        assert result.query == "운동"
        assert result.search_type == "both"
        assert len(result.foods) >= 0  # 음식 결과 (있을 수도 없을 수도)
        assert len(result.exercises) >= 0  # 운동 결과 (있을 수도 없을 수도)
        assert result.total_results == len(result.foods) + len(result.exercises)
        assert result.search_time > 0
        
        print(f"✓ 통합 검색 완료: 음식 {len(result.foods)}개, 운동 {len(result.exercises)}개")
        print("✓ 통합 검색 테스트 통과")


def test_batch_search():
    """배치 검색 테스트."""
    print("\n=== 배치 검색 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager,
            max_workers=2
        )
        
        # 배치 검색할 음식 목록
        food_names = ["백미밥", "김치", "된장찌개", "불고기"]
        
        # 배치 검색 수행
        batch_result = search_manager.batch_search_foods(food_names, max_concurrent=2)
        
        assert batch_result.total_queries == len(food_names)
        assert batch_result.successful_searches >= 0
        assert batch_result.failed_searches >= 0
        assert batch_result.successful_searches + batch_result.failed_searches == len(food_names)
        assert len(batch_result.results) == len(food_names)
        assert batch_result.total_time > 0
        
        # 각 검색 결과 확인
        for food_name in food_names:
            assert food_name in batch_result.results
            result = batch_result.results[food_name]
            assert result.query == food_name
            assert result.search_type == "food"
        
        print(f"✓ 배치 검색 완료: {batch_result.successful_searches}/{batch_result.total_queries} 성공")
        print(f"  - 총 소요 시간: {batch_result.total_time:.2f}초")
        print(f"  - 캐시 히트율: {batch_result.cache_hit_rate:.1f}%")
        print("✓ 배치 검색 테스트 통과")


def test_search_suggestions():
    """검색 제안 테스트."""
    print("\n=== 검색 제안 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager,
            suggestion_threshold=0.5  # 낮은 임계값으로 테스트
        )
        
        # 인기 검색어 시뮬레이션 (여러 번 검색)
        for _ in range(3):
            search_manager.search_food_with_cache("백미밥")
            search_manager.search_exercise_with_cache("달리기")
        
        # 음식 검색 제안
        food_suggestions = search_manager.get_search_suggestions("백", "food")
        print(f"  음식 제안 ({len(food_suggestions)}개): {[s.suggestion for s in food_suggestions]}")
        
        # 운동 검색 제안
        exercise_suggestions = search_manager.get_search_suggestions("달", "exercise")
        print(f"  운동 제안 ({len(exercise_suggestions)}개): {[s.suggestion for s in exercise_suggestions]}")
        
        # 통합 검색 제안
        both_suggestions = search_manager.get_search_suggestions("ㄱ", "both")
        print(f"  통합 제안 ({len(both_suggestions)}개): {[s.suggestion for s in both_suggestions]}")
        
        # 제안 구조 확인
        if food_suggestions:
            suggestion = food_suggestions[0]
            assert hasattr(suggestion, 'suggestion')
            assert hasattr(suggestion, 'type')
            assert hasattr(suggestion, 'confidence')
            assert hasattr(suggestion, 'reason')
            assert suggestion.type in ['food', 'exercise']
            assert 0 <= suggestion.confidence <= 1
        
        print("✓ 검색 제안 테스트 통과")


def test_network_error_retry():
    """네트워크 오류 재시도 테스트."""
    print("\n=== 네트워크 오류 재시도 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 생성 (네트워크 오류 시뮬레이션)
        food_client = Mock()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        # 첫 번째 호출은 네트워크 오류, 두 번째 호출은 성공
        food_client.search_food.side_effect = [
            NetworkError("네트워크 연결 실패"),
            [FoodItem(name="백미밥", food_id="food_001", category="곡류", manufacturer=None)]
        ]
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager
        )
        
        # 재시도 로직 테스트
        result = search_manager.search_food_with_cache("백미밥")
        
        assert result.query == "백미밥"
        assert len(result.foods) == 1
        assert result.foods[0].name == "백미밥"
        
        # API가 2번 호출되었는지 확인 (첫 번째 실패, 두 번째 성공)
        assert food_client.search_food.call_count == 2
        
        print("✓ 네트워크 오류 재시도 성공")
        print("✓ 네트워크 오류 재시도 테스트 통과")


def test_search_statistics():
    """검색 통계 테스트."""
    print("\n=== 검색 통계 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager
        )
        
        # 여러 검색 수행
        search_manager.search_food_with_cache("백미밥")
        search_manager.search_food_with_cache("백미밥")  # 캐시 히트
        search_manager.search_exercise_with_cache("달리기")
        search_manager.search_both("운동")
        
        # 통계 확인
        stats = search_manager.get_search_stats()
        
        assert "search_statistics" in stats
        assert "cache_statistics" in stats
        assert "popular_searches" in stats
        assert "configuration" in stats
        
        search_stats = stats["search_statistics"]
        assert search_stats["total_searches"] > 0
        assert search_stats["cache_hits"] >= 0
        assert search_stats["api_calls"] >= 0
        assert search_stats["average_response_time"] >= 0
        
        print(f"  - 총 검색: {search_stats['total_searches']}회")
        print(f"  - 캐시 히트: {search_stats['cache_hits']}회")
        print(f"  - API 호출: {search_stats['api_calls']}회")
        print(f"  - 평균 응답시간: {search_stats['average_response_time']:.3f}초")
        
        # 인기 검색어 확인
        popular_searches = stats["popular_searches"]
        assert "food_count" in popular_searches
        assert "exercise_count" in popular_searches
        assert "top_food_searches" in popular_searches
        assert "top_exercise_searches" in popular_searches
        
        print(f"  - 인기 음식 검색어: {popular_searches['food_count']}개")
        print(f"  - 인기 운동 검색어: {popular_searches['exercise_count']}개")
        
        print("✓ 검색 통계 테스트 통과")


def test_search_performance_optimization():
    """검색 성능 최적화 테스트."""
    print("\n=== 검색 성능 최적화 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=5)  # 작은 캐시
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager
        )
        
        # 많은 검색 수행 (캐시 용량 초과)
        for i in range(10):
            search_manager.search_food_with_cache(f"음식{i}")
            search_manager.search_exercise_with_cache(f"운동{i}")
        
        # 성능 최적화 실행
        optimization_result = search_manager.optimize_search_performance()
        
        assert "cache_optimization" in optimization_result
        assert "popular_searches_trimmed" in optimization_result
        assert "timestamp" in optimization_result
        
        cache_opt = optimization_result["cache_optimization"]
        popular_trimmed = optimization_result["popular_searches_trimmed"]
        
        print(f"  - 캐시 최적화: {cache_opt}")
        print(f"  - 인기 검색어 정리: 음식 {popular_trimmed['food']}개, 운동 {popular_trimmed['exercise']}개")
        
        print("✓ 검색 성능 최적화 테스트 통과")


def test_error_handling():
    """오류 처리 테스트."""
    print("\n=== 오류 처리 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock 클라이언트 및 매니저 생성
        food_client = create_mock_food_client()
        exercise_client = create_mock_exercise_client()
        cache_manager = CacheManager(cache_dir=temp_dir, max_memory_entries=10)
        
        search_manager = SearchManager(
            food_client=food_client,
            exercise_client=exercise_client,
            cache_manager=cache_manager
        )
        
        # 빈 검색어 테스트
        try:
            search_manager.search_food_with_cache("")
            assert False, "빈 검색어에 대한 예외가 발생하지 않음"
        except SearchError as e:
            print(f"  ✓ 빈 검색어 오류 처리: {str(e)}")
        
        # None 검색어 테스트
        try:
            search_manager.search_exercise_with_cache(None)
            assert False, "None 검색어에 대한 예외가 발생하지 않음"
        except (SearchError, TypeError) as e:
            print(f"  ✓ None 검색어 오류 처리: {str(e)}")
        
        # 빈 배치 검색 테스트
        try:
            search_manager.batch_search_foods([])
            assert False, "빈 배치 목록에 대한 예외가 발생하지 않음"
        except SearchError as e:
            print(f"  ✓ 빈 배치 목록 오류 처리: {str(e)}")
        
        print("✓ 오류 처리 테스트 통과")


if __name__ == "__main__":
    try:
        test_search_manager_initialization()
        test_food_search_with_cache()
        test_exercise_search_with_cache()
        test_integrated_search()
        test_batch_search()
        test_search_suggestions()
        test_network_error_retry()
        test_search_statistics()
        test_search_performance_optimization()
        test_error_handling()
        
        print("\n🎉 모든 검색 매니저 테스트가 성공적으로 완료되었습니다!")
        print("✅ 캐시 기반 통합 검색 기능 검증 완료")
        print("✅ 배치 검색 및 검색 제안 기능 검증 완료")
        print("✅ 네트워크 오류 재시도 로직 검증 완료")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()