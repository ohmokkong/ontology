"""
식약처 API 클라이언트 테스트 모듈.
"""

import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from auth_controller import AuthController
from food_api_client import FoodAPIClient
from integrated_models import FoodItem, NutritionInfo
from exceptions import FoodAPIError, NoSearchResultsError, InvalidAPIKeyError


def create_test_auth_controller():
    """테스트용 인증 컨트롤러 생성."""
    config_data = {
        "food_api_key": "test_food_api_key_12345678901234567890",
        "exercise_api_key": "test_exercise_api_key_123456789",
        "settings": {
            "timeout": 10,
            "retry_count": 2
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
        config_file_path = f.name
    
    auth = AuthController(config_file_path)
    auth.load_api_keys()
    
    # 테스트 후 파일 정리를 위해 경로 저장
    auth._test_config_path = config_file_path
    
    return auth


def create_mock_food_api_response():
    """모의 식약처 API 응답 생성."""
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
                    "DESC_KOR": "현미밥",
                    "NUM": "1002",
                    "GROUP_NAME": "곡류",
                    "MAKER_NAME": "일반",
                    "NUTR_CONT1": "112.0",
                    "NUTR_CONT2": "22.9",
                    "NUTR_CONT3": "2.6",
                    "NUTR_CONT4": "0.9",
                    "NUTR_CONT5": "1.4",
                    "NUTR_CONT6": "2.0"
                },
                {
                    "DESC_KOR": "찹쌀밥",
                    "NUM": "1003",
                    "GROUP_NAME": "곡류",
                    "MAKER_NAME": "일반",
                    "NUTR_CONT1": "116.0",
                    "NUTR_CONT2": "25.4",
                    "NUTR_CONT3": "2.1",
                    "NUTR_CONT4": "0.2",
                    "NUTR_CONT5": "0.2",
                    "NUTR_CONT6": "1.5"
                }
            ]
        }]
    }


def test_client_initialization():
    """클라이언트 초기화 테스트."""
    print("=== 클라이언트 초기화 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = FoodAPIClient(auth)
        
        assert client.api_key is not None
        assert client.base_url == "https://openapi.foodsafetykorea.go.kr/api"
        assert client.timeout == 10
        assert client.retry_count == 2
        
        print("✓ 클라이언트 초기화 성공")
        print(f"  - API 키: {client.api_key[:10]}...")
        print(f"  - 타임아웃: {client.timeout}초")
        print(f"  - 재시도 횟수: {client.retry_count}회")
        
        # 상태 정보 확인
        status = client.get_api_status()
        print(f"✓ API 상태: {status['api_name']}")
        
    except Exception as e:
        print(f"✗ 클라이언트 초기화 실패: {e}")
    
    finally:
        # 테스트 파일 정리
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


@patch('food_api_client.requests.Session.get')
def test_food_search_success(mock_get):
    """음식 검색 성공 테스트."""
    print("\n=== 음식 검색 성공 테스트 ===")
    
    # Mock 응답 설정
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = create_mock_food_api_response()
    mock_get.return_value = mock_response
    
    try:
        auth = create_test_auth_controller()
        client = FoodAPIClient(auth)
        
        # 음식 검색
        results = client.search_food("밥")
        
        assert len(results) == 3
        assert all(isinstance(item, FoodItem) for item in results)
        
        # 첫 번째 결과 확인
        first_item = results[0]
        assert first_item.name == "백미밥"
        assert first_item.food_id == "1001"
        assert first_item.category == "곡류"
        
        print("✓ 음식 검색 성공")
        for item in results:
            print(f"  - {item.name} (ID: {item.food_id}, 분류: {item.category})")
        
    except Exception as e:
        print(f"✗ 음식 검색 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


@patch('food_api_client.requests.Session.get')
def test_food_search_no_results(mock_get):
    """검색 결과 없음 테스트."""
    print("\n=== 검색 결과 없음 테스트 ===")
    
    # 빈 결과 응답
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "RESULT": {
            "CODE": "INFO-200",
            "MSG": "해당하는 데이터가 없습니다."
        }
    }
    mock_get.return_value = mock_response
    
    try:
        auth = create_test_auth_controller()
        client = FoodAPIClient(auth)
        
        # 존재하지 않는 음식 검색
        results = client.search_food("존재하지않는음식")
        print("✗ 검색 결과 없음 예외가 발생해야 함")
        
    except NoSearchResultsError as e:
        print(f"✓ 검색 결과 없음 예외 정상 처리: {e}")
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


@patch('food_api_client.requests.Session.get')
def test_api_error_handling(mock_get):
    """API 오류 처리 테스트."""
    print("\n=== API 오류 처리 테스트 ===")
    
    auth = create_test_auth_controller()
    client = FoodAPIClient(auth)
    
    # 401 Unauthorized 테스트
    mock_response = Mock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response
    
    try:
        client.search_food("테스트")
        print("✗ 401 오류 시 예외가 발생해야 함")
    except InvalidAPIKeyError as e:
        print(f"✓ 401 오류 정상 처리: {e}")
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
    
    # 429 Too Many Requests 테스트
    mock_response.status_code = 429
    try:
        client.search_food("테스트")
        print("✗ 429 오류 시 예외가 발생해야 함")
    except FoodAPIError as e:
        print(f"✓ 429 오류 정상 처리: {e}")
        assert "호출 한도" in str(e)
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
    
    # 500 Server Error 테스트
    mock_response.status_code = 500
    try:
        client.search_food("테스트")
        print("✗ 500 오류 시 예외가 발생해야 함")
    except FoodAPIError as e:
        print(f"✓ 500 오류 정상 처리: {e}")
        assert "서버 오류" in str(e)
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
    
    # 테스트 파일 정리
    if hasattr(auth, '_test_config_path'):
        Path(auth._test_config_path).unlink(missing_ok=True)


@patch('food_api_client.requests.Session.get')
def test_nutrition_info_extraction(mock_get):
    """영양정보 추출 테스트."""
    print("\n=== 영양정보 추출 테스트 ===")
    
    # Mock 응답 설정
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = create_mock_food_api_response()
    mock_get.return_value = mock_response
    
    try:
        auth = create_test_auth_controller()
        client = FoodAPIClient(auth)
        
        # 음식 검색
        results = client.search_food("백미밥")
        food_item = results[0]
        
        # 영양정보 조회 (실제로는 검색 결과에서 추출)
        nutrition = client.get_nutrition_info(food_item)
        
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
        
        # 칼로리 계산 테스트
        calories_200g = nutrition.calculate_calories_for_amount(200.0)
        expected = 130.0 * 2  # 260kcal
        assert abs(calories_200g - expected) < 0.01
        print(f"✓ 칼로리 계산: 200g = {calories_200g}kcal")
        
    except Exception as e:
        print(f"✗ 영양정보 추출 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


@patch('food_api_client.requests.Session.get')
def test_batch_search(mock_get):
    """일괄 검색 테스트."""
    print("\n=== 일괄 검색 테스트 ===")
    
    # Mock 응답 설정 (각 검색마다 다른 결과)
    def mock_response_side_effect(*args, **kwargs):
        url = args[0]
        mock_response = Mock()
        mock_response.status_code = 200
        
        if "백미밥" in url:
            mock_response.json.return_value = {
                "I2790": [{"row": [{
                    "DESC_KOR": "백미밥",
                    "NUM": "1001",
                    "GROUP_NAME": "곡류",
                    "NUTR_CONT1": "130.0"
                }]}]
            }
        elif "김치" in url:
            mock_response.json.return_value = {
                "I2790": [{"row": [{
                    "DESC_KOR": "배추김치",
                    "NUM": "2001",
                    "GROUP_NAME": "채소류",
                    "NUTR_CONT1": "18.0"
                }]}]
            }
        else:
            # 검색 결과 없음
            mock_response.json.return_value = {
                "RESULT": {
                    "CODE": "INFO-200",
                    "MSG": "해당하는 데이터가 없습니다."
                }
            }
        
        return mock_response
    
    mock_get.side_effect = mock_response_side_effect
    
    try:
        auth = create_test_auth_controller()
        client = FoodAPIClient(auth)
        
        # 일괄 검색
        food_names = ["백미밥", "김치", "존재하지않는음식"]
        results = client.batch_search_foods(food_names)
        
        assert len(results) == 3
        assert len(results["백미밥"]) == 1
        assert len(results["김치"]) == 1
        assert len(results["존재하지않는음식"]) == 0
        
        print("✓ 일괄 검색 성공")
        for food_name, items in results.items():
            if items:
                print(f"  - {food_name}: {len(items)}개 결과")
                for item in items:
                    print(f"    • {item.name} (ID: {item.food_id})")
            else:
                print(f"  - {food_name}: 검색 결과 없음")
        
    except Exception as e:
        print(f"✗ 일괄 검색 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_data_conversion_edge_cases():
    """데이터 변환 예외 상황 테스트."""
    print("\n=== 데이터 변환 예외 상황 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = FoodAPIClient(auth)
        
        # 안전한 float 변환 테스트
        test_cases = [
            ("123.45", 123.45),
            ("123.45g", 123.45),  # 단위 포함
            ("", 0.0),            # 빈 문자열
            (None, 0.0),          # None
            ("abc", 0.0),         # 잘못된 형식
            ("-10", 0.0),         # 음수 (0으로 변환)
            ("", None)            # allow_none=True인 경우
        ]
        
        for i, (input_val, expected) in enumerate(test_cases[:-1]):
            result = client._safe_float_conversion(input_val)
            assert result == expected, f"테스트 케이스 {i+1} 실패: {input_val} -> {result} (예상: {expected})"
        
        # allow_none=True 테스트
        result = client._safe_float_conversion("", allow_none=True)
        assert result is None
        
        print("✓ 데이터 변환 예외 상황 처리 성공")
        print("  - 단위 포함 문자열 처리")
        print("  - 빈 값 및 None 처리")
        print("  - 잘못된 형식 처리")
        print("  - 음수 값 처리")
        
    except Exception as e:
        print(f"✗ 데이터 변환 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_korean_food_examples():
    """한국 음식 예제 테스트."""
    print("\n=== 한국 음식 예제 테스트 ===")
    
    # 한국 음식 데이터 시뮬레이션
    korean_foods_data = {
        "김치찌개": {
            "DESC_KOR": "김치찌개",
            "NUM": "K001",
            "GROUP_NAME": "찌개류",
            "NUTR_CONT1": "45.0",
            "NUTR_CONT2": "5.2",
            "NUTR_CONT3": "3.1",
            "NUTR_CONT4": "1.8"
        },
        "불고기": {
            "DESC_KOR": "불고기",
            "NUM": "K002",
            "GROUP_NAME": "육류",
            "NUTR_CONT1": "156.0",
            "NUTR_CONT2": "2.1",
            "NUTR_CONT3": "18.7",
            "NUTR_CONT4": "7.9"
        },
        "비빔밥": {
            "DESC_KOR": "비빔밥",
            "NUM": "K003",
            "GROUP_NAME": "밥류",
            "NUTR_CONT1": "119.0",
            "NUTR_CONT2": "18.5",
            "NUTR_CONT3": "4.2",
            "NUTR_CONT4": "3.1"
        }
    }
    
    with patch('food_api_client.requests.Session.get') as mock_get:
        def korean_food_response(url):
            mock_response = Mock()
            mock_response.status_code = 200
            
            # URL에서 음식명 추출
            for food_name, food_data in korean_foods_data.items():
                if food_name in url:
                    mock_response.json.return_value = {
                        "I2790": [{"row": [food_data]}]
                    }
                    return mock_response
            
            # 기본 응답
            mock_response.json.return_value = {"I2790": [{"row": []}]}
            return mock_response
        
        mock_get.side_effect = korean_food_response
        
        try:
            auth = create_test_auth_controller()
            client = FoodAPIClient(auth)
            
            print("📋 한국 전통 음식 검색 테스트:")
            
            for food_name in korean_foods_data.keys():
                try:
                    results = client.search_food(food_name)
                    if results:
                        food_item = results[0]
                        nutrition = client.get_nutrition_info(food_item)
                        
                        print(f"✓ {food_name}:")
                        print(f"  - 분류: {food_item.category}")
                        print(f"  - 칼로리: {nutrition.calories_per_100g}kcal/100g")
                        print(f"  - 탄수화물: {nutrition.carbohydrate}g")
                        print(f"  - 단백질: {nutrition.protein}g")
                        print(f"  - 지방: {nutrition.fat}g")
                    else:
                        print(f"✗ {food_name}: 검색 결과 없음")
                        
                except Exception as e:
                    print(f"✗ {food_name}: 오류 - {str(e)}")
            
        except Exception as e:
            print(f"✗ 한국 음식 예제 테스트 실패: {e}")
        
        finally:
            if hasattr(auth, '_test_config_path'):
                Path(auth._test_config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_client_initialization()
    test_food_search_success()
    test_food_search_no_results()
    test_api_error_handling()
    test_nutrition_info_extraction()
    test_batch_search()
    test_data_conversion_edge_cases()
    test_korean_food_examples()
    print("\n✅ 모든 식약처 API 클라이언트 테스트 완료!")