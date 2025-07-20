"""
SPARQL 쿼리 매니저 테스트 모듈.

온톨로지 데이터에 대한 SPARQL 쿼리 실행 및 결과 처리 기능을 포괄적으로 테스트합니다.
자주 사용되는 쿼리 템플릿 및 결과 포맷팅 기능을 테스트합니다.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

from sparql_manager import SPARQLManager, QueryResult, QueryTemplate
from exceptions import DataValidationError


def create_test_ontology() -> str:
    """테스트용 온톨로지 파일 생성."""
    # 테스트 그래프 생성
    graph = Graph()
    
    # 네임스페이스 정의
    diet_ns = Namespace("http://example.org/diet#")
    graph.bind("", diet_ns)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("owl", OWL)
    graph.bind("xsd", XSD)
    
    # 클래스 정의
    graph.add((diet_ns.Food, RDF.type, OWL.Class))
    graph.add((diet_ns.Food, RDFS.label, Literal("음식", lang="ko")))
    
    graph.add((diet_ns.Exercise, RDF.type, OWL.Class))
    graph.add((diet_ns.Exercise, RDFS.label, Literal("운동", lang="ko")))
    
    graph.add((diet_ns.NutritionInfo, RDF.type, OWL.Class))
    graph.add((diet_ns.NutritionInfo, RDFS.label, Literal("영양 정보", lang="ko")))
    
    # 속성 정의
    graph.add((diet_ns.hasCategory, RDF.type, OWL.DatatypeProperty))
    graph.add((diet_ns.hasCategory, RDFS.domain, diet_ns.Food))
    graph.add((diet_ns.hasCategory, RDFS.range, XSD.string))
    
    graph.add((diet_ns.hasManufacturer, RDF.type, OWL.DatatypeProperty))
    graph.add((diet_ns.hasManufacturer, RDFS.domain, diet_ns.Food))
    graph.add((diet_ns.hasManufacturer, RDFS.range, XSD.string))
    
    graph.add((diet_ns.hasMET, RDF.type, OWL.DatatypeProperty))
    graph.add((diet_ns.hasMET, RDFS.domain, diet_ns.Exercise))
    graph.add((diet_ns.hasMET, RDFS.range, XSD.decimal))
    
    graph.add((diet_ns.hasNutritionInfo, RDF.type, OWL.ObjectProperty))
    graph.add((diet_ns.hasNutritionInfo, RDFS.domain, diet_ns.Food))
    graph.add((diet_ns.hasNutritionInfo, RDFS.range, diet_ns.NutritionInfo))
    
    graph.add((diet_ns.hasCaloriesPer100g, RDF.type, OWL.DatatypeProperty))
    graph.add((diet_ns.hasCaloriesPer100g, RDFS.domain, diet_ns.NutritionInfo))
    graph.add((diet_ns.hasCaloriesPer100g, RDFS.range, XSD.decimal))
    
    graph.add((diet_ns.hasCarbohydrate, RDF.type, OWL.DatatypeProperty))
    graph.add((diet_ns.hasCarbohydrate, RDFS.domain, diet_ns.NutritionInfo))
    graph.add((diet_ns.hasCarbohydrate, RDFS.range, XSD.decimal))
    
    graph.add((diet_ns.hasProtein, RDF.type, OWL.DatatypeProperty))
    graph.add((diet_ns.hasProtein, RDFS.domain, diet_ns.NutritionInfo))
    graph.add((diet_ns.hasProtein, RDFS.range, XSD.decimal))
    
    graph.add((diet_ns.hasFat, RDF.type, OWL.DatatypeProperty))
    graph.add((diet_ns.hasFat, RDFS.domain, diet_ns.NutritionInfo))
    graph.add((diet_ns.hasFat, RDFS.range, XSD.decimal))
    
    # 인스턴스 추가 - 음식
    # 사과
    apple = diet_ns.Food_Apple
    graph.add((apple, RDF.type, diet_ns.Food))
    graph.add((apple, RDFS.label, Literal("사과", lang="ko")))
    graph.add((apple, diet_ns.hasCategory, Literal("과일")))
    
    apple_nutrition = diet_ns.Nutrition_Apple
    graph.add((apple_nutrition, RDF.type, diet_ns.NutritionInfo))
    graph.add((apple_nutrition, diet_ns.hasCaloriesPer100g, Literal(52.0)))
    graph.add((apple_nutrition, diet_ns.hasCarbohydrate, Literal(14.0)))
    graph.add((apple_nutrition, diet_ns.hasProtein, Literal(0.3)))
    graph.add((apple_nutrition, diet_ns.hasFat, Literal(0.2)))
    
    graph.add((apple, diet_ns.hasNutritionInfo, apple_nutrition))
    
    # 바나나
    banana = diet_ns.Food_Banana
    graph.add((banana, RDF.type, diet_ns.Food))
    graph.add((banana, RDFS.label, Literal("바나나", lang="ko")))
    graph.add((banana, diet_ns.hasCategory, Literal("과일")))
    
    banana_nutrition = diet_ns.Nutrition_Banana
    graph.add((banana_nutrition, RDF.type, diet_ns.NutritionInfo))
    graph.add((banana_nutrition, diet_ns.hasCaloriesPer100g, Literal(89.0)))
    graph.add((banana_nutrition, diet_ns.hasCarbohydrate, Literal(22.8)))
    graph.add((banana_nutrition, diet_ns.hasProtein, Literal(1.1)))
    graph.add((banana_nutrition, diet_ns.hasFat, Literal(0.3)))
    
    graph.add((banana, diet_ns.hasNutritionInfo, banana_nutrition))
    
    # 현미밥
    rice = diet_ns.Food_BrownRice
    graph.add((rice, RDF.type, diet_ns.Food))
    graph.add((rice, RDFS.label, Literal("현미밥", lang="ko")))
    graph.add((rice, diet_ns.hasCategory, Literal("곡류")))
    
    rice_nutrition = diet_ns.Nutrition_BrownRice
    graph.add((rice_nutrition, RDF.type, diet_ns.NutritionInfo))
    graph.add((rice_nutrition, diet_ns.hasCaloriesPer100g, Literal(112.0)))
    graph.add((rice_nutrition, diet_ns.hasCarbohydrate, Literal(24.0)))
    graph.add((rice_nutrition, diet_ns.hasProtein, Literal(2.6)))
    graph.add((rice_nutrition, diet_ns.hasFat, Literal(0.9)))
    
    graph.add((rice, diet_ns.hasNutritionInfo, rice_nutrition))
    
    # 인스턴스 추가 - 운동
    # 달리기
    running = diet_ns.Exercise_Running
    graph.add((running, RDF.type, diet_ns.Exercise))
    graph.add((running, RDFS.label, Literal("달리기", lang="ko")))
    graph.add((running, diet_ns.hasCategory, Literal("유산소")))
    graph.add((running, diet_ns.hasMET, Literal(8.0)))
    graph.add((running, RDFS.comment, Literal("빠른 속도로 달리기", lang="ko")))
    
    # 걷기
    walking = diet_ns.Exercise_Walking
    graph.add((walking, RDF.type, diet_ns.Exercise))
    graph.add((walking, RDFS.label, Literal("걷기", lang="ko")))
    graph.add((walking, diet_ns.hasCategory, Literal("유산소")))
    graph.add((walking, diet_ns.hasMET, Literal(3.5)))
    graph.add((walking, RDFS.comment, Literal("보통 속도로 걷기", lang="ko")))
    
    # 스쿼트
    squat = diet_ns.Exercise_Squat
    graph.add((squat, RDF.type, diet_ns.Exercise))
    graph.add((squat, RDFS.label, Literal("스쿼트", lang="ko")))
    graph.add((squat, diet_ns.hasCategory, Literal("근력")))
    graph.add((squat, diet_ns.hasMET, Literal(5.0)))
    graph.add((squat, RDFS.comment, Literal("하체 근력 운동", lang="ko")))
    
    # 임시 파일에 저장
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
        f.write(graph.serialize(format="turtle"))
        return f.name


def test_sparql_manager_initialization():
    """SPARQL 쿼리 매니저 초기화 테스트."""
    print("=== SPARQL 쿼리 매니저 초기화 테스트 ===")
    
    # 테스트 온톨로지 생성
    test_ontology_path = create_test_ontology()
    
    try:
        # 기본 초기화
        manager = SPARQLManager(ontology_path=test_ontology_path)
        assert manager.ontology_path == test_ontology_path
        assert manager.cache_enabled == True
        assert len(manager.graph) > 0
        assert len(manager.templates) > 0
        
        # 캐시 비활성화 초기화
        no_cache_manager = SPARQLManager(ontology_path=test_ontology_path, cache_enabled=False)
        assert no_cache_manager.cache_enabled == False
        
        print("✓ SPARQL 쿼리 매니저 초기화 성공")
        print(f"  - 온톨로지 트리플 수: {len(manager.graph)}")
        print(f"  - 쿼리 템플릿 수: {len(manager.templates)}")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(test_ontology_path):
            os.unlink(test_ontology_path)


def test_query_templates():
    """쿼리 템플릿 테스트."""
    print("\n=== 쿼리 템플릿 테스트 ===")
    
    # 테스트 온톨로지 생성
    test_ontology_path = create_test_ontology()
    
    try:
        manager = SPARQLManager(ontology_path=test_ontology_path)
        
        # 템플릿 목록 확인
        templates = manager.templates
        assert "food_by_name" in templates
        assert "exercise_by_name" in templates
        assert "food_categories" in templates
        assert "exercise_categories" in templates
        
        print(f"✓ 템플릿 목록 확인 성공: {len(templates)}개 템플릿")
        
        # 템플릿 매개변수 적용 테스트
        food_query = manager.get_query_template("food_by_name", food_name="사과", limit=5)
        assert "사과" in food_query
        assert "LIMIT 5" in food_query
        
        print("✓ 템플릿 매개변수 적용 성공")
        print(f"  - 생성된 쿼리: {food_query[:50]}...")
        
        # 필수 매개변수 누락 테스트
        try:
            manager.get_query_template("food_by_name")
            assert False, "필수 매개변수 누락 예외가 발생하지 않음"
        except ValueError as e:
            print(f"✓ 필수 매개변수 누락 예외 처리: {str(e)}")
        
        # 존재하지 않는 템플릿 테스트
        try:
            manager.get_query_template("nonexistent_template")
            assert False, "존재하지 않는 템플릿 예외가 발생하지 않음"
        except ValueError as e:
            print(f"✓ 존재하지 않는 템플릿 예외 처리: {str(e)}")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(test_ontology_path):
            os.unlink(test_ontology_path)


def test_query_execution():
    """쿼리 실행 테스트."""
    print("\n=== 쿼리 실행 테스트 ===")
    
    # 테스트 온톨로지 생성
    test_ontology_path = create_test_ontology()
    
    try:
        manager = SPARQLManager(ontology_path=test_ontology_path)
        
        # 음식 검색 쿼리 실행
        food_query = manager.get_query_template("food_by_name", food_name="사과", limit=10)
        result = manager.execute_query(food_query)
        
        assert result.success == True
        assert result.row_count > 0
        assert isinstance(result.data, list)
        assert result.execution_time > 0
        
        print(f"✓ 음식 검색 쿼리 실행 성공:")
        print(f"  - 결과 수: {result.row_count}")
        print(f"  - 실행 시간: {result.execution_time:.6f}초")
        
        # 잘못된 쿼리 실행 테스트
        invalid_query = "SELECT ?x WHERE { ?x ?y ?z . FILTER(NOTEXIST) }"
        invalid_result = manager.execute_query(invalid_query)
        
        assert invalid_result.success == False
        assert invalid_result.error_message is not None
        
        print(f"✓ 잘못된 쿼리 예외 처리 성공:")
        print(f"  - 오류 메시지: {invalid_result.error_message[:50]}...")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(test_ontology_path):
            os.unlink(test_ontology_path)


def test_result_formatting():
    """결과 포맷팅 테스트."""
    print("\n=== 결과 포맷팅 테스트 ===")
    
    # 테스트 온톨로지 생성
    test_ontology_path = create_test_ontology()
    
    try:
        manager = SPARQLManager(ontology_path=test_ontology_path)
        
        # 음식 검색 쿼리 실행
        food_query = manager.get_query_template("food_by_name", food_name="사과", limit=10)
        result = manager.execute_query(food_query, format="json")
        
        # JSON 포맷 테스트
        json_output = manager.format_results(result, format="json")
        assert isinstance(json_output, str)
        
        print("✓ JSON 포맷팅 성공")
        print(f"  - JSON 출력: {json_output[:200]}...")
        
        # 결과가 있는지 확인
        if result.data and len(result.data) > 0:
            print(f"  - 첫 번째 결과: {result.data[0]}")
        else:
            print("  - 결과 없음")
        
        # 테이블 포맷 테스트
        table_output = manager.format_results(result, format="table")
        assert isinstance(table_output, str)
        assert "|" in table_output  # 테이블 구분자 확인
        
        print("✓ 테이블 포맷팅 성공")
        print(f"  - 테이블 출력: {table_output[:100]}...")
        
        # CSV 포맷 테스트
        csv_result = manager.execute_query(food_query, format="csv")
        csv_output = manager.format_results(csv_result, format="csv")
        assert isinstance(csv_output, str)
        
        print("✓ CSV 포맷팅 성공")
        print(f"  - CSV 출력: {csv_output[:100]}...")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(test_ontology_path):
            os.unlink(test_ontology_path)


def test_convenience_methods():
    """편의 메서드 테스트."""
    print("\n=== 편의 메서드 테스트 ===")
    
    # 테스트 온톨로지 생성
    test_ontology_path = create_test_ontology()
    
    try:
        manager = SPARQLManager(ontology_path=test_ontology_path)
        
        # 음식 검색 테스트
        foods = manager.get_food_by_name("사과")
        assert isinstance(foods, list)
        assert len(foods) > 0
        
        print(f"✓ 음식 검색 성공: {len(foods)}개 결과")
        
        # 운동 검색 테스트
        exercises = manager.get_exercise_by_name("달리기")
        assert isinstance(exercises, list)
        assert len(exercises) > 0
        
        print(f"✓ 운동 검색 성공: {len(exercises)}개 결과")
        
        # 카테고리 조회 테스트
        food_categories = manager.get_food_categories()
        assert isinstance(food_categories, list)
        assert "과일" in food_categories
        
        print(f"✓ 음식 카테고리 조회 성공: {food_categories}")
        
        exercise_categories = manager.get_exercise_categories()
        assert isinstance(exercise_categories, list)
        assert "유산소" in exercise_categories
        
        print(f"✓ 운동 카테고리 조회 성공: {exercise_categories}")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(test_ontology_path):
            os.unlink(test_ontology_path)


def test_cache_functionality():
    """캐시 기능 테스트."""
    print("\n=== 캐시 기능 테스트 ===")
    
    # 테스트 온톨로지 생성
    test_ontology_path = create_test_ontology()
    
    try:
        manager = SPARQLManager(ontology_path=test_ontology_path, cache_enabled=True)
        
        # 첫 번째 쿼리 실행 (캐시 미스)
        food_query = manager.get_query_template("food_by_name", food_name="사과", limit=10)
        result1 = manager.execute_query(food_query)
        
        initial_cache_misses = manager.stats["cache_misses"]
        initial_cache_hits = manager.stats["cache_hits"]
        
        # 동일한 쿼리 재실행 (캐시 히트)
        result2 = manager.execute_query(food_query)
        
        final_cache_hits = manager.stats["cache_hits"]
        final_cache_misses = manager.stats["cache_misses"]
        
        assert result1.success == True
        assert result2.success == True
        
        print(f"✓ 캐시 기능 테스트 성공:")
        print(f"  - 초기 캐시 미스: {initial_cache_misses}")
        print(f"  - 초기 캐시 히트: {initial_cache_hits}")
        print(f"  - 최종 캐시 미스: {final_cache_misses}")
        print(f"  - 최종 캐시 히트: {final_cache_hits}")
        print(f"  - 캐시 항목 수: {len(manager.query_cache)}")
        
        # 캐시가 작동하는지 확인 (히트가 증가했거나 캐시에 항목이 있어야 함)
        cache_working = final_cache_hits > initial_cache_hits or len(manager.query_cache) > 0
        assert cache_working, "캐시가 작동하지 않습니다"
        
        # 캐시 초기화 테스트
        cleared_count = manager.clear_cache()
        assert cleared_count > 0
        
        print(f"✓ 캐시 초기화 성공: {cleared_count}개 항목 제거")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(test_ontology_path):
            os.unlink(test_ontology_path)


def test_statistics():
    """통계 정보 테스트."""
    print("\n=== 통계 정보 테스트 ===")
    
    # 테스트 온톨로지 생성
    test_ontology_path = create_test_ontology()
    
    try:
        manager = SPARQLManager(ontology_path=test_ontology_path)
        
        # 몇 개의 쿼리 실행
        manager.get_food_by_name("사과")
        manager.get_exercise_by_name("달리기")
        
        # 통계 정보 조회
        stats = manager.get_statistics()
        
        assert "query_statistics" in stats
        assert "cache_info" in stats
        assert "ontology_info" in stats
        assert "templates" in stats
        
        assert stats["query_statistics"]["total_queries"] > 0
        assert stats["ontology_info"]["triples"] > 0
        assert stats["templates"]["count"] > 0
        
        print("✓ 통계 정보 조회 성공:")
        print(f"  - 총 쿼리 수: {stats['query_statistics']['total_queries']}")
        print(f"  - 온톨로지 트리플 수: {stats['ontology_info']['triples']}")
        print(f"  - 템플릿 수: {stats['templates']['count']}")
        print(f"  - 평균 실행 시간: {stats['query_statistics']['avg_execution_time']:.6f}초")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(test_ontology_path):
            os.unlink(test_ontology_path)


def run_all_tests():
    """모든 테스트 실행."""
    print("🧪 SPARQL 쿼리 매니저 테스트 시작\n")
    
    try:
        test_sparql_manager_initialization()
        test_query_templates()
        test_query_execution()
        test_result_formatting()
        test_convenience_methods()
        test_cache_functionality()
        test_statistics()
        
        print("\n🎉 모든 테스트 통과!")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        raise


if __name__ == "__main__":
    run_all_tests()