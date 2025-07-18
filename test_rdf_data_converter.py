"""
RDF 데이터 변환기 테스트 모듈.
"""

import tempfile
from datetime import datetime, date
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from rdf_data_converter import RDFDataConverter
from integrated_models import (
    FoodItem, NutritionInfo, FoodConsumption,
    ExerciseItem, ExerciseSession,
    NetCalorieResult, DailyAnalysis
)
from exceptions import URIGenerationError, DataConversionError, TTLSyntaxError


def create_sample_food_data():
    """샘플 음식 데이터 생성."""
    food = FoodItem(
        name="백미밥",
        food_id="FOOD001",
        category="곡류",
        manufacturer="일반"
    )
    
    nutrition = NutritionInfo(
        food_item=food,
        calories_per_100g=130.0,
        carbohydrate=28.1,
        protein=2.5,
        fat=0.3,
        fiber=0.3,
        sodium=1.0
    )
    
    return food, nutrition


def create_sample_exercise_data():
    """샘플 운동 데이터 생성."""
    exercise = ExerciseItem(
        name="달리기",
        description="일반적인 달리기 운동",
        met_value=8.0,
        category="유산소운동",
        exercise_id="EX001"
    )
    
    return exercise


def test_converter_initialization():
    """변환기 초기화 테스트."""
    print("=== RDF 변환기 초기화 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        
        # 네임스페이스 확인
        assert str(converter.base_ns) == "http://example.org/diet#"
        assert str(converter.food_ns) == "http://example.org/diet#food/"
        assert str(converter.exercise_ns) == "http://example.org/diet#exercise/"
        
        # 클래스 정의 확인
        assert "Food" in converter.classes
        assert "Exercise" in converter.classes
        assert "NutritionInfo" in converter.classes
        
        # 속성 정의 확인
        assert "hasCalories" in converter.properties
        assert "hasMET" in converter.properties
        assert "consumedFood" in converter.properties
        
        print("✓ RDF 변환기 초기화 성공")
        print(f"  - 클래스 정의: {len(converter.classes)}개")
        print(f"  - 속성 정의: {len(converter.properties)}개")
        
    except Exception as e:
        print(f"✗ RDF 변환기 초기화 실패: {e}")


def test_food_to_rdf_conversion():
    """음식 RDF 변환 테스트."""
    print("\n=== 음식 RDF 변환 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        food, nutrition = create_sample_food_data()
        
        # 음식만 변환
        food_graph = converter.convert_food_to_rdf(food)
        
        assert len(food_graph) > 0
        print(f"✓ 음식 RDF 변환 성공: {len(food_graph)} 트리플")
        
        # 영양정보 포함 변환
        food_nutrition_graph = converter.convert_food_to_rdf(food, nutrition)
        
        assert len(food_nutrition_graph) > len(food_graph)
        print(f"✓ 음식+영양정보 RDF 변환 성공: {len(food_nutrition_graph)} 트리플")
        
        # 그래프 내용 검증
        food_uri = food.to_uri(converter.food_ns)
        
        # 음식 클래스 확인
        assert (food_uri, RDF.type, converter.classes["Food"]) in food_nutrition_graph
        
        # 음식명 확인
        assert (food_uri, RDFS.label, Literal("백미밥", lang="ko")) in food_nutrition_graph
        
        # 분류 확인
        assert (food_uri, converter.properties["foodCategory"], 
                Literal("곡류", lang="ko")) in food_nutrition_graph
        
        print("✓ RDF 그래프 내용 검증 통과")
        
        # 통계 확인
        stats = converter.get_conversion_stats()
        assert stats["foods_converted"] == 2
        print(f"✓ 변환 통계: {stats['foods_converted']}개 음식 변환")
        
    except Exception as e:
        print(f"✗ 음식 RDF 변환 테스트 실패: {e}")


def test_exercise_to_rdf_conversion():
    """운동 RDF 변환 테스트."""
    print("\n=== 운동 RDF 변환 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        exercise = create_sample_exercise_data()
        
        # 운동 변환
        exercise_graph = converter.convert_exercise_to_rdf(exercise)
        
        assert len(exercise_graph) > 0
        print(f"✓ 운동 RDF 변환 성공: {len(exercise_graph)} 트리플")
        
        # 그래프 내용 검증
        exercise_uri = exercise.to_uri(converter.exercise_ns)
        
        # 운동 클래스 확인
        assert (exercise_uri, RDF.type, converter.classes["Exercise"]) in exercise_graph
        
        # 운동명 확인
        assert (exercise_uri, RDFS.label, Literal("달리기", lang="ko")) in exercise_graph
        
        # MET 값 확인
        assert (exercise_uri, converter.properties["hasMET"], 
                Literal(8.0, datatype=XSD.float)) in exercise_graph
        
        # 분류 확인
        assert (exercise_uri, converter.properties["exerciseCategory"], 
                Literal("유산소운동", lang="ko")) in exercise_graph
        
        print("✓ RDF 그래프 내용 검증 통과")
        
        # 통계 확인
        stats = converter.get_conversion_stats()
        assert stats["exercises_converted"] == 1
        print(f"✓ 변환 통계: {stats['exercises_converted']}개 운동 변환")
        
    except Exception as e:
        print(f"✗ 운동 RDF 변환 테스트 실패: {e}")


def test_consumption_to_rdf_conversion():
    """음식 섭취 기록 RDF 변환 테스트."""
    print("\n=== 음식 섭취 기록 RDF 변환 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        food, nutrition = create_sample_food_data()
        
        # 섭취 기록 생성
        consumption = FoodConsumption.create_with_calculation(
            food_item=food,
            nutrition=nutrition,
            amount=200.0,  # 200g
            namespace=converter.food_ns
        )
        
        # 섭취 기록 변환
        consumption_graph = converter.convert_consumption_to_rdf(consumption)
        
        assert len(consumption_graph) > 0
        print(f"✓ 섭취 기록 RDF 변환 성공: {len(consumption_graph)} 트리플")
        
        # 그래프 내용 검증
        consumption_uri = converter._generate_consumption_uri(consumption)
        
        # 섭취 기록 클래스 확인
        assert (consumption_uri, RDF.type, converter.classes["FoodConsumption"]) in consumption_graph
        
        # 섭취량 확인
        assert (consumption_uri, converter.properties["consumedAmount"], 
                Literal(200.0, datatype=XSD.float)) in consumption_graph
        
        # 칼로리 확인
        expected_calories = 130.0 * 2  # 200g = 260kcal
        assert (consumption_uri, converter.properties["hasCalories"], 
                Literal(expected_calories, datatype=XSD.float)) in consumption_graph
        
        print("✓ RDF 그래프 내용 검증 통과")
        
        # 통계 확인
        stats = converter.get_conversion_stats()
        assert stats["consumptions_converted"] == 1
        print(f"✓ 변환 통계: {stats['consumptions_converted']}개 섭취 기록 변환")
        
    except Exception as e:
        print(f"✗ 섭취 기록 RDF 변환 테스트 실패: {e}")


def test_session_to_rdf_conversion():
    """운동 세션 RDF 변환 테스트."""
    print("\n=== 운동 세션 RDF 변환 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        exercise = create_sample_exercise_data()
        
        # 운동 세션 생성
        session = ExerciseSession.create_with_calculation(
            exercise_item=exercise,
            weight=70.0,  # 70kg
            duration=30.0,  # 30분
            namespace=converter.exercise_ns
        )
        
        # 세션 변환
        session_graph = converter.convert_session_to_rdf(session)
        
        assert len(session_graph) > 0
        print(f"✓ 운동 세션 RDF 변환 성공: {len(session_graph)} 트리플")
        
        # 그래프 내용 검증
        session_uri = converter._generate_session_uri(session)
        
        # 세션 클래스 확인
        assert (session_uri, RDF.type, converter.classes["ExerciseSession"]) in session_graph
        
        # 체중 확인
        assert (session_uri, converter.properties["hasWeight"], 
                Literal(70.0, datatype=XSD.float)) in session_graph
        
        # 운동 시간 확인
        assert (session_uri, converter.properties["hasDuration"], 
                Literal(30.0, datatype=XSD.float)) in session_graph
        
        # 소모 칼로리 확인
        expected_calories = 8.0 * 70.0 * 0.5  # 280kcal
        assert (session_uri, converter.properties["caloriesBurned"], 
                Literal(expected_calories, datatype=XSD.float)) in session_graph
        
        print("✓ RDF 그래프 내용 검증 통과")
        
        # 통계 확인
        stats = converter.get_conversion_stats()
        assert stats["sessions_converted"] == 1
        print(f"✓ 변환 통계: {stats['sessions_converted']}개 세션 변환")
        
    except Exception as e:
        print(f"✗ 운동 세션 RDF 변환 테스트 실패: {e}")


def test_daily_analysis_to_rdf_conversion():
    """일일 분석 RDF 변환 테스트."""
    print("\n=== 일일 분석 RDF 변환 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        food, nutrition = create_sample_food_data()
        exercise = create_sample_exercise_data()
        
        # 섭취 기록 생성
        consumption = FoodConsumption.create_with_calculation(
            food_item=food,
            nutrition=nutrition,
            amount=200.0,
            namespace=converter.food_ns
        )
        
        # 운동 세션 생성
        session = ExerciseSession.create_with_calculation(
            exercise_item=exercise,
            weight=70.0,
            duration=30.0,
            namespace=converter.exercise_ns
        )
        
        # 순 칼로리 결과 생성
        net_result = NetCalorieResult(
            total_consumed=260.0,
            total_burned=280.0,
            net_calories=-20.0,
            date=date.today(),
            food_consumptions=[consumption],
            exercise_sessions=[session]
        )
        
        # 일일 분석 생성
        analysis = DailyAnalysis(
            date=date.today(),
            net_calorie_result=net_result,
            goal_calories=2000.0
        )
        analysis.calculate_achievement_rate(2000.0)
        
        # 일일 분석 변환
        analysis_graph = converter.convert_daily_analysis_to_rdf(analysis)
        
        assert len(analysis_graph) > 0
        print(f"✓ 일일 분석 RDF 변환 성공: {len(analysis_graph)} 트리플")
        
        # 그래프 내용 검증
        daily_uri = converter._generate_daily_record_uri(analysis.date)
        
        # 일일 기록 클래스 확인
        assert (daily_uri, RDF.type, converter.classes["DailyRecord"]) in analysis_graph
        
        # 날짜 확인
        assert (daily_uri, converter.properties["analysisDate"], 
                Literal(analysis.date, datatype=XSD.date)) in analysis_graph
        
        print("✓ RDF 그래프 내용 검증 통과")
        
        # 통계 확인 (섭취 기록과 세션이 포함되어 추가 변환됨)
        stats = converter.get_conversion_stats()
        print(f"✓ 변환 통계: 총 {stats['total_converted']}개 항목 변환")
        
    except Exception as e:
        print(f"✗ 일일 분석 RDF 변환 테스트 실패: {e}")


def test_graph_merging():
    """그래프 병합 테스트."""
    print("\n=== 그래프 병합 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        food, nutrition = create_sample_food_data()
        exercise = create_sample_exercise_data()
        
        # 개별 그래프 생성
        food_graph = converter.convert_food_to_rdf(food, nutrition)
        exercise_graph = converter.convert_exercise_to_rdf(exercise)
        
        # 그래프 병합
        merged_graph = converter.merge_graphs([food_graph, exercise_graph])
        
        assert len(merged_graph) == len(food_graph) + len(exercise_graph)
        print(f"✓ 그래프 병합 성공: {len(merged_graph)} 트리플")
        
        # 병합된 내용 확인
        food_uri = food.to_uri(converter.food_ns)
        exercise_uri = exercise.to_uri(converter.exercise_ns)
        
        assert (food_uri, RDF.type, converter.classes["Food"]) in merged_graph
        assert (exercise_uri, RDF.type, converter.classes["Exercise"]) in merged_graph
        
        print("✓ 병합된 그래프 내용 검증 통과")
        
        # 통계 확인
        stats = converter.get_conversion_stats()
        assert stats["graphs_merged"] == 1
        print(f"✓ 병합 통계: {stats['graphs_merged']}회 병합")
        
    except Exception as e:
        print(f"✗ 그래프 병합 테스트 실패: {e}")


def test_ontology_schema_creation():
    """온톨로지 스키마 생성 테스트."""
    print("\n=== 온톨로지 스키마 생성 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        
        # 스키마 생성
        schema_graph = converter.create_ontology_schema()
        
        assert len(schema_graph) > 0
        print(f"✓ 온톨로지 스키마 생성 성공: {len(schema_graph)} 트리플")
        
        # 클래스 정의 확인
        assert (converter.classes["Food"], RDF.type, OWL.Class) in schema_graph
        assert (converter.classes["Exercise"], RDF.type, OWL.Class) in schema_graph
        assert (converter.classes["NutritionInfo"], RDF.type, OWL.Class) in schema_graph
        
        # 속성 정의 확인
        assert (converter.properties["hasCalories"], RDF.type, OWL.DatatypeProperty) in schema_graph
        assert (converter.properties["hasMET"], RDF.type, OWL.DatatypeProperty) in schema_graph
        assert (converter.properties["hasNutrition"], RDF.type, OWL.ObjectProperty) in schema_graph
        
        print("✓ 스키마 내용 검증 통과")
        
    except Exception as e:
        print(f"✗ 온톨로지 스키마 생성 테스트 실패: {e}")


def test_turtle_export():
    """Turtle 파일 내보내기 테스트."""
    print("\n=== Turtle 파일 내보내기 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        food, nutrition = create_sample_food_data()
        
        # 그래프 생성
        food_graph = converter.convert_food_to_rdf(food, nutrition)
        
        # 임시 파일로 내보내기
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            temp_path = f.name
        
        try:
            # TTL 파일 내보내기
            success = converter.export_to_turtle(food_graph, temp_path)
            assert success == True
            
            # 파일 존재 확인
            assert Path(temp_path).exists()
            
            # 파일 내용 확인
            with open(temp_path, 'r', encoding='utf-8') as f:
                ttl_content = f.read()
            
            assert len(ttl_content) > 0
            assert "@prefix" in ttl_content  # TTL 형식 확인
            assert "diet:" in ttl_content    # 네임스페이스 확인
            
            print("✓ Turtle 파일 내보내기 성공")
            print(f"  - 파일 크기: {len(ttl_content)} 문자")
            
            # 파일 다시 로드하여 검증
            test_graph = Graph()
            test_graph.parse(temp_path, format="turtle")
            
            assert len(test_graph) == len(food_graph)
            print("✓ 내보낸 TTL 파일 검증 통과")
            
        finally:
            # 임시 파일 정리
            Path(temp_path).unlink(missing_ok=True)
        
    except Exception as e:
        print(f"✗ Turtle 파일 내보내기 테스트 실패: {e}")


def test_graph_syntax_validation():
    """그래프 문법 검증 테스트."""
    print("\n=== 그래프 문법 검증 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        food, nutrition = create_sample_food_data()
        
        # 유효한 그래프 생성
        valid_graph = converter.convert_food_to_rdf(food, nutrition)
        
        # 문법 검증
        is_valid = converter.validate_graph_syntax(valid_graph)
        assert is_valid == True
        print("✓ 유효한 그래프 문법 검증 통과")
        
        # 빈 그래프 검증
        empty_graph = Graph()
        is_empty_valid = converter.validate_graph_syntax(empty_graph)
        assert is_empty_valid == True
        print("✓ 빈 그래프 문법 검증 통과")
        
    except Exception as e:
        print(f"✗ 그래프 문법 검증 테스트 실패: {e}")


def test_korean_data_conversion():
    """한국 데이터 RDF 변환 테스트."""
    print("\n=== 한국 데이터 RDF 변환 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        
        # 한국 음식 데이터
        korean_foods = [
            ("김치찌개", "찌개류", 45.0, 5.2, 3.1, 1.8),
            ("불고기", "육류", 156.0, 2.1, 18.7, 7.9),
            ("비빔밥", "밥류", 119.0, 18.5, 4.2, 3.1)
        ]
        
        # 한국 운동 데이터
        korean_exercises = [
            ("태권도", "전통운동", 10.0),
            ("등산", "유산소운동", 6.0),
            ("줄넘기", "유산소운동", 12.3)
        ]
        
        print("📋 한국 음식 RDF 변환:")
        food_graphs = []
        
        for name, category, calories, carbs, protein, fat in korean_foods:
            food = FoodItem(name, f"K{hash(name) % 1000}", category)
            nutrition = NutritionInfo(food, calories, carbs, protein, fat)
            
            graph = converter.convert_food_to_rdf(food, nutrition)
            food_graphs.append(graph)
            
            print(f"  ✓ {name}: {len(graph)} 트리플")
        
        print("\n🏃 한국 운동 RDF 변환:")
        exercise_graphs = []
        
        for name, category, met_value in korean_exercises:
            exercise = ExerciseItem(name, f"{name} 운동", met_value, category)
            
            graph = converter.convert_exercise_to_rdf(exercise)
            exercise_graphs.append(graph)
            
            print(f"  ✓ {name}: {len(graph)} 트리플")
        
        # 전체 병합
        all_graphs = food_graphs + exercise_graphs
        merged_graph = converter.merge_graphs(all_graphs)
        
        print(f"\n✓ 한국 데이터 통합: {len(merged_graph)} 트리플")
        
        # 통계 확인
        stats = converter.get_conversion_stats()
        print(f"✓ 변환 통계:")
        print(f"  - 음식: {stats['foods_converted']}개")
        print(f"  - 운동: {stats['exercises_converted']}개")
        print(f"  - 성공률: {stats['success_rate']:.1f}%")
        
    except Exception as e:
        print(f"✗ 한국 데이터 RDF 변환 테스트 실패: {e}")


def test_conversion_statistics():
    """변환 통계 테스트."""
    print("\n=== 변환 통계 테스트 ===")
    
    try:
        converter = RDFDataConverter()
        
        # 초기 통계 확인
        initial_stats = converter.get_conversion_stats()
        assert initial_stats["total_converted"] == 0
        assert initial_stats["success_rate"] == 0.0
        print("✓ 초기 통계 확인")
        
        # 데이터 변환 수행
        food, nutrition = create_sample_food_data()
        exercise = create_sample_exercise_data()
        
        converter.convert_food_to_rdf(food, nutrition)
        converter.convert_exercise_to_rdf(exercise)
        
        # 최종 통계 확인
        final_stats = converter.get_conversion_stats()
        assert final_stats["total_converted"] == 2
        assert final_stats["success_rate"] == 100.0
        
        print("✓ 최종 통계 확인")
        print(f"  - 총 변환: {final_stats['total_converted']}개")
        print(f"  - 성공률: {final_stats['success_rate']:.1f}%")
        print(f"  - 오류: {final_stats['errors_encountered']}개")
        
        # 통계 초기화 테스트
        converter.reset_stats()
        reset_stats = converter.get_conversion_stats()
        assert reset_stats["total_converted"] == 0
        print("✓ 통계 초기화 확인")
        
    except Exception as e:
        print(f"✗ 변환 통계 테스트 실패: {e}")


if __name__ == "__main__":
    test_converter_initialization()
    test_food_to_rdf_conversion()
    test_exercise_to_rdf_conversion()
    test_consumption_to_rdf_conversion()
    test_session_to_rdf_conversion()
    test_daily_analysis_to_rdf_conversion()
    test_graph_merging()
    test_ontology_schema_creation()
    test_turtle_export()
    test_graph_syntax_validation()
    test_korean_data_conversion()
    test_conversion_statistics()
    print("\n✅ 모든 RDF 데이터 변환기 테스트 완료!")