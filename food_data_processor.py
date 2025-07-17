"""
음식 데이터 프로세서.

식약처 API에서 받은 음식 데이터를 파싱, 검증, 정규화하는 기능을 제공합니다.
누락된 데이터 처리, 데이터 품질 검증, 한국 음식 특화 처리 등을 포함합니다.
"""

import re
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from integrated_models import FoodItem, NutritionInfo
from exceptions import (
    DataProcessingError, NutritionDataError, JSONParsingError,
    DataValidationError, DataConversionError
)


class FoodDataProcessor:
    """
    음식 데이터 파싱 및 검증 프로세서.
    
    API 응답 파싱, 영양정보 추출, 데이터 검증 및 정규화 기능을 제공합니다.
    """
    
    def __init__(self):
        """FoodDataProcessor 초기화."""
        # 한국 음식 분류 매핑
        self.korean_food_categories = {
            "곡류": ["밥", "죽", "면", "빵", "떡", "시리얼"],
            "채소류": ["김치", "나물", "샐러드", "채소", "버섯"],
            "과일류": ["사과", "배", "바나나", "오렌지", "포도", "딸기"],
            "육류": ["소고기", "돼지고기", "닭고기", "양고기", "오리고기"],
            "어패류": ["생선", "새우", "오징어", "조개", "게", "멸치"],
            "유제품": ["우유", "치즈", "요구르트", "버터", "크림"],
            "두류": ["콩", "두부", "된장", "청국장", "콩나물"],
            "견과류": ["호두", "아몬드", "땅콩", "잣", "참깨"],
            "조미료": ["소금", "설탕", "간장", "고추장", "마요네즈"],
            "음료": ["차", "커피", "주스", "탄산음료", "술"],
            "찌개류": ["김치찌개", "된장찌개", "부대찌개", "순두부찌개"],
            "국류": ["미역국", "콩나물국", "북어국", "갈비탕"],
            "반찬류": ["무침", "조림", "볶음", "구이", "튀김"]
        }
        
        # 영양소 필드 매핑 (식약처 API 기준)
        self.nutrition_field_mapping = {
            "calories": ["NUTR_CONT1", "칼로리", "에너지", "kcal"],
            "carbohydrate": ["NUTR_CONT2", "탄수화물", "당질", "carb"],
            "protein": ["NUTR_CONT3", "단백질", "protein"],
            "fat": ["NUTR_CONT4", "지방", "지질", "fat"],
            "fiber": ["NUTR_CONT5", "식이섬유", "섬유질", "fiber"],
            "sodium": ["NUTR_CONT6", "나트륨", "sodium", "salt"],
            "sugar": ["NUTR_CONT7", "당류", "설탕", "sugar"],
            "calcium": ["NUTR_CONT8", "칼슘", "calcium"],
            "iron": ["NUTR_CONT9", "철분", "iron"],
            "vitamin_c": ["NUTR_CONT10", "비타민C", "vitamin_c"]
        }
        
        # 데이터 품질 기준
        self.quality_thresholds = {
            "max_calories": 900.0,      # 100g당 최대 칼로리
            "max_carbohydrate": 100.0,  # 100g당 최대 탄수화물
            "max_protein": 100.0,       # 100g당 최대 단백질
            "max_fat": 100.0,          # 100g당 최대 지방
            "max_sodium": 50000.0,     # 100g당 최대 나트륨 (mg)
            "min_reasonable_value": 0.1 # 최소 합리적 값
        }
        
        # 처리 통계
        self.processing_stats = {
            "total_processed": 0,
            "successful_processed": 0,
            "failed_processed": 0,
            "data_corrections": 0,
            "missing_data_filled": 0
        }
    
    def parse_api_response(self, response_data: Dict[str, Any]) -> List[FoodItem]:
        """
        API 응답을 파싱하여 FoodItem 목록을 생성합니다.
        
        Args:
            response_data: 식약처 API 응답 데이터
            
        Returns:
            List[FoodItem]: 파싱된 음식 아이템 목록
            
        Raises:
            JSONParsingError: JSON 파싱 오류 시
            DataProcessingError: 데이터 처리 오류 시
        """
        print("📊 API 응답 데이터 파싱 시작")
        
        try:
            # 식약처 API 응답 구조 검증
            if not isinstance(response_data, dict):
                raise JSONParsingError("API 응답이 딕셔너리 형태가 아닙니다")
            
            # 서비스 키 확인 (I2790)
            service_key = "I2790"
            if service_key not in response_data:
                raise DataProcessingError(f"API 응답에 서비스 키 '{service_key}'가 없습니다")
            
            service_data = response_data[service_key]
            if not service_data or not isinstance(service_data, list):
                raise DataProcessingError("서비스 데이터가 올바르지 않습니다")
            
            # row 데이터 추출
            if "row" not in service_data[0]:
                raise DataProcessingError("API 응답에 'row' 데이터가 없습니다")
            
            rows = service_data[0]["row"]
            if not isinstance(rows, list):
                raise DataProcessingError("row 데이터가 리스트 형태가 아닙니다")
            
            # 각 row를 FoodItem으로 변환
            food_items = []
            self.processing_stats["total_processed"] = len(rows)
            
            for i, row in enumerate(rows):
                try:
                    food_item = self._parse_single_food_item(row, i + 1)
                    food_items.append(food_item)
                    self.processing_stats["successful_processed"] += 1
                    
                except Exception as e:
                    print(f"  ⚠️ 음식 항목 {i + 1} 파싱 실패: {str(e)}")
                    self.processing_stats["failed_processed"] += 1
                    continue
            
            if not food_items:
                raise DataProcessingError("파싱 가능한 음식 데이터가 없습니다")
            
            print(f"✓ {len(food_items)}개 음식 아이템 파싱 완료")
            return food_items
            
        except Exception as e:
            if isinstance(e, (JSONParsingError, DataProcessingError)):
                raise
            raise DataProcessingError(f"API 응답 파싱 중 오류: {str(e)}")
    
    def _parse_single_food_item(self, row_data: Dict[str, Any], index: int) -> FoodItem:
        """
        단일 음식 데이터를 파싱하여 FoodItem을 생성합니다.
        
        Args:
            row_data: 개별 음식 데이터
            index: 데이터 인덱스
            
        Returns:
            FoodItem: 생성된 음식 아이템
        """
        try:
            # 필수 필드 추출
            name = self._extract_food_name(row_data)
            food_id = self._extract_food_id(row_data)
            
            # 선택적 필드 추출
            category = self._extract_category(row_data, name)
            manufacturer = self._extract_manufacturer(row_data)
            
            # FoodItem 생성 및 검증
            food_item = FoodItem(
                name=name,
                food_id=food_id,
                category=category,
                manufacturer=manufacturer
            )
            
            return food_item
            
        except Exception as e:
            raise DataProcessingError(f"음식 항목 {index} 파싱 실패: {str(e)}")
    
    def _extract_food_name(self, row_data: Dict[str, Any]) -> str:
        """음식명을 추출하고 정규화합니다."""
        # 다양한 필드명에서 음식명 추출 시도
        name_fields = ["DESC_KOR", "FOOD_NM_KR", "음식명", "name"]
        
        for field in name_fields:
            if field in row_data and row_data[field]:
                name = str(row_data[field]).strip()
                if name:
                    return self._normalize_food_name(name)
        
        raise DataValidationError("음식명을 찾을 수 없습니다")
    
    def _extract_food_id(self, row_data: Dict[str, Any]) -> str:
        """음식 ID를 추출합니다."""
        id_fields = ["NUM", "FOOD_CD", "ID", "food_id"]
        
        for field in id_fields:
            if field in row_data and row_data[field]:
                food_id = str(row_data[field]).strip()
                if food_id:
                    return food_id
        
        raise DataValidationError("음식 ID를 찾을 수 없습니다")
    
    def _extract_category(self, row_data: Dict[str, Any], food_name: str) -> Optional[str]:
        """음식 분류를 추출하거나 추론합니다."""
        # API에서 제공하는 분류 확인
        category_fields = ["GROUP_NAME", "FOOD_GROUP", "분류", "category"]
        
        for field in category_fields:
            if field in row_data and row_data[field]:
                category = str(row_data[field]).strip()
                if category and category != "기타":
                    return category
        
        # 음식명을 기반으로 분류 추론
        return self._infer_category_from_name(food_name)
    
    def _extract_manufacturer(self, row_data: Dict[str, Any]) -> Optional[str]:
        """제조사 정보를 추출합니다."""
        manufacturer_fields = ["MAKER_NAME", "COMPANY", "제조사", "manufacturer"]
        
        for field in manufacturer_fields:
            if field in row_data and row_data[field]:
                manufacturer = str(row_data[field]).strip()
                if manufacturer and manufacturer not in ["일반", "기타", "없음"]:
                    return manufacturer
        
        return None
    
    def _normalize_food_name(self, name: str) -> str:
        """음식명을 정규화합니다."""
        # 불필요한 문자 제거
        name = re.sub(r'[^\w\s가-힣]', '', name)
        
        # 연속된 공백을 하나로 변경
        name = re.sub(r'\s+', ' ', name)
        
        # 앞뒤 공백 제거
        name = name.strip()
        
        if not name:
            raise DataValidationError("정규화 후 음식명이 비어있습니다")
        
        return name
    
    def _infer_category_from_name(self, food_name: str) -> Optional[str]:
        """음식명을 기반으로 분류를 추론합니다."""
        for category, keywords in self.korean_food_categories.items():
            for keyword in keywords:
                if keyword in food_name:
                    return category
        
        return None
    
    def extract_nutrition_info(self, food_data: Dict[str, Any]) -> NutritionInfo:
        """
        음식 데이터에서 영양정보를 추출합니다.
        
        Args:
            food_data: 음식 데이터 (FoodItem + API row 데이터)
            
        Returns:
            NutritionInfo: 추출된 영양정보
            
        Raises:
            NutritionDataError: 영양정보 추출 실패 시
        """
        try:
            # FoodItem 추출
            if "food_item" in food_data:
                food_item = food_data["food_item"]
            else:
                # API 데이터에서 FoodItem 생성
                food_item = self._parse_single_food_item(food_data, 1)
            
            # 영양소 데이터 추출
            nutrition_data = self._extract_nutrition_values(food_data)
            
            # NutritionInfo 생성
            nutrition_info = NutritionInfo(
                food_item=food_item,
                calories_per_100g=nutrition_data["calories"],
                carbohydrate=nutrition_data["carbohydrate"],
                protein=nutrition_data["protein"],
                fat=nutrition_data["fat"],
                fiber=nutrition_data.get("fiber"),
                sodium=nutrition_data.get("sodium")
            )
            
            return nutrition_info
            
        except Exception as e:
            if isinstance(e, NutritionDataError):
                raise
            raise NutritionDataError(f"영양정보 추출 실패: {str(e)}")
    
    def _extract_nutrition_values(self, food_data: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """영양소 값들을 추출합니다."""
        nutrition_values = {}
        
        for nutrient, field_names in self.nutrition_field_mapping.items():
            value = None
            
            # 다양한 필드명에서 값 추출 시도
            for field_name in field_names:
                if field_name in food_data and food_data[field_name]:
                    try:
                        value = self._safe_float_conversion(food_data[field_name])
                        break
                    except (ValueError, TypeError):
                        continue
            
            # 필수 영양소 검증
            if nutrient in ["calories", "carbohydrate", "protein", "fat"]:
                if value is None:
                    print(f"  ⚠️ 필수 영양소 '{nutrient}' 누락, 기본값 사용")
                    value = 0.0
                    self.processing_stats["missing_data_filled"] += 1
            
            nutrition_values[nutrient] = value
        
        return nutrition_values
    
    def _safe_float_conversion(self, value: Any) -> Optional[float]:
        """안전한 float 변환을 수행합니다."""
        if value is None or value == "":
            return None
        
        try:
            # 문자열에서 숫자가 아닌 문자 제거
            if isinstance(value, str):
                # 한국어 단위 제거 (예: "10.5g", "15kcal")
                cleaned = re.sub(r'[^\d.-]', '', value)
                if not cleaned:
                    return None
                value = cleaned
            
            result = float(value)
            
            # 음수 값 처리
            if result < 0:
                print(f"  ⚠️ 음수 값 발견: {result} → 0으로 변경")
                self.processing_stats["data_corrections"] += 1
                return 0.0
            
            return result
            
        except (ValueError, TypeError):
            return None
    
    def validate_nutrition_data(self, nutrition: NutritionInfo) -> bool:
        """
        영양정보 데이터의 품질을 검증합니다.
        
        Args:
            nutrition: 검증할 영양정보
            
        Returns:
            bool: 검증 통과 여부
            
        Raises:
            NutritionDataError: 심각한 데이터 오류 시
        """
        print(f"🔍 영양정보 검증: {nutrition.food_item.name}")
        
        validation_issues = []
        
        try:
            # 기본 범위 검증
            if nutrition.calories_per_100g > self.quality_thresholds["max_calories"]:
                validation_issues.append(f"칼로리가 너무 높음: {nutrition.calories_per_100g}kcal")
            
            if nutrition.carbohydrate > self.quality_thresholds["max_carbohydrate"]:
                validation_issues.append(f"탄수화물이 너무 높음: {nutrition.carbohydrate}g")
            
            if nutrition.protein > self.quality_thresholds["max_protein"]:
                validation_issues.append(f"단백질이 너무 높음: {nutrition.protein}g")
            
            if nutrition.fat > self.quality_thresholds["max_fat"]:
                validation_issues.append(f"지방이 너무 높음: {nutrition.fat}g")
            
            if nutrition.sodium and nutrition.sodium > self.quality_thresholds["max_sodium"]:
                validation_issues.append(f"나트륨이 너무 높음: {nutrition.sodium}mg")
            
            # 논리적 일관성 검증
            total_macros = nutrition.carbohydrate + nutrition.protein + nutrition.fat
            if total_macros > 120:  # 100g + 여유분
                validation_issues.append(f"주요 영양소 합계가 비현실적: {total_macros}g")
            
            # 칼로리 일관성 검증 (대략적)
            estimated_calories = (nutrition.carbohydrate * 4 + 
                                nutrition.protein * 4 + 
                                nutrition.fat * 9)
            
            if abs(nutrition.calories_per_100g - estimated_calories) > 100:
                validation_issues.append(
                    f"칼로리 불일치: 실제 {nutrition.calories_per_100g}kcal, "
                    f"추정 {estimated_calories:.1f}kcal"
                )
            
            # 검증 결과 처리
            if validation_issues:
                print(f"  ⚠️ 검증 이슈 {len(validation_issues)}개:")
                for issue in validation_issues:
                    print(f"    - {issue}")
                
                # 심각한 오류인지 판단
                serious_issues = [issue for issue in validation_issues 
                                if "너무 높음" in issue and "칼로리" in issue]
                
                if serious_issues:
                    raise NutritionDataError(f"심각한 데이터 오류: {'; '.join(serious_issues)}")
                
                return False
            
            print("  ✓ 영양정보 검증 통과")
            return True
            
        except Exception as e:
            if isinstance(e, NutritionDataError):
                raise
            raise NutritionDataError(f"영양정보 검증 중 오류: {str(e)}")
    
    def handle_missing_data(self, nutrition: NutritionInfo) -> NutritionInfo:
        """
        누락된 영양정보를 처리합니다.
        
        Args:
            nutrition: 원본 영양정보
            
        Returns:
            NutritionInfo: 누락 데이터가 처리된 영양정보
        """
        print(f"🔧 누락 데이터 처리: {nutrition.food_item.name}")
        
        corrections_made = []
        
        # 식이섬유 추정
        if nutrition.fiber is None:
            estimated_fiber = self._estimate_fiber(nutrition)
            if estimated_fiber > 0:
                nutrition.fiber = estimated_fiber
                corrections_made.append(f"식이섬유 추정: {estimated_fiber:.1f}g")
        
        # 나트륨 추정
        if nutrition.sodium is None:
            estimated_sodium = self._estimate_sodium(nutrition)
            if estimated_sodium > 0:
                nutrition.sodium = estimated_sodium
                corrections_made.append(f"나트륨 추정: {estimated_sodium:.1f}mg")
        
        # 칼로리 보정
        if nutrition.calories_per_100g == 0:
            estimated_calories = self._estimate_calories(nutrition)
            if estimated_calories > 0:
                nutrition.calories_per_100g = estimated_calories
                corrections_made.append(f"칼로리 추정: {estimated_calories:.1f}kcal")
        
        if corrections_made:
            print(f"  ✓ {len(corrections_made)}개 데이터 보정:")
            for correction in corrections_made:
                print(f"    - {correction}")
            self.processing_stats["missing_data_filled"] += len(corrections_made)
        
        return nutrition
    
    def _estimate_fiber(self, nutrition: NutritionInfo) -> float:
        """식이섬유를 추정합니다."""
        food_name = nutrition.food_item.name.lower()
        
        # 식이섬유가 많은 음식들
        high_fiber_foods = {
            "현미": 1.4, "보리": 8.0, "귀리": 10.0,
            "사과": 2.4, "배": 3.1, "바나나": 2.6,
            "브로콜리": 2.6, "당근": 2.8, "양배추": 2.5
        }
        
        for food, fiber_content in high_fiber_foods.items():
            if food in food_name:
                return fiber_content
        
        # 분류별 기본 추정값
        category = nutrition.food_item.category
        if category == "곡류":
            return 0.8
        elif category == "채소류":
            return 2.0
        elif category == "과일류":
            return 1.5
        
        return 0.0
    
    def _estimate_sodium(self, nutrition: NutritionInfo) -> float:
        """나트륨을 추정합니다."""
        food_name = nutrition.food_item.name.lower()
        
        # 나트륨이 많은 음식들
        high_sodium_foods = {
            "김치": 635, "된장": 4000, "간장": 6000,
            "라면": 1800, "햄": 1200, "치즈": 600
        }
        
        for food, sodium_content in high_sodium_foods.items():
            if food in food_name:
                return sodium_content
        
        # 분류별 기본 추정값
        category = nutrition.food_item.category
        if category in ["찌개류", "국류"]:
            return 400.0
        elif category == "조미료":
            return 2000.0
        elif category in ["과일류", "유제품"]:
            return 5.0
        
        return 50.0  # 기본값
    
    def _estimate_calories(self, nutrition: NutritionInfo) -> float:
        """칼로리를 추정합니다."""
        # 주요 영양소 기반 칼로리 계산
        estimated = (nutrition.carbohydrate * 4 + 
                    nutrition.protein * 4 + 
                    nutrition.fat * 9)
        
        if estimated > 0:
            return estimated
        
        # 음식 분류별 기본 칼로리
        category = nutrition.food_item.category
        default_calories = {
            "곡류": 130, "육류": 200, "어패류": 100,
            "채소류": 20, "과일류": 50, "유제품": 60,
            "견과류": 500, "조미료": 300
        }
        
        return default_calories.get(category, 100)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        데이터 처리 통계를 반환합니다.
        
        Returns:
            Dict[str, Any]: 처리 통계 정보
        """
        stats = self.processing_stats.copy()
        
        if stats["total_processed"] > 0:
            stats["success_rate"] = (stats["successful_processed"] / 
                                   stats["total_processed"]) * 100
        else:
            stats["success_rate"] = 0.0
        
        stats["timestamp"] = datetime.now().isoformat()
        
        return stats
    
    def reset_stats(self) -> None:
        """처리 통계를 초기화합니다."""
        for key in self.processing_stats:
            self.processing_stats[key] = 0
    
    def validate_api_response_structure(self, response_data: Dict[str, Any]) -> bool:
        """
        API 응답 구조를 검증합니다.
        
        Args:
            response_data: API 응답 데이터
            
        Returns:
            bool: 구조 검증 통과 여부
        """
        try:
            # 기본 구조 검증
            if not isinstance(response_data, dict):
                return False
            
            # 식약처 API 특정 구조 검증
            if "I2790" not in response_data:
                return False
            
            service_data = response_data["I2790"]
            if not isinstance(service_data, list) or not service_data:
                return False
            
            if "row" not in service_data[0]:
                return False
            
            rows = service_data[0]["row"]
            if not isinstance(rows, list):
                return False
            
            # 첫 번째 row의 필수 필드 확인
            if rows and isinstance(rows[0], dict):
                required_fields = ["DESC_KOR", "NUM"]
                for field in required_fields:
                    if field not in rows[0]:
                        return False
            
            return True
            
        except Exception:
            return False