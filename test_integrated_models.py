"""
통합 데이터 모델 테스트 모듈.
"""

from datetime import datetime, date
from rdflib import Namespace
from integrated_models import (
    FoodItem, NutritionInfo, FoodConsumption,
    ExerciseItem, ExerciseSession,
    NetCalorieResult, DailyAnalysis
)
import traceback


def test_food_and_exercise_integration():
    """음식과 운동 데이터 통합 테스트."""
    print("=== 음식과 운동 데이터 통합 테스트 ===")
    
    namespace = Namespace("http://example.org/diet#")
    
    try:
        # 음식 데이터 생성
        food = FoodItem("닭가슴살", "FOOD001", "육류")
        nutrition = NutritionInfo(
            food_item=food,
            calories_per_100g=165.0,
            carbohydrate=0.0,
            protein=31.0,
            fat=3.6
        )
        
        # 음식 섭취 기록 (200g)
        consumption = FoodConsumption.create_with_calculation(
            food_item=food,
            nutrition=nutrition,
            amount=200.0,
            namespace=namespace
        )
        
        # 운동 데이터 생성
        exercise = ExerciseItem(
            name="달리기",
            description="일반적인 달리기 운동",
            met_value=8.0,
            category="유산소"
        )
        
        # 운동 세션 기록 (70kg, 30분)
        session = ExerciseSession.create_with_calculation(
            exercise_item=exercise,
            weight=70.0,
            duration=30.0,
            namespace=namespace
        )
        
        print(f"✓ 음식 섭취: {consumption.amount_grams}g {food.name} = {consumption.calories_consumed}kcal")
        print(f"✓ 운동 수행: {session.duration}분 {exercise.name} = {session.calories_burned}kcal 소모")
        
        # 순 칼로리 계산
        net_calories = consumption.calories_consumed - session.calories_burned
        print(f"✓ 순 칼로리: {consumption.calories_consumed} - {session.calories_burned} = {net_calories}kcal")
        
        return consumption, session
        
    except Exception as e:
        print(f"✗ 통합 테스트 실패: {e}")
        traceback.print_exc()
        return None, None


def test_net_calorie_calculation():
    """순 칼로리 계산 테스트."""
    print("\n=== 순 칼로리 계산 테스트 ===")
    
    namespace = Namespace("http://example.org/diet#")
    today = date.today()
    
    try:
        # 여러 음식 섭취 기록
        foods_data = [
            {"name": "백미밥", "id": "F001", "calories": 130, "amount": 200},  # 260kcal
            {"name": "김치찌개", "id": "F002", "calories": 45, "amount": 300},   # 135kcal
            {"name": "사과", "id": "F003", "calories": 52, "amount": 150}        # 78kcal
        ]
        
        consumptions = []
        total_consumed = 0
        
        for food_data in foods_data:
            food = FoodItem(food_data["name"], food_data["id"], "일반")
            nutrition = NutritionInfo(
                food_item=food,
                calories_per_100g=food_data["calories"],
                carbohydrate=20.0,  # 임시값
                protein=5.0,        # 임시값
                fat=2.0            # 임시값
            )
            
            consumption = FoodConsumption.create_with_calculation(
                food_item=food,
                nutrition=nutrition,
                amount=food_data["amount"],
                namespace=namespace
            )
            
            consumptions.append(consumption)
            total_consumed += consumption.calories_consumed
            print(f"  - {food.name} {food_data['amount']}g: {consumption.calories_consumed:.1f}kcal")
        
        # 여러 운동 세션 기록
        exercises_data = [
            {"name": "달리기", "met": 8.0, "duration": 30},      # 280kcal (70kg 기준)
            {"name": "걷기", "met": 3.5, "duration": 60},        # 245kcal
        ]
        
        sessions = []
        total_burned = 0
        weight = 70.0
        
        for exercise_data in exercises_data:
            exercise = ExerciseItem(
                name=exercise_data["name"],
                description=f"{exercise_data['name']} 운동",
                met_value=exercise_data["met"],
                category="유산소"
            )
            
            session = ExerciseSession.create_with_calculation(
                exercise_item=exercise,
                weight=weight,
                duration=exercise_data["duration"],
                namespace=namespace
            )
            
            sessions.append(session)
            total_burned += session.calories_burned
            print(f"  - {exercise.name} {exercise_data['duration']}분: {session.calories_burned:.1f}kcal 소모")
        
        # NetCalorieResult 생성
        net_calories = total_consumed - total_burned
        result = NetCalorieResult(
            total_consumed=total_consumed,
            total_burned=total_burned,
            net_calories=net_calories,
            date=today,
            food_consumptions=consumptions,
            exercise_sessions=sessions
        )
        
        print(f"\n✓ 총 섭취: {result.total_consumed:.1f}kcal")
        print(f"✓ 총 소모: {result.total_burned:.1f}kcal")
        print(f"✓ 순 칼로리: {result.net_calories:.1f}kcal")
        
        return result
        
    except Exception as e:
        print(f"✗ 순 칼로리 계산 실패: {e}")
        traceback.print_exc()
        return None


def test_daily_analysis():
    """일일 분석 테스트."""
    print("\n=== 일일 분석 테스트 ===")
    
    # 이전 테스트에서 생성된 결과 사용
    result = test_net_calorie_calculation()
    
    if result is None:
        print("✗ 순 칼로리 결과가 없어 일일 분석을 수행할 수 없습니다")
        return
    
    try:
        # 일일 분석 생성
        analysis = DailyAnalysis(
            date=result.date,
            net_calorie_result=result
        )
        
        # 목표 칼로리 설정 및 달성률 계산
        goal_calories = 2000.0  # 목표: 2000kcal
        achievement_rate = analysis.calculate_achievement_rate(goal_calories)
        
        print(f"✓ 분석 날짜: {analysis.date}")
        print(f"✓ 목표 칼로리: {analysis.goal_calories}kcal")
        print(f"✓ 달성률: {analysis.achievement_rate:.1f}%")
        
        # 권장사항 생성
        if analysis.net_calorie_result.net_calories > 0:
            analysis.recommendations.append("칼로리 섭취가 소모보다 많습니다. 운동량을 늘리거나 섭취량을 줄이세요.")
        elif analysis.net_calorie_result.net_calories < -500:
            analysis.recommendations.append("칼로리 부족이 심합니다. 적절한 영양 섭취를 권장합니다.")
        else:
            analysis.recommendations.append("칼로리 밸런스가 양호합니다.")
        
        if achievement_rate < 80:
            analysis.recommendations.append("목표 칼로리에 비해 섭취가 부족합니다.")
        elif achievement_rate > 120:
            analysis.recommendations.append("목표 칼로리를 초과했습니다.")
        
        print("✓ 권장사항:")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"  {i}. {rec}")
        
    except Exception as e:
        print(f"✗ 일일 분석 실패: {e}")
        traceback.print_exc()


def test_korean_integration_examples():
    """한국 음식과 운동 통합 예제 테스트."""
    print("\n=== 한국 음식과 운동 통합 예제 ===")
    
    namespace = Namespace("http://example.org/diet#")
    
    # 한국 전통 식단
    korean_meal = [
        {"name": "비빔밥", "calories": 119, "amount": 300},
        {"name": "된장찌개", "calories": 35, "amount": 200},
        {"name": "김치", "calories": 18, "amount": 100}
    ]
    
    # 한국인이 자주 하는 운동
    korean_exercises = [
        {"name": "등산", "met": 6.0, "duration": 120},
        {"name": "태권도", "met": 10.0, "duration": 60}
    ]
    
    try:
        total_food_calories = 0
        total_exercise_calories = 0
        weight = 65.0  # 한국 성인 평균 체중
        
        print("📋 한국 전통 식단:")
        for meal in korean_meal:
            food = FoodItem(meal["name"], f"K{hash(meal['name']) % 1000}", "한식")
            nutrition = NutritionInfo(
                food_item=food,
                calories_per_100g=meal["calories"],
                carbohydrate=15.0,
                protein=3.0,
                fat=2.0
            )
            
            consumption = FoodConsumption.create_with_calculation(
                food_item=food,
                nutrition=nutrition,
                amount=meal["amount"],
                namespace=namespace
            )
            
            total_food_calories += consumption.calories_consumed
            print(f"  - {meal['name']} {meal['amount']}g: {consumption.calories_consumed:.1f}kcal")
        
        print(f"\n🏃 한국인 운동:")
        for ex in korean_exercises:
            exercise = ExerciseItem(
                name=ex["name"],
                description=f"한국인이 즐기는 {ex['name']} 운동",
                met_value=ex["met"],
                category="전통운동" if ex["name"] == "태권도" else "야외활동"
            )
            
            session = ExerciseSession.create_with_calculation(
                exercise_item=exercise,
                weight=weight,
                duration=ex["duration"],
                namespace=namespace
            )
            
            total_exercise_calories += session.calories_burned
            print(f"  - {ex['name']} {ex['duration']}분: {session.calories_burned:.1f}kcal 소모")
        
        net_calories = total_food_calories - total_exercise_calories
        print(f"\n📊 결과:")
        print(f"  총 섭취: {total_food_calories:.1f}kcal")
        print(f"  총 소모: {total_exercise_calories:.1f}kcal")
        print(f"  순 칼로리: {net_calories:.1f}kcal")
        
        if net_calories > 0:
            print("  💡 칼로리 잉여 - 체중 증가 가능성")
        else:
            print("  💡 칼로리 부족 - 체중 감소 가능성")
        
    except Exception as e:
        print(f"✗ 한국 통합 예제 실패: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_food_and_exercise_integration()
    test_net_calorie_calculation()
    test_daily_analysis()
    test_korean_integration_examples()
    print("\n✅ 모든 통합 테스트 완료!")