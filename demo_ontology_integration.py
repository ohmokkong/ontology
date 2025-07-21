"""
온톨로지 통합 테스트 데모 스크립트.
이 스크립트는 온톨로지 생성, 병합, 검증 기능을 시연합니다.
"""

import os
import tempfile
import shutil
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS
from rdflib.plugins.parsers.notation3 import BadSyntax
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_ontology():
    """샘플 온톨로지 생성."""
    print("\n=== 샘플 온톨로지 생성 ===")
    
    sample_ontology = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix diet: <http://example.org/diet-ontology#> .
@prefix food: <http://example.org/food#> .
@prefix exercise: <http://example.org/exercise#> .

# 기본 클래스 정의
diet:DietConcept rdf:type rdfs:Class ;
    rdfs:label "Diet Concept" ;
    rdfs:comment "Base class for all diet-related concepts" .

diet:Food rdf:type rdfs:Class ;
    rdfs:subClassOf diet:DietConcept ;
    rdfs:label "Food" ;
    rdfs:comment "Food items with nutritional information" .

diet:Exercise rdf:type rdfs:Class ;
    rdfs:subClassOf diet:DietConcept ;
    rdfs:label "Exercise" ;
    rdfs:comment "Physical exercises with calorie burn information" .

diet:NutritionInfo rdf:type rdfs:Class ;
    rdfs:label "Nutrition Information" ;
    rdfs:comment "Nutritional data for food items" .

# 속성 정의
diet:hasCalories rdf:type rdf:Property ;
    rdfs:label "has calories" ;
    rdfs:domain diet:Food ;
    rdfs:range rdfs:Literal .

diet:hasCarbohydrate rdf:type rdf:Property ;
    rdfs:label "has carbohydrate" ;
    rdfs:domain diet:NutritionInfo ;
    rdfs:range rdfs:Literal .

diet:hasProtein rdf:type rdf:Property ;
    rdfs:label "has protein" ;
    rdfs:domain diet:NutritionInfo ;
    rdfs:range rdfs:Literal .

diet:hasMET rdf:type rdf:Property ;
    rdfs:label "has MET value" ;
    rdfs:domain diet:Exercise ;
    rdfs:range rdfs:Literal .

# 기존 데이터
food:apple rdf:type diet:Food ;
    rdfs:label "사과" ;
    diet:hasCalories "52.0"^^<http://www.w3.org/2001/XMLSchema#float> .

food:rice rdf:type diet:Food ;
    rdfs:label "밥" ;
    diet:hasCalories "130.0"^^<http://www.w3.org/2001/XMLSchema#float> .

exercise:walking rdf:type diet:Exercise ;
    rdfs:label "걷기" ;
    diet:hasMET "3.5"^^<http://www.w3.org/2001/XMLSchema#float> .
"""
    
    # 임시 파일에 저장
    temp_dir = tempfile.mkdtemp()
    ontology_path = os.path.join(temp_dir, "sample-ontology.ttl")
    
    with open(ontology_path, 'w', encoding='utf-8') as f:
        f.write(sample_ontology)
    
    print(f"✓ 샘플 온톨로지 생성 완료: {ontology_path}")
    return ontology_path, temp_dir


def validate_ttl_syntax(file_path):
    """TTL 파일 문법 검증."""
    print(f"\n=== TTL 문법 검증: {os.path.basename(file_path)} ===")
    
    try:
        graph = Graph()
        start_time = time.time()
        graph.parse(file_path, format="turtle")
        parse_time = time.time() - start_time
        
        print(f"✓ TTL 문법 검증 성공")
        print(f"  - 파싱 시간: {parse_time:.3f}초")
        print(f"  - 트리플 수: {len(graph)}")
        return True, graph
        
    except BadSyntax as e:
        print(f"✗ TTL 문법 오류: {e}")
        return False, None
    except Exception as e:
        print(f"✗ 파일 읽기 오류: {e}")
        return False, None


def create_new_food_data():
    """새로운 음식 데이터 생성."""
    print("\n=== 새로운 음식 데이터 생성 ===")
    
    new_food_data = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix diet: <http://example.org/diet-ontology#> .
@prefix food: <http://example.org/food#> .

food:banana rdf:type diet:Food ;
    rdfs:label "바나나" ;
    diet:hasCalories "89.0"^^<http://www.w3.org/2001/XMLSchema#float> .

food:chicken_breast rdf:type diet:Food ;
    rdfs:label "닭가슴살" ;
    diet:hasCalories "165.0"^^<http://www.w3.org/2001/XMLSchema#float> .

food:broccoli rdf:type diet:Food ;
    rdfs:label "브로콜리" ;
    diet:hasCalories "34.0"^^<http://www.w3.org/2001/XMLSchema#float> .
"""
    
    print("✓ 새로운 음식 데이터 생성 완료")
    print("  - 바나나: 89.0 kcal")
    print("  - 닭가슴살: 165.0 kcal")
    print("  - 브로콜리: 34.0 kcal")
    
    return new_food_data


def create_new_exercise_data():
    """새로운 운동 데이터 생성."""
    print("\n=== 새로운 운동 데이터 생성 ===")
    
    new_exercise_data = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix diet: <http://example.org/diet-ontology#> .
@prefix exercise: <http://example.org/exercise#> .

exercise:running rdf:type diet:Exercise ;
    rdfs:label "달리기" ;
    diet:hasMET "8.0"^^<http://www.w3.org/2001/XMLSchema#float> .

exercise:swimming rdf:type diet:Exercise ;
    rdfs:label "수영" ;
    diet:hasMET "6.0"^^<http://www.w3.org/2001/XMLSchema#float> .

exercise:cycling rdf:type diet:Exercise ;
    rdfs:label "자전거타기" ;
    diet:hasMET "4.0"^^<http://www.w3.org/2001/XMLSchema#float> .
"""
    
    print("✓ 새로운 운동 데이터 생성 완료")
    print("  - 달리기: MET 8.0")
    print("  - 수영: MET 6.0")
    print("  - 자전거타기: MET 4.0")
    
    return new_exercise_data


def merge_ontologies(base_graph, new_data_list):
    """온톨로지 병합."""
    print("\n=== 온톨로지 병합 ===")
    
    merged_graph = Graph()
    
    # 기본 온톨로지 복사
    for triple in base_graph:
        merged_graph.add(triple)
    
    original_count = len(merged_graph)
    print(f"기본 온톨로지 트리플 수: {original_count}")
    
    # 새로운 데이터들 병합
    for i, new_data in enumerate(new_data_list, 1):
        temp_graph = Graph()
        temp_graph.parse(data=new_data, format="turtle")
        
        before_count = len(merged_graph)
        
        # 병합 수행
        for triple in temp_graph:
            merged_graph.add(triple)
        
        after_count = len(merged_graph)
        added_count = after_count - before_count
        
        print(f"데이터셋 {i} 병합: +{added_count} 트리플 (총 {after_count})")
    
    final_count = len(merged_graph)
    total_added = final_count - original_count
    
    print(f"✓ 병합 완료: 총 {total_added}개 트리플 추가")
    print(f"  - 최종 트리플 수: {final_count}")
    
    return merged_graph


def detect_duplicates(graph):
    """중복 데이터 검출."""
    print("\n=== 중복 데이터 검출 ===")
    
    # 같은 주어(subject)를 가진 트리플들 그룹화
    subjects = {}
    for s, p, o in graph:
        if s not in subjects:
            subjects[s] = []
        subjects[s].append((p, o))
    
    duplicates_found = 0
    potential_conflicts = 0
    
    for subject, properties in subjects.items():
        # 같은 속성을 가진 트리플들 찾기
        property_groups = {}
        for prop, obj in properties:
            if prop not in property_groups:
                property_groups[prop] = []
            property_groups[prop].append(obj)
        
        # 중복 속성 검사
        for prop, objects in property_groups.items():
            if len(objects) > 1:
                duplicates_found += 1
                # 값이 다른 경우 충돌로 간주
                unique_values = set(str(obj) for obj in objects)
                if len(unique_values) > 1:
                    potential_conflicts += 1
                    print(f"⚠ 충돌 발견: {subject} {prop}")
                    for obj in objects:
                        print(f"    값: {obj}")
    
    print(f"✓ 중복 검출 완료")
    print(f"  - 중복 속성 수: {duplicates_found}")
    print(f"  - 잠재적 충돌 수: {potential_conflicts}")
    
    return duplicates_found, potential_conflicts


def validate_ontology_consistency(graph):
    """온톨로지 일관성 검증."""
    print("\n=== 온톨로지 일관성 검증 ===")
    
    # 네임스페이스 정의
    DIET = Namespace("http://example.org/diet-ontology#")
    
    # 클래스 계층 구조 검증
    diet_concept = DIET.DietConcept
    food_class = DIET.Food
    exercise_class = DIET.Exercise
    
    # 서브클래스 관계 확인
    food_subclass = (food_class, RDFS.subClassOf, diet_concept) in graph
    exercise_subclass = (exercise_class, RDFS.subClassOf, diet_concept) in graph
    
    print(f"클래스 계층 구조:")
    print(f"  - Food → DietConcept: {food_subclass}")
    print(f"  - Exercise → DietConcept: {exercise_subclass}")
    
    # 인스턴스 타입 검증
    food_instances = list(graph.subjects(RDF.type, food_class))
    exercise_instances = list(graph.subjects(RDF.type, exercise_class))
    
    print(f"인스턴스 수:")
    print(f"  - Food 인스턴스: {len(food_instances)}")
    print(f"  - Exercise 인스턴스: {len(exercise_instances)}")
    
    # 속성 도메인/범위 검증
    properties_with_domain = list(graph.subjects(RDFS.domain, None))
    properties_with_range = list(graph.subjects(RDFS.range, None))
    
    print(f"속성 정의:")
    print(f"  - 도메인 정의된 속성: {len(properties_with_domain)}")
    print(f"  - 범위 정의된 속성: {len(properties_with_range)}")
    
    # 데이터 타입 검증
    calories_property = DIET.hasCalories
    met_property = DIET.hasMET
    
    invalid_calories = 0
    invalid_mets = 0
    
    for s, p, o in graph.triples((None, calories_property, None)):
        try:
            float(o)
        except ValueError:
            invalid_calories += 1
    
    for s, p, o in graph.triples((None, met_property, None)):
        try:
            float(o)
        except ValueError:
            invalid_mets += 1
    
    print(f"데이터 타입 검증:")
    print(f"  - 잘못된 칼로리 값: {invalid_calories}")
    print(f"  - 잘못된 MET 값: {invalid_mets}")
    
    consistency_score = 100
    if not food_subclass:
        consistency_score -= 20
    if not exercise_subclass:
        consistency_score -= 20
    if invalid_calories > 0:
        consistency_score -= 10 * invalid_calories
    if invalid_mets > 0:
        consistency_score -= 10 * invalid_mets
    
    print(f"✓ 일관성 점수: {max(0, consistency_score)}/100")
    
    return consistency_score


def save_merged_ontology(graph, output_path):
    """병합된 온톨로지 저장."""
    print(f"\n=== 병합된 온톨로지 저장 ===")
    
    try:
        start_time = time.time()
        graph.serialize(destination=output_path, format="turtle")
        save_time = time.time() - start_time
        
        file_size = os.path.getsize(output_path)
        
        print(f"✓ 온톨로지 저장 완료: {output_path}")
        print(f"  - 저장 시간: {save_time:.3f}초")
        print(f"  - 파일 크기: {file_size:,} bytes")
        print(f"  - 트리플 수: {len(graph)}")
        
        return True
        
    except Exception as e:
        print(f"✗ 저장 실패: {e}")
        return False


def performance_test(graph):
    """성능 테스트."""
    print("\n=== 성능 테스트 ===")
    
    # 쿼리 성능 테스트
    test_queries = [
        ("모든 음식 조회", "SELECT ?food WHERE { ?food a <http://example.org/diet-ontology#Food> }"),
        ("모든 운동 조회", "SELECT ?exercise WHERE { ?exercise a <http://example.org/diet-ontology#Exercise> }"),
        ("칼로리 정보 조회", "SELECT ?food ?calories WHERE { ?food <http://example.org/diet-ontology#hasCalories> ?calories }"),
        ("MET 값 조회", "SELECT ?exercise ?met WHERE { ?exercise <http://example.org/diet-ontology#hasMET> ?met }")
    ]
    
    for query_name, sparql_query in test_queries:
        start_time = time.time()
        results = list(graph.query(sparql_query))
        query_time = time.time() - start_time
        
        print(f"{query_name}:")
        print(f"  - 실행 시간: {query_time:.3f}초")
        print(f"  - 결과 수: {len(results)}")
        
        # 결과가 있으면 첫 번째 몇 개 출력
        if results and len(results) > 0:
            print(f"  - 샘플 결과:")
            for i, result in enumerate(results[:3]):
                print(f"    {i+1}. {result}")
            if len(results) > 3:
                print(f"    ... 외 {len(results) - 3}개")


def main():
    """메인 함수."""
    print("=== 온톨로지 통합 테스트 데모 ===")
    
    try:
        # 1. 샘플 온톨로지 생성
        ontology_path, temp_dir = create_sample_ontology()
        
        # 2. TTL 문법 검증
        is_valid, base_graph = validate_ttl_syntax(ontology_path)
        if not is_valid:
            print("기본 온톨로지 문법 오류로 인해 테스트를 중단합니다.")
            return
        
        # 3. 새로운 데이터 생성
        new_food_data = create_new_food_data()
        new_exercise_data = create_new_exercise_data()
        
        # 4. 온톨로지 병합
        merged_graph = merge_ontologies(base_graph, [new_food_data, new_exercise_data])
        
        # 5. 중복 데이터 검출
        detect_duplicates(merged_graph)
        
        # 6. 일관성 검증
        validate_ontology_consistency(merged_graph)
        
        # 7. 병합된 온톨로지 저장
        output_path = os.path.join(temp_dir, "merged-ontology.ttl")
        save_merged_ontology(merged_graph, output_path)
        
        # 8. 성능 테스트
        performance_test(merged_graph)
        
        print(f"\n=== 테스트 완료 ===")
        print(f"임시 파일들: {temp_dir}")
        print("테스트가 완료되었습니다. 임시 파일들을 확인해보세요.")
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        raise
    
    finally:
        # 정리 작업은 사용자가 파일을 확인한 후 수동으로 수행
        pass


if __name__ == "__main__":
    main()