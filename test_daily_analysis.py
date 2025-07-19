"""
일일 칼로리 분석 테스트 모듈.

하루 동안의 음식/운동 데이터 집계, 목표 칼로리 대비 달성률 계산,
칼로리 밸런스 분석 리포트 생성 기능을 포괄적으로 테스트합니다.
"""

from datetime import datetime, date, timedelta
from rdflib import URIRef
from daily_analysis import DailyAnalysisManager, MealAnalysis, ExerciseAnalysis, CalorieBalanceReport
from calorie_manager import CalorieManager, CalorieGoal, ActivityLevel
from integrated_models import FoodItem, NutritionInfo, ExerciseItem, FoodConsumption, ExerciseSession
from exceptions import CalorieCalculationError


def create_test_nutrition_data():
    """테스트용 영양정보 데이터 생성."""
    # 음식 아이템 생성
    rice_item = FoodItem(
        name="백미밥",
        food_id="rice",
        category="곡류",
        manufacturer=None
    )
    
    chicken_item = FoodItem(
        name="닭가슴살",
        food_id="chicken",
        category="육류",
        manufacturer=None
    )
    
    salad_item = FoodItem(
        name="샐러드",
        food_id="salad",
        category="채소류",
        manufacturer=None
    )
    
    # 영양정보 생성
    rice_nutrition = NutritionInfo(
        food_item=rice_item,
        calories_per_100g=130.0,
        carbohydrate=28.1,
        protein=2.5,
        fat=0.3,
        fiber=0.4,
        sodium=2.0
    )
    
    chicken_nutrition = NutritionInfo(
        food_item=chicken_item,
        calories_per_100g=165.0,
        carbohydrate=0.0,
        protein=31.0,
        fat=3.6,
        fiber=0.0,
        sodium=74.0
    )
    
    salad_nutrition = NutritionInfo(
        food_item=salad_item,
        calories_per_100g=25.0,
        carbohydrate=4.0,
        protein=2.0,
        fat=0.5,
        fiber=2.0,
        sodium=15.0
    )
    
    return {
        "rice": rice_nutrition,
        "chicken": chicken_nutrition,
        "salad": salad_nutrition
    }


def create_test_consumption_data():
    """테스트용 음식 섭취 데이터 생성."""
    today = date.today()
    
    return [
        # 아침 식사 (8시)
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/rice"),
            amount_grams=150.0,
            calories_consumed=195.0,  # 150g * 130kcal/100g
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=8))
        ),
        # 점심 식사 (12시)
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/chicken"),
            amount_grams=120.0,
            calories_consumed=198.0,  # 120g * 165kcal/100g
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=12))
        ),
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/salad"),
            amount_grams=200.0,
            calories_consumed=50.0,   # 200g * 25kcal/100g
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=12, minute=30))
        ),
        # 저녁 식사 (19시)
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/rice"),
            amount_grams=100.0,
            calories_consumed=130.0,  # 100g * 130kcal/100g
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=19))
        ),
        # 간식 (15시)
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/salad"),
            amount_grams=50.0,
            calories_consumed=12.5,   # 50g * 25kcal/100g
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=15))
        )
    ]


def create_test_exercise_session_data():
    """테스트용 운동 세션 데이터 생성."""
    today = date.today()
    
    return [
        # 아침 운동 (7시) - 고강도
        ExerciseSession(
            exercise_uri=URIRef("http://example.com/exercise/running"),
            duration=30.0,
            weight=70.0,
            calories_burned=280.0,  # 고강도
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=7))
        ),
        # 저녁 운동 (18시) - 중강도
        ExerciseSession(
            exercise_uri=URIRef("http://example.com/exercise/walking"),
            duration=45.0,
            weight=70.0,
            calories_burned=180.0,  # 중강도
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=18))
        ),
        # 밤 운동 (21시) - 저강도
        ExerciseSession(
            exercise_uri=URIRef("http://example.com/exercise/stretching"),
            duration=20.0,
            weight=70.0,
            calories_burned=60.0,   # 저강도
            timestamp=datetime.combine(today, datetime.min.time().replace(hour=21))
        )
    ]


def test_daily_analysis_manager_initialization():
    """일일 분석 매니저 초기화 테스트."""
    print("=== 일일 분석 매니저 초기화 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    assert daily_manager.calorie_manager == calorie_manager
    assert "아침" in daily_manager.meal_time_ranges
    assert "저강도" in daily_manager.exercise_intensity_ranges
    
    print("✓ 일일 분석 매니저 초기화 성공")
    print(f"  - 식사 시간대: {len(daily_manager.meal_time_ranges)}개")
    print(f"  - 운동 강도 분류: {len(daily_manager.exercise_intensity_ranges)}개")


def test_meal_time_classification():
    """식사 시간 분류 테스트."""
    print("\n=== 식사 시간 분류 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    # 시간대별 분류 테스트
    test_cases = [
        (8, "아침"),
        (12, "점심"),
        (19, "저녁"),
        (15, "간식"),
        (23, "간식"),
        (3, "간식")
    ]
    
    for hour, expected_meal_type in test_cases:
        meal_type = daily_manager._classify_meal_time(hour)
        assert meal_type == expected_meal_type
        print(f"✓ {hour}시 → {meal_type}")
    
    print("✓ 식사 시간 분류 테스트 통과")


def test_exercise_intensity_classification():
    """운동 강도 분류 테스트."""
    print("\n=== 운동 강도 분류 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    # 분당 칼로리 소모량별 강도 분류 테스트
    test_cases = [
        (3.0, "저강도 운동"),
        (7.0, "중강도 운동"),
        (12.0, "고강도 운동")
    ]
    
    for calories_per_minute, expected_intensity in test_cases:
        intensity = daily_manager._classify_exercise_intensity(calories_per_minute)
        assert intensity == expected_intensity
        print(f"✓ {calories_per_minute} kcal/min → {intensity}")
    
    print("✓ 운동 강도 분류 테스트 통과")


def test_meal_analysis():
    """식사별 분석 테스트."""
    print("\n=== 식사별 분석 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    consumptions = create_test_consumption_data()
    nutrition_data = create_test_nutrition_data()
    
    meal_analyses = daily_manager._analyze_meals(consumptions, nutrition_data)
    
    # 식사 타입별로 분석 결과 확인
    meal_types = [meal.meal_type for meal in meal_analyses]
    assert "아침" in meal_types
    assert "점심" in meal_types
    assert "저녁" in meal_types
    assert "간식" in meal_types
    
    print(f"✓ 식사별 분석 완료: {len(meal_analyses)}개 식사")
    
    for meal in meal_analyses:
        print(f"  - {meal.meal_type}: {meal.total_calories:.1f} kcal")
        print(f"    음식 수: {meal.food_count}개")
        print(f"    영양소 - 탄수화물: {meal.total_carbs:.1f}g, 단백질: {meal.total_protein:.1f}g, 지방: {meal.total_fat:.1f}g")
        print(f"    음식당 평균 칼로리: {meal.average_calories_per_food:.1f} kcal")
    
    # 점심 식사 상세 검증 (닭가슴살 + 샐러드)
    lunch_meal = next(meal for meal in meal_analyses if meal.meal_type == "점심")
    assert lunch_meal.food_count == 2
    assert abs(lunch_meal.total_calories - 248.0) < 1.0  # 198 + 50
    
    print("✓ 식사별 분석 테스트 통과")


def test_exercise_analysis():
    """운동별 분석 테스트."""
    print("\n=== 운동별 분석 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    sessions = create_test_exercise_session_data()
    exercise_analyses = daily_manager._analyze_exercises(sessions)
    
    assert len(exercise_analyses) > 0
    
    print(f"✓ 운동별 분석 완료: {len(exercise_analyses)}개 운동 타입")
    
    for exercise in exercise_analyses:
        print(f"  - {exercise.exercise_type}: {exercise.total_calories_burned:.1f} kcal")
        print(f"    세션 수: {exercise.session_count}개")
        print(f"    총 시간: {exercise.total_duration:.0f}분")
        print(f"    평균 강도: {exercise.average_intensity:.1f} MET")
        print(f"    분당 소모: {exercise.calories_per_minute:.1f} kcal/min")
    
    # 총 소모 칼로리 검증
    total_burned = sum(ex.total_calories_burned for ex in exercise_analyses)
    expected_total = 280.0 + 180.0 + 60.0  # 520 kcal
    assert abs(total_burned - expected_total) < 1.0
    
    print("✓ 운동별 분석 테스트 통과")


def test_hourly_pattern_analysis():
    """시간대별 패턴 분석 테스트."""
    print("\n=== 시간대별 패턴 분석 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    consumptions = create_test_consumption_data()
    sessions = create_test_exercise_session_data()
    
    hourly_consumption, hourly_exercise = daily_manager._analyze_hourly_patterns(
        consumptions, sessions
    )
    
    # 시간별 섭취 칼로리 확인
    assert 8 in hourly_consumption  # 아침 식사
    assert 12 in hourly_consumption  # 점심 식사
    assert 19 in hourly_consumption  # 저녁 식사
    assert 15 in hourly_consumption  # 간식
    
    # 시간별 운동 칼로리 확인
    assert 7 in hourly_exercise   # 아침 운동
    assert 18 in hourly_exercise  # 저녁 운동
    assert 21 in hourly_exercise  # 밤 운동
    
    print("✓ 시간대별 패턴 분석:")
    print("  섭취 패턴:")
    for hour, calories in sorted(hourly_consumption.items()):
        print(f"    {hour}시: {calories:.1f} kcal")
    
    print("  운동 패턴:")
    for hour, calories in sorted(hourly_exercise.items()):
        print(f"    {hour}시: {calories:.1f} kcal")
    
    print("✓ 시간대별 패턴 분석 테스트 통과")


def test_nutrient_summary_calculation():
    """영양소 요약 계산 테스트."""
    print("\n=== 영양소 요약 계산 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    consumptions = create_test_consumption_data()
    nutrition_data = create_test_nutrition_data()
    
    nutrient_summary = daily_manager._calculate_nutrient_summary(
        consumptions, nutrition_data
    )
    
    # 필수 영양소 항목 확인
    required_nutrients = [
        "total_calories", "total_carbohydrate", "total_protein", 
        "total_fat", "total_fiber", "total_sodium"
    ]
    
    for nutrient in required_nutrients:
        assert nutrient in nutrient_summary
        assert nutrient_summary[nutrient] >= 0
    
    print("✓ 영양소 요약:")
    print(f"  - 총 칼로리: {nutrient_summary['total_calories']:.1f} kcal")
    print(f"  - 탄수화물: {nutrient_summary['total_carbohydrate']:.1f}g")
    print(f"  - 단백질: {nutrient_summary['total_protein']:.1f}g")
    print(f"  - 지방: {nutrient_summary['total_fat']:.1f}g")
    print(f"  - 식이섬유: {nutrient_summary['total_fiber']:.1f}g")
    print(f"  - 나트륨: {nutrient_summary['total_sodium']:.1f}mg")
    
    # 총 칼로리 검증 (모든 음식의 칼로리 합)
    expected_calories = 195.0 + 198.0 + 50.0 + 130.0 + 12.5  # 585.5 kcal
    assert abs(nutrient_summary['total_calories'] - expected_calories) < 1.0
    
    print("✓ 영양소 요약 계산 테스트 통과")


def test_daily_report_generation():
    """일일 리포트 생성 테스트."""
    print("\n=== 일일 리포트 생성 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    consumptions = create_test_consumption_data()
    sessions = create_test_exercise_session_data()
    nutrition_data = create_test_nutrition_data()
    target_date = date.today()
    goal_calories = 2000.0
    
    # 리포트 생성
    report = daily_manager.generate_daily_report(
        consumptions, sessions, nutrition_data, target_date, goal_calories
    )
    
    # 기본 정보 검증
    assert report.analysis_date == target_date
    assert report.goal_calories == goal_calories
    assert report.total_consumed > 0
    assert report.total_burned > 0
    assert report.goal_comparison is not None
    
    # 분석 결과 검증
    assert len(report.meal_analyses) > 0
    assert len(report.exercise_analyses) > 0
    assert len(report.recommendations) > 0
    assert len(report.insights) > 0
    assert 0 <= report.health_score <= 100
    
    print(f"✓ 일일 리포트 생성 완료:")
    print(f"  - 분석 날짜: {report.analysis_date}")
    print(f"  - 총 섭취: {report.total_consumed:.1f} kcal")
    print(f"  - 총 소모: {report.total_burned:.1f} kcal")
    print(f"  - 순 칼로리: {report.net_calories:.1f} kcal")
    print(f"  - 목표 달성률: {report.goal_comparison.achievement_rate:.1f}%")
    print(f"  - 건강 점수: {report.health_score:.1f}/100")
    print(f"  - 식사 분석: {len(report.meal_analyses)}개")
    print(f"  - 운동 분석: {len(report.exercise_analyses)}개")
    print(f"  - 권장사항: {len(report.recommendations)}개")
    print(f"  - 인사이트: {len(report.insights)}개")
    
    print("✓ 일일 리포트 생성 테스트 통과")


def test_recommendations_generation():
    """권장사항 생성 테스트."""
    print("\n=== 권장사항 생성 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    # 테스트 데이터로 리포트 생성
    consumptions = create_test_consumption_data()
    sessions = create_test_exercise_session_data()
    nutrition_data = create_test_nutrition_data()
    
    report = daily_manager.generate_daily_report(
        consumptions, sessions, nutrition_data, date.today(), 2000.0
    )
    
    # 권장사항이 생성되었는지 확인
    assert len(report.recommendations) > 0
    
    print("✓ 생성된 권장사항:")
    for i, recommendation in enumerate(report.recommendations, 1):
        print(f"  {i}. {recommendation}")
    
    # 인사이트가 생성되었는지 확인
    assert len(report.insights) > 0
    
    print("\n✓ 생성된 인사이트:")
    for insight in report.insights:
        print(f"  • {insight}")
    
    print("✓ 권장사항 생성 테스트 통과")


def test_health_score_calculation():
    """건강 점수 계산 테스트."""
    print("\n=== 건강 점수 계산 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    # 다양한 시나리오로 건강 점수 테스트
    consumptions = create_test_consumption_data()
    sessions = create_test_exercise_session_data()
    nutrition_data = create_test_nutrition_data()
    
    # 목표 달성 시나리오
    report_with_goal = daily_manager.generate_daily_report(
        consumptions, sessions, nutrition_data, date.today(), 100.0  # 낮은 목표로 달성 유도
    )
    
    # 목표 없는 시나리오
    report_without_goal = daily_manager.generate_daily_report(
        consumptions, sessions, nutrition_data, date.today()
    )
    
    print(f"✓ 건강 점수 계산:")
    print(f"  - 목표 있음: {report_with_goal.health_score:.1f}/100")
    print(f"  - 목표 없음: {report_without_goal.health_score:.1f}/100")
    
    # 점수가 유효한 범위 내에 있는지 확인
    assert 0 <= report_with_goal.health_score <= 100
    assert 0 <= report_without_goal.health_score <= 100
    
    print("✓ 건강 점수 계산 테스트 통과")


def test_report_export_and_summary():
    """리포트 내보내기 및 요약 테스트."""
    print("\n=== 리포트 내보내기 및 요약 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    consumptions = create_test_consumption_data()
    sessions = create_test_exercise_session_data()
    nutrition_data = create_test_nutrition_data()
    
    report = daily_manager.generate_daily_report(
        consumptions, sessions, nutrition_data, date.today(), 2000.0
    )
    
    # 딕셔너리 변환 테스트
    report_dict = report.to_dict()
    
    assert "analysis_date" in report_dict
    assert "calorie_summary" in report_dict
    assert "meal_analysis" in report_dict
    assert "exercise_analysis" in report_dict
    assert "nutrient_summary" in report_dict
    assert "recommendations" in report_dict
    assert "health_score" in report_dict
    
    print("✓ 리포트 딕셔너리 변환 성공")
    
    # 요약 텍스트 생성 테스트
    summary_text = daily_manager.generate_summary_text(report)
    
    assert len(summary_text) > 0
    assert "일일 칼로리 분석 리포트" in summary_text
    assert "칼로리 요약" in summary_text
    assert "건강 점수" in summary_text
    
    print("✓ 요약 텍스트 생성:")
    print(summary_text[:200] + "..." if len(summary_text) > 200 else summary_text)
    
    # JSON 파일 내보내기 테스트
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file_path = f.name
    
    try:
        daily_manager.export_report_to_json(report, temp_file_path)
        
        # 파일이 생성되었는지 확인
        assert os.path.exists(temp_file_path)
        
        # 파일 내용 확인
        import json
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        assert "analysis_date" in loaded_data
        assert "health_score" in loaded_data
        
        print("✓ JSON 파일 내보내기 성공")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
    
    print("✓ 리포트 내보내기 및 요약 테스트 통과")


def test_edge_cases():
    """엣지 케이스 테스트."""
    print("\n=== 엣지 케이스 테스트 ===")
    
    calorie_manager = CalorieManager()
    daily_manager = DailyAnalysisManager(calorie_manager)
    
    # 빈 데이터로 리포트 생성
    empty_report = daily_manager.generate_daily_report(
        [], [], {}, date.today()
    )
    
    assert empty_report.total_consumed == 0
    assert empty_report.total_burned == 0
    assert empty_report.net_calories == 0
    assert len(empty_report.meal_analyses) == 0
    assert len(empty_report.exercise_analyses) == 0
    
    print("✓ 빈 데이터 처리 성공")
    
    # 과거 날짜 데이터 필터링 테스트
    past_date = date.today() - timedelta(days=1)
    past_consumptions = [
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/rice"),
            amount_grams=100.0,
            calories_consumed=130.0,
            timestamp=datetime.combine(past_date, datetime.min.time().replace(hour=12))
        )
    ]
    
    filtered_report = daily_manager.generate_daily_report(
        past_consumptions, [], {}, date.today()  # 오늘 날짜로 필터링
    )
    
    assert filtered_report.total_consumed == 0  # 과거 데이터는 필터링됨
    
    print("✓ 날짜 필터링 성공")
    
    # 영양정보 없는 음식 처리 테스트
    consumptions_without_nutrition = [
        FoodConsumption(
            food_uri=URIRef("http://example.com/food/unknown"),
            amount_grams=100.0,
            calories_consumed=100.0,
            timestamp=datetime.now()
        )
    ]
    
    report_without_nutrition = daily_manager.generate_daily_report(
        consumptions_without_nutrition, [], {}, date.today()
    )
    
    # 칼로리는 있지만 영양소 정보는 0이어야 함
    assert report_without_nutrition.total_consumed == 100.0
    assert report_without_nutrition.nutrient_summary["total_carbohydrate"] == 0.0
    
    print("✓ 영양정보 없는 음식 처리 성공")
    print("✓ 엣지 케이스 테스트 통과")


if __name__ == "__main__":
    try:
        test_daily_analysis_manager_initialization()
        test_meal_time_classification()
        test_exercise_intensity_classification()
        test_meal_analysis()
        test_exercise_analysis()
        test_hourly_pattern_analysis()
        test_nutrient_summary_calculation()
        test_daily_report_generation()
        test_recommendations_generation()
        test_health_score_calculation()
        test_report_export_and_summary()
        test_edge_cases()
        
        print("\n🎉 모든 일일 분석 테스트가 성공적으로 완료되었습니다!")
        print("✅ 하루 동안의 음식/운동 데이터 집계 검증 완료")
        print("✅ 목표 칼로리 대비 달성률 계산 검증 완료")
        print("✅ 칼로리 밸런스 분석 리포트 생성 검증 완료")
        print("✅ 식사별/운동별 상세 분석 검증 완료")
        print("✅ 개인화된 권장사항 및 인사이트 생성 검증 완료")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()