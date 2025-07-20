"""
API 연동 통합 테스트 모듈.

이 모듈은 Mock API를 사용한 전체 플로우 테스트,
오류 시나리오별 처리 검증, API 응답 시간 검증을 제공합니다.
"""

import unittest
import time
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import threading

from food_api_client import FoodAPIClient
from exercise_api_client import ExerciseAPIClient
from cache_manager import CacheManager
from calorie_manager import CalorieManager
from rdf_data_converter import RDFDataConverter
from integrated_models import FoodItem, ExerciseItem, NutritionInfo
from exceptions import (
    APIConnectionError, APIResponseError, NetworkError, TimeoutError,
    NoSearchResultsError, DataValidationError
)


class MockAPIServer:
    """Mock API 서버 클래스."""
    
    def __init__(self):
        """MockAPIServer 초기화."""
        self.food_data = {
            "getFoodNtrItdntList1": {
                "header": {
                    "resultCode": "00",
                    "resultMsg": "NORMAL SERVICE."
                },
                "body": {
                    "pageNo": 1,
                    "totalCount": 1,
                    "numOfRows": 10,
                    "items": [
                        {
                            "FOOD_CD": "D000001",
                            "FOOD_NM_KR": "사과",
                            "FOOD_NM_EN": "Apple",
                            "NUTR_CONT1": "52.0",  # 칼로리
                            "NUTR_CONT2": "13.8",  # 탄수화물
                            "NUTR_CONT3": "0.3",   # 단백질
                            "NUTR_CONT4": "0.2",   # 지방
                            "NUTR_CONT5": "2.4",   # 식이섬유
                            "NUTR_CONT6": "1.0",   # 나트륨
                            "SERVING_SIZE": "100",
                            "MAKER_NM": "자연산",
                            "GROUP_NM": "과일류"
                        }
                    ]
                }
            }
        }
        
        self.exercise_data = {
            "searchKeyword1": {
                "response": {
                    "header": {
                        "resultCode": "0000",
                        "resultMsg": "OK"
                    },
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "contentid": "EX001",
                                    "title": "걷기",
                                    "overview": "일반적인 걷기 운동",
                                    "cat3": "유산소운동",
                                    "met": "3.5"
                                }
                            ]
                        },
                        "numOfRows": 10,
                        "pageNo": 1,
                        "totalCount": 1
                    }
                }
            }
        }
        
        self.response_delay = 0  # 응답 지연 시간 (초)
        self.should_fail = False  # 실패 시뮬레이션
        self.failure_type = None  # 실패 타입
    
    def set_response_delay(self, delay: float):
        """응답 지연 시간을 설정합니다."""
        self.response_delay = delay
    
    def set_failure_mode(self, should_fail: bool, failure_type: str = None):
        """실패 모드를 설정합니다."""
        self.should_fail = should_fail
        self.failure_type = failure_type
    
    def mock_food_api_response(self, *args, **kwargs):
        """음식 API 응답을 모킹합니다."""
        time.sleep(self.response_delay)
        
        if self.should_fail:
            if self.failure_type == "network":
                raise Exception("네트워크 연결 실패")
            elif self.failure_type == "timeout":
                raise Exception("요청 시간 초과")
            elif self.failure_type == "http_error":
                response = Mock()
                response.status_code = 500
                response.text = "Internal Server Error"
                response.raise_for_status.side_effect = Exception("500 Server Error")
                return response
        
        # 정상 응답
        response = Mock()
        response.status_code = 200
        response.json.return_value = self.food_data
        return response
    
    def mock_exercise_api_response(self, *args, **kwargs):
        """운동 API 응답을 모킹합니다."""
        time.sleep(self.response_delay)
        
        if self.should_fail:
            if self.failure_type == "network":
                raise Exception("네트워크 연결 실패")
            elif self.failure_type == "timeout":
                raise Exception("요청 시간 초과")
        
        # 정상 응답
        response = Mock()
        response.status_code = 200
        response.json.return_value = self.exercise_data
        return response


class APIIntegrationTests(unittest.TestCase):
    """API 연동 통합 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # Mock API 서버 설정
        self.mock_server = MockAPIServer()
        
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        
        # Mock AuthController 생성
        from auth_controller import AuthController
        mock_auth = Mock(spec=AuthController)
        mock_auth.get_api_key.return_value = "test_key"
        mock_auth.validate_api_key.return_value = True
        
        # API 클라이언트 초기화
        self.food_client = FoodAPIClient(
            auth_controller=mock_auth,
            base_url="https://test-food-api.com"
        )
        
        self.exercise_client = ExerciseAPIClient(
            auth_controller=mock_auth,
            base_url="https://test-exercise-api.com"
        )
        
        # 캐시 매니저 초기화
        self.cache_manager = CacheManager(
            cache_dir=self.test_dir,
            default_ttl=300
        )
        
        # 칼로리 매니저 초기화
        self.calorie_manager = CalorieManager()
        
        # RDF 데이터 변환기 초기화
        self.rdf_converter = RDFDataConverter()
    
    def tearDown(self):
        """테스트 정리."""
        # 임시 디렉토리 삭제
        if self.test_dir:
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('requests.get')
    def test_food_api_integration_flow(self, mock_get):
        """음식 API 통합 플로우 테스트."""
        # Mock API 응답 설정
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        # 1. 음식 검색
        search_results = self.food_client.search_food("사과")
        
        self.assertIsInstance(search_results, list)
        self.assertGreater(len(search_results), 0)
        
        # 2. 검색 결과 검증
        food_item = search_results[0]
        self.assertIsInstance(food_item, FoodItem)
        self.assertEqual(food_item.name, "사과")
        self.assertIsNotNone(food_item.nutrition_info)
        
        # 3. 영양 정보 검증
        nutrition = food_item.nutrition_info
        self.assertEqual(nutrition.calories_per_100g, 52.0)
        self.assertEqual(nutrition.carbohydrate, 13.8)
        self.assertEqual(nutrition.protein, 0.3)
        self.assertEqual(nutrition.fat, 0.2)
        
        # 4. 칼로리 계산
        calories = self.calorie_manager.calculate_food_calories(food_item, amount=150)
        expected_calories = 52.0 * 1.5  # 150g
        self.assertEqual(calories, expected_calories)
        
        # 5. RDF 변환
        rdf_data = self.rdf_converter.convert_food_to_rdf(food_item)
        self.assertIsInstance(rdf_data, str)
        self.assertIn("사과", rdf_data)
    
    @patch('requests.get')
    def test_exercise_api_integration_flow(self, mock_get):
        """운동 API 통합 플로우 테스트."""
        # Mock API 응답 설정
        mock_get.side_effect = self.mock_server.mock_exercise_api_response
        
        # 1. 운동 검색
        search_results = self.exercise_client.search_exercise("걷기")
        
        self.assertIsInstance(search_results, list)
        self.assertGreater(len(search_results), 0)
        
        # 2. 검색 결과 검증
        exercise_item = search_results[0]
        self.assertIsInstance(exercise_item, ExerciseItem)
        self.assertEqual(exercise_item.name, "걷기")
        self.assertEqual(exercise_item.met, 3.5)
        
        # 3. 칼로리 소모 계산
        burned_calories = self.calorie_manager.calculate_exercise_calories(
            exercise_item, weight_kg=70, duration_minutes=30
        )
        expected_calories = 3.5 * 70 * 0.5 * 1.05  # MET * 체중 * 시간 * 보정계수
        self.assertAlmostEqual(burned_calories, expected_calories, places=2)
        
        # 4. RDF 변환
        rdf_data = self.rdf_converter.convert_exercise_to_rdf(exercise_item)
        self.assertIsInstance(rdf_data, str)
        self.assertIn("걷기", rdf_data)
    
    @patch('requests.get')
    def test_api_response_time_limit(self, mock_get):
        """API 응답 시간 제한 테스트 (3초 이하)."""
        # 정상 응답 시간 테스트
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        start_time = time.time()
        results = self.food_client.search_food("사과")
        response_time = time.time() - start_time
        
        # 응답 시간이 3초 이하인지 확인
        self.assertLess(response_time, 3.0, "API 응답 시간이 3초를 초과했습니다.")
        self.assertGreater(len(results), 0)
    
    @patch('requests.get')
    def test_network_error_handling(self, mock_get):
        """네트워크 오류 처리 테스트."""
        # 네트워크 오류 시뮬레이션
        self.mock_server.set_failure_mode(True, "network")
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        with self.assertRaises((NetworkError, Exception)):
            self.food_client.search_food("사과")
    
    @patch('requests.get')
    def test_timeout_error_handling(self, mock_get):
        """타임아웃 오류 처리 테스트."""
        # 타임아웃 오류 시뮬레이션
        self.mock_server.set_failure_mode(True, "timeout")
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        with self.assertRaises((TimeoutError, Exception)):
            self.food_client.search_food("사과")
    
    @patch('requests.get')
    def test_http_error_handling(self, mock_get):
        """HTTP 오류 처리 테스트."""
        # HTTP 오류 시뮬레이션
        self.mock_server.set_failure_mode(True, "http_error")
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        with self.assertRaises((APIResponseError, Exception)):
            self.food_client.search_food("사과")
    
    @patch('requests.get')
    def test_concurrent_api_calls(self, mock_get):
        """동시 API 호출 테스트."""
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        results = []
        errors = []
        
        def api_call(query):
            try:
                result = self.food_client.search_food(f"음식{query}")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # 10개의 동시 API 호출
        threads = []
        for i in range(10):
            thread = threading.Thread(target=api_call, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 검증
        self.assertEqual(len(errors), 0, f"동시 API 호출 중 오류 발생: {errors}")
        self.assertEqual(len(results), 10)
    
    @patch('requests.get')
    def test_end_to_end_workflow(self, mock_get):
        """전체 워크플로우 종단간 테스트."""
        # Mock API 응답 설정
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        # 1. 음식 검색
        food_results = self.food_client.search_food("사과")
        self.assertGreater(len(food_results), 0)
        
        food_item = food_results[0]
        
        # 2. 음식 칼로리 계산
        food_calories = self.calorie_manager.calculate_food_calories(food_item, amount=200)
        self.assertGreater(food_calories, 0)
        
        # 3. 운동 검색 (Mock 설정 변경)
        mock_get.side_effect = self.mock_server.mock_exercise_api_response
        exercise_results = self.exercise_client.search_exercise("걷기")
        self.assertGreater(len(exercise_results), 0)
        
        exercise_item = exercise_results[0]
        
        # 4. 운동 칼로리 계산
        exercise_calories = self.calorie_manager.calculate_exercise_calories(
            exercise_item, weight_kg=70, duration_minutes=45
        )
        self.assertGreater(exercise_calories, 0)
        
        # 5. 칼로리 밸런스 계산
        balance = self.calorie_manager.calculate_calorie_balance(
            food_calories, exercise_calories
        )
        expected_balance = food_calories - exercise_calories
        self.assertEqual(balance, expected_balance)
        
        # 6. RDF 변환
        food_rdf = self.rdf_converter.convert_food_to_rdf(food_item)
        exercise_rdf = self.rdf_converter.convert_exercise_to_rdf(exercise_item)
        
        self.assertIsInstance(food_rdf, str)
        self.assertIsInstance(exercise_rdf, str)
        self.assertIn("사과", food_rdf)
        self.assertIn("걷기", exercise_rdf)


class PerformanceTests(unittest.TestCase):
    """성능 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        self.mock_server = MockAPIServer()
        # Mock AuthController 생성
        from auth_controller import AuthController
        mock_auth = Mock(spec=AuthController)
        mock_auth.get_api_key.return_value = "test_key"
        mock_auth.validate_api_key.return_value = True
        
        self.food_client = FoodAPIClient(
            auth_controller=mock_auth,
            base_url="https://test-food-api.com"
        )
    
    @patch('requests.get')
    def test_response_time_benchmark(self, mock_get):
        """응답 시간 벤치마크 테스트."""
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        response_times = []
        
        # 50회 API 호출하여 응답 시간 측정
        for _ in range(50):
            start_time = time.time()
            self.food_client.search_food("사과")
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        # 통계 계산
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        print(f"\n응답 시간 통계:")
        print(f"  평균: {avg_time:.3f}초")
        print(f"  최대: {max_time:.3f}초")
        print(f"  최소: {min_time:.3f}초")
        
        # 성능 기준 검증
        self.assertLess(avg_time, 1.0, "평균 응답 시간이 1초를 초과했습니다.")
        self.assertLess(max_time, 3.0, "최대 응답 시간이 3초를 초과했습니다.")
    
    @patch('requests.get')
    def test_performance_under_load(self, mock_get):
        """부하 상황에서의 성능 테스트."""
        mock_get.side_effect = self.mock_server.mock_food_api_response
        
        # 100개의 순차 API 호출
        start_time = time.time()
        
        for i in range(100):
            try:
                results = self.food_client.search_food(f"음식{i}")
                self.assertGreater(len(results), 0)
            except Exception as e:
                self.fail(f"API 호출 {i}에서 실패: {str(e)}")
        
        total_time = time.time() - start_time
        avg_time_per_call = total_time / 100
        
        # 평균 응답 시간이 1초 이하인지 확인
        self.assertLess(avg_time_per_call, 1.0, 
                       f"평균 API 응답 시간이 너무 깁니다: {avg_time_per_call:.2f}초")


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)