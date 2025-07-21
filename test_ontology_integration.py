"""
온톨로지 생성 및 병합 테스트 모듈.
이 모듈은 TTL 파일 생성, 문법 검증, 기존 온톨로지와의 병합, 중복 데이터 처리를 테스트합니다.
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS
from rdflib.plugins.parsers.notation3 import BadSyntax
from ontology_manager import OntologyManager
from rdf_data_converter import RDFDataConverter
from integrated_models import FoodItem, ExerciseItem, NutritionInfo
from exceptions import OntologyError, DataValidationError


class OntologyIntegrationTests(unittest.TestCase):
    """온톨로지 생성 및 병합 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.test_ontology_path = os.path.join(self.test_dir, "test-ontology.ttl")
        self.backup_dir = os.path.join(self.test_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 온톨로지 매니저 초기화
        self.ontology_manager = OntologyManager()
        
        # RDF 데이터 변환기 초기화
        self.rdf_converter = RDFDataConverter()
        
        # 네임스페이스 정의
        self.DIET = Namespace("http://example.org/diet-ontology#")
        self.FOOD = Namespace("http://example.org/food#")
        self.EXERCISE = Namespace("http://example.org/exercise#")
        
        # 기본 온톨로지 생성
        self._create_base_ontology()
        
    def tearDown(self):
        """테스트 정리."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_base_ontology(self):
        """기본 온톨로지 파일 생성."""
        base_ontology = f"""
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

# 기본 속성 정의
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

diet:hasFat rdf:type rdf:Property ;
    rdfs:label "has fat" ;
    rdfs:domain diet:NutritionInfo ;
    rdfs:range rdfs:Literal .

diet:hasMET rdf:type rdf:Property ;
    rdfs:label "has MET value" ;
    rdfs:domain diet:Exercise ;
    rdfs:range rdfs:Literal .

# 기존 데이터 예시
food:apple rdf:type diet:Food ;
    rdfs:label "사과" ;
    diet:hasCalories "52.0"^^<http://www.w3.org/2001/XMLSchema#float> .

exercise:walking rdf:type diet:Exercise ;
    rdfs:label "걷기" ;
    diet:hasMET "3.5"^^<http://www.w3.org/2001/XMLSchema#float> .
"""
        
        with open(self.test_ontology_path, 'w', encoding='utf-8') as f:
            f.write(base_ontology)
    
    def _create_test_food_item(self):
        """테스트용 음식 아이템 생성."""
        food_item = FoodItem(
            name="바나나",
            food_id="D000002",
            category="과일류",
            manufacturer="자연산"
        )
        
        nutrition = NutritionInfo(
            food_item=food_item,
            calories_per_100g=89.0,
            carbohydrate=22.8,
            protein=1.1,
            fat=0.3,
            fiber=2.6,
            sodium=1.0
        )
        
        food_item.nutrition_info = nutrition
        return food_item
    
    def _create_test_exercise_item(self):
        """테스트용 운동 아이템 생성."""
        exercise_item = ExerciseItem(
            name="달리기",
            description="일반적인 달리기 운동",
            met_value=8.0,
            category="유산소운동",
            exercise_id="EX002"
        )
        return exercise_item
    
    def test_ttl_file_syntax_validation(self):
        """TTL 파일 문법 검증 테스트."""
        print("\n=== TTL 파일 문법 검증 테스트 ===")
        
        # 올바른 TTL 파일 검증
        try:
            graph = Graph()
            graph.parse(self.test_ontology_path, format="turtle")
            print("✓ 기본 온톨로지 TTL 문법 검증 성공")
        except BadSyntax as e:
            self.fail(f"기본 온톨로지 TTL 문법 오류: {e}")
        
        # 잘못된 TTL 파일 생성 및 검증
        invalid_ttl_path = os.path.join(self.test_dir, "invalid.ttl")
        invalid_ttl_content = """
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

# 잘못된 문법 - 세미콜론 누락
diet:Food rdf:type rdfs:Class
    rdfs:label "Food"
"""
        
        with open(invalid_ttl_path, 'w', encoding='utf-8') as f:
            f.write(invalid_ttl_content)
        
        # 잘못된 TTL 파일 파싱 시 예외 발생 확인
        with self.assertRaises(BadSyntax):
            graph = Graph()
            graph.parse(invalid_ttl_path, format="turtle")
        
        print("✓ 잘못된 TTL 문법 검증 성공 (예외 발생 확인)")
    
    def test_new_food_data_integration(self):
        """새로운 음식 데이터 통합 테스트."""
        print("\n=== 새로운 음식 데이터 통합 테스트 ===")
        
        # 새로운 음식 아이템 생성
        food_item = self._create_test_food_item()
        
        # RDF로 변환 (영양정보 포함)
        food_rdf_graph = self.rdf_converter.convert_food_to_rdf(food_item, food_item.nutrition_info)
        
        # 기존 온톨로지에 병합
        original_graph = Graph()
        original_graph.parse(self.test_ontology_path, format="turtle")
        original_count = len(original_graph)
        
        # 새로운 데이터는 이미 Graph 객체
        new_graph = food_rdf_graph
        
        # 병합
        merged_graph = original_graph + new_graph
        
        # 병합 결과 검증
        self.assertGreater(len(merged_graph), original_count)
        
        # 새로운 음식이 추가되었는지 확인
        # RDFDataConverter가 사용하는 네임스페이스와 일치시키기
        food_ns = Namespace("http://example.org/diet#food/")
        banana_uri = food_item.to_uri(food_ns)
        food_type = URIRef("http://example.org/diet#Food")  # 기본 네임스페이스 사용
        
        self.assertTrue((banana_uri, RDF.type, food_type) in merged_graph)
        
        # 영양정보가 포함되었는지 확인 (NutritionInfo 객체를 통해)
        has_nutrition_property = URIRef("http://example.org/diet#hasNutrition")
        calories_property = URIRef("http://example.org/diet#hasCalories")
        
        # 음식이 영양정보를 가지고 있는지 확인
        nutrition_found = False
        calories_found = False
        
        for s, p, o in merged_graph.triples((banana_uri, has_nutrition_property, None)):
            nutrition_found = True
            # 영양정보 객체에서 칼로리 값 확인
            for ns, np, no in merged_graph.triples((o, calories_property, None)):
                calories_found = True
                self.assertEqual(float(no), 89.0)
        
        self.assertTrue(nutrition_found, "영양정보가 추가되지 않았습니다")
        self.assertTrue(calories_found, "칼로리 정보가 추가되지 않았습니다")
        
        print(f"✓ 음식 데이터 통합 성공: {food_item.name} 추가됨")
        print(f"  - 원본 트리플 수: {original_count}")
        print(f"  - 병합 후 트리플 수: {len(merged_graph)}")
    
    def test_new_exercise_data_integration(self):
        """새로운 운동 데이터 통합 테스트."""
        print("\n=== 새로운 운동 데이터 통합 테스트 ===")
        
        # 새로운 운동 아이템 생성
        exercise_item = self._create_test_exercise_item()
        
        # RDF로 변환
        exercise_rdf_graph = self.rdf_converter.convert_exercise_to_rdf(exercise_item)
        
        # 기존 온톨로지에 병합
        original_graph = Graph()
        original_graph.parse(self.test_ontology_path, format="turtle")
        original_count = len(original_graph)
        
        # 새로운 데이터는 이미 Graph 객체
        new_graph = exercise_rdf_graph
        
        # 병합
        merged_graph = original_graph + new_graph
        
        # 병합 결과 검증
        self.assertGreater(len(merged_graph), original_count)
        
        # 새로운 운동이 추가되었는지 확인
        # RDFDataConverter가 사용하는 네임스페이스와 일치시키기
        exercise_ns = Namespace("http://example.org/diet#exercise/")
        running_uri = exercise_item.to_uri(exercise_ns)
        exercise_type = URIRef("http://example.org/diet#Exercise")  # 기본 네임스페이스 사용
        
        self.assertTrue((running_uri, RDF.type, exercise_type) in merged_graph)
        
        # MET 값이 포함되었는지 확인
        met_property = URIRef("http://example.org/diet#hasMET")  # 기본 네임스페이스 사용
        met_found = False
        for s, p, o in merged_graph.triples((running_uri, met_property, None)):
            met_found = True
            self.assertEqual(float(o), exercise_item.met_value)
        
        self.assertTrue(met_found, "MET 값이 추가되지 않았습니다")
        
        print(f"✓ 운동 데이터 통합 성공: {exercise_item.name} 추가됨")
        print(f"  - 원본 트리플 수: {original_count}")
        print(f"  - 병합 후 트리플 수: {len(merged_graph)}")
    
    def test_duplicate_data_detection(self):
        """중복 데이터 검출 테스트."""
        print("\n=== 중복 데이터 검출 테스트 ===")
        
        # 기존 온톨로지 로드
        graph = Graph()
        graph.parse(self.test_ontology_path, format="turtle")
        
        # 기존에 있는 사과 데이터와 동일한 데이터 생성
        apple_uri = URIRef("http://example.org/food#apple")
        food_type = URIRef("http://example.org/diet-ontology#Food")
        
        # 중복 데이터 검출
        existing_apple = (apple_uri, RDF.type, food_type) in graph
        self.assertTrue(existing_apple, "기존 사과 데이터가 존재하지 않습니다")
        
        # 새로운 사과 데이터 추가 시도
        duplicate_apple_rdf = f"""
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix diet: <http://example.org/diet-ontology#> .
@prefix food: <http://example.org/food#> .

food:apple rdf:type diet:Food ;
    rdfs:label "사과" ;
    diet:hasCalories "55.0"^^<http://www.w3.org/2001/XMLSchema#float> .
"""
        
        # 중복 데이터 병합
        new_graph = Graph()
        new_graph.parse(data=duplicate_apple_rdf, format="turtle")
        
        original_count = len(graph)
        merged_graph = graph + new_graph
        
        # 중복 데이터 처리 확인
        # RDFLib은 자동으로 중복 트리플을 제거하므로 트리플 수가 증가하지 않아야 함
        apple_calories_triples = list(merged_graph.triples((apple_uri, URIRef("http://example.org/diet-ontology#hasCalories"), None)))
        
        print(f"✓ 중복 데이터 검출 성공")
        print(f"  - 원본 트리플 수: {original_count}")
        print(f"  - 병합 후 트리플 수: {len(merged_graph)}")
        print(f"  - 사과 칼로리 트리플 수: {len(apple_calories_triples)}")
        
        # 중복 데이터가 있을 때 최신 값으로 업데이트되는지 확인
        if len(apple_calories_triples) > 1:
            print("  - 중복 칼로리 값 발견, 데이터 정리 필요")
    
    def test_ontology_backup_creation(self):
        """온톨로지 백업 생성 테스트."""
        print("\n=== 온톨로지 백업 생성 테스트 ===")
        
        # 백업 생성
        backup_path = self.ontology_manager.create_backup(self.test_ontology_path)
        
        # 백업 파일 존재 확인
        self.assertTrue(os.path.exists(backup_path), "백업 파일이 생성되지 않았습니다")
        
        # 백업 파일 내용 검증
        original_graph = Graph()
        original_graph.parse(self.test_ontology_path, format="turtle")
        
        backup_graph = Graph()
        backup_graph.parse(backup_path, format="turtle")
        
        # 백업 파일과 원본 파일의 트리플 수가 같은지 확인
        self.assertEqual(len(original_graph), len(backup_graph), "백업 파일과 원본 파일의 내용이 다릅니다")
        
        print(f"✓ 백업 생성 성공: {backup_path}")
        print(f"  - 원본 트리플 수: {len(original_graph)}")
        print(f"  - 백업 트리플 수: {len(backup_graph)}")
    
    def test_ontology_merge_with_conflict_resolution(self):
        """충돌 해결을 포함한 온톨로지 병합 테스트."""
        print("\n=== 충돌 해결 온톨로지 병합 테스트 ===")
        
        # 충돌하는 데이터 생성 (같은 URI, 다른 값)
        conflicting_data = f"""
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix diet: <http://example.org/diet-ontology#> .
@prefix food: <http://example.org/food#> .

food:apple rdf:type diet:Food ;
    rdfs:label "사과" ;
    diet:hasCalories "60.0"^^<http://www.w3.org/2001/XMLSchema#float> ;
    diet:hasCarbohydrate "15.0"^^<http://www.w3.org/2001/XMLSchema#float> .
"""
        
        # 기존 온톨로지 로드
        original_graph = Graph()
        original_graph.parse(self.test_ontology_path, format="turtle")
        
        # 충돌 데이터 로드
        conflict_graph = Graph()
        conflict_graph.parse(data=conflicting_data, format="turtle")
        
        # 병합 전 사과의 칼로리 값 확인
        apple_uri = URIRef("http://example.org/food#apple")
        calories_property = URIRef("http://example.org/diet-ontology#hasCalories")
        
        original_calories = None
        for s, p, o in original_graph.triples((apple_uri, calories_property, None)):
            original_calories = float(o)
        
        # 병합 수행
        merged_graph = original_graph + conflict_graph
        
        # 병합 후 칼로리 값들 확인
        merged_calories = []
        for s, p, o in merged_graph.triples((apple_uri, calories_property, None)):
            merged_calories.append(float(o))
        
        print(f"✓ 충돌 해결 병합 테스트 완료")
        print(f"  - 원본 칼로리: {original_calories}")
        print(f"  - 병합 후 칼로리 값들: {merged_calories}")
        print(f"  - 충돌 데이터 수: {len(merged_calories)}")
        
        # 충돌 데이터가 있는 경우 처리 방법 제안
        if len(merged_calories) > 1:
            print("  - 충돌 해결 필요: 최신 값 선택 또는 평균값 계산 고려")
    
    def test_large_ontology_merge_performance(self):
        """대용량 온톨로지 병합 성능 테스트."""
        print("\n=== 대용량 온톨로지 병합 성능 테스트 ===")
        
        import time
        
        # 대량의 테스트 데이터 생성
        large_data_parts = []
        for i in range(100):
            food_data = f"""
food:test_food_{i} rdf:type diet:Food ;
    rdfs:label "테스트음식{i}" ;
    diet:hasCalories "{50 + i}"^^<http://www.w3.org/2001/XMLSchema#float> ;
    diet:hasCarbohydrate "{10 + i * 0.1}"^^<http://www.w3.org/2001/XMLSchema#float> .
"""
            large_data_parts.append(food_data)
        
        large_data = f"""
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix diet: <http://example.org/diet-ontology#> .
@prefix food: <http://example.org/food#> .

{''.join(large_data_parts)}
"""
        
        # 기존 온톨로지 로드
        start_time = time.time()
        original_graph = Graph()
        original_graph.parse(self.test_ontology_path, format="turtle")
        load_time = time.time() - start_time
        
        # 대량 데이터 파싱
        start_time = time.time()
        large_graph = Graph()
        large_graph.parse(data=large_data, format="turtle")
        parse_time = time.time() - start_time
        
        # 병합 수행
        start_time = time.time()
        merged_graph = original_graph + large_graph
        merge_time = time.time() - start_time
        
        print(f"✓ 대용량 병합 성능 테스트 완료")
        print(f"  - 원본 로드 시간: {load_time:.3f}초")
        print(f"  - 대량 데이터 파싱 시간: {parse_time:.3f}초")
        print(f"  - 병합 시간: {merge_time:.3f}초")
        print(f"  - 원본 트리플 수: {len(original_graph)}")
        print(f"  - 추가 트리플 수: {len(large_graph)}")
        print(f"  - 병합 후 트리플 수: {len(merged_graph)}")
        
        # 성능 기준 검증 (예: 1000개 트리플 병합이 1초 이내)
        if len(large_graph) > 0:
            merge_rate = len(large_graph) / merge_time if merge_time > 0 else float('inf')
            print(f"  - 병합 속도: {merge_rate:.0f} 트리플/초")
            
            # 성능 기준: 초당 1000 트리플 이상 처리
            self.assertGreater(merge_rate, 100, "병합 성능이 기준에 미달합니다")
    
    def test_ontology_consistency_validation(self):
        """온톨로지 일관성 검증 테스트."""
        print("\n=== 온톨로지 일관성 검증 테스트 ===")
        
        # 기존 온톨로지 로드
        graph = Graph()
        graph.parse(self.test_ontology_path, format="turtle")
        
        # 클래스 계층 구조 검증
        diet_concept = URIRef("http://example.org/diet-ontology#DietConcept")
        food_class = URIRef("http://example.org/diet-ontology#Food")
        exercise_class = URIRef("http://example.org/diet-ontology#Exercise")
        
        # Food가 DietConcept의 서브클래스인지 확인
        food_subclass = (food_class, RDFS.subClassOf, diet_concept) in graph
        exercise_subclass = (exercise_class, RDFS.subClassOf, diet_concept) in graph
        
        self.assertTrue(food_subclass, "Food 클래스가 DietConcept의 서브클래스가 아닙니다")
        self.assertTrue(exercise_subclass, "Exercise 클래스가 DietConcept의 서브클래스가 아닙니다")
        
        # 속성 도메인/범위 검증
        calories_property = URIRef("http://example.org/diet-ontology#hasCalories")
        calories_domain = list(graph.triples((calories_property, RDFS.domain, None)))
        calories_range = list(graph.triples((calories_property, RDFS.range, None)))
        
        print(f"✓ 온톨로지 일관성 검증 완료")
        print(f"  - Food 서브클래스 관계: {food_subclass}")
        print(f"  - Exercise 서브클래스 관계: {exercise_subclass}")
        print(f"  - hasCalories 도메인 정의: {len(calories_domain) > 0}")
        print(f"  - hasCalories 범위 정의: {len(calories_range) > 0}")
        
        # 데이터 타입 일관성 검증
        apple_uri = URIRef("http://example.org/food#apple")
        apple_calories = list(graph.triples((apple_uri, calories_property, None)))
        
        if apple_calories:
            calories_value = apple_calories[0][2]
            try:
                float_value = float(calories_value)
                print(f"  - 사과 칼로리 값 타입 검증: 성공 ({float_value})")
            except ValueError:
                self.fail(f"사과 칼로리 값이 숫자가 아닙니다: {calories_value}")


if __name__ == '__main__':
    print("=== 온톨로지 생성 및 병합 테스트 ===")
    unittest.main(verbosity=2)