"""
식약처 식품영양성분 API 클라이언트.

식품의약품안전처에서 제공하는 식품영양성분 데이터베이스 Open API를 
활용하여 음식 검색 및 영양정보를 조회하는 기능을 제공합니다.
"""

import requests
import json
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, quote
from auth_controller import AuthController
from integrated_models import FoodItem, NutritionInfo
from exceptions import (
    FoodAPIError, NetworkError, TimeoutError, InvalidAPIKeyError,
    NoSearchResultsError, DataProcessingError, JSONParsingError
)


class FoodAPIClient:
    """
    식약처 식품영양성분 API 클라이언트.
    
    음식 검색, 영양정보 조회, 응답 처리 등의 기능을 제공합니다.
    """
    
    def __init__(self, auth_controller: AuthController, base_url: Optional[str] = None):
        """
        FoodAPIClient 초기화.
        
        Args:
            auth_controller: 인증 컨트롤러
            base_url: API 기본 URL (기본값: 식약처 공식 URL)
        """
        self.auth = auth_controller
        self.base_url = base_url or "https://openapi.foodsafetykorea.go.kr/api"
        self.api_key = None
        self.session = requests.Session()
        
        # API 설정
        self.timeout = self.auth.get_config_value("settings", {}).get("timeout", 30)
        self.retry_count = self.auth.get_config_value("settings", {}).get("retry_count", 3)
        self.retry_delay = 1.0  # 재시도 간격 (초)
        
        # API 엔드포인트
        self.endpoints = {
            "search": "I2790/json",  # 식품영양성분 조회 서비스
            "detail": "I2790/json"   # 상세 정보도 같은 엔드포인트 사용
        }
        
        # 요청 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Korean-Food-Nutrition-Client/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8'
        })
        
        self._initialize_api_key()
    
    def _initialize_api_key(self) -> None:
        """API 키 초기화 및 검증."""
        try:
            self.api_key = self.auth.get_api_key("food_api")
            self.auth.validate_credentials("food_api")
            print("✓ 식약처 API 키 초기화 완료")
        except Exception as e:
            error_msg = self.auth.handle_auth_error(e, "food_api")
            raise FoodAPIError(f"API 키 초기화 실패: {error_msg}")
    
    def search_food(self, food_name: str, start_idx: int = 1, end_idx: int = 10) -> List[FoodItem]:
        """
        음식명으로 검색하여 음식 목록을 반환합니다.
        
        Args:
            food_name: 검색할 음식명
            start_idx: 검색 시작 인덱스 (기본값: 1)
            end_idx: 검색 종료 인덱스 (기본값: 10)
            
        Returns:
            List[FoodItem]: 검색된 음식 목록
            
        Raises:
            FoodAPIError: API 호출 실패 시
            NoSearchResultsError: 검색 결과가 없을 때
        """
        if not food_name or not food_name.strip():
            raise FoodAPIError("검색할 음식명을 입력해주세요")
        
        food_name = food_name.strip()
        print(f"🔍 음식 검색: '{food_name}'")
        
        # API URL 구성
        url = f"{self.base_url}/{self.api_key}/{self.endpoints['search']}/{start_idx}/{end_idx}/DESC_KOR={quote(food_name)}"
        
        try:
            response_data = self._make_request(url)
            return self._parse_food_search_response(response_data, food_name)
            
        except Exception as e:
            if isinstance(e, (FoodAPIError, NoSearchResultsError)):
                raise
            raise FoodAPIError(f"음식 검색 중 오류 발생: {str(e)}")
    
    def get_nutrition_info(self, food_item: FoodItem) -> NutritionInfo:
        """
        특정 음식의 상세 영양정보를 조회합니다.
        
        Args:
            food_item: 영양정보를 조회할 음식 아이템
            
        Returns:
            NutritionInfo: 영양정보 객체
            
        Raises:
            FoodAPIError: API 호출 실패 시
        """
        print(f"📊 영양정보 조회: '{food_item.name}'")
        
        # 식약처 API는 검색과 상세정보가 같은 엔드포인트를 사용
        # food_id를 사용하여 정확한 매칭 시도
        try:
            # 음식명으로 재검색하여 정확한 데이터 확보
            search_results = self.search_food(food_item.name, 1, 5)
            
            # food_id가 일치하는 항목 찾기
            target_food = None
            for result in search_results:
                if result.food_id == food_item.food_id:
                    target_food = result
                    break
            
            if not target_food:
                # ID 매칭 실패 시 이름으로 매칭
                for result in search_results:
                    if result.name == food_item.name:
                        target_food = result
                        break
            
            if not target_food:
                raise FoodAPIError(f"'{food_item.name}' 음식의 상세 정보를 찾을 수 없습니다")
            
            # 영양정보는 검색 결과에 포함되어 있으므로 바로 파싱
            return self._extract_nutrition_from_food_data(target_food, {})
            
        except Exception as e:
            if isinstance(e, FoodAPIError):
                raise
            raise FoodAPIError(f"영양정보 조회 중 오류 발생: {str(e)}")
    
    def batch_search_foods(self, food_names: List[str]) -> Dict[str, List[FoodItem]]:
        """
        여러 음식을 일괄 검색합니다.
        
        Args:
            food_names: 검색할 음식명 목록
            
        Returns:
            Dict[str, List[FoodItem]]: 음식명별 검색 결과
        """
        print(f"📦 일괄 검색: {len(food_names)}개 음식")
        
        results = {}
        failed_searches = []
        
        for i, food_name in enumerate(food_names, 1):
            try:
                print(f"  [{i}/{len(food_names)}] {food_name}")
                search_result = self.search_food(food_name, 1, 5)
                results[food_name] = search_result
                
                # API 호출 제한을 위한 지연
                if i < len(food_names):
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"    ✗ 검색 실패: {str(e)}")
                failed_searches.append(food_name)
                results[food_name] = []
        
        if failed_searches:
            print(f"⚠️ 검색 실패한 음식: {', '.join(failed_searches)}")
        
        return results
    
    def _make_request(self, url: str) -> Dict[str, Any]:
        """
        API 요청을 수행하고 응답을 반환합니다.
        
        Args:
            url: 요청 URL
            
        Returns:
            Dict[str, Any]: 파싱된 JSON 응답
            
        Raises:
            NetworkError: 네트워크 오류 시
            TimeoutError: 타임아웃 시
            FoodAPIError: API 오류 시
        """
        last_exception = None
        
        for attempt in range(self.retry_count):
            try:
                if attempt > 0:
                    print(f"  재시도 {attempt}/{self.retry_count - 1}")
                    time.sleep(self.retry_delay * attempt)
                
                response = self.session.get(url, timeout=self.timeout)
                return self._handle_api_response(response)
                
            except requests.exceptions.Timeout as e:
                last_exception = TimeoutError(f"API 응답 시간 초과 ({self.timeout}초)")
            except requests.exceptions.ConnectionError as e:
                last_exception = NetworkError(f"네트워크 연결 실패: {str(e)}")
            except requests.exceptions.RequestException as e:
                last_exception = FoodAPIError(f"HTTP 요청 오류: {str(e)}")
            except Exception as e:
                last_exception = FoodAPIError(f"예상치 못한 오류: {str(e)}")
        
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
            FoodAPIError: API 오류 시
            InvalidAPIKeyError: 인증 오류 시
            JSONParsingError: JSON 파싱 오류 시
        """
        # HTTP 상태 코드 확인
        if response.status_code == 401:
            raise InvalidAPIKeyError("API 키가 유효하지 않습니다")
        elif response.status_code == 403:
            raise InvalidAPIKeyError("API 접근 권한이 없습니다")
        elif response.status_code == 429:
            raise FoodAPIError("API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요", response.status_code)
        elif response.status_code >= 500:
            raise FoodAPIError("서버 오류가 발생했습니다. 나중에 다시 시도해주세요", response.status_code)
        elif response.status_code != 200:
            raise FoodAPIError(f"API 호출 실패 (HTTP {response.status_code})", response.status_code)
        
        # JSON 파싱
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise JSONParsingError(f"JSON 파싱 실패: {str(e)}")
        
        # API 응답 구조 검증
        if not isinstance(data, dict):
            raise FoodAPIError("잘못된 API 응답 형식")
        
        # 식약처 API 특정 오류 확인
        if "RESULT" in data:
            result = data["RESULT"]
            if result.get("CODE") != "INFO-000":
                error_msg = result.get("MSG", "알 수 없는 오류")
                if "해당하는 데이터가 없습니다" in error_msg:
                    raise NoSearchResultsError("검색 결과가 없습니다")
                raise FoodAPIError(f"API 오류: {error_msg}")
        
        return data
    
    def _parse_food_search_response(self, response_data: Dict[str, Any], search_term: str) -> List[FoodItem]:
        """
        음식 검색 응답을 파싱하여 FoodItem 목록을 생성합니다.
        
        Args:
            response_data: API 응답 데이터
            search_term: 검색어
            
        Returns:
            List[FoodItem]: 파싱된 음식 목록
            
        Raises:
            NoSearchResultsError: 검색 결과가 없을 때
            DataProcessingError: 데이터 처리 오류 시
        """
        try:
            # 식약처 API 응답 구조: {"I2790": [{"row": [...]}]}
            service_key = "I2790"
            if service_key not in response_data:
                raise NoSearchResultsError(f"'{search_term}' 검색 결과가 없습니다")
            
            service_data = response_data[service_key]
            if not service_data or "row" not in service_data[0]:
                raise NoSearchResultsError(f"'{search_term}' 검색 결과가 없습니다")
            
            rows = service_data[0]["row"]
            if not rows:
                raise NoSearchResultsError(f"'{search_term}' 검색 결과가 없습니다")
            
            food_items = []
            for row in rows:
                try:
                    food_item = self._create_food_item_from_row(row)
                    food_items.append(food_item)
                except Exception as e:
                    print(f"    ⚠️ 음식 데이터 파싱 실패: {str(e)}")
                    continue
            
            if not food_items:
                raise NoSearchResultsError(f"'{search_term}' 유효한 검색 결과가 없습니다")
            
            print(f"✓ {len(food_items)}개 음식 검색 완료")
            return food_items
            
        except NoSearchResultsError:
            raise
        except Exception as e:
            raise DataProcessingError(f"검색 결과 처리 중 오류: {str(e)}")
    
    def _create_food_item_from_row(self, row: Dict[str, Any]) -> FoodItem:
        """
        API 응답의 row 데이터에서 FoodItem을 생성합니다.
        
        Args:
            row: API 응답의 개별 음식 데이터
            
        Returns:
            FoodItem: 생성된 음식 아이템
        """
        # 필수 필드 추출
        name = row.get("DESC_KOR", "").strip()
        food_id = str(row.get("NUM", "")).strip()
        
        if not name:
            raise DataProcessingError("음식명이 없습니다")
        if not food_id:
            raise DataProcessingError("음식 ID가 없습니다")
        
        # 선택적 필드 추출
        category = row.get("GROUP_NAME", "").strip() or None
        manufacturer = row.get("MAKER_NAME", "").strip() or None
        
        return FoodItem(
            name=name,
            food_id=food_id,
            category=category,
            manufacturer=manufacturer
        )
    
    def _extract_nutrition_from_food_data(self, food_item: FoodItem, row_data: Dict[str, Any]) -> NutritionInfo:
        """
        음식 데이터에서 영양정보를 추출합니다.
        
        Args:
            food_item: 음식 아이템
            row_data: API 응답의 영양정보 데이터
            
        Returns:
            NutritionInfo: 영양정보 객체
        """
        try:
            # 기본 영양소 추출 (100g 기준)
            calories = self._safe_float_conversion(row_data.get("NUTR_CONT1", "0"))  # 칼로리
            carbohydrate = self._safe_float_conversion(row_data.get("NUTR_CONT2", "0"))  # 탄수화물
            protein = self._safe_float_conversion(row_data.get("NUTR_CONT3", "0"))  # 단백질
            fat = self._safe_float_conversion(row_data.get("NUTR_CONT4", "0"))  # 지방
            
            # 선택적 영양소
            fiber = self._safe_float_conversion(row_data.get("NUTR_CONT5", ""), allow_none=True)  # 식이섬유
            sodium = self._safe_float_conversion(row_data.get("NUTR_CONT6", ""), allow_none=True)  # 나트륨
            
            return NutritionInfo(
                food_item=food_item,
                calories_per_100g=calories,
                carbohydrate=carbohydrate,
                protein=protein,
                fat=fat,
                fiber=fiber,
                sodium=sodium
            )
            
        except Exception as e:
            # 영양정보가 없는 경우 기본값으로 생성
            print(f"    ⚠️ 영양정보 추출 실패, 기본값 사용: {str(e)}")
            return NutritionInfo(
                food_item=food_item,
                calories_per_100g=0.0,
                carbohydrate=0.0,
                protein=0.0,
                fat=0.0
            )
    
    def _safe_float_conversion(self, value: Any, allow_none: bool = False) -> Optional[float]:
        """
        안전한 float 변환을 수행합니다.
        
        Args:
            value: 변환할 값
            allow_none: None 허용 여부
            
        Returns:
            Optional[float]: 변환된 값 또는 None
        """
        if value is None or value == "":
            return None if allow_none else 0.0
        
        try:
            # 문자열에서 숫자가 아닌 문자 제거
            if isinstance(value, str):
                # 한국어 단위 제거 (예: "10.5g" -> "10.5")
                import re
                cleaned = re.sub(r'[^\d.-]', '', value)
                if not cleaned:
                    return None if allow_none else 0.0
                value = cleaned
            
            result = float(value)
            return result if result >= 0 else (None if allow_none else 0.0)
            
        except (ValueError, TypeError):
            return None if allow_none else 0.0
    
    def get_api_status(self) -> Dict[str, Any]:
        """
        API 상태 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: API 상태 정보
        """
        return {
            "api_name": "식약처 식품영양성분 API",
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "endpoints": self.endpoints
        }