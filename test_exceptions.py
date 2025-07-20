"""
예외 처리 시스템 테스트 모듈.
"""

from exceptions import (
    IntegratedAPIError, ConfigurationError, APIKeyError,
    APIConnectionError, NetworkError, InvalidAPIKeyError,
    APIResponseError, FoodAPIError, ExerciseAPIError,
    DataValidationError, NutritionDataError, CalorieCalculationError,
    OntologyError, TTLSyntaxError, FileSystemError,
    ErrorHandler
)


def test_basic_exception_hierarchy():
    """기본 예외 계층 구조 테스트."""
    print("=== 기본 예외 계층 구조 테스트 ===")
    
    try:
        # 기본 예외 클래스 테스트
        error = IntegratedAPIError("기본 오류", "상세 정보")
        print(f"✓ 기본 예외: {error}")
        
        # 상속 관계 확인
        config_error = ConfigurationError("설정 오류")
        assert isinstance(config_error, IntegratedAPIError)
        print("✓ 설정 오류는 기본 예외를 상속함")
        
        api_key_error = APIKeyError("API 키 오류")
        assert isinstance(api_key_error, ConfigurationError)
        assert isinstance(api_key_error, IntegratedAPIError)
        print("✓ API 키 오류는 설정 오류와 기본 예외를 상속함")
        
    except Exception as e:
        print(f"✗ 기본 예외 테스트 실패: {e}")


def test_api_related_exceptions():
    """API 관련 예외 테스트."""
    print("\n=== API 관련 예외 테스트 ===")
    
    try:
        # API 응답 오류 (HTTP 상태 코드 포함)
        response_error = APIResponseError(
            "API 응답 오류", 
            status_code=404, 
            response_data='{"error": "Not Found"}'
        )
        print(f"✓ API 응답 오류: {response_error}")
        assert "HTTP 404" in str(response_error)
        
        # 식약처 API 오류
        food_error = FoodAPIError("음식 검색 실패", status_code=400)
        assert isinstance(food_error, APIResponseError)
        print("✓ 식약처 API 오류 생성 성공")
        
        # 운동 API 오류
        exercise_error = ExerciseAPIError("운동 검색 실패", status_code=500)
        assert isinstance(exercise_error, APIResponseError)
        print("✓ 운동 API 오류 생성 성공")
        
    except Exception as e:
        print(f"✗ API 관련 예외 테스트 실패: {e}")


def test_data_validation_exceptions():
    """데이터 검증 예외 테스트."""
    print("\n=== 데이터 검증 예외 테스트 ===")
    
    try:
        # 데이터 검증 오류 (필드명과 값 포함)
        validation_error = DataValidationError(
            "잘못된 데이터",
            field_name="calories",
            invalid_value=-100
        )
        print(f"✓ 데이터 검증 오류: {validation_error}")
        assert "필드: calories" in str(validation_error)
        assert "값: -100" in str(validation_error)
        
        # 영양 정보 검증 오류
        nutrition_error = NutritionDataError(
            "칼로리가 음수입니다",
            field_name="calories_per_100g",
            invalid_value=-50
        )
        assert isinstance(nutrition_error, DataValidationError)
        print("✓ 영양 정보 검증 오류 생성 성공")
        
    except Exception as e:
        print(f"✗ 데이터 검증 예외 테스트 실패: {e}")


def test_error_handler():
    """오류 처리 유틸리티 테스트."""
    print("\n=== 오류 처리 유틸리티 테스트 ===")
    
    try:
        # 사용자 친화적 메시지 테스트
        api_key_error = InvalidAPIKeyError("Invalid API key")
        friendly_msg = ErrorHandler.get_user_friendly_message(api_key_error)
        print(f"✓ API 키 오류 메시지: {friendly_msg}")
        assert "API 키가 유효하지 않습니다" in friendly_msg
        
        # 해결 방법 제안 테스트
        solution = ErrorHandler.get_solution_suggestion(api_key_error)
        print(f"✓ API 키 오류 해결 방법: {solution}")
        assert "환경변수" in solution
        
        # 네트워크 오류 테스트
        network_error = NetworkError("Connection failed")
        network_msg = ErrorHandler.get_user_friendly_message(network_error)
        network_solution = ErrorHandler.get_solution_suggestion(network_error)
        print(f"✓ 네트워크 오류 메시지: {network_msg}")
        print(f"✓ 네트워크 오류 해결 방법: {network_solution}")
        
        # 알 수 없는 오류 테스트
        unknown_error = ValueError("Unknown error")
        unknown_msg = ErrorHandler.get_user_friendly_message(unknown_error)
        print(f"✓ 알 수 없는 오류 메시지: {unknown_msg}")
        assert "예상치 못한 오류" in unknown_msg
        
    except Exception as e:
        print(f"✗ 오류 처리 유틸리티 테스트 실패: {e}")


def test_specific_error_scenarios():
    """특정 오류 시나리오 테스트."""
    print("\n=== 특정 오류 시나리오 테스트 ===")
    
    # 시나리오 1: API 키 누락
    try:
        raise APIKeyError("API 키가 환경변수에 설정되지 않았습니다")
    except APIKeyError as e:
        msg = ErrorHandler.get_user_friendly_message(e)
        solution = ErrorHandler.get_solution_suggestion(e)
        print(f"✓ 시나리오 1 - API 키 누락:")
        print(f"  메시지: {msg}")
        print(f"  해결방법: {solution.split(chr(10))[0]}")  # 첫 번째 줄만
    
    # 시나리오 2: 음식 검색 결과 없음
    try:
        raise FoodAPIError("검색 결과가 없습니다", status_code=404)
    except FoodAPIError as e:
        msg = ErrorHandler.get_user_friendly_message(e)
        print(f"✓ 시나리오 2 - 음식 검색 실패: {msg}")
    
    # 시나리오 3: 칼로리 계산 오류
    try:
        raise CalorieCalculationError("체중이 0 이하입니다")
    except CalorieCalculationError as e:
        msg = ErrorHandler.get_user_friendly_message(e)
        print(f"✓ 시나리오 3 - 칼로리 계산 오류: {msg}")
    
    # 시나리오 4: TTL 파일 문법 오류
    try:
        raise TTLSyntaxError("잘못된 Turtle 문법입니다")
    except TTLSyntaxError as e:
        msg = ErrorHandler.get_user_friendly_message(e)
        print(f"✓ 시나리오 4 - TTL 문법 오류: {msg}")


def test_exception_chaining():
    """예외 연쇄 테스트."""
    print("\n=== 예외 연쇄 테스트 ===")
    
    try:
        try:
            # 원본 오류 발생
            raise ValueError("원본 데이터 오류")
        except ValueError as original_error:
            # 새로운 오류로 감싸기
            raise DataValidationError("데이터 검증 실패") from original_error
    
    except DataValidationError as e:
        print(f"✓ 연쇄된 예외: {e}")
        if e.__cause__:
            print(f"✓ 원본 예외: {e.__cause__}")
        else:
            print("✗ 원본 예외 정보가 없습니다")


def demonstrate_error_handling():
    """실제 사용 예제 시연."""
    print("\n=== 실제 사용 예제 시연 ===")
    
    def simulate_api_call(api_key: str, search_term: str):
        """API 호출 시뮬레이션."""
        if not api_key:
            raise APIKeyError("API 키가 제공되지 않았습니다")
        
        if api_key == "invalid":
            raise InvalidAPIKeyError("유효하지 않은 API 키입니다")
        
        if search_term == "network_error":
            raise NetworkError("네트워크 연결 실패")
        
        if search_term == "no_results":
            raise FoodAPIError("검색 결과가 없습니다", status_code=404)
        
        return {"result": f"{search_term}에 대한 검색 결과"}
    
    # 다양한 오류 상황 테스트
    test_cases = [
        ("", "백미밥"),           # API 키 누락
        ("invalid", "백미밥"),    # 잘못된 API 키
        ("valid", "network_error"), # 네트워크 오류
        ("valid", "no_results"),    # 검색 결과 없음
        ("valid", "백미밥")         # 정상 케이스
    ]
    
    for api_key, search_term in test_cases:
        try:
            result = simulate_api_call(api_key, search_term)
            print(f"✓ 성공: {search_term} -> {result}")
        
        except IntegratedAPIError as e:
            friendly_msg = ErrorHandler.get_user_friendly_message(e)
            solution = ErrorHandler.get_solution_suggestion(e)
            print(f"✗ 오류: {search_term}")
            print(f"  메시지: {friendly_msg}")
            print(f"  해결방법: {solution.split(chr(10))[0]}")  # 첫 번째 줄만


if __name__ == "__main__":
    test_basic_exception_hierarchy()
    test_api_related_exceptions()
    test_data_validation_exceptions()
    test_error_handler()
    test_specific_error_scenarios()
    test_exception_chaining()
    demonstrate_error_handling()
    print("\n✅ 모든 예외 처리 테스트 완료!")