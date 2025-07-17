"""
한국건강증진개발원 운동 API 클라이언트.

한국건강증진개발원에서 제공하는 보건소 모바일 헬스케어 운동 API를 
활용하여 운동 검색 및 MET 계수 정보를 조회하는 기능을 제공합니다.
"""

import requests
import json
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, quote
from auth_controller import AuthController
from integrated_models import ExerciseItem, ExerciseSession
from exceptions import (
    ExerciseAPIError, NetworkError, TimeoutError, InvalidAPIKeyError,
    NoSearchResultsError, DataProcessingError, JSONParsingError
)


class ExerciseAPIClient:
    """
    한국건강증진개발원 운동 API 클라이언트.
    
    운동 검색, MET 계수 조회, 응답 처리 등의 기능을 제공합니다.
    """
    
    def __init__(self, auth_controller: AuthController, base_url: Optional[str] = None):
        """
        ExerciseAPIClient 초기화.
        
        Args:
            auth_controller: 인증 컨트롤러
            base_url: API 기본 URL (기본값: 건강증진원 공식 URL)
        """
        self.auth = auth_controller
        self.base_url = base_url or "https://openapi.k-health.or.kr/api"
        self.api_key = None
        self.session = requests.Session()
        
        # API 설정
        self.timeout = self.auth.get_config_value("settings", {}).get("timeout", 30)
        self.retry_count = self.auth.get_config_value("settings", {}).get("retry_count", 3)
        self.retry_delay = 1.0  # 재시도 간격 (초)
        
        # API 엔드포인트 (실제 API 구조에 맞게 조정 필요)
        self.endpoints = {
            "search": "exercise/search",  # 운동 검색
            "detail": "exercise/detail",  # 운동 상세정보
            "categories": "exercise/categories"  # 운동 분류
        }
        
        # 요청 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Korean-Exercise-API-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        
        # 기본 MET 값 데이터베이스 (API가 제공하지 않는 경우 대비)
        self.default_met_values = {
            "걷기": 3.5,
            "빠른걷기": 4.3,
            "조깅": 7.0,
            "달리기": 8.0,
            "빠른달리기": 11.0,
            "자전거타기": 6.8,
            "수영": 8.0,
            "등산": 6.0,
            "계단오르기": 8.8,
            "줄넘기": 12.3,
            "팔굽혀펴기": 8.0,
            "윗몸일으키기": 8.0,
            "스쿼트": 8.0,
            "요가": 2.5,
            "필라테스": 3.0,
            "태권도": 10.0,
            "축구": 10.0,
            "농구": 8.0,
            "배드민턴": 7.0,
            "탁구": 4.0,
            "테니스": 8.0,
            "골프": 4.8,
            "볼링": 3.0,
            "춤": 5.0,
            "에어로빅": 7.3,
            "헬스": 6.0,
            "웨이트트레이닝": 6.0
        }
        
        self._initialize_api_key()
    
    def _initialize_api_key(self) -> None:
        """API 키 초기화 및 검증."""
        try:
            self.api_key = self.auth.get_api_key("exercise_api")
            self.auth.validate_credentials("exercise_api")
            print("✓ 건강증진원 운동 API 키 초기화 완료")
        except Exception as e:
            error_msg = self.auth.handle_auth_error(e, "exercise_api")
            raise ExerciseAPIError(f"API 키 초기화 실패: {error_msg}")
    
    def search_exercise(self, exercise_name: str, category: Optional[str] = None) -> List[ExerciseItem]:
        """
        운동명으로 검색하여 운동 목록을 반환합니다.
        
        Args:
            exercise_name: 검색할 운동명
            category: 운동 분류 (선택사항)
            
        Returns:
            List[ExerciseItem]: 검색된 운동 목록
            
        Raises:
            ExerciseAPIError: API 호출 실패 시
            NoSearchResultsError: 검색 결과가 없을 때
        """
        if not exercise_name or not exercise_name.strip():
            raise ExerciseAPIError("검색할 운동명을 입력해주세요")
        
        exercise_name = exercise_name.strip()
        print(f"🏃 운동 검색: '{exercise_name}'")
        
        try:
            # 실제 API가 없는 경우를 대비한 시뮬레이션
            if self._is_simulation_mode():
                return self._simulate_exercise_search(exercise_name, category)
            
            # 실제 API 호출
            return self._call_real_api_search(exercise_name, category)
            
        except Exception as e:
            if isinstance(e, (ExerciseAPIError, NoSearchResultsError)):
                raise
            raise ExerciseAPIError(f"운동 검색 중 오류 발생: {str(e)}")
    
    def get_exercise_details(self, exercise_id: str) -> ExerciseItem:
        """
        특정 운동의 상세 정보를 조회합니다.
        
        Args:
            exercise_id: 운동 ID
            
        Returns:
            ExerciseItem: 운동 상세 정보
            
        Raises:
            ExerciseAPIError: API 호출 실패 시
        """
        print(f"📊 운동 상세정보 조회: ID '{exercise_id}'")
        
        try:
            if self._is_simulation_mode():
                return self._simulate_exercise_detail(exercise_id)
            
            return self._call_real_api_detail(exercise_id)
            
        except Exception as e:
            if isinstance(e, ExerciseAPIError):
                raise
            raise ExerciseAPIError(f"운동 상세정보 조회 중 오류 발생: {str(e)}")
    
    def get_exercise_categories(self) -> List[Dict[str, str]]:
        """
        운동 분류 목록을 조회합니다.
        
        Returns:
            List[Dict[str, str]]: 운동 분류 목록
        """
        print("📋 운동 분류 목록 조회")
        
        # 기본 운동 분류
        categories = [
            {"id": "aerobic", "name": "유산소운동", "description": "심폐지구력 향상 운동"},
            {"id": "strength", "name": "근력운동", "description": "근력 및 근지구력 향상 운동"},
            {"id": "flexibility", "name": "유연성운동", "description": "관절 가동범위 향상 운동"},
            {"id": "sports", "name": "스포츠", "description": "구기종목 및 경기 스포츠"},
            {"id": "traditional", "name": "전통운동", "description": "한국 전통 운동 및 무술"},
            {"id": "daily", "name": "일상활동", "description": "일상생활 중 신체활동"}
        ]
        
        return categories
    
    def batch_search_exercises(self, exercise_names: List[str]) -> Dict[str, List[ExerciseItem]]:
        """
        여러 운동을 일괄 검색합니다.
        
        Args:
            exercise_names: 검색할 운동명 목록
            
        Returns:
            Dict[str, List[ExerciseItem]]: 운동명별 검색 결과
        """
        print(f"📦 운동 일괄 검색: {len(exercise_names)}개 운동")
        
        results = {}
        failed_searches = []
        
        for i, exercise_name in enumerate(exercise_names, 1):
            try:
                print(f"  [{i}/{len(exercise_names)}] {exercise_name}")
                search_result = self.search_exercise(exercise_name)
                results[exercise_name] = search_result
                
                # API 호출 제한을 위한 지연
                if i < len(exercise_names):
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"    ✗ 검색 실패: {str(e)}")
                failed_searches.append(exercise_name)
                results[exercise_name] = []
        
        if failed_searches:
            print(f"⚠️ 검색 실패한 운동: {', '.join(failed_searches)}")
        
        return results
    
    def _is_simulation_mode(self) -> bool:
        """
        시뮬레이션 모드 여부를 확인합니다.
        실제 API가 사용 불가능한 경우 시뮬레이션 모드로 동작합니다.
        """
        # 테스트 API 키인 경우 시뮬레이션 모드
        return self.api_key and "test_" in self.api_key.lower()
    
    def _simulate_exercise_search(self, exercise_name: str, category: Optional[str] = None) -> List[ExerciseItem]:
        """
        운동 검색 시뮬레이션.
        실제 API가 없는 경우 기본 데이터로 응답을 생성합니다.
        """
        print("  (시뮬레이션 모드)")
        
        # 검색어와 매칭되는 운동 찾기
        matched_exercises = []
        
        for exercise, met_value in self.default_met_values.items():
            if exercise_name in exercise or exercise in exercise_name:
                # 운동 분류 결정
                exercise_category = self._determine_exercise_category(exercise)
                
                # 카테고리 필터링
                if category and category != exercise_category:
                    continue
                
                exercise_item = ExerciseItem(
                    name=exercise,
                    description=f"{exercise} 운동 (MET: {met_value})",
                    met_value=met_value,
                    category=exercise_category,
                    exercise_id=f"EX_{hash(exercise) % 10000:04d}"
                )
                matched_exercises.append(exercise_item)
        
        # 정확한 매칭 우선, 부분 매칭 후순위
        exact_matches = [ex for ex in matched_exercises if ex.name == exercise_name]
        partial_matches = [ex for ex in matched_exercises if ex.name != exercise_name]
        
        results = exact_matches + partial_matches
        
        if not results:
            raise NoSearchResultsError(f"'{exercise_name}' 운동을 찾을 수 없습니다")
        
        # 최대 5개까지만 반환
        return results[:5]
    
    def _simulate_exercise_detail(self, exercise_id: str) -> ExerciseItem:
        """운동 상세정보 시뮬레이션."""
        print("  (시뮬레이션 모드)")
        
        # ID에서 운동명 추출 (간단한 매핑)
        exercise_mapping = {
            "EX_0001": ("달리기", 8.0, "유산소운동"),
            "EX_0002": ("걷기", 3.5, "유산소운동"),
            "EX_0003": ("수영", 8.0, "유산소운동"),
            "EX_0004": ("자전거타기", 6.8, "유산소운동"),
            "EX_0005": ("등산", 6.0, "유산소운동")
        }
        
        if exercise_id in exercise_mapping:
            name, met_value, category = exercise_mapping[exercise_id]
            return ExerciseItem(
                name=name,
                description=f"{name} - 상세 정보 (MET: {met_value})",
                met_value=met_value,
                category=category,
                exercise_id=exercise_id
            )
        else:
            raise ExerciseAPIError(f"운동 ID '{exercise_id}'를 찾을 수 없습니다")
    
    def _determine_exercise_category(self, exercise_name: str) -> str:
        """운동명을 기반으로 분류를 결정합니다."""
        aerobic_keywords = ["걷기", "달리기", "조깅", "자전거", "수영", "등산", "에어로빅", "춤"]
        strength_keywords = ["팔굽혀펴기", "윗몸일으키기", "스쿼트", "헬스", "웨이트"]
        flexibility_keywords = ["요가", "필라테스", "스트레칭"]
        sports_keywords = ["축구", "농구", "배드민턴", "탁구", "테니스", "골프", "볼링"]
        traditional_keywords = ["태권도", "검도", "합기도", "씨름"]
        
        for keyword in aerobic_keywords:
            if keyword in exercise_name:
                return "유산소운동"
        
        for keyword in strength_keywords:
            if keyword in exercise_name:
                return "근력운동"
        
        for keyword in flexibility_keywords:
            if keyword in exercise_name:
                return "유연성운동"
        
        for keyword in sports_keywords:
            if keyword in exercise_name:
                return "스포츠"
        
        for keyword in traditional_keywords:
            if keyword in exercise_name:
                return "전통운동"
        
        return "일반운동"
    
    def _call_real_api_search(self, exercise_name: str, category: Optional[str] = None) -> List[ExerciseItem]:
        """실제 API 호출을 통한 운동 검색."""
        # 실제 API URL 구성
        url = f"{self.base_url}/{self.endpoints['search']}"
        
        params = {
            "serviceKey": self.api_key,
            "exercise_name": exercise_name,
            "numOfRows": 10,
            "pageNo": 1,
            "type": "json"
        }
        
        if category:
            params["category"] = category
        
        try:
            response_data = self._make_request(url, params)
            return self._parse_exercise_search_response(response_data, exercise_name)
            
        except Exception as e:
            if isinstance(e, (ExerciseAPIError, NoSearchResultsError)):
                raise
            raise ExerciseAPIError(f"실제 API 호출 실패: {str(e)}")
    
    def _call_real_api_detail(self, exercise_id: str) -> ExerciseItem:
        """실제 API 호출을 통한 운동 상세정보 조회."""
        url = f"{self.base_url}/{self.endpoints['detail']}"
        
        params = {
            "serviceKey": self.api_key,
            "exercise_id": exercise_id,
            "type": "json"
        }
        
        try:
            response_data = self._make_request(url, params)
            return self._parse_exercise_detail_response(response_data, exercise_id)
            
        except Exception as e:
            if isinstance(e, ExerciseAPIError):
                raise
            raise ExerciseAPIError(f"실제 API 상세정보 호출 실패: {str(e)}")
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        API 요청을 수행하고 응답을 반환합니다.
        
        Args:
            url: 요청 URL
            params: 요청 매개변수
            
        Returns:
            Dict[str, Any]: 파싱된 JSON 응답
            
        Raises:
            NetworkError: 네트워크 오류 시
            TimeoutError: 타임아웃 시
            ExerciseAPIError: API 오류 시
        """
        last_exception = None
        
        for attempt in range(self.retry_count):
            try:
                if attempt > 0:
                    print(f"  재시도 {attempt}/{self.retry_count - 1}")
                    time.sleep(self.retry_delay * attempt)
                
                response = self.session.get(url, params=params, timeout=self.timeout)
                return self._handle_api_response(response)
                
            except requests.exceptions.Timeout as e:
                last_exception = TimeoutError(f"API 응답 시간 초과 ({self.timeout}초)")
            except requests.exceptions.ConnectionError as e:
                last_exception = NetworkError(f"네트워크 연결 실패: {str(e)}")
            except requests.exceptions.RequestException as e:
                last_exception = ExerciseAPIError(f"HTTP 요청 오류: {str(e)}")
            except Exception as e:
                last_exception = ExerciseAPIError(f"예상치 못한 오류: {str(e)}")
        
        # 모든 재시도 실패
        raise last_exception
    
    def _handle_api_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        API 응답을 처리하고 검증합니다.
        
        Args:
            response: HTTP 응답 객체
            
        Returns:
            Dict[str, Any]: 파싱된 응답 데이터
            
        Raises:
            ExerciseAPIError: API 오류 시
            InvalidAPIKeyError: 인증 오류 시
            JSONParsingError: JSON 파싱 오류 시
        """
        # HTTP 상태 코드 확인
        if response.status_code == 401:
            raise InvalidAPIKeyError("운동 API 키가 유효하지 않습니다")
        elif response.status_code == 403:
            raise InvalidAPIKeyError("운동 API 접근 권한이 없습니다")
        elif response.status_code == 429:
            raise ExerciseAPIError("운동 API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요", response.status_code)
        elif response.status_code >= 500:
            raise ExerciseAPIError("운동 API 서버 오류가 발생했습니다. 나중에 다시 시도해주세요", response.status_code)
        elif response.status_code != 200:
            raise ExerciseAPIError(f"운동 API 호출 실패 (HTTP {response.status_code})", response.status_code)
        
        # JSON 파싱
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise JSONParsingError(f"운동 API JSON 파싱 실패: {str(e)}")
        
        return data
    
    def _parse_exercise_search_response(self, response_data: Dict[str, Any], search_term: str) -> List[ExerciseItem]:
        """
        운동 검색 응답을 파싱하여 ExerciseItem 목록을 생성합니다.
        
        Args:
            response_data: API 응답 데이터
            search_term: 검색어
            
        Returns:
            List[ExerciseItem]: 파싱된 운동 목록
        """
        # 실제 API 응답 구조에 맞게 구현
        # 현재는 시뮬레이션 모드에서만 사용되므로 기본 구현
        return []
    
    def _parse_exercise_detail_response(self, response_data: Dict[str, Any], exercise_id: str) -> ExerciseItem:
        """
        운동 상세정보 응답을 파싱하여 ExerciseItem을 생성합니다.
        
        Args:
            response_data: API 응답 데이터
            exercise_id: 운동 ID
            
        Returns:
            ExerciseItem: 파싱된 운동 정보
        """
        # 실제 API 응답 구조에 맞게 구현
        # 현재는 시뮬레이션 모드에서만 사용되므로 기본 구현
        raise ExerciseAPIError("실제 API 상세정보 파싱이 구현되지 않았습니다")
    
    def _parse_met_value(self, exercise_data: Dict[str, Any]) -> float:
        """
        운동 데이터에서 MET 값을 추출합니다.
        
        Args:
            exercise_data: 운동 데이터
            
        Returns:
            float: MET 값
        """
        # 다양한 필드명에서 MET 값 추출 시도
        met_fields = ["met", "met_value", "metabolic_equivalent", "intensity"]
        
        for field in met_fields:
            if field in exercise_data:
                try:
                    return float(exercise_data[field])
                except (ValueError, TypeError):
                    continue
        
        # MET 값을 찾을 수 없는 경우 기본값 반환
        return 5.0  # 중간 강도 운동의 평균 MET 값
    
    def get_api_status(self) -> Dict[str, Any]:
        """
        API 상태 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: API 상태 정보
        """
        return {
            "api_name": "한국건강증진개발원 운동 API",
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "simulation_mode": self._is_simulation_mode(),
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "endpoints": self.endpoints,
            "supported_exercises": len(self.default_met_values)
        }
    
    def get_supported_exercises(self) -> Dict[str, float]:
        """
        지원되는 운동 목록과 MET 값을 반환합니다.
        
        Returns:
            Dict[str, float]: 운동명과 MET 값의 매핑
        """
        return self.default_met_values.copy()