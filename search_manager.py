"""
검색 매니저.

음식과 운동을 통합 검색하는 비즈니스 로직을 제공합니다.
캐시 기반 검색, 배치 검색, 검색 제안, 네트워크 오류 재시도 등의 기능을 포함합니다.
"""

import time
import asyncio
from typing import List, Dict, Optional, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta

from food_api_client import FoodAPIClient
from exercise_api_client import ExerciseAPIClient
from cache_manager import CacheManager
from integrated_models import FoodItem, NutritionInfo, ExerciseItem
from exceptions import (
    SearchError, NetworkError, TimeoutError, NoSearchResultsError,
    CacheError, APIResponseError
)


@dataclass
class SearchResult:
    """통합 검색 결과 데이터 클래스."""
    query: str
    search_type: str  # 'food', 'exercise', 'both'
    foods: List[FoodItem]
    exercises: List[ExerciseItem]
    total_results: int
    cache_hit: bool
    search_time: float
    timestamp: datetime


@dataclass
class SearchSuggestion:
    """검색 제안 데이터 클래스."""
    suggestion: str
    type: str  # 'food', 'exercise'
    confidence: float
    reason: str


@dataclass
class BatchSearchResult:
    """배치 검색 결과 데이터 클래스."""
    total_queries: int
    successful_searches: int
    failed_searches: int
    results: Dict[str, SearchResult]
    total_time: float
    cache_hit_rate: float


class SearchManager:
    """
    통합 검색 관리자.
    
    음식과 운동을 통합 검색하고, 캐시를 활용하여 성능을 최적화하며,
    배치 검색과 검색 제안 기능을 제공합니다.
    """
    
    def __init__(self, 
                 food_client: FoodAPIClient,
                 exercise_client: ExerciseAPIClient,
                 cache_manager: CacheManager,
                 max_workers: int = 5,
                 suggestion_threshold: float = 0.7):
        """
        SearchManager 초기화.
        
        Args:
            food_client: 음식 API 클라이언트
            exercise_client: 운동 API 클라이언트
            cache_manager: 캐시 매니저
            max_workers: 병렬 처리 최대 워커 수
            suggestion_threshold: 검색 제안 임계값
        """
        self.food_client = food_client
        self.exercise_client = exercise_client
        self.cache_manager = cache_manager
        self.max_workers = max_workers
        self.suggestion_threshold = suggestion_threshold
        
        # 검색 통계
        self.search_stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "failed_searches": 0,
            "average_response_time": 0.0
        }
        
        # 검색 제안을 위한 인기 검색어 캐시
        self.popular_searches = {
            "food": {},
            "exercise": {}
        }
        
        print("✓ 검색 매니저 초기화 완료")
        print(f"  - 최대 워커 수: {max_workers}")
        print(f"  - 제안 임계값: {suggestion_threshold}")
    
    def search_food_with_cache(self, food_name: str, use_suggestions: bool = True) -> SearchResult:
        """
        캐시를 활용한 음식 검색.
        
        Args:
            food_name: 검색할 음식명
            use_suggestions: 검색 제안 사용 여부
            
        Returns:
            SearchResult: 검색 결과
            
        Raises:
            SearchError: 검색 실패 시
        """
        if not food_name or not food_name.strip():
            raise SearchError("검색할 음식명을 입력해주세요")
        
        food_name = food_name.strip()
        start_time = time.time()
        
        print(f"🔍 음식 검색 (캐시 활용): '{food_name}'")
        
        try:
            # 1단계: 캐시에서 검색
            cached_foods = self.cache_manager.get_cached_food(food_name)
            cache_hit = cached_foods is not None
            
            if cache_hit:
                print(f"  💾 캐시 히트: {len(cached_foods)}개 결과")
                foods = cached_foods
                self.search_stats["cache_hits"] += 1
            else:
                # 2단계: API 호출
                print("  🌐 API 호출 중...")
                foods = self._search_food_with_retry(food_name)
                
                # 3단계: 캐시에 저장
                if foods:
                    self.cache_manager.cache_food_result(food_name, foods)
                    print(f"  💾 캐시 저장: {len(foods)}개 결과")
                
                self.search_stats["api_calls"] += 1
            
            # 4단계: 검색 통계 업데이트
            search_time = time.time() - start_time
            self._update_search_stats(search_time)
            self._update_popular_searches("food", food_name)
            
            # 5단계: 결과 생성
            result = SearchResult(
                query=food_name,
                search_type="food",
                foods=foods,
                exercises=[],
                total_results=len(foods),
                cache_hit=cache_hit,
                search_time=search_time,
                timestamp=datetime.now()
            )
            
            print(f"✓ 음식 검색 완료: {len(foods)}개 결과 ({search_time:.2f}초)")
            return result
            
        except Exception as e:
            self.search_stats["failed_searches"] += 1
            if isinstance(e, SearchError):
                raise
            raise SearchError(f"음식 검색 중 오류 발생: {str(e)}")
    
    def search_exercise_with_cache(self, exercise_name: str, category: Optional[str] = None) -> SearchResult:
        """
        캐시를 활용한 운동 검색.
        
        Args:
            exercise_name: 검색할 운동명
            category: 운동 분류 (선택사항)
            
        Returns:
            SearchResult: 검색 결과
            
        Raises:
            SearchError: 검색 실패 시
        """
        if not exercise_name or not exercise_name.strip():
            raise SearchError("검색할 운동명을 입력해주세요")
        
        exercise_name = exercise_name.strip()
        start_time = time.time()
        
        print(f"🏃 운동 검색 (캐시 활용): '{exercise_name}'")
        
        try:
            # 캐시 키에 카테고리 포함
            cache_key = f"{exercise_name}_{category}" if category else exercise_name
            
            # 1단계: 캐시에서 검색
            cached_exercises = self.cache_manager.get_cached_exercise(cache_key)
            cache_hit = cached_exercises is not None
            
            if cache_hit:
                print(f"  💾 캐시 히트: {len(cached_exercises)}개 결과")
                exercises = cached_exercises
                self.search_stats["cache_hits"] += 1
            else:
                # 2단계: API 호출
                print("  🌐 API 호출 중...")
                exercises = self._search_exercise_with_retry(exercise_name, category)
                
                # 3단계: 캐시에 저장
                if exercises:
                    self.cache_manager.cache_exercise_result(cache_key, exercises)
                    print(f"  💾 캐시 저장: {len(exercises)}개 결과")
                
                self.search_stats["api_calls"] += 1
            
            # 4단계: 검색 통계 업데이트
            search_time = time.time() - start_time
            self._update_search_stats(search_time)
            self._update_popular_searches("exercise", exercise_name)
            
            # 5단계: 결과 생성
            result = SearchResult(
                query=exercise_name,
                search_type="exercise",
                foods=[],
                exercises=exercises,
                total_results=len(exercises),
                cache_hit=cache_hit,
                search_time=search_time,
                timestamp=datetime.now()
            )
            
            print(f"✓ 운동 검색 완료: {len(exercises)}개 결과 ({search_time:.2f}초)")
            return result
            
        except Exception as e:
            self.search_stats["failed_searches"] += 1
            if isinstance(e, SearchError):
                raise
            raise SearchError(f"운동 검색 중 오류 발생: {str(e)}")
    
    def search_both(self, query: str) -> SearchResult:
        """
        음식과 운동을 동시에 검색합니다.
        
        Args:
            query: 검색어
            
        Returns:
            SearchResult: 통합 검색 결과
        """
        if not query or not query.strip():
            raise SearchError("검색어를 입력해주세요")
        
        query = query.strip()
        start_time = time.time()
        
        print(f"🔍🏃 통합 검색: '{query}'")
        
        try:
            # 병렬로 음식과 운동 검색 수행
            with ThreadPoolExecutor(max_workers=2) as executor:
                # 음식 검색 작업 제출
                food_future = executor.submit(self._safe_search_food, query)
                
                # 운동 검색 작업 제출
                exercise_future = executor.submit(self._safe_search_exercise, query)
                
                # 결과 수집
                foods = food_future.result()
                exercises = exercise_future.result()
            
            # 검색 시간 계산
            search_time = time.time() - start_time
            self._update_search_stats(search_time)
            
            # 결과 생성
            result = SearchResult(
                query=query,
                search_type="both",
                foods=foods,
                exercises=exercises,
                total_results=len(foods) + len(exercises),
                cache_hit=False,  # 통합 검색은 개별 캐시 히트 여부를 정확히 판단하기 어려움
                search_time=search_time,
                timestamp=datetime.now()
            )
            
            print(f"✓ 통합 검색 완료: 음식 {len(foods)}개, 운동 {len(exercises)}개 ({search_time:.2f}초)")
            return result
            
        except Exception as e:
            self.search_stats["failed_searches"] += 1
            raise SearchError(f"통합 검색 중 오류 발생: {str(e)}")
    
    def batch_search_foods(self, food_names: List[str], max_concurrent: Optional[int] = None) -> BatchSearchResult:
        """
        여러 음식을 배치로 검색합니다.
        
        Args:
            food_names: 검색할 음식명 목록
            max_concurrent: 최대 동시 실행 수 (기본값: max_workers)
            
        Returns:
            BatchSearchResult: 배치 검색 결과
        """
        if not food_names:
            raise SearchError("검색할 음식 목록이 비어있습니다")
        
        max_concurrent = max_concurrent or self.max_workers
        start_time = time.time()
        
        print(f"📦 음식 배치 검색: {len(food_names)}개 (동시 실행: {max_concurrent})")
        
        results = {}
        successful_searches = 0
        failed_searches = 0
        cache_hits = 0
        
        try:
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                # 모든 검색 작업 제출
                future_to_name = {
                    executor.submit(self._safe_search_food_for_batch, name): name 
                    for name in food_names
                }
                
                # 결과 수집
                for future in as_completed(future_to_name):
                    food_name = future_to_name[future]
                    try:
                        search_result = future.result()
                        results[food_name] = search_result
                        successful_searches += 1
                        
                        if search_result.cache_hit:
                            cache_hits += 1
                            
                        print(f"  ✓ {food_name}: {search_result.total_results}개 결과")
                        
                    except Exception as e:
                        print(f"  ✗ {food_name}: {str(e)}")
                        failed_searches += 1
                        
                        # 실패한 검색도 빈 결과로 기록
                        results[food_name] = SearchResult(
                            query=food_name,
                            search_type="food",
                            foods=[],
                            exercises=[],
                            total_results=0,
                            cache_hit=False,
                            search_time=0.0,
                            timestamp=datetime.now()
                        )
            
            # 배치 검색 결과 생성
            total_time = time.time() - start_time
            cache_hit_rate = (cache_hits / len(food_names)) * 100 if food_names else 0
            
            batch_result = BatchSearchResult(
                total_queries=len(food_names),
                successful_searches=successful_searches,
                failed_searches=failed_searches,
                results=results,
                total_time=total_time,
                cache_hit_rate=cache_hit_rate
            )
            
            print(f"✓ 배치 검색 완료: {successful_searches}/{len(food_names)} 성공 ({total_time:.2f}초)")
            print(f"  캐시 히트율: {cache_hit_rate:.1f}%")
            
            return batch_result
            
        except Exception as e:
            raise SearchError(f"배치 검색 중 오류 발생: {str(e)}")
    
    def get_search_suggestions(self, partial_query: str, search_type: str = "both") -> List[SearchSuggestion]:
        """
        부분 검색어를 기반으로 검색 제안을 생성합니다.
        
        Args:
            partial_query: 부분 검색어
            search_type: 검색 타입 ('food', 'exercise', 'both')
            
        Returns:
            List[SearchSuggestion]: 검색 제안 목록
        """
        if not partial_query or len(partial_query.strip()) < 2:
            return []
        
        partial_query = partial_query.strip().lower()
        suggestions = []
        
        print(f"💡 검색 제안 생성: '{partial_query}' (타입: {search_type})")
        
        try:
            # 1. 인기 검색어 기반 제안
            if search_type in ["food", "both"]:
                food_suggestions = self._get_popular_search_suggestions(
                    partial_query, "food"
                )
                suggestions.extend(food_suggestions)
            
            if search_type in ["exercise", "both"]:
                exercise_suggestions = self._get_popular_search_suggestions(
                    partial_query, "exercise"
                )
                suggestions.extend(exercise_suggestions)
            
            # 2. 기본 데이터베이스 기반 제안
            if search_type in ["exercise", "both"]:
                exercise_db_suggestions = self._get_exercise_db_suggestions(partial_query)
                suggestions.extend(exercise_db_suggestions)
            
            # 3. 제안 정렬 및 필터링
            suggestions = self._filter_and_sort_suggestions(suggestions)
            
            print(f"✓ {len(suggestions)}개 검색 제안 생성")
            return suggestions[:10]  # 최대 10개까지
            
        except Exception as e:
            print(f"⚠️ 검색 제안 생성 실패: {str(e)}")
            return []
    
    def _search_food_with_retry(self, food_name: str, max_retries: int = 3) -> List[FoodItem]:
        """재시도 로직을 포함한 음식 검색."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"    재시도 {attempt}/{max_retries - 1}")
                    time.sleep(1.0 * attempt)  # 지수 백오프
                
                return self.food_client.search_food(food_name)
                
            except NoSearchResultsError:
                # 검색 결과 없음은 재시도하지 않음
                return []
            except (NetworkError, TimeoutError) as e:
                last_exception = e
                print(f"    네트워크 오류, 재시도 예정: {str(e)}")
                continue
            except Exception as e:
                last_exception = e
                break
        
        # 모든 재시도 실패
        if last_exception:
            raise last_exception
        return []
    
    def _search_exercise_with_retry(self, exercise_name: str, category: Optional[str] = None, max_retries: int = 3) -> List[ExerciseItem]:
        """재시도 로직을 포함한 운동 검색."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"    재시도 {attempt}/{max_retries - 1}")
                    time.sleep(1.0 * attempt)  # 지수 백오프
                
                return self.exercise_client.search_exercise(exercise_name, category)
                
            except NoSearchResultsError:
                # 검색 결과 없음은 재시도하지 않음
                return []
            except (NetworkError, TimeoutError) as e:
                last_exception = e
                print(f"    네트워크 오류, 재시도 예정: {str(e)}")
                continue
            except Exception as e:
                last_exception = e
                break
        
        # 모든 재시도 실패
        if last_exception:
            raise last_exception
        return []
    
    def _safe_search_food(self, food_name: str) -> List[FoodItem]:
        """안전한 음식 검색 (예외를 빈 리스트로 변환)."""
        try:
            result = self.search_food_with_cache(food_name)
            return result.foods
        except Exception as e:
            print(f"    음식 검색 실패: {str(e)}")
            return []
    
    def _safe_search_exercise(self, exercise_name: str) -> List[ExerciseItem]:
        """안전한 운동 검색 (예외를 빈 리스트로 변환)."""
        try:
            result = self.search_exercise_with_cache(exercise_name)
            return result.exercises
        except Exception as e:
            print(f"    운동 검색 실패: {str(e)}")
            return []
    
    def _safe_search_food_for_batch(self, food_name: str) -> SearchResult:
        """배치 검색용 안전한 음식 검색."""
        try:
            return self.search_food_with_cache(food_name)
        except Exception as e:
            raise SearchError(f"'{food_name}' 검색 실패: {str(e)}")
    
    def _update_search_stats(self, search_time: float) -> None:
        """검색 통계를 업데이트합니다."""
        self.search_stats["total_searches"] += 1
        
        # 평균 응답 시간 계산
        total_time = (self.search_stats["average_response_time"] * 
                     (self.search_stats["total_searches"] - 1) + search_time)
        self.search_stats["average_response_time"] = total_time / self.search_stats["total_searches"]
    
    def _update_popular_searches(self, search_type: str, query: str) -> None:
        """인기 검색어를 업데이트합니다."""
        if search_type not in self.popular_searches:
            return
        
        query_lower = query.lower()
        if query_lower in self.popular_searches[search_type]:
            self.popular_searches[search_type][query_lower] += 1
        else:
            self.popular_searches[search_type][query_lower] = 1
    
    def _get_popular_search_suggestions(self, partial_query: str, search_type: str) -> List[SearchSuggestion]:
        """인기 검색어 기반 제안을 생성합니다."""
        suggestions = []
        
        if search_type not in self.popular_searches:
            return suggestions
        
        for query, count in self.popular_searches[search_type].items():
            if partial_query in query and len(query) > len(partial_query):
                confidence = min(count / 10.0, 1.0)  # 최대 1.0
                if confidence >= self.suggestion_threshold:
                    suggestions.append(SearchSuggestion(
                        suggestion=query,
                        type=search_type,
                        confidence=confidence,
                        reason=f"인기 검색어 (검색 {count}회)"
                    ))
        
        return suggestions
    
    def _get_exercise_db_suggestions(self, partial_query: str) -> List[SearchSuggestion]:
        """운동 데이터베이스 기반 제안을 생성합니다."""
        suggestions = []
        
        # 운동 클라이언트의 지원 운동 목록 활용
        try:
            supported_exercises = self.exercise_client.get_supported_exercises()
            
            for exercise_name in supported_exercises.keys():
                exercise_lower = exercise_name.lower()
                if partial_query in exercise_lower and len(exercise_name) > len(partial_query):
                    # 매칭 정도에 따른 신뢰도 계산
                    if exercise_lower.startswith(partial_query):
                        confidence = 0.9  # 시작 매칭
                    elif partial_query in exercise_lower[:len(exercise_lower)//2]:
                        confidence = 0.8  # 앞부분 매칭
                    else:
                        confidence = 0.7  # 일반 매칭
                    
                    suggestions.append(SearchSuggestion(
                        suggestion=exercise_name,
                        type="exercise",
                        confidence=confidence,
                        reason="지원 운동 목록"
                    ))
        
        except Exception as e:
            print(f"    운동 DB 제안 생성 실패: {str(e)}")
        
        return suggestions
    
    def _filter_and_sort_suggestions(self, suggestions: List[SearchSuggestion]) -> List[SearchSuggestion]:
        """제안을 필터링하고 정렬합니다."""
        # 중복 제거
        unique_suggestions = {}
        for suggestion in suggestions:
            key = f"{suggestion.suggestion}_{suggestion.type}"
            if key not in unique_suggestions or suggestion.confidence > unique_suggestions[key].confidence:
                unique_suggestions[key] = suggestion
        
        # 신뢰도 기준으로 정렬
        filtered_suggestions = list(unique_suggestions.values())
        filtered_suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        return filtered_suggestions
    
    def get_search_stats(self) -> Dict[str, Any]:
        """
        검색 통계를 반환합니다.
        
        Returns:
            Dict[str, Any]: 검색 통계 정보
        """
        cache_stats = self.cache_manager.get_cache_stats()
        
        return {
            "search_statistics": self.search_stats.copy(),
            "cache_statistics": {
                "hit_rate": cache_stats.hit_rate,
                "total_requests": cache_stats.total_requests,
                "cache_hits": cache_stats.cache_hits,
                "cache_misses": cache_stats.cache_misses
            },
            "popular_searches": {
                "food_count": len(self.popular_searches["food"]),
                "exercise_count": len(self.popular_searches["exercise"]),
                "top_food_searches": self._get_top_searches("food", 5),
                "top_exercise_searches": self._get_top_searches("exercise", 5)
            },
            "configuration": {
                "max_workers": self.max_workers,
                "suggestion_threshold": self.suggestion_threshold
            }
        }
    
    def _get_top_searches(self, search_type: str, limit: int = 5) -> List[Tuple[str, int]]:
        """상위 검색어를 반환합니다."""
        if search_type not in self.popular_searches:
            return []
        
        searches = self.popular_searches[search_type]
        sorted_searches = sorted(searches.items(), key=lambda x: x[1], reverse=True)
        return sorted_searches[:limit]
    
    def clear_search_cache(self) -> None:
        """검색 캐시를 정리합니다."""
        print("🧹 검색 캐시 정리")
        self.cache_manager.clear_all_cache()
        self.popular_searches = {"food": {}, "exercise": {}}
        print("✓ 검색 캐시 정리 완료")
    
    def optimize_search_performance(self) -> Dict[str, Any]:
        """
        검색 성능을 최적화합니다.
        
        Returns:
            Dict[str, Any]: 최적화 결과
        """
        print("⚡ 검색 성능 최적화 시작")
        
        # 캐시 최적화
        cache_optimization = self.cache_manager.optimize_cache()
        
        # 인기 검색어 정리 (상위 100개만 유지)
        for search_type in ["food", "exercise"]:
            if len(self.popular_searches[search_type]) > 100:
                top_searches = dict(self._get_top_searches(search_type, 100))
                self.popular_searches[search_type] = top_searches
        
        optimization_result = {
            "cache_optimization": cache_optimization,
            "popular_searches_trimmed": {
                "food": len(self.popular_searches["food"]),
                "exercise": len(self.popular_searches["exercise"])
            },
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✓ 검색 성능 최적화 완료: {optimization_result}")
        return optimization_result