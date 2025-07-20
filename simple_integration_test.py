"""
간단한 API 연동 통합 테스트.
실제 구현된 모듈들을 사용한 통합 테스트입니다.
"""

import unittest
import time
from unittest.mock import Mock, patch
from calorie_manager import CalorieManager
from integrated_models import FoodItem, ExerciseItem, NutritionInfo
from exceptions import DataValidationError


class SimpleIntegrationTest(unittest.TestCase):
    """간단한 통합 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        self.calorie_manager = CalorieManager()
    
    def test_food_calorie_calculation_integration(self):
        """음식 칼로리 계산 통합 테스트."""
        # 테스트 음식 데이터 생성
        nutrition = NutritionInfo(
            calories_per_100g=52.0,
            carbohydrate=13.8,
            protein=0.3,
            fat=0.2,
            fiber=2.4,
            sodium=1.0
        )
        
        food_item = FoodItem(
            id="apple_001",
            name="사과",
            nutrition_info=nutrition,
            serving_size=100,
            category="과일류",
            manufacturer="자연산"
        )
        
        # 칼로리 계산 (150g)
        calories = self.calorie_manager.calculate_food_calories(food_item, amount=150)
        expected_calories = 52.0 * 1.5  # 78.0
        
        self.assertEqual(calories, expected_calories)
        print(f"음식 칼로리 계산: {food_item.name} {150}g = {calories}kcal")
    
    def test_exercise_calorie_calculation_integration(self):
        """운동 칼로리 계산 통합 테스트."""
        # 테스트 운동 데이터 생성
        exercise_item = ExerciseItem(
            id="walking_001",
            name="걷기",
            met=3.5,
            description="일반적인 걷기 운동",
            category="유산소운동",
            intensity="중간"
        )
        
        # 칼로리 소모 계산 (70kg, 30분)
        burned_calories = self.calorie_manager.calculate_exercise_calories(
            exercise_item, weight_kg=70, duration_minutes=30
        )
        expected_calories = 3.5 * 70 * 0.5 * 1.05  # 128.625
        
        self.assertAlmostEqual(burned_calories, expected_calories, places=2)
        print(f"운동 칼로리 계산: {exercise_item.name} 30분 = {burned_calories:.1f}kcal")
    
    def test_calorie_balance_integration(self):
        """칼로리 밸런스 통합 테스트."""
        # 음식 데이터
        nutrition = NutritionInfo(
            calories_per_100g=250,
            carbohydrate=30,
            protein=10,
            fat=12,
            fiber=5,
            sodium=200
        )
        
        food_item = FoodItem(
            id="rice_001",
            name="밥",
            nutrition_info=nutrition,
            serving_size=100,
            category="곡류",
            manufacturer="일반"
        )
        
        # 운동 데이터
        exercise_item = ExerciseItem(
            id="running_001",
            name="달리기",
            met=8.0,
            description="일반적인 달리기",
            category="유산소운동",
            intensity="높음"
        )
        
        # 칼로리 계산
        food_calories = self.calorie_manager.calculate_food_calories(food_item, amount=200)  # 500kcal
        exercise_calories = self.calorie_manager.calculate_exercise_calories(
            exercise_item, weight_kg=70, duration_minutes=30
        )  # 8.0 * 70 * 0.5 * 1.05 = 294kcal
        
        # 칼로리 밸런스
        balance = self.calorie_manager.calculate_calorie_balance(food_calories, exercise_calories)
        expected_balance = food_calories - exercise_calories
        
        self.assertEqual(balance, expected_balance)
        print(f"칼로리 밸런스: 섭취 {food_calories}kcal - 소모 {exercise_calories:.1f}kcal = {balance:.1f}kcal")
    
    def test_goal_achievement_integration(self):
        """목표 달성률 통합 테스트."""
        # 목표: 500kcal 적자
        target_deficit = -500
        
        # 실제: 600kcal 적자
        actual_balance = -600
        
        # 목표 달성률 계산
        achievement = self.calorie_manager.calculate_goal_achievement(target_deficit, actual_balance)
        expected_achievement = 120.0  # 120% 달성
        
        self.assertEqual(achievement, expected_achievement)
        print(f"목표 달성률: 목표 {target_deficit}kcal, 실제 {actual_balance}kcal = {achievement}% 달성")
    
    def test_macronutrient_analysis_integration(self):
        """영양소 분석 통합 테스트."""
        # 균형 잡힌 영양소 데이터
        nutrition = NutritionInfo(
            calories_per_100g=400,
            carbohydrate=50,  # 200kcal (50%)
            protein=25,       # 100kcal (25%)
            fat=11.11,        # 100kcal (25%)
            fiber=10,
            sodium=300
        )
        
        # 영양소별 칼로리 계산
        macro_calories = self.calorie_manager.calculate_macronutrient_calories(nutrition)
        
        self.assertAlmostEqual(macro_calories['carbohydrate'], 200, places=1)
        self.assertAlmostEqual(macro_calories['protein'], 100, places=1)
        self.assertAlmostEqual(macro_calories['fat'], 100, places=1)
        self.assertAlmostEqual(macro_calories['total'], 400, places=1)
        
        # 영양소 비율 계산
        macro_ratio = self.calorie_manager.calculate_macronutrient_ratio(nutrition)
        
        self.assertAlmostEqual(macro_ratio['carbohydrate'], 50.0, places=1)
        self.assertAlmostEqual(macro_ratio['protein'], 25.0, places=1)
        self.assertAlmostEqual(macro_ratio['fat'], 25.0, places=1)
        
        print(f"영양소 비율: 탄수화물 {macro_ratio['carbohydrate']:.1f}%, "
              f"단백질 {macro_ratio['protein']:.1f}%, 지방 {macro_ratio['fat']:.1f}%")
    
    def test_response_time_requirement(self):
        """응답 시간 요구사항 테스트 (3초 이하)."""
        # 복잡한 계산 시뮬레이션
        nutrition = NutritionInfo(
            calories_per_100g=300,
            carbohydrate=40,
            protein=20,
            fat=15,
            fiber=8,
            sodium=250
        )
        
        food_item = FoodItem(
            id="complex_food",
            name="복합 음식",
            nutrition_info=nutrition,
            serving_size=100,
            category="복합식품",
            manufacturer="테스트"
        )
        
        exercise_item = ExerciseItem(
            id="complex_exercise",
            name="복합 운동",
            met=6.0,
            description="복합 운동",
            category="복합운동",
            intensity="중간"
        )
        
        # 응답 시간 측정
        start_time = time.time()
        
        # 여러 계산 수행
        for i in range(100):
            food_calories = self.calorie_manager.calculate_food_calories(food_item, amount=100 + i)
            exercise_calories = self.calorie_manager.calculate_exercise_calories(
                exercise_item, weight_kg=70, duration_minutes=30 + i
            )
            balance = self.calorie_manager.calculate_calorie_balance(food_calories, exercise_calories)
            macro_calories = self.calorie_manager.calculate_macronutrient_calories(nutrition)
            macro_ratio = self.calorie_manager.calculate_macronutrient_ratio(nutrition)
        
        response_time = time.time() - start_time
        
        # 3초 이하 검증
        self.assertLess(response_time, 3.0, f"응답 시간이 3초를 초과했습니다: {response_time:.3f}초")
        print(f"100회 복합 계산 응답 시간: {response_time:.3f}초 (< 3초)")
    
    def test_error_handling_integration(self):
        """오류 처리 통합 테스트."""
        # 잘못된 음식 데이터
        invalid_nutrition = NutritionInfo(
            calories_per_100g=None,  # 잘못된 칼로리 값
            carbohydrate=10,
            protein=5,
            fat=3,
            fiber=2,
            sodium=100
        )
        
        invalid_food = FoodItem(
            id="invalid_food",
            name="잘못된 음식",
            nutrition_info=invalid_nutrition,
            serving_size=100,
            category="테스트",
            manufacturer="테스트"
        )
        
        # 오류 발생 확인
        with self.assertRaises(DataValidationError):
            self.calorie_manager.calculate_food_calories(invalid_food)
        
        # 잘못된 운동 데이터
        invalid_exercise = ExerciseItem(
            id="invalid_exercise",
            name="잘못된 운동",
            met=None,  # 잘못된 MET 값
            description="잘못된 운동",
            category="테스트",
            intensity="테스트"
        )
        
        # 오류 발생 확인
        with self.assertRaises(DataValidationError):
            self.calorie_manager.calculate_exercise_calories(invalid_exercise)
        
        print("오류 처리 테스트: 잘못된 데이터에 대해 적절한 예외 발생 확인")
    
    def test_data_validation_integration(self):
        """데이터 검증 통합 테스트."""
        # 유효한 데이터
        valid_nutrition = NutritionInfo(
            calories_per_100g=200,
            carbohydrate=25,
            protein=15,
            fat=8,
            fiber=5,
            sodium=150
        )
        
        valid_food = FoodItem(
            id="valid_food",
            name="유효한 음식",
            nutrition_info=valid_nutrition,
            serving_size=100,
            category="테스트",
            manufacturer="테스트"
        )
        
        # 정상 계산 확인
        calories = self.calorie_manager.calculate_food_calories(valid_food, amount=100)
        self.assertEqual(calories, 200)
        
        # 경계값 테스트
        edge_cases = [
            (0.1, "최소 양"),
            (1000, "최대 양"),
            (50.5, "소수점 양")
        ]
        
        for amount, description in edge_cases:
            try:
                result = self.calorie_manager.calculate_food_calories(valid_food, amount=amount)
                expected = 200 * (amount / 100)
                self.assertAlmostEqual(result, expected, places=2)
                print(f"경계값 테스트 통과: {description} ({amount}g) = {result}kcal")
            except Exception as e:
                self.fail(f"경계값 테스트 실패: {description} - {str(e)}")


if __name__ == '__main__':
    print("=== 간단한 API 연동 통합 테스트 ===")
    unittest.main(verbosity=2)