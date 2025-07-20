"""
온톨로지 스키마 매니저 테스트 모듈.
이 모듈은 온톨로지 스키마 매니저의 기능을 테스트합니다.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from ontology_schema_manager import OntologySchemaManager
from exceptions import OntologyError


class TestOntologySchemaManager(unittest.TestCase):
    """온톨로지 스키마 매니저 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        
        # 테스트용 기본 온톨로지 파일 생성
        self.base_ontology_path = os.path.join(self.test_dir, "test-diet-ontology.ttl")
        self._create_test_ontology()
        
        # 온톨로지 스키마 매니저 초기화
        self.schema_manager = OntologySchemaManager(
            base_ontology_path=self.base_ontology_path,
            namespace_uri="http://example.org/diet#"
        )
    
    def tearDown(self):
        """테스트 정리."""
        # 임시 디렉토리 삭제
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_ontology(self):
        """테스트용 기본 온톨로지 파일을 생성합니다."""
        ontology_content = """
@prefix : <http://example.org/diet#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:DietConcept a owl:Class ;
    rdfs:label "다이어트 개념"@ko .

:Food a owl:Class ;
    rdfs:subClassOf :DietConcept ;
    rdfs:label "음식"@ko .

:Exercise a owl:Class ;
    rdfs:subClassOf :DietConcept ;
    rdfs:label "운동"@ko .

:hasCalorie a owl:DatatypeProperty ;
    rdfs:domain :Food ;
    rdfs:range xsd:decimal ;
    rdfs:label "칼로리 정보"@ko .

:hasCarbohydrate a owl:DatatypeProperty ;
    rdfs:domain :Food ;
    rdfs:range xsd:decimal ;
    rdfs:label "탄수화물(g)"@ko .

:hasProtein a owl:DatatypeProperty ;
    rdfs:domain :Food ;
    rdfs:range xsd:decimal ;
    rdfs:label "단백질(g)"@ko .

:hasFat a owl:DatatypeProperty ;
    rdfs:domain :Food ;
    rdfs:range xsd:decimal ;
    rdfs:label "지방(g)"@ko .
"""
        
        with open(self.base_ontology_path, 'w', encoding='utf-8') as f:
            f.write(ontology_content)
    
    def test_initialization(self):
        """초기화 테스트."""
        self.assertIsNotNone(self.schema_manager.graph)
        self.assertEqual(self.schema_manager.base_ontology_path, self.base_ontology_path)
        self.assertEqual(self.schema_manager.namespace_uri, "http://example.org/diet#")
        
        # 기존 온톨로지가 로드되었는지 확인
        self.assertGreater(len(self.schema_manager.graph), 0)
    
    def test_initialization_without_base_ontology(self):
        """기존 온톨로지 파일이 없는 경우 초기화 테스트."""
        non_existent_path = os.path.join(self.test_dir, "non_existent.ttl")
        
        # 경고 로그가 출력되지만 예외는 발생하지 않아야 함
        schema_manager = OntologySchemaManager(
            base_ontology_path=non_existent_path,
            namespace_uri="http://example.org/diet#"
        )
        
        self.assertIsNotNone(schema_manager.graph)
    
    def test_define_food_classes(self):
        """음식 관련 클래스 정의 테스트."""
        initial_class_count = len(list(self.schema_manager.graph.subjects(
            self.schema_manager.graph.namespace_manager.store.namespace("rdf")["type"],
            self.schema_manager.graph.namespace_manager.store.namespace("owl")["Class"]
        )))
        
        self.schema_manager.define_food_classes()
        
        # 새로운 클래스들이 추가되었는지 확인
        final_class_count = len(list(self.schema_manager.graph.subjects(
            self.schema_manager.graph.namespace_manager.store.namespace("rdf")["type"],
            self.schema_manager.graph.namespace_manager.store.namespace("owl")["Class"]
        )))
        
        self.assertGreater(final_class_count, initial_class_count)
        
        # 특정 클래스가 정의되었는지 확인
        food_item_uri = self.schema_manager.ns.FoodItem
        self.assertTrue((food_item_uri, 
                        self.schema_manager.graph.namespace_manager.store.namespace("rdf")["type"],
                        self.schema_manager.graph.namespace_manager.store.namespace("owl")["Class"]) 
                       in self.schema_manager.graph)
    
    def test_define_exercise_classes(self):
        """운동 관련 클래스 정의 테스트."""
        self.schema_manager.define_exercise_classes()
        
        # ExerciseItem 클래스가 정의되었는지 확인
        exercise_item_uri = self.schema_manager.ns.ExerciseItem
        from rdflib.namespace import RDF, OWL
        
        self.assertTrue((exercise_item_uri, RDF.type, OWL.Class) in self.schema_manager.graph)
    
    def test_define_food_properties(self):
        """음식 관련 속성 정의 테스트."""
        self.schema_manager.define_food_classes()  # 클래스 먼저 정의
        self.schema_manager.define_food_properties()
        
        # hasServingSize 속성이 정의되었는지 확인
        serving_size_uri = self.schema_manager.ns.hasServingSize
        from rdflib.namespace import RDF, OWL
        
        self.assertTrue((serving_size_uri, RDF.type, OWL.DatatypeProperty) in self.schema_manager.graph)
    
    def test_define_exercise_properties(self):
        """운동 관련 속성 정의 테스트."""
        self.schema_manager.define_exercise_classes()  # 클래스 먼저 정의
        self.schema_manager.define_exercise_properties()
        
        # hasMET 속성이 정의되었는지 확인
        met_uri = self.schema_manager.ns.hasMET
        from rdflib.namespace import RDF, OWL
        
        self.assertTrue((met_uri, RDF.type, OWL.DatatypeProperty) in self.schema_manager.graph)
    
    def test_extend_schema(self):
        """전체 스키마 확장 테스트."""
        initial_triple_count = len(self.schema_manager.graph)
        
        self.schema_manager.extend_schema()
        
        # 트리플 수가 증가했는지 확인
        final_triple_count = len(self.schema_manager.graph)
        self.assertGreater(final_triple_count, initial_triple_count)
    
    def test_validate_schema_success(self):
        """스키마 검증 성공 테스트."""
        self.schema_manager.extend_schema()
        
        validation_result = self.schema_manager.validate_schema()
        
        self.assertTrue(validation_result['is_valid'])
        self.assertEqual(len(validation_result['errors']), 0)
    
    def test_validate_schema_empty_graph(self):
        """빈 그래프 스키마 검증 테스트."""
        # 새로운 빈 스키마 매니저 생성
        empty_schema_manager = OntologySchemaManager(
            base_ontology_path="non_existent.ttl",
            namespace_uri="http://example.org/diet#"
        )
        
        validation_result = empty_schema_manager.validate_schema()
        
        self.assertFalse(validation_result['is_valid'])
        self.assertGreater(len(validation_result['errors']), 0)
    
    def test_save_extended_schema(self):
        """확장된 스키마 저장 테스트."""
        self.schema_manager.extend_schema()
        
        output_path = os.path.join(self.test_dir, "extended_schema.ttl")
        saved_path = self.schema_manager.save_extended_schema(output_path)
        
        # 파일이 저장되었는지 확인
        self.assertEqual(saved_path, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        # 파일 내용이 유효한 TTL인지 확인
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn("@prefix", content)
        self.assertIn("owl:Class", content)
    
    def test_save_extended_schema_default_path(self):
        """기본 경로로 확장된 스키마 저장 테스트."""
        self.schema_manager.extend_schema()
        
        # 현재 디렉토리를 테스트 디렉토리로 변경
        original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        try:
            saved_path = self.schema_manager.save_extended_schema()
            
            # 파일이 저장되었는지 확인
            self.assertTrue(os.path.exists(saved_path))
            self.assertTrue(saved_path.startswith("extended-diet-ontology_"))
            self.assertTrue(saved_path.endswith(".ttl"))
        finally:
            os.chdir(original_cwd)
    
    def test_get_schema_statistics(self):
        """스키마 통계 정보 조회 테스트."""
        self.schema_manager.extend_schema()
        
        stats = self.schema_manager.get_schema_statistics()
        
        # 통계 정보가 올바르게 반환되는지 확인
        self.assertIn('total_triples', stats)
        self.assertIn('classes', stats)
        self.assertIn('data_properties', stats)
        self.assertIn('object_properties', stats)
        
        # 값들이 0보다 큰지 확인
        self.assertGreater(stats['total_triples'], 0)
        self.assertGreater(stats['classes'], 0)
        self.assertGreater(stats['data_properties'], 0)
        self.assertGreater(stats['object_properties'], 0)
    
    @patch('ontology_schema_manager.Graph.parse')
    def test_load_base_ontology_failure(self, mock_parse):
        """기존 온톨로지 로드 실패 테스트."""
        mock_parse.side_effect = Exception("파싱 오류")
        
        with self.assertRaises(OntologyError):
            OntologySchemaManager(
                base_ontology_path=self.base_ontology_path,
                namespace_uri="http://example.org/diet#"
            )
    
    @patch('builtins.open')
    def test_save_extended_schema_failure(self, mock_open):
        """스키마 저장 실패 테스트."""
        mock_open.side_effect = IOError("파일 저장 실패")
        
        self.schema_manager.extend_schema()
        
        with self.assertRaises(OntologyError):
            self.schema_manager.save_extended_schema("test_output.ttl")
    
    def test_namespace_binding(self):
        """네임스페이스 바인딩 테스트."""
        # 네임스페이스가 올바르게 바인딩되었는지 확인
        namespaces = dict(self.schema_manager.graph.namespaces())
        
        self.assertIn('', namespaces.values())  # 기본 네임스페이스
        self.assertIn('http://www.w3.org/1999/02/22-rdf-syntax-ns#', namespaces.values())  # RDF
        self.assertIn('http://www.w3.org/2000/01/rdf-schema#', namespaces.values())  # RDFS
        self.assertIn('http://www.w3.org/2002/07/owl#', namespaces.values())  # OWL
        self.assertIn('http://www.w3.org/2001/XMLSchema#', namespaces.values())  # XSD
    
    def test_class_hierarchy(self):
        """클래스 계층 구조 테스트."""
        self.schema_manager.extend_schema()
        
        from rdflib.namespace import RDFS
        
        # FoodItem이 Food의 하위 클래스인지 확인
        food_item_uri = self.schema_manager.ns.FoodItem
        food_uri = self.schema_manager.ns.Food
        
        self.assertTrue((food_item_uri, RDFS.subClassOf, food_uri) in self.schema_manager.graph)
        
        # ExerciseItem이 Exercise의 하위 클래스인지 확인
        exercise_item_uri = self.schema_manager.ns.ExerciseItem
        exercise_uri = self.schema_manager.ns.Exercise
        
        self.assertTrue((exercise_item_uri, RDFS.subClassOf, exercise_uri) in self.schema_manager.graph)
    
    def test_property_domain_range(self):
        """속성의 도메인과 범위 테스트."""
        self.schema_manager.extend_schema()
        
        from rdflib.namespace import RDFS, XSD
        
        # hasMET 속성의 도메인과 범위 확인
        met_uri = self.schema_manager.ns.hasMET
        exercise_item_uri = self.schema_manager.ns.ExerciseItem
        
        self.assertTrue((met_uri, RDFS.domain, exercise_item_uri) in self.schema_manager.graph)
        self.assertTrue((met_uri, RDFS.range, XSD.decimal) in self.schema_manager.graph)


if __name__ == '__main__':
    unittest.main()