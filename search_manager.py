"""
검색 매니저.

캐시 기반 음식/운동 통합 검색 기능을 제공하며, 배치 검색, 검색 제안,
네트워크 오류 시 재시도 로직 등의 고급 검색 기능을 포함합니다.
"""

import time
from typing import List, Dict, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import difflib

from cache_manager import CacheManager
from food_api_client import FoodAPIClient
from exercise_api_client import ExerciseAPIClient
from integrated_models import FoodItem, NutritionInfo, ExerciseItem
from exceptions import (
    SearchError, NetworkError, TimeoutError, NoSearchResultsError,
    CacheError, IntegratedAPIError
)


@dataclass
class SearchResult:
    """검색 결과를 나타내는 데이터 클래스."""
    query: str
    food_results: List[FoodItem]
    exercise_results: List[ExerciseItem]
    search_time: float
    cache_hit: bool
    suggestions: List[str]
    total_results: int
    
    @property
    def has_results(self) -> bool:
        """검색 결과가 있는지 확인합니다."""
        return len(self.food_results) > 0 or len(self.exercise_results) > 0


@dataclass
class BatchSearchResult:
    """배치 검색 결과를 나타내는 데이터 클래스."""
    queries: List[str]
    results: Dict[str, SearchResult]
    total_time: float
    success_count: int
    failure_count: int
    cache_hit_rate: float


class SearchManager:
    """
    캐시 기반 음식/운동 통합 검색 매니저.
    
    음식과 운동 데이터를 효율적으로 검색하고, 캐싱을 통해 성능을 최적화하며,
    배치 검색, 검색 제안, 네트워크 재시도 등의 고급 기능을 제공합니다.
    """
    
    def __init__(self, 
                 food_client: FoodAPIClient,
                 exercise_client: ExerciseAPIClient,
                 cache_manager: CacheManager,
                 max_workers: int = 5,
                 suggestion_threshold: float = 0.6):
        """
        SearchManager 초기화.
        
        Args:
            food_client: 음식 API 클라이언트
            exercise_client: 운동 API 클라이언트
            cache_manager: 캐시 매니저
            max_workers: 병렬 처리 최대 워커 수
            suggestion_threshold: 검색 제안 유사도 임계값
        """
        self.food_client = food_client
        self.exercise_client = exercise_client
        self.cache = cache_manager
        self.max_workers = max_workers
        self.suggestion_threshold = suggestion_threshold
        
        # 검색 설정
        self.retry_count = 3
        self.retry_delay = 1.0
        self.network_timeout = 30.0
        
        # 검색 기록 (제안 기능용)
        self.search_history: Set[str] = set()
        self.popular_searches: Dict[str, int] = {}
        
        # 성능 통계
        self.stats = {
            "total_searches": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "average_response_time": 0.0,
            "error_count": 0
        }
        
        print("✓ 검색 매니저 초기화 완료")
        print(f"  - 최대 워커 수: {max_workers}")
        print(f"  - 제안 임계값: {suggestion_threshold}")
    
    def search(self, query: str, 
               search_food: bool = True, 
               search_exercise: bool = True,
               max_results: int = 10) -> SearchResult:
        """
        통합 검색을 수행합니다.
        
        Args:
            query: 검색어
            search_food: 음식 검색 여부
            search_exercise: 운동 검색 여부
            max_results: 최대 결과 수
            
        Returns:
            SearchResult: 검색 결과
            
        Raises:
            SearchError: 검색 실패 시
        """
        if not query or not query.strip():
            raise SearchError("검색어를 입력해주세요")
        
        query = query.strip()
        start_time = time.time()
        
        print(f"🔍 통합 검색: '{query}'")
        
        try:
            # 검색 기록 업데이트
            self._update_search_history(query)
            
            # 캐시에서 검색 시도
            cached_result = self._search_from_cache(query, search_food, search_exercise)
            if cached_result:
                search_time = time.time() - start_time
                self._update_stats(cache_hit=True, response_time=search_time)
                
                return SearchResult(
                    query=query,
                    food_results=cached_result.get('food', [])[:max_results],
                    exercise_results=cached_result.get('exercise', [])[:max_results],
                    search_time=search_time,
                    cache_hit=True,
                    suggestions=self._generate_suggestions(query),
                    total_results=len(cached_result.get('food', [])) + len(cached_result.get('exercise', []))
                )
            
            # API에서 검색
            food_results = []
            exercise_results = []
            
            # 병렬 검색 수행
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                
                if search_food:
                    futures.append(executor.submit(self._search_food_with_retry, query))
                
                if search_exercise:
                    futures.append(executor.submit(self._search_exercise_with_retry, query))
                
                for future in as_completed(futures):
                    try:
                        result_type, results = future.result()
                        if result_type == 'food':
                            food_results = results[:max_results]
                        elif result_type == 'exercise':
                            exercise_results = results[:max_results]
                    except Exception as e:
                        print(f"  ⚠️ 병렬 검색 오류: {str(e)}")
                        continue
            
            # 결과 캐싱
            self._cache_search_results(query, food_results, exercise_results)
            
            search_time = time.time() - start_time
            self._update_stats(cache_hit=False, response_time=search_time)
            
            return SearchResult(
                query=query,
                food_results=food_results,
                exercise_results=exercise_results,
                search_time=search_time,
                cache_hit=False,
                suggestions=self._generate_suggestions(query),
                total_results=len(food_results) + len(exercise_results)
            )
            
        except Exception as e:
            self._update_stats(error=True)
            if isinstance(e, SearchError):
                raise
            raise SearchError(f"검색 중 오류 발생: {str(e)}")
    
    def search_food_with_cache(self, food_name: str, max_results: int = 10) -> List[FoodItem]:
        """
        캐시 기반 음식 검색.
        
        Args:
            food_name: 음식명
            max_results: 최대 결과 수
            
        Returns:
            List[FoodItem]: 검색된 음식 목록
        """
        print(f"🍽️ 음식 검색: '{food_name}'")
        
        # 캐시에서 먼저 확인
        cached_foods = self.cache.get_cached_food(food_name)
        if cached_foods:
            print(f"  💾 캐시에서 {len(cached_foods)}개 음식 조회")
            return cached_foods[:max_results]
        
        # API에서 검색
        try:
            foods = self.food_client.search_food(food_name, 1, max_results)
            
            # 캐시에 저장
            if foods:
                self.cache.cache_food_result(food_name, foods)
                print(f"  🔄 {len(foods)}개 음식 캐시 저장")
            
            return foods
            
        except Exception as e:
            print(f"  ❌ 음식 검색 실패: {str(e)}")
            return []
    
    def search_exercise_with_cache(self, exercise_name: str, max_results: int = 10) -> List[ExerciseItem]:
        """
        캐시 기반 운동 검색.
        
        Args:
            exercise_name: 운동명
            max_results: 최대 결과 수
            
        Returns:
            List[ExerciseItem]: 검색된 운동 목록
        """
        print(f"🏃 운동 검색: '{exercise_name}'")
        
        # 캐시에서 먼저 확인
        cached_exercises = self.cache.get_cached_exercise(exercise_name)
        if cached_exercises:
            print(f"  💾 캐시에서 {len(cached_exercises)}개 운동 조회")
            return cached_exercises[:max_results]
        
        # API에서 검색
        try:
            exercises = self.exercise_client.search_exercise(exercise_name)
            
            # 캐시에 저장
            if exercises:
                self.cache.cache_exercise_result(exercise_name, exercises)
                print(f"  🔄 {len(exercises)}개 운동 캐시 저장")
            
            return exercises[:max_results]
            
        except Exception as e:
            print(f"  ❌ 운동 검색 실패: {str(e)}")
            return []   
 
    def batch_search_foods(self, food_names: List[str], max_results_per_item: int = 5) -> Dict[str, List[FoodItem]]:
        """
        여러 음식을 배치로 검색합니다.
        
        Args:
            food_names: 검색할 음식명 목록
            max_results_per_item: 항목당 최대 결과 수
            
        Returns:
            Dict[str, List[FoodItem]]: 음식명별 검색 결과
        """
        print(f"📦 음식 배치 검색: {len(food_names)}개 항목")
        
        results = {}
        
        # 병렬 처리로 성능 향상
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_name = {
                executor.submit(self.search_food_with_cache, name, max_results_per_item): name
                for name in food_names
            }
            
            # 결과 수집
            for future in as_completed(future_to_name):
                food_name = future_to_name[future]
                try:
                    food_results = future.result()
                    results[food_name] = food_results
                    print(f"  ✓ {food_name}: {len(food_results)}개 결과")
                except Exception as e:
                    print(f"  ✗ {food_name}: 검색 실패 - {str(e)}")
                    results[food_name] = []
        
        return results
    
    def batch_search_exercises(self, exercise_names: List[str], max_results_per_item: int = 5) -> Dict[str, List[ExerciseItem]]:
        """
        여러 운동을 배치로 검색합니다.
        
        Args:
            exercise_names: 검색할 운동명 목록
            max_results_per_item: 항목당 최대 결과 수
            
        Returns:
            Dict[str, List[ExerciseItem]]: 운동명별 검색 결과
        """
        print(f"📦 운동 배치 검색: {len(exercise_names)}개 항목")
        
        results = {}
        
        # 병렬 처리로 성능 향상
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_name = {
                executor.submit(self.search_exercise_with_cache, name, max_results_per_item): name
                for name in exercise_names
            }
            
            # 결과 수집
            for future in as_completed(future_to_name):
                exercise_name = future_to_name[future]
                try:
                    exercise_results = future.result()
                    results[exercise_name] = exercise_results
                    print(f"  ✓ {exercise_name}: {len(exercise_results)}개 결과")
                except Exception as e:
                    print(f"  ✗ {exercise_name}: 검색 실패 - {str(e)}")
                    results[exercise_name] = []
        
        return results
    
    def batch_search(self, queries: List[str], 
                    search_food: bool = True, 
                    search_exercise: bool = True,
                    max_results_per_query: int = 5) -> BatchSearchResult:
        """
        여러 검색어를 배치로 처리합니다.
        
        Args:
            queries: 검색어 목록
            search_food: 음식 검색 여부
            search_exercise: 운동 검색 여부
            max_results_per_query: 검색어당 최대 결과 수
            
        Returns:
            BatchSearchResult: 배치 검색 결과
        """
        print(f"📦 배치 검색: {len(queries)}개 검색어")
        
        start_time = time.time()
        results = {}
        success_count = 0
        failure_count = 0
        cache_hits = 0
        
        # 병렬 처리
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_query = {
                executor.submit(
                    self.search, 
                    query, 
                    search_food, 
                    search_exercise, 
                    max_results_per_query
                ): query
                for query in queries
            }
            
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    result = future.result()
                    results[query] = result
                    success_count += 1
                    if result.cache_hit:
                        cache_hits += 1
                    print(f"  ✓ '{query}': {result.total_results}개 결과")
                except Exception as e:
                    print(f"  ✗ '{query}': 검색 실패 - {str(e)}")
                    failure_count += 1
                    results[query] = SearchResult(
                        query=query,
                        food_results=[],
                        exercise_results=[],
                        search_time=0.0,
                        cache_hit=False,
                        suggestions=[],
                        total_results=0
                    )
        
        total_time = time.time() - start_time
        cache_hit_rate = (cache_hits / len(queries)) * 100 if queries else 0
        
        return BatchSearchResult(
            queries=queries,
            results=results,
            total_time=total_time,
            success_count=success_count,
            failure_count=failure_count,
            cache_hit_rate=cache_hit_rate
        )
    
    def get_search_suggestions(self, partial_query: str, max_suggestions: int = 5) -> List[str]:
        """
        부분 검색어를 기반으로 검색 제안을 생성합니다.
        
        Args:
            partial_query: 부분 검색어
            max_suggestions: 최대 제안 수
            
        Returns:
            List[str]: 검색 제안 목록
        """
        if not partial_query or len(partial_query) < 2:
            return []
        
        suggestions = []
        partial_query = partial_query.lower().strip()
        
        # 검색 기록에서 유사한 검색어 찾기
        for search_term in self.search_history:
            if partial_query in search_term.lower():
                suggestions.append(search_term)
        
        # 인기 검색어에서 유사한 검색어 찾기
        for popular_term in sorted(self.popular_searches.keys(), 
                                 key=lambda x: self.popular_searches[x], 
                                 reverse=True):
            if partial_query in popular_term.lower() and popular_term not in suggestions:
                suggestions.append(popular_term)
        
        # 유사도 기반 제안 (difflib 사용)
        all_terms = list(self.search_history) + list(self.popular_searches.keys())
        similar_terms = difflib.get_close_matches(
            partial_query, 
            all_terms, 
            n=max_suggestions, 
            cutoff=self.suggestion_threshold
        )
        
        for term in similar_terms:
            if term not in suggestions:
                suggestions.append(term)
        
        return suggestions[:max_suggestions]
    
    def _search_from_cache(self, query: str, search_food: bool, search_exercise: bool) -> Optional[Dict[str, List]]:
        """캐시에서 검색 결과를 조회합니다."""
        cached_result = {}
        cache_found = False
        
        if search_food:
            cached_foods = self.cache.get_cached_food(query)
            if cached_foods:
                cached_result['food'] = cached_foods
                cache_found = True
        
        if search_exercise:
            cached_exercises = self.cache.get_cached_exercise(query)
            if cached_exercises:
                cached_result['exercise'] = cached_exercises
                cache_found = True
        
        return cached_result if cache_found else None
    
    def _search_food_with_retry(self, query: str) -> Tuple[str, List[FoodItem]]:
        """재시도 로직을 포함한 음식 검색."""
        last_exception = None
        
        for attempt in range(self.retry_count):
            try:
                if attempt > 0:
                    print(f"    음식 검색 재시도 {attempt}/{self.retry_count - 1}")
                    time.sleep(self.retry_delay * attempt)
                
                results = self.food_client.search_food(query)
                return ('food', results)
                
            except NetworkError as e:
                last_exception = e
                continue
            except TimeoutError as e:
                last_exception = e
                continue
            except NoSearchResultsError:
                # 검색 결과 없음은 재시도하지 않음
                return ('food', [])
            except Exception as e:
                last_exception = e
                break
        
        print(f"    음식 검색 최종 실패: {str(last_exception)}")
        return ('food', [])
    
    def _search_exercise_with_retry(self, query: str) -> Tuple[str, List[ExerciseItem]]:
        """재시도 로직을 포함한 운동 검색."""
        last_exception = None
        
        for attempt in range(self.retry_count):
            try:
                if attempt > 0:
                    print(f"    운동 검색 재시도 {attempt}/{self.retry_count - 1}")
                    time.sleep(self.retry_delay * attempt)
                
                results = self.exercise_client.search_exercise(query)
                return ('exercise', results)
                
            except NetworkError as e:
                last_exception = e
                continue
            except TimeoutError as e:
                last_exception = e
                continue
            except NoSearchResultsError:
                # 검색 결과 없음은 재시도하지 않음
                return ('exercise', [])
            except Exception as e:
                last_exception = e
                break
        
        print(f"    운동 검색 최종 실패: {str(last_exception)}")
        return ('exercise', [])
    
    def _cache_search_results(self, query: str, food_results: List[FoodItem], exercise_results: List[ExerciseItem]) -> None:
        """검색 결과를 캐시에 저장합니다."""
        try:
            if food_results:
                self.cache.cache_food_result(query, food_results)
            
            if exercise_results:
                self.cache.cache_exercise_result(query, exercise_results)
                
        except Exception as e:
            print(f"  ⚠️ 캐시 저장 실패: {str(e)}")
    
    def _update_search_history(self, query: str) -> None:
        """검색 기록을 업데이트합니다."""
        self.search_history.add(query)
        
        # 인기 검색어 카운트 업데이트
        if query in self.popular_searches:
            self.popular_searches[query] += 1
        else:
            self.popular_searches[query] = 1
        
        # 검색 기록 크기 제한 (메모리 관리)
        if len(self.search_history) > 1000:
            # 오래된 검색어 일부 제거
            old_terms = list(self.search_history)[:100]
            for term in old_terms:
                self.search_history.discard(term)
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """검색어 기반 제안을 생성합니다."""
        suggestions = []
        
        # 유사한 검색어 찾기
        similar_queries = self.get_search_suggestions(query, 3)
        suggestions.extend(similar_queries)
        
        # 관련 키워드 제안
        related_keywords = self._get_related_keywords(query)
        suggestions.extend(related_keywords)
        
        # 중복 제거 및 원본 검색어 제외
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion != query and suggestion not in unique_suggestions:
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]
    
    def _get_related_keywords(self, query: str) -> List[str]:
        """관련 키워드를 생성합니다."""
        related = []
        query_lower = query.lower()
        
        # 음식 관련 키워드
        food_keywords = {
            "밥": ["백미밥", "현미밥", "볶음밥"],
            "면": ["라면", "우동", "파스타"],
            "고기": ["소고기", "돼지고기", "닭고기"],
            "생선": ["연어", "고등어", "참치"],
            "야채": ["브로콜리", "시금치", "당근"],
            "과일": ["사과", "바나나", "오렌지"]
        }
        
        # 운동 관련 키워드
        exercise_keywords = {
            "달리기": ["조깅", "마라톤", "트레드밀"],
            "걷기": ["산책", "빠른걷기", "파워워킹"],
            "운동": ["헬스", "피트니스", "체조"],
            "수영": ["자유형", "배영", "접영"],
            "자전거": ["사이클링", "실내자전거", "로드바이크"]
        }
        
        # 관련 키워드 찾기
        for keyword, related_list in {**food_keywords, **exercise_keywords}.items():
            if keyword in query_lower:
                related.extend(related_list)
        
        return related[:3]
    
    def _update_stats(self, cache_hit: bool = False, response_time: float = 0.0, error: bool = False) -> None:
        """검색 통계를 업데이트합니다."""
        self.stats["total_searches"] += 1
        
        if cache_hit:
            self.stats["cache_hits"] += 1
        else:
            self.stats["api_calls"] += 1
        
        if error:
            self.stats["error_count"] += 1
        
        # 평균 응답 시간 계산
        if response_time > 0:
            current_avg = self.stats["average_response_time"]
            total_searches = self.stats["total_searches"]
            self.stats["average_response_time"] = (
                (current_avg * (total_searches - 1) + response_time) / total_searches
            )
    
    def get_search_stats(self) -> Dict[str, Any]:
        """
        검색 통계를 반환합니다.
        
        Returns:
            Dict[str, Any]: 검색 통계 정보
        """
        cache_hit_rate = 0.0
        if self.stats["total_searches"] > 0:
            cache_hit_rate = (self.stats["cache_hits"] / self.stats["total_searches"]) * 100
        
        return {
            "total_searches": self.stats["total_searches"],
            "cache_hits": self.stats["cache_hits"],
            "api_calls": self.stats["api_calls"],
            "cache_hit_rate": cache_hit_rate,
            "average_response_time": self.stats["average_response_time"],
            "error_count": self.stats["error_count"],
            "search_history_size": len(self.search_history),
            "popular_searches": dict(sorted(
                self.popular_searches.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10])
        }
    
    def clear_search_history(self) -> None:
        """검색 기록을 초기화합니다."""
        self.search_history.clear()
        self.popular_searches.clear()
        print("✓ 검색 기록 초기화 완료")
    
    def optimize_search_performance(self) -> Dict[str, Any]:
        """
        검색 성능을 최적화합니다.
        
        Returns:
            Dict[str, Any]: 최적화 결과
        """
        print("⚡ 검색 성능 최적화 시작")
        
        # 캐시 최적화
        cache_optimization = self.cache.optimize_cache()
        
        # 검색 기록 정리
        history_before = len(self.search_history)
        if history_before > 500:
            # 인기도가 낮은 검색어 제거
            low_popularity_terms = [
                term for term, count in self.popular_searches.items() 
                if count == 1
            ]
            for term in low_popularity_terms[:100]:
                self.search_history.discard(term)
                del self.popular_searches[term]
        
        history_after = len(self.search_history)
        
        result = {
            "cache_optimization": cache_optimization,
            "search_history_cleaned": history_before - history_after,
            "current_history_size": history_after,
            "popular_searches_count": len(self.popular_searches)
        }
        
        print(f"✓ 검색 성능 최적화 완료: {result}")
        return result