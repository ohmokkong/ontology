"""
음식 데이터 프로세서 테스트 모듈.
"""

from food_data_processor import FoodDataProcessor
from integrated_models import FoodItem, NutritionInfo
from exceptions import DataProcessingError, NutritionDataError, JSONParsingError


def create_sample_api_response():
    """샘플 API 응답 데이터 생성."""
    return {
        "I2790": [{
            "head": [{"list_total_count": 3}],
            "row": [
                {
                    "DESC_KOR": "백미밥",
                    "NUM": "1001",
                    "GROUP_NAME": "곡류",
                    "MAKER_NAME": "일반",
                    "NUTR_CONT1": "130.0",  # 칼로리
                    "NUTR_CONT2": "28.1",   # 탄수화물
                    "NUTR_CONT3": "2.5",    # 단백질
                    "NUTR_CONT4": "0.3",    # 지방
                    "NUTR_CONT5": "0.3",    # 식이섬유
                    "NUTR_CONT6": "1.0"     # 나트륨
                },
                {
                    "DESC_KOR": "김치찌개",
                    "NUM": "2001",
                    "GROUP_NAME": "찌개류",
                    "MAKER_NAME": "일반",
                    "NUTR_CONT1": "45.0",
                    "NUTR_CONT2": "5.2",
                    "NUTR_CONT3": "3.1",
                    "NUTR_CONT4": "1.8",
                    "NUTR_CONT5": "",       # 누락된 데이터
                    "NUTR_CONT6": "635.0"
                },
                {
                    "DESC_KOR": "사과",
                    "NUM": "3001",
                    "GROUP_NAME": "과일류",
                    "MAKER_NAME": "",
                    "NUTR_CONT1": "52.0",
                    "NUTR_CONT2": "13.8",
                    "NUTR_CONT3": "0.3",
                    "NUTR_CONT4": "0.2",
                    "NUTR_CONT5": "2.4",
                    "NUTR_CONT6": "1.0"
                }
            ]
        }]
    }


def create_invalid_api_response():
    """잘못된 API 응답 데이터 생성."""
    return {
        "INVALID_KEY": [{
            "row": []
        }]
    }


def test_api_response_parsing():
    """API 응답 파싱 테스트."""
    print("=== API 응답 파싱 테스트 ===")
    
    try:
        processor = FoodDataProcessor()
        response_data = create_sample_api_response()
        
        # 정상 파싱 테스트
        food_items = processor.parse_api_response(response_data)
        
        assert len(food_items) == 3
        assert all(isinstance(item, FoodItem) for item in food_items)
        
        # 첫 번째 아이템 검증
        first_item = food_items[0]
        assert first_item.name == "백미밥"
        assert first_item.food_id == "1001"
        assert first_item.category == "곡류"
        assert first_item.manufacturer == "일반"
        
        print("✓ API 응답 파싱 성공")
        for item in food_items:
            print(f"  - {item.name} (ID: {item.food_id}, 분류: {item.category})")
        
        # 처리 통계 확인
        stats = processor.get_processing_stats()
        print(f"✓ 처리 통계: 성공률 {stats['success_rate']:.1f}%")
        
    except Exception as e:
        print(f"✗ API 응답 파싱 테스트 실패: {e}")


def test_invalid_api_response():
    """잘못된 API 응답 처리 테스트."""
    print("\n=== 잘못된 API 응답 처리 테스트 ===")
    
    processor = FoodDataProcessor()
    
    # 잘못된 구조 테스트
    try:
        invalid_response = create_invalid_api_response()
        food_items = processor.parse_api_response(invalid_response)
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
        empty_response = {"I2790": [{"row": []}]}
        processor.parse_api_response(empty_response)
        print("✗ 빈 응답에 대해 오류가 발생해야 함")
    except DataProcessingError as e:
        print(f"✓ 빈 응답 오류 정상 처리: {e}")


def test_nutrition_info_extraction():
    """영양정보 추출 테스트."""
    print("\n=== 영양정보 추출 테스트 ===")
    
    try:
        processor = FoodDataProcessor()
        
        # 샘플 음식 데이터 (백미밥)
        food_data = {
            "DESC_KOR": "백미밥",
            "NUM": "1001",
            "GROUP_NAME": "곡류",
            "NUTR_CONT1": "130.0",  # 칼로리
            "NUTR_CONT2": "28.1",   # 탄수화물
            "NUTR_CONT3": "2.5",    # 단백질
            "NUTR_CONT4": "0.3",    # 지방
            "NUTR_CONT5": "0.3",    # 식이섬유
            "NUTR_CONT6": "1.0"     # 나트륨
        }
        
        # 영양정보 추출
        nutrition = processor.extract_nutrition_info(food_data)
        
        assert isinstance(nutrition, NutritionInfo)
        assert nutrition.food_item.name == "백미밥"
        assert nutrition.calories_per_100g == 130.0
        assert nutrition.carbohydrate == 28.1
        assert nutrition.protein == 2.5
        assert nutrition.fat == 0.3
        assert nutrition.fiber == 0.3
        assert nutrition.sodium == 1.0
        
        print("✓ 영양정보 추출 성공")
        print(f"  - 칼로리: {nutrition.calories_per_100g}kcal/100g")
        print(f"  - 탄수화물: {nutrition.carbohydrate}g")
        print(f"  - 단백질: {nutrition.protein}g")
        print(f"  - 지방: {nutrition.fat}g")
        print(f"  - 식이섬유: {nutrition.fiber}g")
        print(f"  - 나트륨: {nutrition.sodium}mg")
        
    except Exception as e:
        print(f"✗ 영양정보 추출 테스트 실패: {e}")


def test_data_validation():
    """데이터 검증 테스트."""
    print("\n=== 데이터 검증 테스트 ===")
    
    try:
        processor = FoodDataProcessor()
        
        # 정상 데이터 검증
        food_item = FoodItem("백미밥", "1001", "곡류")
        normal_nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=130.0,
            carbohydrate=28.1,
            protein=2.5,
            fat=0.3,
            fiber=0.3,
            sodium=1.0
        )
        
        is_valid = processor.validate_nutrition_data(normal_nutrition)
        assert is_valid == True
        print("✓ 정상 데이터 검증 통과")
        
        # 비정상 데이터 검증 (칼로리가 너무 높음)
        abnormal_nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=1000.0,  # 너무 높은 칼로리
            carbohydrate=28.1,
            protein=2.5,
            fat=0.3
        )
        
        try:
            processor.validate_nutrition_data(abnormal_nutrition)
            print("✗ 비정상 데이터에 대해 오류가 발생해야 함")
        except NutritionDataError as e:
            print(f"✓ 비정상 데이터 검증 오류 정상 처리: {e}")
        
    except Exception as e:
        print(f"✗ 데이터 검증 테스트 실패: {e}")


def test_missing_data_handling():
    """누락 데이터 처리 테스트."""
    print("\n=== 누락 데이터 처리 테스트 ===")
    
    try:
        processor = FoodDataProcessor()
        
        # 누락 데이터가 있는 영양정보
        food_item = FoodItem("현미밥", "1002", "곡류")
        incomplete_nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=112.0,
            carbohydrate=22.9,
            protein=2.6,
            fat=0.9,
            fiber=None,  # 누락
            sodium=None  # 누락
        )
        
        # 누락 데이터 처리
        completed_nutrition = processor.handle_missing_data(incomplete_nutrition)
        
        assert completed_nutrition.fiber is not None
        assert completed_nutrition.sodium is not None
        
        print("✓ 누락 데이터 처리 성공")
        print(f"  - 추정된 식이섬유: {completed_nutrition.fiber}g")
        print(f"  - 추정된 나트륨: {completed_nutrition.sodium}mg")
        
        # 처리 통계 확인
        stats = processor.get_processing_stats()
        print(f"✓ 누락 데이터 보정: {stats['missing_data_filled']}개")
        
    except Exception as e:
        print(f"✗ 누락 데이터 처리 테스트 실패: {e}")


def test_korean_food_processing():
    """한국 음식 특화 처리 테스트."""
    print("\n=== 한국 음식 특화 처리 테스트 ===")
    
    try:
        processor = FoodDataProcessor()
        
        # 한국 음식 데이터
        korean_foods_data = [
            {
                "DESC_KOR": "김치찌개",
                "NUM": "K001",
                "GROUP_NAME": "",  # 분류 누락
                "NUTR_CONT1": "45.0",
                "NUTR_CONT2": "5.2",
                "NUTR_CONT3": "3.1",
                "NUTR_CONT4": "1.8",
                "NUTR_CONT6": "635.0"
            },
            {
                "DESC_KOR": "불고기",
                "NUM": "K002",
                "GROUP_NAME": "",
                "NUTR_CONT1": "156.0",
                "NUTR_CONT2": "2.1",
                "NUTR_CONT3": "18.7",
                "NUTR_CONT4": "7.9"
            },
            {
                "DESC_KOR": "비빔밥",
                "NUM": "K003",
                "GROUP_NAME": "",
                "NUTR_CONT1": "119.0",
                "NUTR_CONT2": "18.5",
                "NUTR_CONT3": "4.2",
                "NUTR_CONT4": "3.1"
            }
        ]
        
        print("📋 한국 음식 처리 테스트:")
        
        for food_data in korean_foods_data:
            try:
                # 영양정보 추출
                nutrition = processor.extract_nutrition_info(food_data)
                
                # 누락 데이터 처리
                nutrition = processor.handle_missing_data(nutrition)
                
                # 분류 추론 확인
                inferred_category = processor._infer_category_from_name(nutrition.food_item.name)
                
                print(f"✓ {nutrition.food_item.name}:")
                print(f"  - 추론된 분류: {inferred_category}")
                print(f"  - 칼로리: {nutrition.calories_per_100g}kcal/100g")
                print(f"  - 주요 영양소: 탄수화물 {nutrition.carbohydrate}g, "
                      f"단백질 {nutrition.protein}g, 지방 {nutrition.fat}g")
                
                if nutrition.sodium:
                    print(f"  - 나트륨: {nutrition.sodium}mg")
                
            except Exception as e:
                print(f"✗ {food_data['DESC_KOR']} 처리 실패: {e}")
        
    except Exception as e:
        print(f"✗ 한국 음식 특화 처리 테스트 실패: {e}")


def test_data_normalization():
    """데이터 정규화 테스트."""
    print("\n=== 데이터 정규화 테스트 ===")
    
    try:
        processor = FoodDataProcessor()
        
        # 정규화 테스트 케이스
        test_cases = [
            ("  백미밥  ", "백미밥"),                    # 공백 제거
            ("김치찌개(매운맛)", "김치찌개매운맛"),        # 특수문자 제거
            ("현미   밥", "현미 밥"),                    # 연속 공백 정리
            ("사과🍎", "사과"),                         # 이모지 제거
            ("닭가슴살 (100g)", "닭가슴살 100g")         # 괄호 제거
        ]
        
        print("📝 음식명 정규화 테스트:")
        for original, expected in test_cases:
            normalized = processor._normalize_food_name(original)
            assert normalized == expected, f"{original} -> {normalized} (예상: {expected})"
            print(f"  ✓ '{original}' → '{normalized}'")
        
        # 안전한 float 변환 테스트
        float_test_cases = [
            ("123.45", 123.45),
            ("123.45g", 123.45),      # 단위 포함
            ("10kcal", 10.0),         # 단위 포함
            ("", None),               # 빈 문자열
            ("abc", None),            # 잘못된 형식
            ("-5.0", 0.0),           # 음수 (0으로 변환)
            (None, None)              # None
        ]
        
        print("\n🔢 숫자 변환 테스트:")
        for original, expected in float_test_cases:
            result = processor._safe_float_conversion(original)
            if expected is None:
                assert result is None, f"{original} -> {result} (예상: None)"
            else:
                assert abs(result - expected) < 0.01, f"{original} -> {result} (예상: {expected})"
            print(f"  ✓ '{original}' → {result}")
        
    except Exception as e:
        print(f"✗ 데이터 정규화 테스트 실패: {e}")


def test_response_structure_validation():
    """API 응답 구조 검증 테스트."""
    print("\n=== API 응답 구조 검증 테스트 ===")
    
    try:
        processor = FoodDataProcessor()
        
        # 유효한 구조
        valid_response = create_sample_api_response()
        assert processor.validate_api_response_structure(valid_response) == True
        print("✓ 유효한 구조 검증 통과")
        
        # 무효한 구조들
        invalid_responses = [
            None,                                    # None
            "invalid",                              # 문자열
            {},                                     # 빈 딕셔너리
            {"WRONG_KEY": []},                      # 잘못된 키
            {"I2790": []},                          # 빈 리스트
            {"I2790": [{}]},                        # row 없음
            {"I2790": [{"row": "invalid"}]}         # row가 리스트가 아님
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
        processor = FoodDataProcessor()
        
        # 초기 통계 확인
        initial_stats = processor.get_processing_stats()
        assert initial_stats["total_processed"] == 0
        print("✓ 초기 통계 확인")
        
        # 데이터 처리 후 통계 확인
        response_data = create_sample_api_response()
        food_items = processor.parse_api_response(response_data)
        
        final_stats = processor.get_processing_stats()
        assert final_stats["total_processed"] == 3
        assert final_stats["successful_processed"] == 3
        assert final_stats["success_rate"] == 100.0
        
        print("✓ 처리 후 통계 확인")
        print(f"  - 총 처리: {final_stats['total_processed']}개")
        print(f"  - 성공: {final_stats['successful_processed']}개")
        print(f"  - 실패: {final_stats['failed_processed']}개")
        print(f"  - 성공률: {final_stats['success_rate']:.1f}%")
        
        # 통계 초기화 테스트
        processor.reset_stats()
        reset_stats = processor.get_processing_stats()
        assert reset_stats["total_processed"] == 0
        print("✓ 통계 초기화 확인")
        
    except Exception as e:
        print(f"✗ 처리 통계 테스트 실패: {e}")


if __name__ == "__main__":
    test_api_response_parsing()
    test_invalid_api_response()
    test_nutrition_info_extraction()
    test_data_validation()
    test_missing_data_handling()
    test_korean_food_processing()
    test_data_normalization()
    test_response_structure_validation()
    test_processing_statistics()
    print("\n✅ 모든 음식 데이터 프로세서 테스트 완료!")