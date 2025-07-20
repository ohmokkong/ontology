"""
칼로리 매니저 테스트 모듈.

음식 섭취량 기반 칼로리 계산, MET 공식 기반 운동 소모 칼로리 계산,
순 칼로리 계산, 일일 분석 등의 기능을 포괄적으로 테스트합니다.
"""

from datetime import datetime, date, timedelta
from rdflib import URIRef
from calorie_manager import CalorieManager, CalorieGoal, ActivityLevel, NetCalorieResult, DailyAnalysis
from integrated_models import FoodItem, NutritionInfo, ExerciseItem, FoodConsumption, ExerciseSession
from exceptions import CalorieCalculationError, InvalidMETValueError, InvalidWeightError, InvalidAmountError


def create_test_food_data():
    """테스트용 음식 데이터 생성."""
    food_item = FoodItem(
        name="백미밥",
        food_id="food_001",
        category="곡류",
        manufacturer=None
    )
    
    nutrition_info = NutritionInfo(
        food_item=food_item,
        calories_per_100g=130.0,  # 100g당 130kcal
        carbohydrate=28.1,
        protein=2.5,
        fat=0.3,
        fiber=0.4,
        sodium=2.0
    )
    
    return food_item, nutrition_info


def create_test_exercise_data():
    """테스트용 운동 데이터 생성."""
    return ExerciseItem(
        name="달리기",
        exercise_id="ex_001",
        category="유산소",
        met_value=8.0,
        description="빠른 속도 달리기"
    )


def create_test_consumption_data():
    """테스트용 음식 섭취 데이터 생성."""
    return [
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/rice"),
            amount_grams=150.0,
            calories_consumed=195.0,  # 150g * 130kcal/100g = 195kcal
            timestamp=datetime.now()
        ),
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/chicken"),
            amount_grams=100.0,
            calories_consumed=165.0,
            timestamp=datetime.now()
        )
    ]


def create_test_exercise_session_data():
    """테스트용 운동 세션 데이터 생성."""
    return [
        ExerciseSession(
            exercise_uri=URIRef("http://example.com/exercise/running"),
            duration=30.0,
            weight=70.0,
            calories_burned=280.0,  # 8.0 MET * 70kg * 0.5h = 280kcal
            timestamp=datetime.now()
        ),
        ExerciseSession(
            exercise_uri=URIRef("http://example.com/exercise/walking"),
            duration=60.0,
            weight=70.0,
            calories_burned=147.0,  # 3.5 MET * 70kg * 1h = 245kcal (예시)
            timestamp=datetime.now()
        )
    ]


def test_calorie_manager_initialization():
    """칼로리 매니저 초기화 테스트."""
    print("=== 칼로리 매니저 초기화 테스트 ===")
    
    # 기본 초기화
    manager = CalorieManager()
    assert manager.default_weight == 70.0
    assert manager.calculation_stats["total_calculations"] == 0
    
    # 사용자 정의 체중으로 초기화
    custom_manager = CalorieManager(default_weight=65.0)
    assert custom_manager.default_weight == 65.0
    
    # 활동 수준 확인
    assert ActivityLevel.SEDENTARY in manager.activity_multipliers
    assert ActivityLevel.VERY_ACTIVE in manager.activity_multipliers
    
    print("✓ 칼로리 매니저 초기화 성공")
    print(f"  - 기본 체중: {manager.default_weight}kg")
    print(f"  - 지원 활동 수준: {len(manager.activity_multipliers)}개")


def test_food_calorie_calculation():
    """음식 칼로리 계산 테스트."""
    print("\n=== 음식 칼로리 계산 테스트 ===")
    
    manager = CalorieManager()
    food_item, nutrition_info = create_test_food_data()
    
    # 정상적인 칼로리 계산
    calories = manager.calculate_food_calories(food_item, nutrition_info, 150.0)
    expected_calories = (130.0 * 150.0) / 100.0  # 195kcal
    
    assert abs(calories - expected_calories) < 0.1
    assert manager.calculation_stats["food_calculations"] == 1
    assert manager.calculation_stats["total_calculations"] == 1
    
    print(f"✓ 음식 칼로리 계산: {food_item.name} 150g = {calories}kcal")
    
    # 다양한 양으로 계산 테스트
    test_amounts = [50.0, 100.0, 200.0, 300.0]
    for amount in test_amounts:
        calories = manager.calculate_food_calories(food_item, nutrition_info, amount)
        expected = (130.0 * amount) / 100.0
        assert abs(calories - expected) < 0.1
        print(f"  - {amount}g = {calories}kcal")
    
    # 오류 케이스 테스트
    try:
        manager.calculate_food_calories(food_item, nutrition_info, 0)
        assert False, "0g에 대한 예외가 발생하지 않음"
    except InvalidAmountError:
        print("✓ 0g 입력 오류 처리 성공")
    
    try:
        manager.calculate_food_calories(food_item, nutrition_info, -100)
        assert False, "음수 양에 대한 예외가 발생하지 않음"
    except InvalidAmountError:
        print("✓ 음수 양 입력 오류 처리 성공")
    
    print("✓ 음식 칼로리 계산 테스트 통과")


def test_exercise_calorie_calculation():
    """운동 칼로리 계산 테스트."""
    print("\n=== 운동 칼로리 계산 테스트 ===")
    
    manager = CalorieManager()
    exercise_item = create_test_exercise_data()
    
    # 정상적인 칼로리 계산 (MET 공식: 8.0 * 70kg * 0.5h = 280kcal)
    calories = manager.calculate_exercise_calories(exercise_item, 70.0, 30.0)
    expected_calories = 8.0 * 70.0 * (30.0 / 60.0)  # 280kcal
    
    assert abs(calories - expected_calories) < 0.1
    assert manager.calculation_stats["exercise_calculations"] == 1
    
    print(f"✓ 운동 칼로리 계산: {exercise_item.name} 30분 (70kg) = {calories}kcal")
    print(f"  - MET 공식: {exercise_item.met_value} × 70 × 0.5 = {expected_calories}kcal")
    
    # 다양한 체중과 시간으로 테스트
    test_cases = [
        (60.0, 20.0),  # 60kg, 20분
        (80.0, 45.0),  # 80kg, 45분
        (65.0, 60.0),  # 65kg, 60분
    ]
    
    for weight, duration in test_cases:
        calories = manager.calculate_exercise_calories(exercise_item, weight, duration)
        expected = 8.0 * weight * (duration / 60.0)
        assert abs(calories - expected) < 0.1
        print(f"  - {weight}kg, {duration}분 = {calories}kcal")
    
    # 오류 케이스 테스트
    try:
        manager.calculate_exercise_calories(exercise_item, 0, 30)
        assert False, "0kg에 대한 예외가 발생하지 않음"
    except InvalidWeightError:
        print("✓ 0kg 체중 오류 처리 성공")
    
    try:
        manager.calculate_exercise_calories(exercise_item, 70, 0)
        assert False, "0분에 대한 예외가 발생하지 않음"
    except InvalidAmountError:
        print("✓ 0분 운동시간 오류 처리 성공")
    
    # 잘못된 MET 값 테스트 (모델 검증을 우회하여 테스트)
    try:
        # ExerciseItem 생성 시 검증이 실행되므로, 직접 MET 값을 0으로 설정
        valid_exercise = create_test_exercise_data()
        valid_exercise.met_value = 0  # 검증 후 값 변경
        manager.calculate_exercise_calories(valid_exercise, 70, 30)
        assert False, "잘못된 MET 값에 대한 예외가 발생하지 않음"
    except InvalidMETValueError:
        print("✓ 잘못된 MET 값 오류 처리 성공")
    
    print("✓ 운동 칼로리 계산 테스트 통과")


def test_net_calorie_calculation():
    """순 칼로리 계산 테스트."""
    print("\n=== 순 칼로리 계산 테스트 ===")
    
    manager = CalorieManager()
    consumptions = create_test_consumption_data()
    sessions = create_test_exercise_session_data()
    
    # 순 칼로리 계산
    result = manager.calculate_net_calories(consumptions, sessions)
    
    # 예상 값 계산
    expected_intake = sum(c.calories_consumed for c in consumptions)  # 195 + 165 = 360kcal
    expected_burned = sum(s.calories_burned for s in sessions)        # 280 + 147 = 427kcal
    expected_net = expected_intake - expected_burned                  # 360 - 427 = -67kcal
    
    assert abs(result.total_intake - expected_intake) < 0.1
    assert abs(result.total_burned - expected_burned) < 0.1
    assert abs(result.net_calories - expected_net) < 0.1
    assert result.food_count == len(consumptions)
    assert result.exercise_count == len(sessions)
    
    print(f"✓ 순 칼로리 계산:")
    print(f"  - 총 섭취: {result.total_intake}kcal")
    print(f"  - 총 소모: {result.total_burned}kcal")
    print(f"  - 순 칼로리: {result.net_calories}kcal")
    print(f"  - 음식 수: {result.food_count}개")
    print(f"  - 운동 수: {result.exercise_count}개")
    
    # 빈 목록 테스트
    empty_result = manager.calculate_net_calories([], [])
    assert empty_result.total_intake == 0
    assert empty_result.total_burned == 0
    assert empty_result.net_calories == 0
    
    print("✓ 빈 목록 처리 성공")
    print("✓ 순 칼로리 계산 테스트 통과")


def test_daily_analysis():
    """일일 칼로리 분석 테스트."""
    print("\n=== 일일 칼로리 분석 테스트 ===")
    
    manager = CalorieManager()
    analysis_date = date.today()
    consumptions = create_test_consumption_data()
    sessions = create_test_exercise_session_data()
    
    # 목표 설정
    goal = CalorieGoal(
        daily_intake_goal=2000.0,
        daily_burn_goal=400.0,
        activity_level=ActivityLevel.MODERATELY_ACTIVE
    )
    
    # 일일 분석 수행
    analysis = manager.analyze_daily_balance(analysis_date, consumptions, sessions, goal)
    
    assert analysis.analysis_date == analysis_date
    assert analysis.total_intake > 0
    assert analysis.total_burned > 0
    assert analysis.goal_intake == 2000.0
    assert analysis.goal_burn == 400.0
    assert analysis.intake_achievement_rate is not None
    assert analysis.burn_achievement_rate is not None
    assert len(analysis.food_breakdown) > 0
    assert len(analysis.exercise_breakdown) > 0
    assert len(analysis.recommendations) > 0
    
    print(f"✓ 일일 분석 완료:")
    print(f"  - 분석 날짜: {analysis.analysis_date}")
    print(f"  - 섭취 칼로리: {analysis.total_intake}kcal")
    print(f"  - 소모 칼로리: {analysis.total_burned}kcal")
    print(f"  - 순 칼로리: {analysis.net_calories}kcal")
    print(f"  - 섭취 목표 달성률: {analysis.intake_achievement_rate:.1f}%")
    print(f"  - 소모 목표 달성률: {analysis.burn_achievement_rate:.1f}%")
    print(f"  - 음식 종류: {len(analysis.food_breakdown)}개")
    print(f"  - 운동 종류: {len(analysis.exercise_breakdown)}개")
    print(f"  - 권장사항: {len(analysis.recommendations)}개")
    
    # 목표 없이 분석
    analysis_no_goal = manager.analyze_daily_balance(analysis_date, consumptions, sessions)
    assert analysis_no_goal.goal_intake is None
    assert analysis_no_goal.goal_burn is None
    assert analysis_no_goal.intake_achievement_rate is None
    assert analysis_no_goal.burn_achievement_rate is None
    
    print("✓ 목표 없는 분석 성공")
    print("✓ 일일 칼로리 분석 테스트 통과")


def test_goal_comparison():
    """목표 비교 테스트."""
    print("\n=== 목표 비교 테스트 ===")
    
    manager = CalorieManager()
    
    # 목표 달성 케이스
    comparison1 = manager.compare_with_goal(2000.0, 2000.0, "섭취 칼로리")
    assert comparison1.achievement_rate == 100.0
    assert comparison1.status == "달성"
    assert comparison1.difference == 0.0
    
    print(f"✓ 목표 달성: {comparison1.actual_value}kcal / {comparison1.goal_value}kcal = {comparison1.achievement_rate}%")
    
    # 목표 미달성 케이스
    comparison2 = manager.compare_with_goal(1500.0, 2000.0, "섭취 칼로리")
    assert comparison2.achievement_rate == 75.0
    assert comparison2.status == "미달성"
    assert comparison2.difference == -500.0
    
    print(f"✓ 목표 미달성: {comparison2.actual_value}kcal / {comparison2.goal_value}kcal = {comparison2.achievement_rate}%")
    
    # 목표 초과달성 케이스
    comparison3 = manager.compare_with_goal(2500.0, 2000.0, "섭취 칼로리")
    assert comparison3.achievement_rate == 125.0
    assert comparison3.status == "초과달성"
    assert comparison3.difference == 500.0
    
    print(f"✓ 목표 초과달성: {comparison3.actual_value}kcal / {comparison3.goal_value}kcal = {comparison3.achievement_rate}%")
    
    # 각 케이스별 권장사항 확인
    assert "달성" in comparison1.recommendation or "유지" in comparison1.recommendation
    assert "부족" in comparison2.recommendation or "재검토" in comparison2.recommendation
    assert "초과" in comparison3.recommendation or "조절" in comparison3.recommendation
    
    print("✓ 목표 비교 테스트 통과")


def test_bmr_calculation():
    """기초대사율(BMR) 계산 테스트."""
    print("\n=== BMR 계산 테스트 ===")
    
    manager = CalorieManager()
    
    # 남성 BMR 계산
    male_bmr = manager.calculate_bmr(70.0, 175.0, 30, "male")
    expected_male_bmr = 88.362 + (13.397 * 70) + (4.799 * 175) - (5.677 * 30)
    assert abs(male_bmr - expected_male_bmr) < 0.1
    
    print(f"✓ 남성 BMR: 30세, 70kg, 175cm = {male_bmr}kcal/day")
    
    # 여성 BMR 계산
    female_bmr = manager.calculate_bmr(60.0, 165.0, 25, "female")
    expected_female_bmr = 447.593 + (9.247 * 60) + (3.098 * 165) - (4.330 * 25)
    assert abs(female_bmr - expected_female_bmr) < 0.1
    
    print(f"✓ 여성 BMR: 25세, 60kg, 165cm = {female_bmr}kcal/day")
    
    # 잘못된 성별 테스트
    try:
        manager.calculate_bmr(70.0, 175.0, 30, "invalid")
        assert False, "잘못된 성별에 대한 예외가 발생하지 않음"
    except Exception:
        print("✓ 잘못된 성별 오류 처리 성공")
    
    print("✓ BMR 계산 테스트 통과")


def test_tdee_calculation():
    """총 일일 에너지 소비량(TDEE) 계산 테스트."""
    print("\n=== TDEE 계산 테스트 ===")
    
    manager = CalorieManager()
    bmr = 1800.0
    
    # 다양한 활동 수준별 TDEE 계산
    activity_levels = [
        (ActivityLevel.SEDENTARY, 1.2),
        (ActivityLevel.LIGHTLY_ACTIVE, 1.375),
        (ActivityLevel.MODERATELY_ACTIVE, 1.55),
        (ActivityLevel.VERY_ACTIVE, 1.725),
        (ActivityLevel.EXTREMELY_ACTIVE, 1.9)
    ]
    
    for activity_level, multiplier in activity_levels:
        tdee = manager.calculate_tdee(bmr, activity_level)
        expected_tdee = bmr * multiplier
        assert abs(tdee - expected_tdee) < 0.1
        print(f"  - {activity_level.value}: {tdee}kcal/day (×{multiplier})")
    
    print("✓ TDEE 계산 테스트 통과")


def test_calculation_statistics():
    """계산 통계 테스트."""
    print("\n=== 계산 통계 테스트 ===")
    
    manager = CalorieManager()
    food_item, nutrition_info = create_test_food_data()
    exercise_item = create_test_exercise_data()
    
    # 여러 계산 수행
    manager.calculate_food_calories(food_item, nutrition_info, 100.0)
    manager.calculate_food_calories(food_item, nutrition_info, 150.0)
    manager.calculate_exercise_calories(exercise_item, 70.0, 30.0)
    manager.calculate_net_calories(create_test_consumption_data(), create_test_exercise_session_data())
    
    # 통계 확인
    stats = manager.get_calculation_stats()
    
    assert stats["calculation_statistics"]["food_calculations"] == 2
    assert stats["calculation_statistics"]["exercise_calculations"] == 1
    assert stats["calculation_statistics"]["net_calculations"] == 1
    assert stats["calculation_statistics"]["total_calculations"] == 4
    assert stats["calculation_statistics"]["average_intake"] > 0
    assert stats["calculation_statistics"]["average_burn"] > 0
    
    print(f"✓ 계산 통계:")
    print(f"  - 총 계산: {stats['calculation_statistics']['total_calculations']}회")
    print(f"  - 음식 계산: {stats['calculation_statistics']['food_calculations']}회")
    print(f"  - 운동 계산: {stats['calculation_statistics']['exercise_calculations']}회")
    print(f"  - 순 칼로리 계산: {stats['calculation_statistics']['net_calculations']}회")
    print(f"  - 평균 섭취: {stats['calculation_statistics']['average_intake']:.1f}kcal")
    print(f"  - 평균 소모: {stats['calculation_statistics']['average_burn']:.1f}kcal")
    
    # 통계 초기화 테스트
    manager.reset_statistics()
    reset_stats = manager.get_calculation_stats()
    assert reset_stats["calculation_statistics"]["total_calculations"] == 0
    
    print("✓ 통계 초기화 성공")
    print("✓ 계산 통계 테스트 통과")


def test_error_handling():
    """오류 처리 테스트."""
    print("\n=== 오류 처리 테스트 ===")
    
    manager = CalorieManager()
    food_item, nutrition_info = create_test_food_data()
    exercise_item = create_test_exercise_data()
    
    # 음식 칼로리 계산 오류
    error_cases = [
        (0, "0g 섭취량"),
        (-100, "음수 섭취량"),
        (15000, "과도한 섭취량")
    ]
    
    for amount, description in error_cases:
        try:
            manager.calculate_food_calories(food_item, nutrition_info, amount)
            assert False, f"{description}에 대한 예외가 발생하지 않음"
        except (InvalidAmountError, CalorieCalculationError):
            print(f"✓ {description} 오류 처리 성공")
    
    # 운동 칼로리 계산 오류
    exercise_error_cases = [
        (0, 30, "0kg 체중"),
        (70, 0, "0분 운동시간"),
        (-70, 30, "음수 체중"),
        (70, -30, "음수 운동시간"),
        (600, 30, "과도한 체중"),
        (70, 2000, "과도한 운동시간")
    ]
    
    for weight, duration, description in exercise_error_cases:
        try:
            manager.calculate_exercise_calories(exercise_item, weight, duration)
            assert False, f"{description}에 대한 예외가 발생하지 않음"
        except (InvalidWeightError, InvalidAmountError, CalorieCalculationError):
            print(f"✓ {description} 오류 처리 성공")
    
    # 목표 비교 오류
    try:
        manager.compare_with_goal(100.0, 0, "테스트")
        assert False, "0 목표값에 대한 예외가 발생하지 않음"
    except CalorieCalculationError:
        print("✓ 0 목표값 오류 처리 성공")
    
    print("✓ 오류 처리 테스트 통과")


if __name__ == "__main__":
    try:
        test_calorie_manager_initialization()
        test_food_calorie_calculation()
        test_exercise_calorie_calculation()
        test_net_calorie_calculation()
        test_daily_analysis()
        test_goal_comparison()
        test_bmr_calculation()
        test_tdee_calculation()
        test_calculation_statistics()
        test_error_handling()
        
        print("\n🎉 모든 칼로리 매니저 테스트가 성공적으로 완료되었습니다!")
        print("✅ 음식 섭취량 기반 칼로리 계산 검증 완료")
        print("✅ MET 공식 기반 운동 소모 칼로리 계산 검증 완료")
        print("✅ 순 칼로리(섭취-소모) 계산 기능 검증 완료")
        print("✅ 일일 칼로리 분석 및 목표 비교 기능 검증 완료")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()