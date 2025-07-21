"""
데이터 처리 정확성 테스트 데모 스크립트.
이 스크립트는 데이터 처리 정확성 테스트의 기능을 시연합니다.
"""

import time
import logging
from decimal import Decimal, getcontext

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Decimal 정밀도 설정
getcontext().prec = 28

def test_food_calorie_calculation():
    """음식 칼로리 계산 정확도 테스트."""
    print("\n=== 음식 칼로리 계산 정확도 테스트 ===")
    
    # 테스트 데이터
    test_foods = [
        {"name": "사과", "calories_per_100g": 52.0, "amount": 150, "expected": 78.0},
        {"name": "바나나", "calories_per_100g": 89.0, "amount": 120, "expected": 106.8},
        {"name": "닭가슴살", "calories_per_100g": 165.0, "amount": 200, "expected": 330.0},
        {"name": "현미밥", "calories_per_100g": 130.0, "amount": 210, "expected": 273.0},
        {"name": "아보카도", "calories_per_100g": 160.0, "amount": 50, "expected": 80.0}
    ]
    
    for food in test_foods:
        # 칼로리 계산
        calculated = food["calories_per_100g"] * (food["amount"] / 100)
        
        # 정확도 검증
        is_accurate = abs(calculated - food["expected"]) < 0.1
        status = "✓" if is_accurate else "✗"
        
        print(f"{status} {food['name']} ({food['amount']}g): "
              f"계산값={calculated:.1f}kcal, 예상값={food['expected']}kcal")

def test_exercise_calorie_calculation():
    """운동 칼로리 계산 정확도 테스트."""
    print("\n=== 운동 칼로리 계산 정확도 테스트 ===")
    
    # 테스트 데이터
    test_exercises = [
        {"name": "걷기", "met": 3.5, "weight": 70, "duration": 30, "expected": 128.6},
        {"name": "달리기", "met": 8.0, "weight": 70, "duration": 30, "expected": 294.0},
        {"name": "수영", "met": 6.0, "weight": 70, "duration": 30, "expected": 220.5},
        {"name": "자전거", "met": 4.0, "weight": 70, "duration": 30, "expected": 147.0},
        {"name": "요가", "met": 2.5, "weight": 70, "duration": 30, "expected": 91.9}
    ]
    
    for exercise in test_exercises:
        # 칼로리 계산: MET * 체중(kg) * 시간(시간) * 1.05
        hours = exercise["duration"] / 60
        calculated = exercise["met"] * exercise["weight"] * hours * 1.05
        
        # 정확도 검증
        is_accurate = abs(calculated - exercise["expected"]) < 0.1
        status = "✓" if is_accurate else "✗"
        
        print(f"{status} {exercise['name']} ({exercise['duration']}분): "
              f"계산값={calculated:.1f}kcal, 예상값={exercise['expected']}kcal")

def test_macronutrient_calculation():
    """영양소별 칼로리 계산 정확도 테스트."""
    print("\n=== 영양소별 칼로리 계산 정확도 테스트 ===")
    
    # 테스트 데이터 (100g 기준)
    test_foods = [
        {
            "name": "닭가슴살",
            "carbohydrate": 0.0,
            "protein": 31.0,
            "fat": 3.6,
            "expected_carb": 0.0,    # 0.0g * 4kcal/g
            "expected_protein": 124.0,  # 31.0g * 4kcal/g
            "expected_fat": 32.4,    # 3.6g * 9kcal/g
            "expected_total": 156.4
        },
        {
            "name": "현미밥",
            "carbohydrate": 28.0,
            "protein": 2.7,
            "fat": 0.3,
            "expected_carb": 112.0,  # 28.0g * 4kcal/g
            "expected_protein": 10.8,   # 2.7g * 4kcal/g
            "expected_fat": 2.7,     # 0.3g * 9kcal/g
            "expected_total": 125.5
        }
    ]
    
    for food in test_foods:
        # 영양소별 칼로리 계산
        carb_calories = food["carbohydrate"] * 4
        protein_calories = food["protein"] * 4
        fat_calories = food["fat"] * 9
        total_calories = carb_calories + protein_calories + fat_calories
        
        # 정확도 검증
        carb_accurate = abs(carb_calories - food["expected_carb"]) < 0.1
        protein_accurate = abs(protein_calories - food["expected_protein"]) < 0.1
        fat_accurate = abs(fat_calories - food["expected_fat"]) < 0.1
        total_accurate = abs(total_calories - food["expected_total"]) < 0.1
        
        carb_status = "✓" if carb_accurate else "✗"
        protein_status = "✓" if protein_accurate else "✗"
        fat_status = "✓" if fat_accurate else "✗"
        total_status = "✓" if total_accurate else "✗"
        
        print(f"{food['name']}:")
        print(f"  {carb_status} 탄수화물: {carb_calories:.1f}kcal (예상: {food['expected_carb']}kcal)")
        print(f"  {protein_status} 단백질: {protein_calories:.1f}kcal (예상: {food['expected_protein']}kcal)")
        print(f"  {fat_status} 지방: {fat_calories:.1f}kcal (예상: {food['expected_fat']}kcal)")
        print(f"  {total_status} 총합: {total_calories:.1f}kcal (예상: {food['expected_total']}kcal)")

def test_calorie_balance():
    """칼로리 밸런스 계산 테스트."""
    print("\n=== 칼로리 밸런스 계산 테스트 ===")
    
    test_cases = [
        {"intake": 2000, "burned": 1500, "expected": 500, "status": "흑자"},
        {"intake": 1500, "burned": 2000, "expected": -500, "status": "적자"},
        {"intake": 2000, "burned": 2000, "expected": 0, "status": "균형"},
        {"intake": 0, "burned": 500, "expected": -500, "status": "적자"},
        {"intake": 500, "burned": 0, "expected": 500, "status": "흑자"}
    ]
    
    for case in test_cases:
        balance = case["intake"] - case["burned"]
        is_accurate = balance == case["expected"]
        status = "✓" if is_accurate else "✗"
        
        print(f"{status} 섭취: {case['intake']}kcal, 소모: {case['burned']}kcal "
              f"→ 밸런스: {balance}kcal ({case['status']})")

def test_decimal_precision():
    """소수점 정밀도 테스트."""
    print("\n=== 소수점 정밀도 테스트 ===")
    
    # Decimal 타입 테스트
    decimal_tests = [
        (Decimal('52.0'), Decimal('1.5'), Decimal('78.0')),
        (Decimal('3.333'), Decimal('3'), Decimal('9.999')),
        (Decimal('0.1'), Decimal('0.2'), Decimal('0.02'))
    ]
    
    for val1, val2, expected in decimal_tests:
        result = val1 * val2
        is_accurate = result == expected
        status = "✓" if is_accurate else "✗"
        
        print(f"{status} Decimal: {val1} × {val2} = {result} (예상: {expected})")
    
    # 부동소수점 정밀도 테스트
    float_tests = [
        (0.1 + 0.2, 0.3, "0.1 + 0.2"),
        (0.1 * 3, 0.3, "0.1 × 3")
    ]
    
    for actual, expected, description in float_tests:
        is_close = abs(actual - expected) < 1e-10
        status = "✓" if is_close else "✗"
        
        print(f"{status} Float: {description} = {actual:.15f} (예상: {expected})")

def test_edge_cases():
    """경계값 테스트."""
    print("\n=== 경계값 테스트 ===")
    
    # 매우 작은 값
    small_tests = [
        {"value": 0.001, "multiplier": 100, "expected": 0.1},
        {"value": 0.0001, "multiplier": 1000, "expected": 0.1}
    ]
    
    for test in small_tests:
        result = test["value"] * test["multiplier"]
        is_accurate = abs(result - test["expected"]) < 0.001
        status = "✓" if is_accurate else "✗"
        
        print(f"{status} 소수값: {test['value']} × {test['multiplier']} = {result:.4f}")
    
    # 매우 큰 값
    large_tests = [
        {"value": 10000, "multiplier": 0.52, "expected": 5200},
        {"value": 50000, "multiplier": 0.165, "expected": 8250}
    ]
    
    for test in large_tests:
        result = test["value"] * test["multiplier"]
        is_accurate = abs(result - test["expected"]) < 1
        status = "✓" if is_accurate else "✗"
        
        print(f"{status} 대용량: {test['value']} × {test['multiplier']} = {result:.0f}")

def main():
    """메인 함수."""
    print("=" * 60)
    print("데이터 처리 정확성 테스트 데모")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        test_food_calorie_calculation()
        test_exercise_calorie_calculation()
        test_macronutrient_calculation()
        test_calorie_balance()
        test_decimal_precision()
        test_edge_cases()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print("\n" + "=" * 60)
        print(f"모든 테스트 완료! 소요 시간: {elapsed_time:.2f}초")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
        logging.error(f"테스트 실행 오류: {e}", exc_info=True)

if __name__ == "__main__":
    main()