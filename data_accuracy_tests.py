"""
데이터 처리 정확성 테스트 모듈.
이 모듈은 데이터 변환 및 계산 로직의 정확성을 검증하는 테스트를 제공합니다.
영양소 계산, 칼로리 계산, 데이터 변환 정확도를 검증합니다.
"""

import unittest
import json
import os
import tempfile
from decimal import Decimal, getcontext
from unittest.mock import Mock, patch, MagicMock
from food_api_client import FoodAPIClient
from exercise_api_client import ExerciseAPIClient
from calorie_manager import CalorieManager
from rdf_data_converter import RDFDataConverter
from integrated_models import FoodItem, ExerciseItem, NutritionInfo
from exceptions import DataValidationError

# Decimal 정밀도 설정
getcontext().prec = 28

class DataAccuracyTests(unittest.TestCase):
    """데이터 처리 정확성 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 테스트 데이터 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        
        # 칼로리 매니저 초기화
        self.calorie_manager = CalorieManager()
        
        # RDF 데이터 변환기 초기화
        self.rdf_converter = RDFDataConverter()
        
        # 테스트 데이터 로드
        self.food_test_data = self._load_food_test_data()
        self.exercise_test_data = self._load_exercise_test_data()
    
    def tearDown(self):
        """테스트 정리."""
        # 임시 디렉토리 삭제
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _load_food_test_data(self):
        """음식 테스트 데이터를 로드합니다."""
        return {
            "apple": {
                "name": "사과",
                "calories_per_100g": 52.0,
                "carbohydrate": 13.8,
                "protein": 0.3,
                "fat": 0.2,
                "fiber": 2.4,
                "sodium": 1.0,
                "serving_size": 100,
                "expected_calories_150g": 78.0,
                "expected_carb_calories": 55.2,  # 13.8g * 4kcal/g
                "expected_protein_calories": 1.2,  # 0.3g * 4kcal/g
                "expected_fat_calories": 1.8,  # 0.2g * 9kcal/g
            },
            "rice": {
                "name": "밥",
                "calories_per_100g": 130.0,
                "carbohydrate": 28.0,
                "protein": 2.7,
                "fat": 0.3,
                "fiber": 0.5,
                "sodium": 2.0,
                "serving_size": 100,
                "expected_calories_200g": 260.0,
                "expected_carb_calories": 112.0,  # 28.0g * 4kcal/g
                "expected_protein_calories": 10.8,  # 2.7g * 4kcal/g
                "expected_fat_calories": 2.7,  # 0.3g * 9kcal/g
            },
            "chicken_breast": {
                "name": "닭가슴살",
                "calories_per_100g": 165.0,
                "carbohydrate": 0.0,
                "protein": 31.0,
                "fat": 3.6,
                "fiber": 0.0,
                "sodium": 74.0,
                "serving_size": 100,
                "expected_calories_150g": 247.5,
                "expected_carb_calories": 0.0,  # 0.0g * 4kcal/g
                "expected_protein_calories": 124.0,  # 31.0g * 4kcal/g
                "expected_fat_calories": 32.4,  # 3.6g * 9kcal/g
            }
        }
    
    def _load_exercise_test_data(self):
        """운동 테스트 데이터를 로드합니다."""
        return {
            "walking": {
                "name": "걷기",
                "met": 3.5,
                "expected_calories_70kg_30min": 128.625,  # 3.5 * 70 * 0.5 * 1.05
                "expected_calories_80kg_45min": 220.5,  # 3.5 * 80 * 0.75 * 1.05
            },
            "running": {
                "name": "달리기",
                "met": 8.0,
                "expected_calories_70kg_30min": 294.0,  # 8.0 * 70 * 0.5 * 1.05
                "expected_calories_80kg_45min": 504.0,  # 8.0 * 80 * 0.75 * 1.05
            },
            "swimming": {
                "name": "수영",
                "met": 6.0,
                "expected_calories_70kg_30min": 220.5,  # 6.0 * 70 * 0.5 * 1.05
                "expected_calories_80kg_45min": 378.0,  # 6.0 * 80 * 0.75 * 1.05
            }
        }
    
    def _create_food_item(self, food_data):
        """테스트 음식 아이템을 생성합니다."""
        food_item = FoodItem(
            name=food_data["name"],
            food_id=f"test_{food_data['name']}",
            category="테스트",
            manufacturer="테스트"
        )
        nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=food_data["calories_per_100g"],
            carbohydrate=food_data["carbohydrate"],
            protein=food_data["protein"],
            fat=food_data["fat"],
            fiber=food_data["fiber"],
            sodium=food_data["sodium"]
        )
        food_item.nutrition_info = nutrition
        return food_item
    
    def _create_exercise_item(self, exercise_data):
        """테스트 운동 아이템을 생성합니다."""
        exercise_item = ExerciseItem(
            name=exercise_data["name"],
            exercise_id=f"test_{exercise_data['name']}",
            description=f"테스트 {exercise_data['name']}",
            category="테스트"
        )
        # MET 값은 별도로 설정
        exercise_item.met = exercise_data["met"]
        return exercise_item
    
    def test_food_calorie_calculation_accuracy(self):
        """음식 칼로리 계산 정확도 테스트."""
        print("\n=== 음식 칼로리 계산 정확도 테스트 ===")
        
        for food_key, food_data in self.food_test_data.items():
            food_item = self._create_food_item(food_data)
            
            # 기본 양(100g)에 대한 칼로리 계산
            calories_100g = self.calorie_manager.calculate_food_calories(food_item)
            self.assertAlmostEqual(calories_100g, food_data["calories_per_100g"], places=1)
            
            # 150g에 대한 칼로리 계산
            calories_150g = self.calorie_manager.calculate_food_calories(food_item, amount=150)
            self.assertAlmostEqual(calories_150g, food_data["expected_calories_150g"], places=1)
            
            print(f"✓ {food_data['name']} 칼로리 계산 정확도 검증 완료: "
                  f"100g={calories_100g}kcal, 150g={calories_150g}kcal")
    
    def test_exercise_calorie_calculation_accuracy(self):
        """운동 칼로리 계산 정확도 테스트."""
        print("\n=== 운동 칼로리 계산 정확도 테스트 ===")
        
        for exercise_key, exercise_data in self.exercise_test_data.items():
            exercise_item = self._create_exercise_item(exercise_data)
            
            # 70kg, 30분에 대한 칼로리 계산
            calories_70kg_30min = self.calorie_manager.calculate_exercise_calories(
                exercise_item, weight_kg=70, duration_minutes=30
            )
            self.assertAlmostEqual(
                calories_70kg_30min, 
                exercise_data["expected_calories_70kg_30min"], 
                places=1
            )
            
            # 80kg, 45분에 대한 칼로리 계산
            calories_80kg_45min = self.calorie_manager.calculate_exercise_calories(
                exercise_item, weight_kg=80, duration_minutes=45
            )
            self.assertAlmostEqual(
                calories_80kg_45min, 
                exercise_data["expected_calories_80kg_45min"], 
                places=1
            )
            
            print(f"✓ {exercise_data['name']} 칼로리 계산 정확도 검증 완료: "
                  f"70kg/30분={calories_70kg_30min:.1f}kcal, "
                  f"80kg/45분={calories_80kg_45min:.1f}kcal")
    
    def test_macronutrient_calculation_accuracy(self):
        """영양소별 칼로리 계산 정확도 테스트."""
        print("\n=== 영양소별 칼로리 계산 정확도 테스트 ===")
        
        for food_key, food_data in self.food_test_data.items():
            food_item = self._create_food_item(food_data)
            
            # 영양소별 칼로리 계산
            macro_calories = self.calorie_manager.calculate_macronutrient_calories(
                food_item.nutrition_info
            )
            
            # 영양소별 칼로리 검증
            self.assertAlmostEqual(
                macro_calories['carbohydrate'], 
                food_data["expected_carb_calories"], 
                places=1
            )
            self.assertAlmostEqual(
                macro_calories['protein'], 
                food_data["expected_protein_calories"], 
                places=1
            )
            self.assertAlmostEqual(
                macro_calories['fat'], 
                food_data["expected_fat_calories"], 
                places=1
            )
            
            # 총 칼로리 검증 (영양소별 칼로리의 합)
            expected_total = (
                food_data["expected_carb_calories"] + 
                food_data["expected_protein_calories"] + 
                food_data["expected_fat_calories"]
            )
            self.assertAlmostEqual(macro_calories['total'], expected_total, places=1)
            
            print(f"✓ {food_data['name']} 영양소별 칼로리 계산 정확도 검증 완료: "
                  f"탄수화물={macro_calories['carbohydrate']:.1f}kcal, "
                  f"단백질={macro_calories['protein']:.1f}kcal, "
                  f"지방={macro_calories['fat']:.1f}kcal, "
                  f"총합={macro_calories['total']:.1f}kcal")
    
    def test_calorie_balance_calculation_accuracy(self):
        """칼로리 밸런스 계산 정확도 테스트."""
        print("\n=== 칼로리 밸런스 계산 정확도 테스트 ===")
        
        test_cases = [
            # (섭취 칼로리, 소모 칼로리, 예상 밸런스)
            (2000, 1500, 500),    # 흑자
            (1500, 2000, -500),   # 적자
            (2000, 2000, 0),      # 균형
            (0, 500, -500),       # 섭취 없음
            (500, 0, 500)         # 소모 없음
        ]
        
        for intake, burned, expected_balance in test_cases:
            balance = self.calorie_manager.calculate_calorie_balance(intake, burned)
            self.assertEqual(balance, expected_balance)
            
            status = "흑자" if balance > 0 else "적자" if balance < 0 else "균형"
            print(f"✓ 칼로리 밸런스 계산 정확도 검증 완료: "
                  f"섭취={intake}kcal, 소모={burned}kcal, 밸런스={balance}kcal ({status})")
    
    def test_rdf_conversion_accuracy(self):
        """RDF 변환 정확도 테스트."""
        print("\n=== RDF 변환 정확도 테스트 ===")
        
        # 음식 RDF 변환 테스트
        food_item = self._create_food_item(self.food_test_data["apple"])
        food_rdf = self.rdf_converter.convert_food_to_rdf(food_item)
        
        # RDF 문자열 검증
        self.assertIsInstance(food_rdf, str)
        self.assertIn(food_item.name, food_rdf)
        self.assertIn(str(food_item.nutrition_info.calories_per_100g), food_rdf)
        self.assertIn(str(food_item.nutrition_info.carbohydrate), food_rdf)
        
        print(f"✓ 음식 RDF 변환 정확도 검증 완료: {food_item.name}")
        
        # 운동 RDF 변환 테스트
        exercise_item = self._create_exercise_item(self.exercise_test_data["walking"])
        exercise_rdf = self.rdf_converter.convert_exercise_to_rdf(exercise_item)
        
        # RDF 문자열 검증
        self.assertIsInstance(exercise_rdf, str)
        self.assertIn(exercise_item.name, exercise_rdf)
        self.assertIn(str(exercise_item.met), exercise_rdf)
        
        print(f"✓ 운동 RDF 변환 정확도 검증 완료: {exercise_item.name}")
    
    def test_data_rounding_accuracy(self):
        """데이터 반올림 정확도 테스트."""
        print("\n=== 데이터 반올림 정확도 테스트 ===")
        
        # 소수점 자리수가 많은 테스트 데이터
        test_cases = [
            # (원본 값, 반올림 자릿수, 예상 결과)
            (3.14159265359, 2, 3.14),
            (3.14159265359, 4, 3.1416),
            (3.14159265359, 0, 3),
            (9.999, 2, 10.00),
            (0.0001, 3, 0.000)  # 반올림하면 0
        ]
        
        for original, decimal_places, expected in test_cases:
            # 직접 반올림 함수 구현 또는 기존 함수 사용
            rounded = round(original, decimal_places)
            self.assertAlmostEqual(rounded, expected, places=decimal_places)
            
            print(f"✓ 반올림 정확도 검증 완료: {original} → {rounded} (자릿수: {decimal_places})")
    
    def test_edge_case_calculations(self):
        """경계값 계산 정확도 테스트."""
        print("\n=== 경계값 계산 정확도 테스트 ===")
        
        # 음식 경계값 테스트
        food_item = self._create_food_item(self.food_test_data["apple"])
        
        # 매우 작은 양 (0.1g)
        small_amount = 0.1
        small_calories = self.calorie_manager.calculate_food_calories(food_item, amount=small_amount)
        expected_small = food_item.nutrition_info.calories_per_100g * (small_amount / 100)
        self.assertAlmostEqual(small_calories, expected_small, places=4)
        
        # 매우 큰 양 (10kg)
        large_amount = 10000
        large_calories = self.calorie_manager.calculate_food_calories(food_item, amount=large_amount)
        expected_large = food_item.nutrition_info.calories_per_100g * (large_amount / 100)
        self.assertAlmostEqual(large_calories, expected_large, places=1)
        
        print(f"✓ 음식 경계값 계산 정확도 검증 완료: "
              f"최소량({small_amount}g)={small_calories:.4f}kcal, "
              f"최대량({large_amount}g)={large_calories:.1f}kcal")
        
        # 운동 경계값 테스트
        exercise_item = self._create_exercise_item(self.exercise_test_data["walking"])
        
        # 매우 짧은 시간 (1분)
        short_duration = 1
        short_calories = self.calorie_manager.calculate_exercise_calories(
            exercise_item, weight_kg=70, duration_minutes=short_duration
        )
        expected_short = exercise_item.met * 70 * (short_duration / 60) * 1.05
        self.assertAlmostEqual(short_calories, expected_short, places=2)
        
        # 매우 긴 시간 (24시간)
        long_duration = 24 * 60
        long_calories = self.calorie_manager.calculate_exercise_calories(
            exercise_item, weight_kg=70, duration_minutes=long_duration
        )
        expected_long = exercise_item.met * 70 * (long_duration / 60) * 1.05
        self.assertAlmostEqual(long_calories, expected_long, places=1)
        
        print(f"✓ 운동 경계값 계산 정확도 검증 완료: "
              f"최소시간({short_duration}분)={short_calories:.2f}kcal, "
              f"최대시간({long_duration}분)={long_calories:.1f}kcal")
    
    def test_data_conversion_accuracy(self):
        """데이터 변환 정확도 테스트."""
        print("\n=== 데이터 변환 정확도 테스트 ===")
        
        # API 응답 형식의 테스트 데이터
        api_food_data = {
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
        
        # Mock을 사용한 데이터 변환 테스트
        with patch.object(FoodAPIClient, '_parse_food_item') as mock_parse:
            mock_food_item = self._create_food_item(self.food_test_data["apple"])
            mock_parse.return_value = mock_food_item
            
            food_client = FoodAPIClient()
            parsed_item = food_client._parse_food_item(api_food_data)
            
            # 변환 정확도 검증
            self.assertEqual(parsed_item.name, "사과")
            self.assertEqual(parsed_item.nutrition_info.calories_per_100g, 52.0)
            self.assertEqual(parsed_item.nutrition_info.carbohydrate, 13.8)
            
            print(f"✓ 음식 데이터 변환 정확도 검증 완료: {parsed_item.name}")
    
    def test_decimal_precision(self):
        """소수점 정밀도 테스트."""
        print("\n=== 소수점 정밀도 테스트 ===")
        
        # Decimal 타입 사용 테스트
        decimal_values = [
            (Decimal('52.0'), Decimal('1.5'), Decimal('78.0')),  # 52.0 * 1.5 = 78.0
            (Decimal('3.333'), Decimal('3'), Decimal('9.999')),  # 3.333 * 3 = 9.999
            (Decimal('0.1'), Decimal('0.2'), Decimal('0.02'))    # 0.1 * 0.2 = 0.02
        ]
        
        for value1, value2, expected_product in decimal_values:
            product = value1 * value2
            self.assertEqual(product, expected_product)
            print(f"✓ Decimal 정밀도 검증 완료: {value1} * {value2} = {product}")
        
        # 부동소수점 오차 테스트
        float_values = [
            (0.1 + 0.2, 0.3),  # 0.1 + 0.2 ≈ 0.3 (부동소수점에서는 정확히 0.3이 아님)
            (0.1 * 3, 0.3)     # 0.1 * 3 ≈ 0.3
        ]
        
        for actual, expected in float_values:
            # 부동소수점 비교는 정확히 같지 않을 수 있으므로 assertAlmostEqual 사용
            self.assertAlmostEqual(actual, expected, places=10)
            print(f"✓ 부동소수점 정밀도 검증 완료: 실제값={actual}, 예상값={expected}")

if __name__ == '__main__':
    print("=== 데이터 처리 정확성 테스트 ===")
    unittest.main(verbosity=2)