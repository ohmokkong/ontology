"""
운동 데이터 프로세서 테스트 모듈.
"""

from exercise_data_processor import ExerciseDataProcessor
from integrated_models import ExerciseItem, ExerciseSession
from exceptions import DataProcessingError, ExerciseDataError, JSONParsingError
from rdflib import Namespace


def create_sample_exercise_api_response():
    """샘플 운동 API 응답 데이터 생성."""
    return {
        "exercises": [
            {
                "EXERCISE_NM": "달리기",
                "EXERCISE_ID": "EX001",
                "MET": "8.0",
                "CATEGORY": "유산소운동",
                "DESCRIPTION": "일반적인 달리기 운동"
            },
            {
                "EXERCISE_NM": "팔굽혀펴기",
                "EXERCISE_ID": "EX002",
                "MET": "8.0",
                "CATEGORY": "근력운동",
                "DESCRIPTION": "상체 근력 강화 운동"
            },
            {
                "EXERCISE_NM": "요가",
                "EXERCISE_ID": "EX003",
                "MET": "2.5",
                "CATEGORY": "",  # 누락된 분류
                "DESCRIPTION": ""  # 누락된 설명
            }
        ]
    }


def create_invalid_exercise_api_response():
    """잘못된 운동 API 응답 데이터 생성."""
    return {
        "invalid_key": []
    }


def test_api_response_parsing():
    """API 응답 파싱 테스트."""
    print("=== 운동 API 응답 파싱 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        response_data = create_sample_exercise_api_response()
        
        # 정상 파싱 테스트
        exercise_items = processor.parse_api_response(response_data)
        
        assert len(exercise_items) == 3
        assert all(isinstance(item, ExerciseItem) for item in exercise_items)
        
        # 첫 번째 아이템 검증
        first_item = exercise_items[0]
        assert first_item.name == "달리기"
        assert first_item.exercise_id == "EX001"
        assert first_item.met_value == 8.0
        assert first_item.category == "유산소운동"
        
        print("✓ 운동 API 응답 파싱 성공")
        for item in exercise_items:
            print(f"  - {item.name} (MET: {item.met_value}, 분류: {item.category})")
        
        # 처리 통계 확인
        stats = processor.get_processing_stats()
        print(f"✓ 처리 통계: 성공률 {stats['success_rate']:.1f}%")
        
    except Exception as e:
        print(f"✗ 운동 API 응답 파싱 테스트 실패: {e}")


def test_invalid_api_response():
    """잘못된 API 응답 처리 테스트."""
    print("\n=== 잘못된 운동 API 응답 처리 테스트 ===")
    
    processor = ExerciseDataProcessor()
    
    # 잘못된 구조 테스트
    try:
        invalid_response = create_invalid_exercise_api_response()
        exercise_items = processor.parse_api_response(invalid_response)
        print("✗ 잘못된 응답에 대해 오류가 발생해야 함")
    except DataProcessingError as e:
        print(f"✓ 잘못된 응답 오류 정상 처리: {e}")
    
    # None 응답 테스트
    try:
        processor.parse_api_response(None)
        print("✗ None 응답에 대해 오류가 발생해야 함")
    except JSONParsingError as e:
        print(f"✓ None 응답 오류 정상 처리: {e}")
    
    # 빈 응답 테스트
    try:
        empty_response = {"exercises": []}
        processor.parse_api_response(empty_response)
        print("✗ 빈 응답에 대해 오류가 발생해야 함")
    except DataProcessingError as e:
        print(f"✓ 빈 응답 오류 정상 처리: {e}")


def test_met_value_extraction():
    """MET 값 추출 및 추정 테스트."""
    print("\n=== MET 값 추출 및 추정 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # API에서 MET 값 제공하는 경우
        exercise_data_with_met = {
            "EXERCISE_NM": "수영",
            "MET": "8.0",
            "CATEGORY": "유산소운동"
        }
        
        exercise_item = processor._parse_single_exercise_item(exercise_data_with_met, 1)
        assert exercise_item.met_value == 8.0
        print("✓ API 제공 MET 값 추출 성공: 수영 = 8.0 MET")
        
        # MET 값이 없어서 추정하는 경우
        exercise_data_without_met = {
            "EXERCISE_NM": "태권도",
            "CATEGORY": "전통운동"
        }
        
        exercise_item = processor._parse_single_exercise_item(exercise_data_without_met, 2)
        assert exercise_item.met_value == 10.0  # 데이터베이스에서 추정
        print("✓ MET 값 추정 성공: 태권도 = 10.0 MET")
        
        # 알 수 없는 운동의 경우 기본값 사용
        exercise_data_unknown = {
            "EXERCISE_NM": "알수없는운동",
            "CATEGORY": "기타"
        }
        
        exercise_item = processor._parse_single_exercise_item(exercise_data_unknown, 3)
        assert exercise_item.met_value == 5.0  # 기본값
        print("✓ 기본 MET 값 사용: 알수없는운동 = 5.0 MET")
        
    except Exception as e:
        print(f"✗ MET 값 추출 테스트 실패: {e}")


def test_exercise_data_validation():
    """운동 데이터 검증 테스트."""
    print("\n=== 운동 데이터 검증 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 정상 데이터 검증
        normal_exercise = ExerciseItem(
            name="달리기",
            description="일반적인 달리기 운동",
            met_value=8.0,
            category="유산소운동",
            exercise_id="EX001"
        )
        
        is_valid = processor.validate_exercise_data(normal_exercise)
        assert is_valid == True
        print("✓ 정상 운동 데이터 검증 통과")
        
        # 비정상 데이터 검증 (MET 값이 범위를 벗어남)
        abnormal_exercise = ExerciseItem(
            name="초고강도운동",
            description="비현실적으로 강한 운동",
            met_value=25.0,  # 범위 초과
            category="기타운동"
        )
        
        try:
            processor.validate_exercise_data(abnormal_exercise)
            print("✗ 비정상 데이터에 대해 오류가 발생해야 함")
        except ExerciseDataError as e:
            print(f"✓ 비정상 데이터 검증 오류 정상 처리: {e}")
        
    except Exception as e:
        print(f"✗ 운동 데이터 검증 테스트 실패: {e}")


def test_missing_data_handling():
    """누락 데이터 처리 테스트."""
    print("\n=== 누락 데이터 처리 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 누락 데이터가 있는 운동 아이템
        incomplete_exercise = ExerciseItem(
            name="축구",
            description="축구 운동",  # 기본 설명
            met_value=5.0,  # 기본값
            category=None,  # 누락
            exercise_id=None  # 누락
        )
        
        # 누락 데이터 처리
        completed_exercise = processor.handle_missing_data(incomplete_exercise)
        
        assert completed_exercise.category is not None
        assert completed_exercise.exercise_id is not None
        assert completed_exercise.met_value == 10.0  # 축구의 실제 MET 값
        
        print("✓ 누락 데이터 처리 성공")
        print(f"  - 추론된 분류: {completed_exercise.category}")
        print(f"  - 생성된 ID: {completed_exercise.exercise_id}")
        print(f"  - 보정된 MET: {completed_exercise.met_value}")
        
    except Exception as e:
        print(f"✗ 누락 데이터 처리 테스트 실패: {e}")


def test_korean_exercise_processing():
    """한국 운동 특화 처리 테스트."""
    print("\n=== 한국 운동 특화 처리 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 한국 운동 데이터
        korean_exercises_data = [
            {"EXERCISE_NM": "태권도", "CATEGORY": ""},
            {"EXERCISE_NM": "등산", "MET": ""},
            {"EXERCISE_NM": "걷기", "DESCRIPTION": ""},
            {"EXERCISE_NM": "줄넘기", "CATEGORY": "", "MET": ""}
        ]
        
        print("📋 한국 운동 처리 테스트:")
        
        for exercise_data in korean_exercises_data:
            try:
                # 운동 아이템 파싱
                exercise_item = processor._parse_single_exercise_item(exercise_data, 1)
                
                # 누락 데이터 처리
                exercise_item = processor.handle_missing_data(exercise_item)
                
                print(f"✓ {exercise_item.name}:")
                print(f"  - MET 값: {exercise_item.met_value}")
                print(f"  - 분류: {exercise_item.category}")
                print(f"  - 설명: {exercise_item.description[:50]}...")
                
            except Exception as e:
                print(f"✗ {exercise_data['EXERCISE_NM']} 처리 실패: {e}")
        
    except Exception as e:
        print(f"✗ 한국 운동 특화 처리 테스트 실패: {e}")


def test_exercise_name_normalization():
    """운동명 정규화 테스트."""
    print("\n=== 운동명 정규화 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 정규화 테스트 케이스
        test_cases = [
            ("  달리기  ", "달리기"),                    # 공백 제거
            ("팔굽혀펴기(푸시업)", "팔굽혀펴기푸시업"),    # 특수문자 제거
            ("요가   수업", "요가 수업"),                # 연속 공백 정리
            ("수영🏊‍♂️", "수영"),                        # 이모지 제거
            ("헬스 (웨이트)", "헬스 웨이트")             # 괄호 제거
        ]
        
        print("📝 운동명 정규화 테스트:")
        for original, expected in test_cases:
            normalized = processor._normalize_exercise_name(original)
            assert normalized == expected, f"{original} -> {normalized} (예상: {expected})"
            print(f"  ✓ '{original}' → '{normalized}'")
        
    except Exception as e:
        print(f"✗ 운동명 정규화 테스트 실패: {e}")


def test_exercise_categories():
    """운동 분류 테스트."""
    print("\n=== 운동 분류 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 지원되는 운동 목록 확인
        supported_exercises = processor.get_supported_exercises()
        print(f"✓ 지원되는 운동 총 {len(supported_exercises)}개")
        
        # 분류별 운동 목록 확인
        categories = ["유산소운동", "근력운동", "유연성운동", "스포츠", "전통운동"]
        
        for category in categories:
            exercises = processor.get_exercises_by_category(category)
            print(f"✓ {category}: {len(exercises)}개")
            for exercise in exercises[:3]:  # 최대 3개만 표시
                print(f"  - {exercise['name']} (MET: {exercise['met']})")
        
    except Exception as e:
        print(f"✗ 운동 분류 테스트 실패: {e}")


def test_exercise_session_creation():
    """운동 세션 생성 테스트."""
    print("\n=== 운동 세션 생성 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        namespace = Namespace("http://example.org/exercise#")
        
        # 운동 아이템 생성
        exercise = ExerciseItem(
            name="달리기",
            description="일반적인 달리기 운동",
            met_value=8.0,
            category="유산소운동",
            exercise_id="EX001"
        )
        
        # 운동 세션 생성
        session = processor.create_exercise_session(
            exercise=exercise,
            weight=70.0,  # 70kg
            duration=30.0,  # 30분
            namespace=namespace
        )
        
        assert isinstance(session, ExerciseSession)
        assert session.weight == 70.0
        assert session.duration == 30.0
        assert session.calories_burned == 280.0  # 8.0 * 70.0 * 0.5
        
        print("✓ 운동 세션 생성 성공")
        print(f"  - 운동: {exercise.name}")
        print(f"  - 체중: {session.weight}kg")
        print(f"  - 시간: {session.duration}분")
        print(f"  - 소모 칼로리: {session.calories_burned}kcal")
        
    except Exception as e:
        print(f"✗ 운동 세션 생성 테스트 실패: {e}")


def test_response_structure_validation():
    """API 응답 구조 검증 테스트."""
    print("\n=== API 응답 구조 검증 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 유효한 구조
        valid_response = create_sample_exercise_api_response()
        assert processor.validate_api_response_structure(valid_response) == True
        print("✓ 유효한 구조 검증 통과")
        
        # 무효한 구조들
        invalid_responses = [
            None,                                    # None
            "invalid",                              # 문자열
            {},                                     # 빈 딕셔너리
            {"wrong_key": []},                      # 잘못된 키
            {"exercises": []},                      # 빈 리스트
            {"exercises": [{}]},                    # 운동명 없음
            {"exercises": [{"invalid_field": "test"}]}  # 필수 필드 없음
        ]
        
        for i, invalid_response in enumerate(invalid_responses, 1):
            result = processor.validate_api_response_structure(invalid_response)
            assert result == False, f"무효한 응답 {i}이 유효하다고 판단됨"
            print(f"  ✓ 무효한 구조 {i} 정상 감지")
        
    except Exception as e:
        print(f"✗ API 응답 구조 검증 테스트 실패: {e}")


def test_processing_statistics():
    """처리 통계 테스트."""
    print("\n=== 처리 통계 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 초기 통계 확인
        initial_stats = processor.get_processing_stats()
        assert initial_stats["total_processed"] == 0
        print("✓ 초기 통계 확인")
        
        # 데이터 처리 후 통계 확인
        response_data = create_sample_exercise_api_response()
        exercise_items = processor.parse_api_response(response_data)
        
        final_stats = processor.get_processing_stats()
        assert final_stats["total_processed"] == 3
        assert final_stats["successful_processed"] == 3
        assert final_stats["success_rate"] == 100.0
        
        print("✓ 처리 후 통계 확인")
        print(f"  - 총 처리: {final_stats['total_processed']}개")
        print(f"  - 성공: {final_stats['successful_processed']}개")
        print(f"  - 실패: {final_stats['failed_processed']}개")
        print(f"  - 성공률: {final_stats['success_rate']:.1f}%")
        print(f"  - MET 보정: {final_stats['met_corrections']}개")
        print(f"  - 분류 추론: {final_stats['category_inferences']}개")
        
        # 통계 초기화 테스트
        processor.reset_stats()
        reset_stats = processor.get_processing_stats()
        assert reset_stats["total_processed"] == 0
        print("✓ 통계 초기화 확인")
        
    except Exception as e:
        print(f"✗ 처리 통계 테스트 실패: {e}")


def test_intensity_description():
    """운동 강도 설명 테스트."""
    print("\n=== 운동 강도 설명 테스트 ===")
    
    try:
        processor = ExerciseDataProcessor()
        
        # 강도별 테스트
        intensity_tests = [
            (2.0, "가벼운 강도"),    # 요가
            (4.0, "중간 강도"),      # 탁구
            (8.0, "격렬한 강도"),    # 달리기
            (12.0, "격렬한 강도")    # 줄넘기
        ]
        
        print("💪 운동 강도 분류 테스트:")
        for met_value, expected_intensity in intensity_tests:
            intensity = processor._get_intensity_description(met_value)
            assert intensity == expected_intensity
            print(f"  ✓ MET {met_value} → {intensity}")
        
    except Exception as e:
        print(f"✗ 운동 강도 설명 테스트 실패: {e}")


if __name__ == "__main__":
    test_api_response_parsing()
    test_invalid_api_response()
    test_met_value_extraction()
    test_exercise_data_validation()
    test_missing_data_handling()
    test_korean_exercise_processing()
    test_exercise_name_normalization()
    test_exercise_categories()
    test_exercise_session_creation()
    test_response_structure_validation()
    test_processing_statistics()
    test_intensity_description()
    print("\n✅ 모든 운동 데이터 프로세서 테스트 완료!")