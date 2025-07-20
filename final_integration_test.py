"""
최종 API 연동 통합 테스트.
실제 구현된 모듈들을 사용한 통합 테스트입니다.
"""

import unittest
import time
from calorie_manager import CalorieManager
from integrated_models import FoodItem, ExerciseItem, NutritionInfo
from exceptions import DataValidationError


class FinalIntegrationTest(unittest.TestCase):
    """최종 통합 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        self.calorie_manager = CalorieManager()
    
    def test_food_calorie_calculation_integration(self):
        """음식 칼로리 계산 통합 테스트."""
        # 실제 모델 구조에 맞는 테스트 음식 데이터 생성
        food_item = FoodItem(
            name="사과",
            food_id="apple_001",
            category="과일류",
            manufacturer="자연산"
        )
        
        # 영양 정보 생성
        nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=52.0,
            carbohydrate=13.8,
            protein=0.3,
            fat=0.2,
            fiber=2.4,
            sodium=1.0
        )
        
        # 음식 아이템에 영양 정보 연결
        food_item.nutrition_info = nutrition
        
        # 칼로리 계산 (150g)
        calories = self.calorie_manager.calculate_food_calories(food_item, amount=150)
        expected_calories = 52.0 * 1.5  # 78.0
        
        self.assertEqual(calories, expected_calories)
        print(f"✅ 음식 칼로리 계산: {food_item.name} {150}g = {calories}kcal")
    
    def test_exercise_calorie_calculation_integration(self):
        """운동 칼로리 계산 통합 테스트."""
        # 실제 모델 구조에 맞는 테스트 운동 데이터 생성
        exercise_item = ExerciseItem(
            name="걷기",
            exercise_id="walking_001",
            met=3.5,
            description="일반적인 걷기 운동",
            category="유산소운동"
        )
        
        # 칼로리 소모 계산 (70kg, 30분)
        burned_calories = self.calorie_manager.calculate_exercise_calories(
            exercise_item, weight_kg=70, duration_minutes=30
        )
        expected_calories = 3.5 * 70 * 0.5 * 1.05  # 128.625
        
        self.assertAlmostEqual(burned_calories, expected_calories, places=2)
        print(f"✅ 운동 칼로리 계산: {exercise_item.name} 30분 = {burned_calories:.1f}kcal")
    
    def test_calorie_balance_integration(self):
        """칼로리 밸런스 통합 테스트."""
        # 음식 데이터
        food_item = FoodItem(
            name="밥",
            food_id="rice_001",
            category="곡류",
            manufacturer="일반"
        )
        
        nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=250,
            carbohydrate=30,
            protein=10,
            fat=12,
            fiber=5,
            sodium=200
        )
        
        food_item.nutrition_info = nutrition
        
        # 운동 데이터
        exercise_item = ExerciseItem(
            name="달리기",
            exercise_id="running_001",
            met=8.0,
            description="일반적인 달리기",
            category="유산소운동"
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
        print(f"✅ 칼로리 밸런스: 섭취 {food_calories}kcal - 소모 {exercise_calories:.1f}kcal = {balance:.1f}kcal")
    
    def test_macronutrient_analysis_integration(self):
        """영양소 분석 통합 테스트."""
        # 균형 잡힌 영양소 데이터
        food_item = FoodItem(
            name="균형식품",
            food_id="balanced_001",
            category="복합식품",
            manufacturer="테스트"
        )
        
        nutrition = NutritionInfo(
            food_item=food_item,
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
        
        print(f"✅ 영양소 비율: 탄수화물 {macro_ratio['carbohydrate']:.1f}%, "
              f"단백질 {macro_ratio['protein']:.1f}%, 지방 {macro_ratio['fat']:.1f}%")
    
    def test_response_time_requirement(self):
        """응답 시간 요구사항 테스트 (3초 이하)."""
        # 복잡한 계산 시뮬레이션
        food_item = FoodItem(
            name="복합 음식",
            food_id="complex_food",
            category="복합식품",
            manufacturer="테스트"
        )
        
        nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=300,
            carbohydrate=40,
            protein=20,
            fat=15,
            fiber=8,
            sodium=250
        )
        
        food_item.nutrition_info = nutrition
        
        exercise_item = ExerciseItem(
            name="복합 운동",
            exercise_id="complex_exercise",
            met=6.0,
            description="복합 운동",
            category="복합운동"
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
        print(f"✅ 100회 복합 계산 응답 시간: {response_time:.3f}초 (< 3초)")
    
    def test_error_handling_integration(self):
        """오류 처리 통합 테스트."""
        # 잘못된 음식 데이터
        food_item = FoodItem(
            name="잘못된 음식",
            food_id="invalid_food",
            category="테스트",
            manufacturer="테스트"
        )
        
        invalid_nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=None,  # 잘못된 칼로리 값
            carbohydrate=10,
            protein=5,
            fat=3,
            fiber=2,
            sodium=100
        )
        
        food_item.nutrition_info = invalid_nutrition
        
        # 오류 발생 확인
        with self.assertRaises(DataValidationError):
            self.calorie_manager.calculate_food_calories(food_item)
        
        # 잘못된 운동 데이터
        invalid_exercise = ExerciseItem(
            name="잘못된 운동",
            exercise_id="invalid_exercise",
            met=None,  # 잘못된 MET 값
            description="잘못된 운동",
            category="테스트"
        )
        
        # 오류 발생 확인
        with self.assertRaises(DataValidationError):
            self.calorie_manager.calculate_exercise_calories(invalid_exercise)
        
        print("✅ 오류 처리 테스트: 잘못된 데이터에 대해 적절한 예외 발생 확인")
    
    def test_data_validation_integration(self):
        """데이터 검증 통합 테스트."""
        # 유효한 데이터
        food_item = FoodItem(
            name="유효한 음식",
            food_id="valid_food",
            category="테스트",
            manufacturer="테스트"
        )
        
        valid_nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=200,
            carbohydrate=25,
            protein=15,
            fat=8,
            fiber=5,
            sodium=150
        )
        
        food_item.nutrition_info = valid_nutrition
        
        # 정상 계산 확인
        calories = self.calorie_manager.calculate_food_calories(food_item, amount=100)
        self.assertEqual(calories, 200)
        
        # 경계값 테스트
        edge_cases = [
            (0.1, "최소 양"),
            (1000, "최대 양"),
            (50.5, "소수점 양")
        ]
        
        for amount, description in edge_cases:
            try:
                result = self.calorie_manager.calculate_food_calories(food_item, amount=amount)
                expected = 200 * (amount / 100)
                self.assertAlmostEqual(result, expected, places=2)
                print(f"✅ 경계값 테스트 통과: {description} ({amount}g) = {result}kcal")
            except Exception as e:
                self.fail(f"경계값 테스트 실패: {description} - {str(e)}")
    
    def test_concurrent_processing_simulation(self):
        """동시 처리 시뮬레이션 테스트."""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def process_calculation(thread_id):
            """개별 계산 처리."""
            try:
                # 음식 데이터 생성
                food_item = FoodItem(
                    name=f"음식{thread_id}",
                    food_id=f"food_{thread_id}",
                    category="테스트",
                    manufacturer="테스트"
                )
                
                nutrition = NutritionInfo(
                    food_item=food_item,
                    calories_per_100g=100 + thread_id,
                    carbohydrate=20,
                    protein=10,
                    fat=5,
                    fiber=3,
                    sodium=100
                )
                
                food_item.nutrition_info = nutrition
                
                # 운동 데이터 생성
                exercise_item = ExerciseItem(
                    name=f"운동{thread_id}",
                    exercise_id=f"exercise_{thread_id}",
                    met=3.0 + (thread_id * 0.1),
                    description=f"테스트 운동 {thread_id}",
                    category="테스트"
                )
                
                # 계산 수행
                food_calories = self.calorie_manager.calculate_food_calories(food_item, amount=100)
                exercise_calories = self.calorie_manager.calculate_exercise_calories(
                    exercise_item, weight_kg=70, duration_minutes=30
                )
                balance = self.calorie_manager.calculate_calorie_balance(food_calories, exercise_calories)
                
                results.put(f"스레드 {thread_id}: 밸런스 {balance:.1f}kcal")
                
            except Exception as e:
                errors.put(f"스레드 {thread_id} 오류: {str(e)}")
        
        # 10개의 동시 계산 스레드 생성
        threads = []
        for i in range(10):
            thread = threading.Thread(target=process_calculation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 확인
        success_count = results.qsize()
        error_count = errors.qsize()
        
        self.assertEqual(error_count, 0, f"동시 처리 중 오류 발생: {error_count}개")
        self.assertEqual(success_count, 10, f"성공한 처리: {success_count}개")
        
        print(f"✅ 동시 처리 테스트: {success_count}개 성공, {error_count}개 실패")


if __name__ == '__main__':
    print("=== 최종 API 연동 통합 테스트 ===")
    unittest.main(verbosity=2)