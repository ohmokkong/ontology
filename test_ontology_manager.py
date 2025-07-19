"""
온톨로지 매니저 테스트 모듈.

기존 TTL 파일 로드 및 파싱, 새로운 RDF 그래프와 기존 온톨로지 병합,
중복 데이터 검출 및 처리 로직을 포괄적으로 테스트합니다.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

from ontology_manager import OntologyManager, ValidationResult, MergeResult, Duplicate
from integrated_models import FoodItem, NutritionInfo, ExerciseItem, FoodConsumption, ExerciseSession
from exceptions import DataValidationError


def create_test_food_data():
    """테스트용 음식 데이터 생성."""
    food_item = FoodItem(
        name="테스트 음식",
        food_id="test_food_001",
        category="테스트 카테고리",
        manufacturer="테스트 제조사"
    )
    
    nutrition_info = NutritionInfo(
        food_item=food_item,
        calories_per_100g=200.0,
        carbohydrate=40.0,
        protein=10.0,
        fat=5.0,
        fiber=3.0,
        sodium=100.0
    )
    
    return food_item, nutrition_info


def create_test_exercise_data():
    """테스트용 운동 데이터 생성."""
    return ExerciseItem(
        name="테스트 운동",
        exercise_id="test_exercise_001",
        category="테스트 운동",
        met_value=6.0,
        description="테스트용 운동입니다"
    )


def create_test_ttl_file(content: str) -> str:
    """테스트용 TTL 파일 생성."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name


def test_ontology_manager_initialization():
    """온톨로지 매니저 초기화 테스트."""
    print("=== 온톨로지 매니저 초기화 테스트 ===")
    
    # 기본 초기화
    manager = OntologyManager()
    assert str(manager.base_namespace) == "http://example.org/diet#"
    assert manager.stats["loaded_files"] == 0
    
    # 사용자 정의 네임스페이스로 초기화
    custom_manager = OntologyManager("http://test.org/custom#")
    assert str(custom_manager.base_namespace) == "http://test.org/custom#"
    
    print("✓ 온톨로지 매니저 초기화 성공")
    print(f"  - 기본 네임스페이스: {manager.base_namespace}")
    print(f"  - 초기 통계: {manager.stats}")


def test_load_existing_ontology():
    """기존 온톨로지 로드 테스트."""
    print("\n=== 기존 온톨로지 로드 테스트 ===")
    
    manager = OntologyManager()
    
    # 실제 diet-ontology.ttl 파일 로드
    if os.path.exists("diet-ontology.ttl"):
        graph = manager.load_existing_ontology("diet-ontology.ttl")
        
        assert len(graph) > 0
        assert manager.stats["loaded_files"] == 1
        
        print(f"✓ 기존 온톨로지 로드 성공")
        print(f"  - 트리플 수: {len(graph)}")
        print(f"  - 클래스 수: {len(list(graph.subjects(RDF.type, OWL.Class)))}")
        
        # 특정 클래스 존재 확인
        diet_ns = Namespace("http://example.org/diet#")
        assert (diet_ns.Food, RDF.type, OWL.Class) in graph
        assert (diet_ns.Exercise, RDF.type, OWL.Class) in graph
        
        print("✓ 예상 클래스들이 존재함을 확인")
    else:
        print("⚠️ diet-ontology.ttl 파일이 없어 테스트 스킵")
    
    # 존재하지 않는 파일 로드 시 예외 처리 테스트
    try:
        manager.load_existing_ontology("nonexistent.ttl")
        assert False, "존재하지 않는 파일에 대한 예외가 발생하지 않음"
    except DataValidationError as e:
        print(f"✓ 파일 없음 예외 처리: {str(e)}")
    
    print("✓ 기존 온톨로지 로드 테스트 통과")


def test_ttl_syntax_validation():
    """TTL 문법 검증 테스트."""
    print("\n=== TTL 문법 검증 테스트 ===")
    
    manager = OntologyManager()
    
    # 유효한 TTL 파일 테스트
    valid_ttl = """
    @prefix : <http://example.org/diet#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    
    :TestFood rdf:type owl:Class ;
        rdfs:label "테스트 음식"@ko .
    
    :hasTestProperty rdf:type owl:DatatypeProperty ;
        rdfs:domain :TestFood ;
        rdfs:range xsd:string ;
        rdfs:label "테스트 속성"@ko .
    """
    
    valid_file = create_test_ttl_file(valid_ttl)
    
    try:
        result = manager.validate_ttl_syntax(valid_file)
        
        assert result.is_valid == True
        assert result.triples_count > 0
        assert result.classes_count >= 1
        assert result.properties_count >= 1
        assert len(result.errors) == 0
        
        print(f"✓ 유효한 TTL 검증 성공:")
        print(f"  - 트리플 수: {result.triples_count}")
        print(f"  - 클래스 수: {result.classes_count}")
        print(f"  - 속성 수: {result.properties_count}")
        print(f"  - 경고 수: {len(result.warnings)}")
        
    finally:
        os.unlink(valid_file)
    
    # 잘못된 TTL 파일 테스트
    invalid_ttl = """
    @prefix : <http://example.org/diet#> .
    
    :InvalidSyntax rdf:type owl:Class
    # 세미콜론 누락으로 인한 문법 오류
    :AnotherClass rdf:type owl:Class .
    """
    
    invalid_file = create_test_ttl_file(invalid_ttl)
    
    try:
        result = manager.validate_ttl_syntax(invalid_file)
        
        assert result.is_valid == False
        assert len(result.errors) > 0
        
        print(f"✓ 잘못된 TTL 검증 성공:")
        print(f"  - 오류 수: {len(result.errors)}")
        print(f"  - 첫 번째 오류: {result.errors[0]}")
        
    finally:
        os.unlink(invalid_file)
    
    # 존재하지 않는 파일 테스트
    result = manager.validate_ttl_syntax("nonexistent.ttl")
    assert result.is_valid == False
    assert len(result.errors) > 0
    
    print("✓ TTL 문법 검증 테스트 통과")


def test_schema_extension():
    """스키마 확장 테스트."""
    print("\n=== 스키마 확장 테스트 ===")
    
    manager = OntologyManager()
    
    # 기본 그래프 생성
    base_graph = Graph()
    base_graph.bind("", manager.base_namespace)
    base_graph.bind("rdf", RDF)
    base_graph.bind("rdfs", RDFS)
    base_graph.bind("owl", OWL)
    base_graph.bind("xsd", XSD)
    
    # 기본 클래스 추가
    base_graph.add((manager.base_namespace.DietConcept, RDF.type, OWL.Class))
    base_graph.add((manager.base_namespace.DietConcept, RDFS.label, Literal("다이어트 개념", lang="ko")))
    
    # 스키마 확장
    extended_graph = manager.extend_ontology_schema(base_graph)
    
    # 확장된 클래스들 확인
    expected_classes = [
        manager.base_namespace.NutritionInfo,
        manager.base_namespace.FoodConsumption,
        manager.base_namespace.ExerciseSession,
        manager.base_namespace.User
    ]
    
    for cls in expected_classes:
        assert (cls, RDF.type, OWL.Class) in extended_graph
        assert (cls, RDFS.subClassOf, manager.base_namespace.DietConcept) in extended_graph
        print(f"✓ 클래스 {cls} 확장 확인")
    
    # 확장된 속성들 확인
    expected_properties = [
        manager.base_namespace.hasCaloriesPer100g,
        manager.base_namespace.consumedAmount,
        manager.base_namespace.hasMET,
        manager.base_namespace.hasNutritionInfo
    ]
    
    for prop in expected_properties:
        # 속성이 정의되어 있는지 확인
        prop_types = list(extended_graph.objects(prop, RDF.type))
        assert len(prop_types) > 0
        print(f"✓ 속성 {prop} 확장 확인")
    
    print(f"✓ 스키마 확장 완료: {len(extended_graph)}개 트리플")
    print("✓ 스키마 확장 테스트 통과")


def test_food_to_rdf_conversion():
    """음식 데이터 RDF 변환 테스트."""
    print("\n=== 음식 데이터 RDF 변환 테스트 ===")
    
    manager = OntologyManager()
    food_item, nutrition_info = create_test_food_data()
    
    # 음식 데이터를 RDF로 변환
    rdf_graph = manager.convert_food_to_rdf(food_item, nutrition_info)
    
    assert len(rdf_graph) > 0
    
    # 음식 URI 생성 및 확인
    food_uri = food_item.to_uri(manager.base_namespace)
    
    # 음식 인스턴스 확인
    assert (food_uri, RDF.type, manager.base_namespace.Food) in rdf_graph
    assert (food_uri, RDFS.label, Literal(food_item.name, lang="ko")) in rdf_graph
    
    # 영양 정보 확인
    nutrition_uri = URIRef(f"{food_uri}_nutrition")
    assert (nutrition_uri, RDF.type, manager.base_namespace.NutritionInfo) in rdf_graph
    assert (nutrition_uri, manager.base_namespace.hasCaloriesPer100g, Literal(nutrition_info.calories_per_100g)) in rdf_graph
    
    # 관계 확인
    assert (food_uri, manager.base_namespace.hasNutritionInfo, nutrition_uri) in rdf_graph
    
    print(f"✓ 음식 RDF 변환 성공:")
    print(f"  - 트리플 수: {len(rdf_graph)}")
    print(f"  - 음식 URI: {food_uri}")
    print(f"  - 영양정보 URI: {nutrition_uri}")
    
    print("✓ 음식 데이터 RDF 변환 테스트 통과")


def test_exercise_to_rdf_conversion():
    """운동 데이터 RDF 변환 테스트."""
    print("\n=== 운동 데이터 RDF 변환 테스트 ===")
    
    manager = OntologyManager()
    exercise_item = create_test_exercise_data()
    
    # 운동 데이터를 RDF로 변환
    rdf_graph = manager.convert_exercise_to_rdf(exercise_item)
    
    assert len(rdf_graph) > 0
    
    # 운동 URI 생성 및 확인
    exercise_uri = exercise_item.to_uri(manager.base_namespace)
    
    # 운동 인스턴스 확인
    assert (exercise_uri, RDF.type, manager.base_namespace.Exercise) in rdf_graph
    assert (exercise_uri, RDFS.label, Literal(exercise_item.name, lang="ko")) in rdf_graph
    assert (exercise_uri, manager.base_namespace.hasMET, Literal(exercise_item.met_value)) in rdf_graph
    
    if exercise_item.description:
        assert (exercise_uri, RDFS.comment, Literal(exercise_item.description, lang="ko")) in rdf_graph
    
    print(f"✓ 운동 RDF 변환 성공:")
    print(f"  - 트리플 수: {len(rdf_graph)}")
    print(f"  - 운동 URI: {exercise_uri}")
    print(f"  - MET 값: {exercise_item.met_value}")
    
    print("✓ 운동 데이터 RDF 변환 테스트 통과")


def test_duplicate_detection():
    """중복 데이터 검출 테스트."""
    print("\n=== 중복 데이터 검출 테스트 ===")
    
    manager = OntologyManager()
    
    # 첫 번째 그래프 생성
    graph1 = Graph()
    graph1.bind("", manager.base_namespace)
    graph1.add((manager.base_namespace.TestFood1, RDF.type, manager.base_namespace.Food))
    graph1.add((manager.base_namespace.TestFood1, RDFS.label, Literal("테스트 음식 1")))
    graph1.add((manager.base_namespace.TestFood1, manager.base_namespace.hasCalorie, Literal(100)))
    
    # 두 번째 그래프 생성 (일부 중복 포함)
    graph2 = Graph()
    graph2.bind("", manager.base_namespace)
    graph2.add((manager.base_namespace.TestFood1, RDF.type, manager.base_namespace.Food))  # 정확한 중복
    graph2.add((manager.base_namespace.TestFood1, RDFS.label, Literal("테스트 음식 1 수정")))  # 충돌
    graph2.add((manager.base_namespace.TestFood2, RDF.type, manager.base_namespace.Food))  # 새로운 데이터
    
    # 중복 검출
    duplicates = manager.detect_duplicates(graph1, graph2)
    
    assert len(duplicates) > 0
    
    # 정확한 중복 확인
    exact_duplicates = [d for d in duplicates if d.duplicate_type == "exact"]
    assert len(exact_duplicates) > 0
    
    # 충돌 확인
    conflict_duplicates = [d for d in duplicates if d.duplicate_type == "conflict"]
    
    print(f"✓ 중복 검출 성공:")
    print(f"  - 총 중복: {len(duplicates)}개")
    print(f"  - 정확한 중복: {len(exact_duplicates)}개")
    print(f"  - 충돌: {len(conflict_duplicates)}개")
    
    for duplicate in duplicates[:3]:  # 처음 3개만 출력
        print(f"  - {duplicate.duplicate_type}: {duplicate.subject} {duplicate.predicate}")
    
    print("✓ 중복 데이터 검출 테스트 통과")


def test_backup_creation():
    """백업 생성 테스트."""
    print("\n=== 백업 생성 테스트 ===")
    
    manager = OntologyManager()
    
    # 임시 파일 생성
    test_content = """
    @prefix : <http://example.org/diet#> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    
    :TestData rdf:type :TestClass .
    """
    
    test_file = create_test_ttl_file(test_content)
    
    try:
        # 백업 생성
        backup_path = manager.create_backup(test_file)
        
        assert os.path.exists(backup_path)
        assert manager.stats["created_backups"] == 1
        
        # 백업 파일 내용 확인
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        
        assert "TestData" in backup_content
        
        print(f"✓ 백업 생성 성공:")
        print(f"  - 원본 파일: {test_file}")
        print(f"  - 백업 파일: {backup_path}")
        
        # 백업 파일 정리
        os.unlink(backup_path)
        
    finally:
        # 원본 파일 정리
        os.unlink(test_file)
    
    # 존재하지 않는 파일 백업 시 예외 처리 테스트
    try:
        manager.create_backup("nonexistent.ttl")
        assert False, "존재하지 않는 파일 백업에 대한 예외가 발생하지 않음"
    except DataValidationError as e:
        print(f"✓ 파일 없음 백업 예외 처리: {str(e)}")
    
    print("✓ 백업 생성 테스트 통과")


def test_graph_merging():
    """그래프 병합 테스트."""
    print("\n=== 그래프 병합 테스트 ===")
    
    manager = OntologyManager()
    
    # 여러 개의 작은 그래프 생성
    graphs = []
    
    for i in range(3):
        graph = Graph()
        graph.bind("", manager.base_namespace)
        
        test_uri = URIRef(f"{manager.base_namespace}TestItem{i}")
        graph.add((test_uri, RDF.type, manager.base_namespace.Food))
        graph.add((test_uri, RDFS.label, Literal(f"테스트 아이템 {i}")))
        
        graphs.append(graph)
    
    # 그래프 병합
    merged_graph = manager.merge_graphs(graphs)
    
    # 병합 결과 확인
    expected_triples = sum(len(g) for g in graphs)
    assert len(merged_graph) == expected_triples
    
    # 각 그래프의 데이터가 모두 포함되었는지 확인
    for i in range(3):
        test_uri = URIRef(f"{manager.base_namespace}TestItem{i}")
        assert (test_uri, RDF.type, manager.base_namespace.Food) in merged_graph
        assert (test_uri, RDFS.label, Literal(f"테스트 아이템 {i}")) in merged_graph
    
    print(f"✓ 그래프 병합 성공:")
    print(f"  - 입력 그래프 수: {len(graphs)}")
    print(f"  - 병합된 트리플 수: {len(merged_graph)}")
    
    # 빈 목록 병합 테스트
    empty_merged = manager.merge_graphs([])
    assert len(empty_merged) == 0
    
    print("✓ 그래프 병합 테스트 통과")


def test_save_and_load_cycle():
    """저장 및 로드 사이클 테스트."""
    print("\n=== 저장 및 로드 사이클 테스트 ===")
    
    manager = OntologyManager()
    
    # 테스트 그래프 생성
    test_graph = Graph()
    test_graph.bind("", manager.base_namespace)
    test_graph.bind("rdf", RDF)
    test_graph.bind("rdfs", RDFS)
    test_graph.bind("owl", OWL)
    
    # 테스트 데이터 추가
    test_graph.add((manager.base_namespace.SaveLoadTest, RDF.type, OWL.Class))
    test_graph.add((manager.base_namespace.SaveLoadTest, RDFS.label, Literal("저장 로드 테스트", lang="ko")))
    
    # 임시 파일에 저장
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
        temp_file = f.name
    
    try:
        # 저장
        success = manager.save_ontology(test_graph, temp_file)
        assert success == True
        assert os.path.exists(temp_file)
        
        # 로드
        loaded_graph = manager.load_existing_ontology(temp_file)
        
        # 로드된 데이터 확인
        assert len(loaded_graph) == len(test_graph)
        assert (manager.base_namespace.SaveLoadTest, RDF.type, OWL.Class) in loaded_graph
        assert (manager.base_namespace.SaveLoadTest, RDFS.label, Literal("저장 로드 테스트", lang="ko")) in loaded_graph
        
        print(f"✓ 저장 및 로드 사이클 성공:")
        print(f"  - 저장된 트리플 수: {len(test_graph)}")
        print(f"  - 로드된 트리플 수: {len(loaded_graph)}")
        
    finally:
        # 임시 파일 정리
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    print("✓ 저장 및 로드 사이클 테스트 통과")


def test_statistics_and_utilities():
    """통계 및 유틸리티 테스트."""
    print("\n=== 통계 및 유틸리티 테스트 ===")
    
    manager = OntologyManager()
    
    # 초기 통계 확인
    initial_stats = manager.get_statistics()
    assert "manager_statistics" in initial_stats
    assert "configuration" in initial_stats
    assert "timestamp" in initial_stats
    
    print(f"✓ 초기 통계:")
    print(f"  - 로드된 파일: {initial_stats['manager_statistics']['loaded_files']}")
    print(f"  - 병합된 그래프: {initial_stats['manager_statistics']['merged_graphs']}")
    
    # 일부 작업 수행하여 통계 변경
    if os.path.exists("diet-ontology.ttl"):
        manager.load_existing_ontology("diet-ontology.ttl")
    
    # 변경된 통계 확인
    updated_stats = manager.get_statistics()
    if os.path.exists("diet-ontology.ttl"):
        assert updated_stats['manager_statistics']['loaded_files'] > initial_stats['manager_statistics']['loaded_files']
    
    # 통계 초기화
    manager.reset_statistics()
    reset_stats = manager.get_statistics()
    assert reset_stats['manager_statistics']['loaded_files'] == 0
    assert reset_stats['manager_statistics']['merged_graphs'] == 0
    
    print("✓ 통계 초기화 성공")
    print("✓ 통계 및 유틸리티 테스트 통과")


if __name__ == "__main__":
    try:
        test_ontology_manager_initialization()
        test_load_existing_ontology()
        test_ttl_syntax_validation()
        test_schema_extension()
        test_food_to_rdf_conversion()
        test_exercise_to_rdf_conversion()
        test_duplicate_detection()
        test_backup_creation()
        test_graph_merging()
        test_save_and_load_cycle()
        test_statistics_and_utilities()
        
        print("\n🎉 모든 온톨로지 매니저 테스트가 성공적으로 완료되었습니다!")
        print("✅ 기존 TTL 파일 로드 및 파싱 검증 완료")
        print("✅ 새로운 RDF 그래프와 기존 온톨로지 병합 검증 완료")
        print("✅ 중복 데이터 검출 및 처리 로직 검증 완료")
        print("✅ TTL 문법 검증 및 오류 처리 검증 완료")
        print("✅ 음식/운동 데이터 RDF 변환 검증 완료")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()