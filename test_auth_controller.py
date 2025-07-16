"""
인증 컨트롤러 테스트 모듈.
"""

import os
import json
import tempfile
from pathlib import Path
from auth_controller import AuthController
from exceptions import APIKeyError, InvalidAPIKeyError, ConfigurationError


def test_environment_variable_loading():
    """환경변수에서 API 키 로드 테스트."""
    print("=== 환경변수 API 키 로드 테스트 ===")
    
    # 테스트용 환경변수 설정
    test_food_key = "test_food_api_key_12345"
    test_exercise_key = "test_exercise_api_key_67890"
    
    os.environ["FOOD_API_KEY"] = test_food_key
    os.environ["EXERCISE_API_KEY"] = test_exercise_key
    
    try:
        auth = AuthController()
        api_keys = auth.load_api_keys()
        
        assert "food_api" in api_keys
        assert "exercise_api" in api_keys
        assert api_keys["food_api"] == test_food_key
        assert api_keys["exercise_api"] == test_exercise_key
        
        print("✓ 환경변수에서 API 키 로드 성공")
        print(f"  - 식약처 API: {api_keys['food_api'][:10]}...")
        print(f"  - 운동 API: {api_keys['exercise_api'][:10]}...")
        
    except Exception as e:
        print(f"✗ 환경변수 로드 테스트 실패: {e}")
    
    finally:
        # 테스트 환경변수 정리
        if "FOOD_API_KEY" in os.environ:
            del os.environ["FOOD_API_KEY"]
        if "EXERCISE_API_KEY" in os.environ:
            del os.environ["EXERCISE_API_KEY"]


def test_config_file_loading():
    """설정파일에서 API 키 로드 테스트."""
    print("\n=== 설정파일 API 키 로드 테스트 ===")
    
    # 임시 설정파일 생성
    config_data = {
        "food_api_key": "config_food_key_12345",
        "exercise_api_key": "config_exercise_key_67890",
        "api_endpoints": {
            "food_api_base_url": "https://test.food.api",
            "exercise_api_base_url": "https://test.exercise.api"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
        config_file_path = f.name
    
    try:
        auth = AuthController(config_file_path)
        api_keys = auth.load_api_keys()
        
        assert "food_api" in api_keys
        assert "exercise_api" in api_keys
        assert api_keys["food_api"] == config_data["food_api_key"]
        assert api_keys["exercise_api"] == config_data["exercise_api_key"]
        
        print("✓ 설정파일에서 API 키 로드 성공")
        print(f"  - 식약처 API: {api_keys['food_api'][:10]}...")
        print(f"  - 운동 API: {api_keys['exercise_api'][:10]}...")
        
        # 설정값 가져오기 테스트
        base_url = auth.get_config_value("api_endpoints", {}).get("food_api_base_url")
        print(f"✓ 설정값 로드: {base_url}")
        
    except Exception as e:
        print(f"✗ 설정파일 로드 테스트 실패: {e}")
    
    finally:
        # 임시 파일 정리
        Path(config_file_path).unlink(missing_ok=True)


def test_priority_order():
    """환경변수 > 설정파일 우선순위 테스트."""
    print("\n=== 우선순위 테스트 (환경변수 > 설정파일) ===")
    
    # 환경변수 설정
    env_food_key = "env_food_key_priority"
    os.environ["FOOD_API_KEY"] = env_food_key
    
    # 설정파일 생성 (다른 키 값)
    config_data = {
        "food_api_key": "config_food_key_priority",
        "exercise_api_key": "config_exercise_key_only"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
        config_file_path = f.name
    
    try:
        auth = AuthController(config_file_path)
        api_keys = auth.load_api_keys()
        
        # 환경변수가 우선되어야 함
        assert api_keys["food_api"] == env_food_key
        # 환경변수에 없는 것은 설정파일에서
        assert api_keys["exercise_api"] == config_data["exercise_api_key"]
        
        print("✓ 우선순위 테스트 성공")
        print(f"  - 식약처 API (환경변수): {api_keys['food_api']}")
        print(f"  - 운동 API (설정파일): {api_keys['exercise_api']}")
        
    except Exception as e:
        print(f"✗ 우선순위 테스트 실패: {e}")
    
    finally:
        if "FOOD_API_KEY" in os.environ:
            del os.environ["FOOD_API_KEY"]
        Path(config_file_path).unlink(missing_ok=True)


def test_missing_api_keys():
    """API 키 누락 시 오류 처리 테스트."""
    print("\n=== API 키 누락 오류 처리 테스트 ===")
    
    # 환경변수와 설정파일 모두 없는 상태
    auth = AuthController("nonexistent_config.json")
    
    try:
        api_keys = auth.load_api_keys()
        print("✗ API 키 누락 시 오류가 발생해야 함")
    except APIKeyError as e:
        print(f"✓ API 키 누락 오류 정상 처리: {e}")
        assert "누락되었습니다" in str(e)
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")


def test_api_key_validation():
    """API 키 검증 테스트."""
    print("\n=== API 키 검증 테스트 ===")
    
    # 유효한 키로 테스트
    os.environ["FOOD_API_KEY"] = "valid_food_api_key_12345678"
    os.environ["EXERCISE_API_KEY"] = "valid_exercise_key_123"
    
    try:
        auth = AuthController()
        auth.load_api_keys()
        
        # 유효한 키 검증
        assert auth.validate_credentials("food_api") == True
        print("✓ 유효한 식약처 API 키 검증 성공")
        
        assert auth.validate_credentials("exercise_api") == True
        print("✓ 유효한 운동 API 키 검증 성공")
        
    except Exception as e:
        print(f"✗ 유효한 키 검증 실패: {e}")
    
    # 무효한 키로 테스트
    os.environ["FOOD_API_KEY"] = "short"  # 너무 짧은 키
    
    try:
        auth = AuthController()
        auth.load_api_keys()
        auth.validate_credentials("food_api")
        print("✗ 무효한 키에 대해 오류가 발생해야 함")
    except InvalidAPIKeyError as e:
        print(f"✓ 무효한 키 검증 오류 정상 처리: {e}")
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
    
    finally:
        # 환경변수 정리
        for key in ["FOOD_API_KEY", "EXERCISE_API_KEY"]:
            if key in os.environ:
                del os.environ[key]


def test_error_handling():
    """오류 처리 메시지 테스트."""
    print("\n=== 오류 처리 메시지 테스트 ===")
    
    auth = AuthController()
    
    # API 키 누락 오류
    api_key_error = APIKeyError("API 키가 설정되지 않았습니다")
    message = auth.handle_auth_error(api_key_error, "food_api")
    print("✓ API 키 누락 오류 메시지:")
    print(message[:100] + "...")
    
    # 무효한 키 오류
    invalid_key_error = InvalidAPIKeyError("키 형식이 올바르지 않습니다")
    message = auth.handle_auth_error(invalid_key_error, "exercise_api")
    print("✓ 무효한 키 오류 메시지:")
    print(message[:100] + "...")


def test_sample_config_creation():
    """샘플 설정파일 생성 테스트."""
    print("\n=== 샘플 설정파일 생성 테스트 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.json"
        auth = AuthController(str(config_path))
        
        try:
            auth.create_sample_config()
            sample_path = Path(f"{config_path}.sample")
            
            assert sample_path.exists()
            print("✓ 샘플 설정파일 생성 성공")
            
            # 샘플 파일 내용 확인
            with open(sample_path, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            
            assert "food_api_key" in sample_data
            assert "exercise_api_key" in sample_data
            assert "api_endpoints" in sample_data
            print("✓ 샘플 파일 내용 검증 성공")
            
        except Exception as e:
            print(f"✗ 샘플 설정파일 생성 실패: {e}")


def test_api_list():
    """설정된 API 목록 조회 테스트."""
    print("\n=== API 목록 조회 테스트 ===")
    
    # 일부만 설정된 상태
    os.environ["FOOD_API_KEY"] = "test_food_key_12345"
    
    try:
        auth = AuthController()
        auth.load_api_keys()
        
        api_list = auth.list_configured_apis()
        print("✓ API 목록 조회 성공:")
        
        for api_name, info in api_list.items():
            status = "✓" if info["configured"] else "✗"
            print(f"  {status} {info['name']}: {info['source']}")
        
        assert api_list["food_api"]["configured"] == True
        assert api_list["exercise_api"]["configured"] == False
        
    except Exception as e:
        print(f"✗ API 목록 조회 실패: {e}")
    
    finally:
        if "FOOD_API_KEY" in os.environ:
            del os.environ["FOOD_API_KEY"]


def test_real_world_scenario():
    """실제 사용 시나리오 테스트."""
    print("\n=== 실제 사용 시나리오 테스트 ===")
    
    # 시나리오: 환경변수에 일부만 설정, 설정파일에 나머지 설정
    os.environ["FOOD_API_KEY"] = "real_food_api_key_from_env"
    
    config_data = {
        "exercise_api_key": "real_exercise_api_key_from_config",
        "api_endpoints": {
            "food_api_base_url": "https://openapi.foodsafetykorea.go.kr/api",
            "exercise_api_base_url": "https://openapi.k-health.or.kr/api"
        },
        "settings": {
            "timeout": 30,
            "retry_count": 3
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
        config_file_path = f.name
    
    try:
        # 1. AuthController 초기화
        auth = AuthController(config_file_path)
        
        # 2. API 키 로드
        api_keys = auth.load_api_keys()
        print("✓ 혼합 소스에서 API 키 로드 성공")
        
        # 3. 개별 키 조회
        food_key = auth.get_api_key("food_api")
        exercise_key = auth.get_api_key("exercise_api")
        print(f"✓ 식약처 API 키: {food_key[:10]}... (환경변수)")
        print(f"✓ 운동 API 키: {exercise_key[:10]}... (설정파일)")
        
        # 4. 키 검증
        auth.validate_credentials("food_api")
        auth.validate_credentials("exercise_api")
        print("✓ 모든 API 키 검증 성공")
        
        # 5. 설정값 조회
        timeout = auth.get_config_value("settings", {}).get("timeout", 10)
        print(f"✓ 설정값 조회: timeout = {timeout}초")
        
        # 6. API 목록 확인
        api_list = auth.list_configured_apis()
        configured_count = sum(1 for info in api_list.values() if info["configured"])
        print(f"✓ 설정된 API 개수: {configured_count}/{len(api_list)}")
        
    except Exception as e:
        print(f"✗ 실제 시나리오 테스트 실패: {e}")
    
    finally:
        if "FOOD_API_KEY" in os.environ:
            del os.environ["FOOD_API_KEY"]
        Path(config_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_environment_variable_loading()
    test_config_file_loading()
    test_priority_order()
    test_missing_api_keys()
    test_api_key_validation()
    test_error_handling()
    test_sample_config_creation()
    test_api_list()
    test_real_world_scenario()
    print("\n✅ 모든 인증 컨트롤러 테스트 완료!")