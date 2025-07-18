"""
캐시 매니저.

음식/운동 검색 결과를 메모리 및 파일 기반으로 캐싱하여 
API 호출을 최적화하고 성능을 향상시키는 기능을 제공합니다.
"""

import json
import time
import hashlib
import pickle
from typing import Dict, Optional, Any, List, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from dataclasses import dataclass, asdict
from integrated_models import FoodItem, NutritionInfo, ExerciseItem
from exceptions import CacheError, CacheExpiredError, CacheCorruptedError


@dataclass
class CacheEntry:
    """캐시 엔트리 데이터 클래스."""
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """캐시 엔트리가 만료되었는지 확인합니다."""
        return datetime.now() > self.expires_at
    
    def access(self) -> None:
        """캐시 엔트리 접근 시 호출됩니다."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheStats:
    """캐시 통계 데이터 클래스."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    expired_entries: int = 0
    evicted_entries: int = 0
    memory_usage_bytes: int = 0
    disk_usage_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """캐시 히트율을 계산합니다."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """캐시 미스율을 계산합니다."""
        return 100.0 - self.hit_rate


class CacheManager:
    """
    메모리 및 파일 기반 캐시 매니저.
    
    음식/운동 검색 결과를 효율적으로 캐싱하여 API 호출을 최적화합니다.
    """
    
    def __init__(self, 
                 max_memory_entries: int = 1000,
                 default_ttl: int = 3600,  # 1시간
                 cache_dir: str = ".cache",
                 enable_disk_cache: bool = True,
                 max_disk_size_mb: int = 100):
        """
        CacheManager 초기화.
        
        Args:
            max_memory_entries: 메모리 캐시 최대 엔트리 수
            default_ttl: 기본 TTL (초)
            cache_dir: 디스크 캐시 디렉토리
            enable_disk_cache: 디스크 캐시 활성화 여부
            max_disk_size_mb: 최대 디스크 캐시 크기 (MB)
        """
        self.max_memory_entries = max_memory_entries
        self.default_ttl = default_ttl
        self.cache_dir = Path(cache_dir)
        self.enable_disk_cache = enable_disk_cache
        self.max_disk_size_bytes = max_disk_size_mb * 1024 * 1024
        
        # 메모리 캐시 저장소
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # LRU를 위한 접근 순서
        
        # 스레드 안전성을 위한 락
        self.lock = Lock()
        
        # 통계
        self.stats = CacheStats()
        
        # 디스크 캐시 디렉토리 생성
        if self.enable_disk_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.food_cache_dir = self.cache_dir / "food"
            self.exercise_cache_dir = self.cache_dir / "exercise"
            self.food_cache_dir.mkdir(exist_ok=True)
            self.exercise_cache_dir.mkdir(exist_ok=True)
        
        print(f"✓ 캐시 매니저 초기화 완료")
        print(f"  - 메모리 캐시: 최대 {max_memory_entries}개 엔트리")
        print(f"  - 기본 TTL: {default_ttl}초")
        print(f"  - 디스크 캐시: {'활성화' if enable_disk_cache else '비활성화'}")
    
    def get_cached_food(self, food_name: str) -> Optional[List[FoodItem]]:
        """
        캐시된 음식 검색 결과를 반환합니다.
        
        Args:
            food_name: 음식명
            
        Returns:
            Optional[List[FoodItem]]: 캐시된 음식 목록 또는 None
        """
        cache_key = self._generate_food_cache_key(food_name)
        return self._get_from_cache(cache_key, "food")
    
    def cache_food_result(self, food_name: str, result: List[FoodItem], ttl: Optional[int] = None) -> None:
        """
        음식 검색 결과를 캐시에 저장합니다.
        
        Args:
            food_name: 음식명
            result: 검색 결과
            ttl: TTL (초), None이면 기본값 사용
        """
        cache_key = self._generate_food_cache_key(food_name)
        self._store_in_cache(cache_key, result, ttl or self.default_ttl, "food")
    
    def get_cached_exercise(self, exercise_name: str) -> Optional[List[ExerciseItem]]:
        """
        캐시된 운동 검색 결과를 반환합니다.
        
        Args:
            exercise_name: 운동명
            
        Returns:
            Optional[List[ExerciseItem]]: 캐시된 운동 목록 또는 None
        """
        cache_key = self._generate_exercise_cache_key(exercise_name)
        return self._get_from_cache(cache_key, "exercise")
    
    def cache_exercise_result(self, exercise_name: str, result: List[ExerciseItem], ttl: Optional[int] = None) -> None:
        """
        운동 검색 결과를 캐시에 저장합니다.
        
        Args:
            exercise_name: 운동명
            result: 검색 결과
            ttl: TTL (초), None이면 기본값 사용
        """
        cache_key = self._generate_exercise_cache_key(exercise_name)
        self._store_in_cache(cache_key, result, ttl or self.default_ttl, "exercise")
    
    def get_cached_nutrition(self, food_id: str) -> Optional[NutritionInfo]:
        """
        캐시된 영양정보를 반환합니다.
        
        Args:
            food_id: 음식 ID
            
        Returns:
            Optional[NutritionInfo]: 캐시된 영양정보 또는 None
        """
        cache_key = self._generate_nutrition_cache_key(food_id)
        return self._get_from_cache(cache_key, "nutrition")
    
    def cache_nutrition_result(self, food_id: str, nutrition: NutritionInfo, ttl: Optional[int] = None) -> None:
        """
        영양정보를 캐시에 저장합니다.
        
        Args:
            food_id: 음식 ID
            nutrition: 영양정보
            ttl: TTL (초), None이면 기본값 사용
        """
        cache_key = self._generate_nutrition_cache_key(food_id)
        self._store_in_cache(cache_key, nutrition, ttl or self.default_ttl, "nutrition")
    
    def _get_from_cache(self, cache_key: str, cache_type: str) -> Optional[Any]:
        """
        캐시에서 데이터를 조회합니다.
        
        Args:
            cache_key: 캐시 키
            cache_type: 캐시 타입 (food, exercise, nutrition)
            
        Returns:
            Optional[Any]: 캐시된 데이터 또는 None
        """
        with self.lock:
            self.stats.total_requests += 1
            
            # 메모리 캐시에서 먼저 확인
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                
                if entry.is_expired():
                    # 만료된 엔트리 제거
                    del self.memory_cache[cache_key]
                    if cache_key in self.access_order:
                        self.access_order.remove(cache_key)
                    self.stats.expired_entries += 1
                    self.stats.cache_misses += 1
                    
                    # 디스크 캐시에서 확인
                    return self._get_from_disk_cache(cache_key, cache_type)
                else:
                    # 유효한 엔트리 반환
                    entry.access()
                    self._update_access_order(cache_key)
                    self.stats.cache_hits += 1
                    
                    print(f"  💾 메모리 캐시 히트: {cache_key[:20]}...")
                    return entry.data
            
            # 메모리 캐시에 없으면 디스크 캐시 확인
            self.stats.cache_misses += 1
            return self._get_from_disk_cache(cache_key, cache_type)
    
    def _store_in_cache(self, cache_key: str, data: Any, ttl: int, cache_type: str) -> None:
        """
        데이터를 캐시에 저장합니다.
        
        Args:
            cache_key: 캐시 키
            data: 저장할 데이터
            ttl: TTL (초)
            cache_type: 캐시 타입
        """
        with self.lock:
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl)
            
            # 메모리 캐시 용량 확인 및 정리
            if len(self.memory_cache) >= self.max_memory_entries:
                self._evict_lru_entries()
            
            # 메모리 캐시에 저장
            entry = CacheEntry(
                key=cache_key,
                data=data,
                created_at=now,
                expires_at=expires_at
            )
            
            self.memory_cache[cache_key] = entry
            self._update_access_order(cache_key)
            
            # 디스크 캐시에도 저장
            if self.enable_disk_cache:
                self._store_in_disk_cache(cache_key, entry, cache_type)
            
            print(f"  💾 캐시 저장: {cache_key[:20]}... (TTL: {ttl}초)")
    
    def _get_from_disk_cache(self, cache_key: str, cache_type: str) -> Optional[Any]:
        """디스크 캐시에서 데이터를 조회합니다."""
        if not self.enable_disk_cache:
            return None
        
        try:
            cache_file = self._get_cache_file_path(cache_key, cache_type)
            
            if not cache_file.exists():
                return None
            
            # 파일에서 캐시 엔트리 로드
            with open(cache_file, 'rb') as f:
                entry = pickle.load(f)
            
            if entry.is_expired():
                # 만료된 파일 삭제
                cache_file.unlink(missing_ok=True)
                self.stats.expired_entries += 1
                return None
            
            # 메모리 캐시에도 로드 (용량 허용 시)
            if len(self.memory_cache) < self.max_memory_entries:
                entry.access()
                self.memory_cache[cache_key] = entry
                self._update_access_order(cache_key)
            
            self.stats.cache_hits += 1
            print(f"  💿 디스크 캐시 히트: {cache_key[:20]}...")
            return entry.data
            
        except Exception as e:
            print(f"  ⚠️ 디스크 캐시 읽기 오류: {str(e)}")
            return None
    
    def _store_in_disk_cache(self, cache_key: str, entry: CacheEntry, cache_type: str) -> None:
        """디스크 캐시에 데이터를 저장합니다."""
        try:
            cache_file = self._get_cache_file_path(cache_key, cache_type)
            
            # 디스크 용량 확인
            if self._get_disk_cache_size() > self.max_disk_size_bytes:
                self._cleanup_disk_cache()
            
            # 파일에 캐시 엔트리 저장
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
            
        except Exception as e:
            print(f"  ⚠️ 디스크 캐시 저장 오류: {str(e)}")
    
    def _generate_food_cache_key(self, food_name: str) -> str:
        """음식 캐시 키를 생성합니다."""
        normalized_name = food_name.lower().strip()
        return f"food:{hashlib.md5(normalized_name.encode()).hexdigest()}"
    
    def _generate_exercise_cache_key(self, exercise_name: str) -> str:
        """운동 캐시 키를 생성합니다."""
        normalized_name = exercise_name.lower().strip()
        return f"exercise:{hashlib.md5(normalized_name.encode()).hexdigest()}"
    
    def _generate_nutrition_cache_key(self, food_id: str) -> str:
        """영양정보 캐시 키를 생성합니다."""
        return f"nutrition:{hashlib.md5(food_id.encode()).hexdigest()}"
    
    def _get_cache_file_path(self, cache_key: str, cache_type: str) -> Path:
        """캐시 파일 경로를 생성합니다."""
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        
        if cache_type == "food":
            return self.food_cache_dir / f"{cache_hash}.cache"
        elif cache_type == "exercise":
            return self.exercise_cache_dir / f"{cache_hash}.cache"
        else:  # nutrition
            return self.food_cache_dir / f"nutrition_{cache_hash}.cache"
    
    def _update_access_order(self, cache_key: str) -> None:
        """LRU를 위한 접근 순서를 업데이트합니다."""
        if cache_key in self.access_order:
            self.access_order.remove(cache_key)
        self.access_order.append(cache_key)
    
    def _evict_lru_entries(self) -> None:
        """LRU 정책에 따라 오래된 엔트리를 제거합니다."""
        evict_count = max(1, self.max_memory_entries // 10)  # 10% 제거
        
        for _ in range(evict_count):
            if not self.access_order:
                break
            
            lru_key = self.access_order.pop(0)
            if lru_key in self.memory_cache:
                del self.memory_cache[lru_key]
                self.stats.evicted_entries += 1
        
        print(f"  🗑️ LRU 정책으로 {evict_count}개 엔트리 제거")
    
    def _get_disk_cache_size(self) -> int:
        """디스크 캐시 크기를 계산합니다."""
        if not self.enable_disk_cache:
            return 0
        
        total_size = 0
        for cache_dir in [self.food_cache_dir, self.exercise_cache_dir]:
            for cache_file in cache_dir.glob("*.cache"):
                try:
                    total_size += cache_file.stat().st_size
                except OSError:
                    continue
        
        return total_size
    
    def _cleanup_disk_cache(self) -> None:
        """디스크 캐시를 정리합니다."""
        print("  🧹 디스크 캐시 정리 시작")
        
        # 만료된 파일들 수집
        expired_files = []
        for cache_dir in [self.food_cache_dir, self.exercise_cache_dir]:
            for cache_file in cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                    
                    if entry.is_expired():
                        expired_files.append(cache_file)
                        
                except Exception:
                    # 손상된 파일도 제거 대상
                    expired_files.append(cache_file)
        
        # 만료된 파일 삭제
        for cache_file in expired_files:
            try:
                cache_file.unlink()
                self.stats.expired_entries += 1
            except OSError:
                continue
        
        print(f"  🗑️ {len(expired_files)}개 만료된 캐시 파일 삭제")
    
    def clear_expired_cache(self) -> int:
        """
        만료된 캐시 엔트리를 정리합니다.
        
        Returns:
            int: 정리된 엔트리 수
        """
        print("🧹 만료된 캐시 정리 시작")
        
        with self.lock:
            cleared_count = 0
            
            # 메모리 캐시 정리
            expired_keys = []
            for key, entry in self.memory_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                cleared_count += 1
            
            # 디스크 캐시 정리
            if self.enable_disk_cache:
                self._cleanup_disk_cache()
            
            self.stats.expired_entries += cleared_count
            
            print(f"✓ {cleared_count}개 만료된 캐시 엔트리 정리 완료")
            return cleared_count
    
    def clear_all_cache(self) -> None:
        """모든 캐시를 삭제합니다."""
        print("🗑️ 전체 캐시 삭제 시작")
        
        with self.lock:
            # 메모리 캐시 삭제
            memory_count = len(self.memory_cache)
            self.memory_cache.clear()
            self.access_order.clear()
            
            # 디스크 캐시 삭제
            disk_count = 0
            if self.enable_disk_cache:
                for cache_dir in [self.food_cache_dir, self.exercise_cache_dir]:
                    for cache_file in cache_dir.glob("*.cache"):
                        try:
                            cache_file.unlink()
                            disk_count += 1
                        except OSError:
                            continue
            
            # 통계 초기화
            self.stats = CacheStats()
            
            print(f"✓ 전체 캐시 삭제 완료")
            print(f"  - 메모리: {memory_count}개 엔트리")
            print(f"  - 디스크: {disk_count}개 파일")
    
    def get_cache_stats(self) -> CacheStats:
        """
        캐시 통계를 반환합니다.
        
        Returns:
            CacheStats: 캐시 통계 정보
        """
        with self.lock:
            # 메모리 사용량 계산 (대략적)
            self.stats.memory_usage_bytes = len(self.memory_cache) * 1024  # 대략 1KB per entry
            
            # 디스크 사용량 계산
            self.stats.disk_usage_bytes = self._get_disk_cache_size()
            
            return self.stats
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        상세한 캐시 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 캐시 정보
        """
        stats = self.get_cache_stats()
        
        return {
            "memory_cache": {
                "entries": len(self.memory_cache),
                "max_entries": self.max_memory_entries,
                "usage_percentage": (len(self.memory_cache) / self.max_memory_entries) * 100
            },
            "disk_cache": {
                "enabled": self.enable_disk_cache,
                "size_bytes": stats.disk_usage_bytes,
                "max_size_bytes": self.max_disk_size_bytes,
                "usage_percentage": (stats.disk_usage_bytes / self.max_disk_size_bytes) * 100 if self.enable_disk_cache else 0
            },
            "statistics": {
                "total_requests": stats.total_requests,
                "cache_hits": stats.cache_hits,
                "cache_misses": stats.cache_misses,
                "hit_rate": stats.hit_rate,
                "miss_rate": stats.miss_rate,
                "expired_entries": stats.expired_entries,
                "evicted_entries": stats.evicted_entries
            },
            "configuration": {
                "default_ttl": self.default_ttl,
                "cache_directory": str(self.cache_dir)
            }
        }
    
    def optimize_cache(self) -> Dict[str, int]:
        """
        캐시를 최적화합니다.
        
        Returns:
            Dict[str, int]: 최적화 결과
        """
        print("⚡ 캐시 최적화 시작")
        
        result = {
            "expired_cleared": 0,
            "lru_evicted": 0,
            "disk_cleaned": 0
        }
        
        # 만료된 엔트리 정리
        result["expired_cleared"] = self.clear_expired_cache()
        
        # 메모리 사용량이 80% 이상이면 LRU 제거
        if len(self.memory_cache) > self.max_memory_entries * 0.8:
            before_count = len(self.memory_cache)
            self._evict_lru_entries()
            result["lru_evicted"] = before_count - len(self.memory_cache)
        
        # 디스크 사용량이 80% 이상이면 정리
        if self.enable_disk_cache and self._get_disk_cache_size() > self.max_disk_size_bytes * 0.8:
            before_size = self._get_disk_cache_size()
            self._cleanup_disk_cache()
            after_size = self._get_disk_cache_size()
            result["disk_cleaned"] = before_size - after_size
        
        print(f"✓ 캐시 최적화 완료: {result}")
        return result