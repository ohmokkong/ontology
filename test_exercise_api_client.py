"""
운동 API 클라이언트 테스트 모듈.
"""

import json
import tempfile
from pathlib import Path
from auth_controller import AuthController
from exercise_api_client import ExerciseAPIClient
from integrated_models import ExerciseItem, ExerciseSession
from exceptions import ExerciseAPIError, NoSearchResultsError


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


def test_client_initialization():
    """클라이언트 초기화 테스트."""
    print("=== 운동 API 클라이언트 초기화 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        assert client.api_key is not None
        assert client.base_url == "https://openapi.k-health.or.kr/api"
        assert client.timeout == 10
        assert client.retry_count == 2
        assert client._is_simulation_mode() == True  # 테스트 키이므로 시뮬레이션 모드
        
        print("✓ 운동 API 클라이언트 초기화 성공")
        print(f"  - API 키: {client.api_key[:10]}...")
        print(f"  - 타임아웃: {client.timeout}초")
        print(f"  - 재시도 횟수: {client.retry_count}회")
        print(f"  - 시뮬레이션 모드: {client._is_simulation_mode()}")
        
        # 상태 정보 확인
        status = client.get_api_status()
        print(f"✓ API 상태: {status['api_name']}")
        print(f"  - 지원 운동 수: {status['supported_exercises']}개")
        
    except Exception as e:
        print(f"✗ 클라이언트 초기화 실패: {e}")
    
    finally:
        # 테스트 파일 정리
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_exercise_search_success():
    """운동 검색 성공 테스트."""
    print("\n=== 운동 검색 성공 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 정확한 매칭 테스트
        results = client.search_exercise("달리기")
        
        assert len(results) > 0
        assert all(isinstance(item, ExerciseItem) for item in results)
        
        # 첫 번째 결과 확인
        first_item = results[0]
        assert first_item.name == "달리기"
        assert first_item.met_value == 8.0
        assert first_item.category == "유산소운동"
        assert first_item.exercise_id is not None
        
        print("✓ 정확한 운동 검색 성공")
        print(f"  - {first_item.name}: MET {first_item.met_value}, 분류: {first_item.category}")
        
        # 부분 매칭 테스트
        partial_results = client.search_exercise("걷")
        assert len(partial_results) > 0
        
        print("✓ 부분 매칭 검색 성공")
        for item in partial_results:
            print(f"  - {item.name}: MET {item.met_value}")
        
    except Exception as e:
        print(f"✗ 운동 검색 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_exercise_search_no_results():
    """검색 결과 없음 테스트."""
    print("\n=== 운동 검색 결과 없음 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 존재하지 않는 운동 검색
        results = client.search_exercise("존재하지않는운동12345")
        print("✗ 검색 결과 없음 예외가 발생해야 함")
        
    except NoSearchResultsError as e:
        print(f"✓ 검색 결과 없음 예외 정상 처리: {e}")
    except Exception as e:
        print(f"✗ 예상치 못한 오류: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_exercise_categories():
    """운동 분류 테스트."""
    print("\n=== 운동 분류 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 운동 분류 조회
        categories = client.get_exercise_categories()
        
        assert len(categories) > 0
        assert all("id" in cat and "name" in cat for cat in categories)
        
        print("✓ 운동 분류 조회 성공")
        for category in categories:
            print(f"  - {category['name']} ({category['id']}): {category.get('description', '')}")
        
        # 분류별 검색 테스트
        aerobic_results = client.search_exercise("달리기", category="유산소운동")
        assert len(aerobic_results) > 0
        assert all(item.category == "유산소운동" for item in aerobic_results)
        
        print("✓ 분류별 검색 성공")
        
    except Exception as e:
        print(f"✗ 운동 분류 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_exercise_detail():
    """운동 상세정보 테스트."""
    print("\n=== 운동 상세정보 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 상세정보 조회
        detail = client.get_exercise_details("EX_0001")
        
        assert isinstance(detail, ExerciseItem)
        assert detail.name == "달리기"
        assert detail.met_value == 8.0
        assert detail.exercise_id == "EX_0001"
        
        print("✓ 운동 상세정보 조회 성공")
        print(f"  - 운동명: {detail.name}")
        print(f"  - MET 값: {detail.met_value}")
        print(f"  - 분류: {detail.category}")
        print(f"  - 설명: {detail.description}")
        
    except Exception as e:
        print(f"✗ 운동 상세정보 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_batch_search():
    """일괄 검색 테스트."""
    print("\n=== 운동 일괄 검색 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 일괄 검색
        exercise_names = ["달리기", "걷기", "수영", "존재하지않는운동"]
        results = client.batch_search_exercises(exercise_names)
        
        assert len(results) == 4
        assert len(results["달리기"]) > 0
        assert len(results["걷기"]) > 0
        assert len(results["수영"]) > 0
        assert len(results["존재하지않는운동"]) == 0
        
        print("✓ 운동 일괄 검색 성공")
        for exercise_name, items in results.items():
            if items:
                print(f"  - {exercise_name}: {len(items)}개 결과")
                for item in items[:2]:  # 최대 2개만 표시
                    print(f"    • {item.name} (MET: {item.met_value})")
            else:
                print(f"  - {exercise_name}: 검색 결과 없음")
        
    except Exception as e:
        print(f"✗ 운동 일괄 검색 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_met_value_extraction():
    """MET 값 추출 테스트."""
    print("\n=== MET 값 추출 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 다양한 형태의 데이터에서 MET 값 추출 테스트
        test_cases = [
            ({"met": 8.0}, 8.0),
            ({"met_value": "6.5"}, 6.5),
            ({"metabolic_equivalent": 10}, 10.0),
            ({"intensity": "7.2"}, 7.2),
            ({}, 5.0),  # 기본값
            ({"invalid_field": "test"}, 5.0)  # 기본값
        ]
        
        for i, (test_data, expected) in enumerate(test_cases):
            result = client._parse_met_value(test_data)
            assert abs(result - expected) < 0.01, f"테스트 케이스 {i+1} 실패: {result} != {expected}"
        
        print("✓ MET 값 추출 테스트 성공")
        print("  - 다양한 필드명 처리")
        print("  - 문자열 숫자 변환")
        print("  - 기본값 처리")
        
    except Exception as e:
        print(f"✗ MET 값 추출 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_exercise_category_determination():
    """운동 분류 결정 테스트."""
    print("\n=== 운동 분류 결정 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 분류 결정 테스트
        test_cases = [
            ("달리기", "유산소운동"),
            ("팔굽혀펴기", "근력운동"),
            ("요가", "유연성운동"),
            ("축구", "스포츠"),
            ("태권도", "전통운동"),
            ("알수없는운동", "일반운동")
        ]
        
        for exercise_name, expected_category in test_cases:
            result = client._determine_exercise_category(exercise_name)
            assert result == expected_category, f"{exercise_name}: {result} != {expected_category}"
        
        print("✓ 운동 분류 결정 테스트 성공")
        for exercise_name, category in test_cases:
            print(f"  - {exercise_name} → {category}")
        
    except Exception as e:
        print(f"✗ 운동 분류 결정 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_korean_exercises():
    """한국 운동 예제 테스트."""
    print("\n=== 한국 운동 예제 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 한국 전통 운동 및 일반 운동
        korean_exercises = [
            "태권도", "걷기", "달리기", "등산", "자전거타기",
            "수영", "요가", "헬스", "축구", "농구"
        ]
        
        print("📋 한국 운동 검색 테스트:")
        
        successful_searches = 0
        for exercise_name in korean_exercises:
            try:
                results = client.search_exercise(exercise_name)
                if results:
                    exercise_item = results[0]
                    print(f"✓ {exercise_name}:")
                    print(f"  - MET 값: {exercise_item.met_value}")
                    print(f"  - 분류: {exercise_item.category}")
                    print(f"  - ID: {exercise_item.exercise_id}")
                    successful_searches += 1
                else:
                    print(f"✗ {exercise_name}: 검색 결과 없음")
                    
            except Exception as e:
                print(f"✗ {exercise_name}: 오류 - {str(e)}")
        
        print(f"\n✓ 총 {successful_searches}/{len(korean_exercises)}개 운동 검색 성공")
        
        # 지원되는 운동 목록 확인
        supported = client.get_supported_exercises()
        print(f"✓ 지원되는 운동 총 {len(supported)}개")
        
    except Exception as e:
        print(f"✗ 한국 운동 예제 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_exercise_session_integration():
    """운동 세션 통합 테스트."""
    print("\n=== 운동 세션 통합 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 운동 검색
        results = client.search_exercise("달리기")
        exercise_item = results[0]
        
        # 운동 세션 생성 (통합 모델 사용)
        from rdflib import Namespace
        namespace = Namespace("http://example.org/exercise#")
        
        session = ExerciseSession.create_with_calculation(
            exercise_item=exercise_item,
            weight=70.0,  # 70kg
            duration=30.0,  # 30분
            namespace=namespace
        )
        
        # 검증
        assert session.weight == 70.0
        assert session.duration == 30.0
        assert session.calories_burned == exercise_item.met_value * 70.0 * 0.5  # 280kcal
        
        print("✓ 운동 세션 통합 테스트 성공")
        print(f"  - 운동: {exercise_item.name}")
        print(f"  - MET 값: {exercise_item.met_value}")
        print(f"  - 체중: {session.weight}kg")
        print(f"  - 시간: {session.duration}분")
        print(f"  - 소모 칼로리: {session.calories_burned}kcal")
        
        # 칼로리 계산 검증
        expected_calories = exercise_item.met_value * 70.0 * (30.0 / 60.0)
        assert abs(session.calories_burned - expected_calories) < 0.01
        print(f"✓ 칼로리 계산 정확성 검증: {expected_calories}kcal")
        
    except Exception as e:
        print(f"✗ 운동 세션 통합 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


def test_error_handling():
    """오류 처리 테스트."""
    print("\n=== 오류 처리 테스트 ===")
    
    try:
        auth = create_test_auth_controller()
        client = ExerciseAPIClient(auth)
        
        # 빈 검색어 테스트
        try:
            client.search_exercise("")
            print("✗ 빈 검색어에 대해 오류가 발생해야 함")
        except ExerciseAPIError as e:
            print(f"✓ 빈 검색어 오류 정상 처리: {e}")
        
        # 잘못된 운동 ID 테스트
        try:
            client.get_exercise_details("INVALID_ID")
            print("✗ 잘못된 ID에 대해 오류가 발생해야 함")
        except ExerciseAPIError as e:
            print(f"✓ 잘못된 ID 오류 정상 처리: {e}")
        
        print("✓ 오류 처리 테스트 완료")
        
    except Exception as e:
        print(f"✗ 오류 처리 테스트 실패: {e}")
    
    finally:
        if hasattr(auth, '_test_config_path'):
            Path(auth._test_config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_client_initialization()
    test_exercise_search_success()
    test_exercise_search_no_results()
    test_exercise_categories()
    test_exercise_detail()
    test_batch_search()
    test_met_value_extraction()
    test_exercise_category_determination()
    test_korean_exercises()
    test_exercise_session_integration()
    test_error_handling()
    print("\n✅ 모든 운동 API 클라이언트 테스트 완료!")