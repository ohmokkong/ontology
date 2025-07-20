"""
운동 데이터 프로세서.

한국건강증진개발원 API에서 받은 운동 데이터를 파싱, 검증, 정규화하는 기능을 제공합니다.
MET 값 추출, 운동 분류, 한국 운동 특화 처리 등을 포함합니다.
"""

import re
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from integrated_models import ExerciseItem, ExerciseSession
from exceptions import (
    DataProcessingError, ExerciseDataError, JSONParsingError,
    DataValidationError, DataConversionError
)


class ExerciseDataProcessor:
    """
    운동 데이터 파싱 및 검증 프로세서.
    
    API 응답 파싱, MET 값 추출, 데이터 검증 및 정규화 기능을 제공합니다.
    """
    
    def __init__(self):
        """ExerciseDataProcessor 초기화."""
        # 한국 운동 분류 및 MET 값 데이터베이스
        self.korean_exercise_database = {
            # 유산소 운동
            "걷기": {"met": 3.5, "category": "유산소운동", "keywords": ["걷기", "보행", "산책"]},
            "빠른걷기": {"met": 4.3, "category": "유산소운동", "keywords": ["빠른걷기", "속보"]},
            "조깅": {"met": 7.0, "category": "유산소운동", "keywords": ["조깅", "가벼운달리기"]},
            "달리기": {"met": 8.0, "category": "유산소운동", "keywords": ["달리기", "러닝", "마라톤"]},
            "빠른달리기": {"met": 11.0, "category": "유산소운동", "keywords": ["빠른달리기", "스프린트"]},
            "자전거타기": {"met": 6.8, "category": "유산소운동", "keywords": ["자전거", "사이클링", "바이크"]},
            "수영": {"met": 8.0, "category": "유산소운동", "keywords": ["수영", "스위밍", "물놀이"]},
            "등산": {"met": 6.0, "category": "유산소운동", "keywords": ["등산", "하이킹", "트레킹"]},
            "계단오르기": {"met": 8.8, "category": "유산소운동", "keywords": ["계단", "스텝"]},
            "줄넘기": {"met": 12.3, "category": "유산소운동", "keywords": ["줄넘기", "로프점프"]},
            "에어로빅": {"met": 7.3, "category": "유산소운동", "keywords": ["에어로빅", "댄스"]},
            
            # 근력 운동
            "팔굽혀펴기": {"met": 8.0, "category": "근력운동", "keywords": ["팔굽혀펴기", "푸시업"]},
            "윗몸일으키기": {"met": 8.0, "category": "근력운동", "keywords": ["윗몸일으키기", "싯업", "복근"]},
            "스쿼트": {"met": 8.0, "category": "근력운동", "keywords": ["스쿼트", "하체운동"]},
            "헬스": {"met": 6.0, "category": "근력운동", "keywords": ["헬스", "웨이트", "근력"]},
            "웨이트트레이닝": {"met": 6.0, "category": "근력운동", "keywords": ["웨이트", "덤벨", "바벨"]},
            
            # 유연성 운동
            "요가": {"met": 2.5, "category": "유연성운동", "keywords": ["요가", "명상", "스트레칭"]},
            "필라테스": {"met": 3.0, "category": "유연성운동", "keywords": ["필라테스", "코어"]},
            
            # 스포츠
            "축구": {"met": 10.0, "category": "스포츠", "keywords": ["축구", "풋볼", "사커"]},
            "농구": {"met": 8.0, "category": "스포츠", "keywords": ["농구", "바스켓볼"]},
            "배드민턴": {"met": 7.0, "category": "스포츠", "keywords": ["배드민턴", "셔틀콕"]},
            "탁구": {"met": 4.0, "category": "스포츠", "keywords": ["탁구", "핑퐁"]},
            "테니스": {"met": 8.0, "category": "스포츠", "keywords": ["테니스", "라켓"]},
            "골프": {"met": 4.8, "category": "스포츠", "keywords": ["골프", "드라이버"]},
            "볼링": {"met": 3.0, "category": "스포츠", "keywords": ["볼링", "핀"]},
            
            # 전통 운동
            "태권도": {"met": 10.0, "category": "전통운동", "keywords": ["태권도", "무술", "격투기"]},
            
            # 기타
            "춤": {"met": 5.0, "category": "기타운동", "keywords": ["춤", "댄스", "무용"]}
        }
        
        # MET 값 범위 검증 기준
        self.met_validation_ranges = {
            "min_met": 1.0,      # 최소 MET 값
            "max_met": 20.0,     # 최대 MET 값
            "default_met": 5.0,  # 기본 MET 값
            "light_activity": (1.0, 3.0),      # 가벼운 활동
            "moderate_activity": (3.0, 6.0),   # 중간 강도
            "vigorous_activity": (6.0, 20.0)   # 격렬한 활동
        }
        
        # API 응답 필드 매핑
        self.api_field_mapping = {
            "exercise_name": ["EXERCISE_NM", "운동명", "name", "exercise"],
            "exercise_id": ["EXERCISE_ID", "ID", "운동코드", "code"],
            "met_value": ["MET", "MET_VALUE", "INTENSITY", "강도", "met"],
            "category": ["CATEGORY", "GROUP", "분류", "category"],
            "description": ["DESCRIPTION", "DESC", "설명", "description"],
            "duration": ["DURATION", "TIME", "시간", "duration"],
            "calories": ["CALORIES", "CAL", "칼로리", "calories"]
        }
        
        # 처리 통계
        self.processing_stats = {
            "total_processed": 0,
            "successful_processed": 0,
            "failed_processed": 0,
            "met_corrections": 0,
            "category_inferences": 0,
            "data_normalizations": 0
        }
    
    def parse_api_response(self, response_data: Dict[str, Any]) -> List[ExerciseItem]:
        """
        API 응답을 파싱하여 ExerciseItem 목록을 생성합니다.
        
        Args:
            response_data: 운동 API 응답 데이터
            
        Returns:
            List[ExerciseItem]: 파싱된 운동 아이템 목록
            
        Raises:
            JSONParsingError: JSON 파싱 오류 시
            DataProcessingError: 데이터 처리 오류 시
        """
        print("🏃 운동 API 응답 데이터 파싱 시작")
        
        try:
            # API 응답 구조 검증
            if not isinstance(response_data, dict):
                raise JSONParsingError("API 응답이 딕셔너리 형태가 아닙니다")
            
            # 운동 데이터 추출 (API 구조에 따라 조정)
            exercise_data_list = self._extract_exercise_data_list(response_data)
            
            if not exercise_data_list:
                raise DataProcessingError("파싱 가능한 운동 데이터가 없습니다")
            
            # 각 운동 데이터를 ExerciseItem으로 변환
            exercise_items = []
            self.processing_stats["total_processed"] = len(exercise_data_list)
            
            for i, exercise_data in enumerate(exercise_data_list):
                try:
                    exercise_item = self._parse_single_exercise_item(exercise_data, i + 1)
                    exercise_items.append(exercise_item)
                    self.processing_stats["successful_processed"] += 1
                    
                except Exception as e:
                    print(f"  ⚠️ 운동 항목 {i + 1} 파싱 실패: {str(e)}")
                    self.processing_stats["failed_processed"] += 1
                    continue
            
            if not exercise_items:
                raise DataProcessingError("파싱 가능한 운동 아이템이 없습니다")
            
            print(f"✓ {len(exercise_items)}개 운동 아이템 파싱 완료")
            return exercise_items
            
        except Exception as e:
            if isinstance(e, (JSONParsingError, DataProcessingError)):
                raise
            raise DataProcessingError(f"운동 API 응답 파싱 중 오류: {str(e)}")
    
    def _extract_exercise_data_list(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답에서 운동 데이터 리스트를 추출합니다."""
        # 다양한 API 응답 구조 지원
        possible_keys = ["exercises", "data", "items", "results", "response"]
        
        for key in possible_keys:
            if key in response_data and isinstance(response_data[key], list):
                return response_data[key]
        
        # 직접 리스트인 경우
        if isinstance(response_data, list):
            return response_data
        
        # 단일 객체인 경우 리스트로 변환
        if "exercise_name" in response_data or "EXERCISE_NM" in response_data:
            return [response_data]
        
        return []
    
    def _parse_single_exercise_item(self, exercise_data: Dict[str, Any], index: int) -> ExerciseItem:
        """
        단일 운동 데이터를 파싱하여 ExerciseItem을 생성합니다.
        
        Args:
            exercise_data: 개별 운동 데이터
            index: 데이터 인덱스
            
        Returns:
            ExerciseItem: 생성된 운동 아이템
        """
        try:
            # 필수 필드 추출
            name = self._extract_exercise_name(exercise_data)
            description = self._extract_description(exercise_data, name)
            met_value = self._extract_met_value(exercise_data, name)
            
            # 선택적 필드 추출
            category = self._extract_category(exercise_data, name)
            exercise_id = self._extract_exercise_id(exercise_data, name)
            
            # ExerciseItem 생성 및 검증
            exercise_item = ExerciseItem(
                name=name,
                description=description,
                met_value=met_value,
                category=category,
                exercise_id=exercise_id
            )
            
            return exercise_item
            
        except Exception as e:
            raise DataProcessingError(f"운동 항목 {index} 파싱 실패: {str(e)}")
    
    def _extract_exercise_name(self, exercise_data: Dict[str, Any]) -> str:
        """운동명을 추출하고 정규화합니다."""
        name_fields = self.api_field_mapping["exercise_name"]
        
        for field in name_fields:
            if field in exercise_data and exercise_data[field]:
                name = str(exercise_data[field]).strip()
                if name:
                    return self._normalize_exercise_name(name)
        
        raise DataValidationError("운동명을 찾을 수 없습니다")
    
    def _extract_description(self, exercise_data: Dict[str, Any], exercise_name: str) -> str:
        """운동 설명을 추출하거나 생성합니다."""
        desc_fields = self.api_field_mapping["description"]
        
        # API에서 제공하는 설명 확인
        for field in desc_fields:
            if field in exercise_data and exercise_data[field]:
                description = str(exercise_data[field]).strip()
                if description and description != exercise_name:
                    return description
        
        # 설명이 없는 경우 기본 설명 생성
        return self._generate_default_description(exercise_name)
    
    def _extract_met_value(self, exercise_data: Dict[str, Any], exercise_name: str) -> float:
        """MET 값을 추출하거나 추정합니다."""
        met_fields = self.api_field_mapping["met_value"]
        
        # API에서 제공하는 MET 값 확인
        for field in met_fields:
            if field in exercise_data and exercise_data[field]:
                try:
                    met_value = self._safe_float_conversion(exercise_data[field])
                    if met_value and self._validate_met_value(met_value):
                        return met_value
                except (ValueError, TypeError):
                    continue
        
        # MET 값이 없는 경우 추정
        estimated_met = self._estimate_met_value(exercise_name)
        if estimated_met:
            print(f"  ℹ️ MET 값 추정: {exercise_name} → {estimated_met}")
            self.processing_stats["met_corrections"] += 1
            return estimated_met
        
        # 기본값 사용
        print(f"  ⚠️ MET 값 기본값 사용: {exercise_name} → {self.met_validation_ranges['default_met']}")
        return self.met_validation_ranges["default_met"]
    
    def _extract_category(self, exercise_data: Dict[str, Any], exercise_name: str) -> Optional[str]:
        """운동 분류를 추출하거나 추론합니다."""
        category_fields = self.api_field_mapping["category"]
        
        # API에서 제공하는 분류 확인
        for field in category_fields:
            if field in exercise_data and exercise_data[field]:
                category = str(exercise_data[field]).strip()
                if category and category not in ["기타", "일반", "없음"]:
                    return category
        
        # 운동명을 기반으로 분류 추론
        inferred_category = self._infer_category_from_name(exercise_name)
        if inferred_category:
            print(f"  ℹ️ 분류 추론: {exercise_name} → {inferred_category}")
            self.processing_stats["category_inferences"] += 1
        
        return inferred_category
    
    def _extract_exercise_id(self, exercise_data: Dict[str, Any], exercise_name: str) -> Optional[str]:
        """운동 ID를 추출하거나 생성합니다."""
        id_fields = self.api_field_mapping["exercise_id"]
        
        # API에서 제공하는 ID 확인
        for field in id_fields:
            if field in exercise_data and exercise_data[field]:
                exercise_id = str(exercise_data[field]).strip()
                if exercise_id:
                    return exercise_id
        
        # ID가 없는 경우 운동명 기반으로 생성
        return f"EX_{hash(exercise_name) % 10000:04d}"
    
    def _normalize_exercise_name(self, name: str) -> str:
        """운동명을 정규화합니다."""
        # 불필요한 문자 제거
        name = re.sub(r'[^\w\s가-힣]', '', name)
        
        # 연속된 공백을 하나로 변경
        name = re.sub(r'\s+', ' ', name)
        
        # 앞뒤 공백 제거
        name = name.strip()
        
        if not name:
            raise DataValidationError("정규화 후 운동명이 비어있습니다")
        
        self.processing_stats["data_normalizations"] += 1
        return name
    
    def _generate_default_description(self, exercise_name: str) -> str:
        """기본 운동 설명을 생성합니다."""
        # 데이터베이스에서 운동 정보 확인
        for exercise, info in self.korean_exercise_database.items():
            if exercise == exercise_name or exercise_name in info["keywords"]:
                intensity = self._get_intensity_description(info["met"])
                return f"{exercise_name} - {info['category']} ({intensity})"
        
        # 기본 설명
        return f"{exercise_name} 운동"
    
    def _get_intensity_description(self, met_value: float) -> str:
        """MET 값을 기반으로 강도 설명을 생성합니다."""
        ranges = self.met_validation_ranges
        
        if ranges["light_activity"][0] <= met_value < ranges["light_activity"][1]:
            return "가벼운 강도"
        elif ranges["moderate_activity"][0] <= met_value < ranges["moderate_activity"][1]:
            return "중간 강도"
        elif ranges["vigorous_activity"][0] <= met_value <= ranges["vigorous_activity"][1]:
            return "격렬한 강도"
        else:
            return "일반 강도"
    
    def _estimate_met_value(self, exercise_name: str) -> Optional[float]:
        """운동명을 기반으로 MET 값을 추정합니다."""
        # 정확한 매칭
        if exercise_name in self.korean_exercise_database:
            return self.korean_exercise_database[exercise_name]["met"]
        
        # 키워드 매칭
        for exercise, info in self.korean_exercise_database.items():
            for keyword in info["keywords"]:
                if keyword in exercise_name or exercise_name in keyword:
                    return info["met"]
        
        # 부분 매칭
        for exercise, info in self.korean_exercise_database.items():
            if exercise in exercise_name or exercise_name in exercise:
                return info["met"]
        
        return None
    
    def _infer_category_from_name(self, exercise_name: str) -> Optional[str]:
        """운동명을 기반으로 분류를 추론합니다."""
        # 정확한 매칭
        if exercise_name in self.korean_exercise_database:
            return self.korean_exercise_database[exercise_name]["category"]
        
        # 키워드 매칭
        for exercise, info in self.korean_exercise_database.items():
            for keyword in info["keywords"]:
                if keyword in exercise_name or exercise_name in keyword:
                    return info["category"]
        
        # 부분 매칭
        for exercise, info in self.korean_exercise_database.items():
            if exercise in exercise_name or exercise_name in exercise:
                return info["category"]
        
        return None
    
    def _validate_met_value(self, met_value: float) -> bool:
        """MET 값의 유효성을 검증합니다."""
        ranges = self.met_validation_ranges
        return ranges["min_met"] <= met_value <= ranges["max_met"]
    
    def _safe_float_conversion(self, value: Any) -> Optional[float]:
        """안전한 float 변환을 수행합니다."""
        if value is None or value == "":
            return None
        
        try:
            # 문자열에서 숫자가 아닌 문자 제거
            if isinstance(value, str):
                cleaned = re.sub(r'[^\d.-]', '', value)
                if not cleaned:
                    return None
                value = cleaned
            
            result = float(value)
            
            # 음수 값 처리
            if result < 0:
                print(f"  ⚠️ 음수 MET 값 발견: {result} → 절댓값 사용")
                return abs(result)
            
            return result
            
        except (ValueError, TypeError):
            return None
    
    def validate_exercise_data(self, exercise: ExerciseItem) -> bool:
        """
        운동 데이터의 품질을 검증합니다.
        
        Args:
            exercise: 검증할 운동 아이템
            
        Returns:
            bool: 검증 통과 여부
            
        Raises:
            ExerciseDataError: 심각한 데이터 오류 시
        """
        print(f"🔍 운동 데이터 검증: {exercise.name}")
        
        validation_issues = []
        
        try:
            # MET 값 범위 검증
            if not self._validate_met_value(exercise.met_value):
                validation_issues.append(
                    f"MET 값이 범위를 벗어남: {exercise.met_value} "
                    f"(유효 범위: {self.met_validation_ranges['min_met']}-{self.met_validation_ranges['max_met']})"
                )
            
            # 운동명 길이 검증
            if len(exercise.name) > 50:
                validation_issues.append(f"운동명이 너무 김: {len(exercise.name)}자")
            
            # 설명 길이 검증
            if len(exercise.description) > 200:
                validation_issues.append(f"설명이 너무 김: {len(exercise.description)}자")
            
            # 분류 일관성 검증
            if exercise.category:
                expected_category = self._infer_category_from_name(exercise.name)
                if expected_category and expected_category != exercise.category:
                    validation_issues.append(
                        f"분류 불일치: 실제 '{exercise.category}', 예상 '{expected_category}'"
                    )
            
            # 검증 결과 처리
            if validation_issues:
                print(f"  ⚠️ 검증 이슈 {len(validation_issues)}개:")
                for issue in validation_issues:
                    print(f"    - {issue}")
                
                # 심각한 오류인지 판단
                serious_issues = [issue for issue in validation_issues 
                                if "범위를 벗어남" in issue]
                
                if serious_issues:
                    raise ExerciseDataError(f"심각한 데이터 오류: {'; '.join(serious_issues)}")
                
                return False
            
            print("  ✓ 운동 데이터 검증 통과")
            return True
            
        except Exception as e:
            if isinstance(e, ExerciseDataError):
                raise
            raise ExerciseDataError(f"운동 데이터 검증 중 오류: {str(e)}")
    
    def handle_missing_data(self, exercise: ExerciseItem) -> ExerciseItem:
        """
        누락된 운동 데이터를 처리합니다.
        
        Args:
            exercise: 원본 운동 아이템
            
        Returns:
            ExerciseItem: 누락 데이터가 처리된 운동 아이템
        """
        print(f"🔧 누락 데이터 처리: {exercise.name}")
        
        corrections_made = []
        
        # 분류 보완
        if not exercise.category:
            inferred_category = self._infer_category_from_name(exercise.name)
            if inferred_category:
                exercise.category = inferred_category
                corrections_made.append(f"분류 추론: {inferred_category}")
        
        # 설명 보완
        if not exercise.description or exercise.description == f"{exercise.name} 운동":
            enhanced_description = self._generate_default_description(exercise.name)
            if enhanced_description != exercise.description:
                exercise.description = enhanced_description
                corrections_made.append(f"설명 보완: {enhanced_description[:30]}...")
        
        # MET 값 보정
        if exercise.met_value == self.met_validation_ranges["default_met"]:
            estimated_met = self._estimate_met_value(exercise.name)
            if estimated_met and estimated_met != exercise.met_value:
                exercise.met_value = estimated_met
                corrections_made.append(f"MET 값 보정: {estimated_met}")
        
        # 운동 ID 보완
        if not exercise.exercise_id:
            exercise.exercise_id = f"EX_{hash(exercise.name) % 10000:04d}"
            corrections_made.append(f"ID 생성: {exercise.exercise_id}")
        
        if corrections_made:
            print(f"  ✓ {len(corrections_made)}개 데이터 보정:")
            for correction in corrections_made:
                print(f"    - {correction}")
        
        return exercise
    
    def get_supported_exercises(self) -> Dict[str, Dict[str, Any]]:
        """
        지원되는 운동 목록을 반환합니다.
        
        Returns:
            Dict[str, Dict[str, Any]]: 운동명과 정보의 매핑
        """
        return self.korean_exercise_database.copy()
    
    def get_exercises_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        특정 분류의 운동 목록을 반환합니다.
        
        Args:
            category: 운동 분류
            
        Returns:
            List[Dict[str, Any]]: 해당 분류의 운동 목록
        """
        exercises = []
        for name, info in self.korean_exercise_database.items():
            if info["category"] == category:
                exercises.append({
                    "name": name,
                    "met": info["met"],
                    "category": info["category"],
                    "keywords": info["keywords"]
                })
        
        return exercises
    
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
        stats["supported_exercises"] = len(self.korean_exercise_database)
        
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
            
            # 운동 데이터 리스트 추출 시도
            exercise_data_list = self._extract_exercise_data_list(response_data)
            
            if not exercise_data_list:
                return False
            
            # 첫 번째 운동 데이터의 필수 필드 확인
            if exercise_data_list and isinstance(exercise_data_list[0], dict):
                first_exercise = exercise_data_list[0]
                
                # 운동명 필드 중 하나라도 있으면 유효
                name_fields = self.api_field_mapping["exercise_name"]
                has_name_field = any(field in first_exercise for field in name_fields)
                
                if not has_name_field:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def create_exercise_session(self, exercise: ExerciseItem, weight: float, 
                              duration: float, namespace) -> ExerciseSession:
        """
        운동 세션을 생성합니다.
        
        Args:
            exercise: 운동 아이템
            weight: 사용자 체중 (kg)
            duration: 운동 시간 (분)
            namespace: RDF 네임스페이스
            
        Returns:
            ExerciseSession: 생성된 운동 세션
        """
        return ExerciseSession.create_with_calculation(
            exercise_item=exercise,
            weight=weight,
            duration=duration,
            namespace=namespace
        )