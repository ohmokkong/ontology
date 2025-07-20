"""
온톨로지 스키마 매니저 모듈.

이 모듈은 음식/운동 관련 클래스 및 속성을 정의하고,
기존 diet-ontology.ttl과의 호환성을 보장하는 기능을 제공합니다.
"""

import os
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime

from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from exceptions import OntologyError


class OntologySchemaManager:
    """온톨로지 스키마 매니저 클래스."""
    
    def __init__(self, 
                 base_ontology_path: str = "diet-ontology.ttl",
                 namespace_uri: str = "http://example.org/diet#"):
        """
        OntologySchemaManager 초기화.
        
        Args:
            base_ontology_path: 기존 온톨로지 파일 경로
            namespace_uri: 온톨로지 네임스페이스 URI
        """
        self.base_ontology_path = base_ontology_path
        self.namespace_uri = namespace_uri
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # 네임스페이스 설정
        self.ns = Namespace(namespace_uri)
        
        # 기본 그래프 초기화
        self.graph = Graph()
        self._bind_namespaces()
        
        # 기존 온톨로지 로드
        self._load_base_ontology()
        
        self.logger.info(f"온톨로지 스키마 매니저 초기화 완료: {base_ontology_path}")
    
    def _bind_namespaces(self) -> None:
        """네임스페이스를 그래프에 바인딩합니다."""
        self.graph.bind("", self.ns)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("xsd", XSD)
    
    def _load_base_ontology(self) -> None:
        """기존 온톨로지 파일을 로드합니다."""
        if not os.path.exists(self.base_ontology_path):
            self.logger.warning(f"기존 온톨로지 파일이 없습니다: {self.base_ontology_path}")
            return
        
        try:
            self.graph.parse(self.base_ontology_path, format="turtle")
            self.logger.info(f"기존 온톨로지 로드 완료: {len(self.graph)} 트리플")
        except Exception as e:
            error_msg = f"온톨로지 로드 실패: {str(e)}"
            self.logger.error(error_msg)
            raise OntologyError(error_msg)
    
    def define_food_classes(self) -> None:
        """음식 관련 클래스들을 정의합니다."""
        food_classes = {
            'FoodItem': ('음식 아이템', 'API에서 조회된 개별 음식 아이템'),
            'NutritionInfo': ('영양 정보', '음식의 영양성분 정보'),
            'FoodConsumption': ('음식 섭취', '특정 시점의 음식 섭취 기록'),
            'FoodCategory': ('음식 카테고리', '음식의 분류 카테고리'),
            'Manufacturer': ('제조사', '음식 제조업체 정보')
        }
        
        for class_name, (label, comment) in food_classes.items():
            class_uri = self.ns[class_name]
            
            # 클래스 정의
            self.graph.add((class_uri, RDF.type, OWL.Class))
            self.graph.add((class_uri, RDFS.label, Literal(label, lang='ko')))
            self.graph.add((class_uri, RDFS.comment, Literal(comment, lang='ko')))
            
            # 상위 클래스 관계 설정
            if class_name in ['FoodItem']:
                self.graph.add((class_uri, RDFS.subClassOf, self.ns.Food))
            else:
                self.graph.add((class_uri, RDFS.subClassOf, self.ns.DietConcept))
        
        self.logger.info("음식 관련 클래스 정의 완료")
    
    def define_exercise_classes(self) -> None:
        """운동 관련 클래스들을 정의합니다."""
        exercise_classes = {
            'ExerciseItem': ('운동 아이템', 'API에서 조회된 개별 운동 아이템'),
            'ExerciseSession': ('운동 세션', '특정 시점의 운동 수행 기록'),
            'ExerciseCategory': ('운동 카테고리', '운동의 분류 카테고리'),
            'METValue': ('MET 값', '운동의 대사당량 정보')
        }
        
        for class_name, (label, comment) in exercise_classes.items():
            class_uri = self.ns[class_name]
            
            # 클래스 정의
            self.graph.add((class_uri, RDF.type, OWL.Class))
            self.graph.add((class_uri, RDFS.label, Literal(label, lang='ko')))
            self.graph.add((class_uri, RDFS.comment, Literal(comment, lang='ko')))
            
            # 상위 클래스 관계 설정
            if class_name in ['ExerciseItem']:
                self.graph.add((class_uri, RDFS.subClassOf, self.ns.Exercise))
            else:
                self.graph.add((class_uri, RDFS.subClassOf, self.ns.DietConcept))
        
        self.logger.info("운동 관련 클래스 정의 완료")
    
    def define_food_properties(self) -> None:
        """음식 관련 속성들을 정의합니다."""
        # 데이터 속성 정의
        data_properties = {
            'hasServingSize': ('1회 제공량', '음식의 1회 제공량 (g)', self.ns.FoodItem, XSD.decimal),
            'hasFiber': ('식이섬유', '식이섬유 함량 (g)', self.ns.NutritionInfo, XSD.decimal),
            'hasSodium': ('나트륨', '나트륨 함량 (mg)', self.ns.NutritionInfo, XSD.decimal),
            'hasCaloriesPer100g': ('100g당 칼로리', '100g당 칼로리 (kcal)', self.ns.NutritionInfo, XSD.decimal),
            'hasAmount': ('섭취량', '실제 섭취한 양 (g)', self.ns.FoodConsumption, XSD.decimal),
            'hasConsumedCalories': ('섭취 칼로리', '실제 섭취한 칼로리 (kcal)', self.ns.FoodConsumption, XSD.decimal),
            'hasConsumedTime': ('섭취 시간', '음식을 섭취한 시간', self.ns.FoodConsumption, XSD.dateTime),
            'hasFoodId': ('음식 ID', 'API에서 제공하는 음식 고유 식별자', self.ns.FoodItem, XSD.string)
        }
        
        for prop_name, (label, comment, domain, range_type) in data_properties.items():
            prop_uri = self.ns[prop_name]
            
            # 속성 정의
            self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            self.graph.add((prop_uri, RDFS.label, Literal(label, lang='ko')))
            self.graph.add((prop_uri, RDFS.comment, Literal(comment, lang='ko')))
            self.graph.add((prop_uri, RDFS.domain, domain))
            self.graph.add((prop_uri, RDFS.range, range_type))
        
        # 객체 속성 정의
        object_properties = {
            'hasNutritionInfo': ('영양 정보 포함', '음식이 포함하는 영양 정보', self.ns.FoodItem, self.ns.NutritionInfo),
            'consumedFood': ('섭취한 음식', '섭취 기록이 참조하는 음식', self.ns.FoodConsumption, self.ns.FoodItem),
            'belongsToCategory': ('카테고리 소속', '음식이 속하는 카테고리', self.ns.FoodItem, self.ns.FoodCategory)
        }
        
        for prop_name, (label, comment, domain, range_type) in object_properties.items():
            prop_uri = self.ns[prop_name]
            
            # 속성 정의
            self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((prop_uri, RDFS.label, Literal(label, lang='ko')))
            self.graph.add((prop_uri, RDFS.comment, Literal(comment, lang='ko')))
            self.graph.add((prop_uri, RDFS.domain, domain))
            self.graph.add((prop_uri, RDFS.range, range_type))
        
        self.logger.info("음식 관련 속성 정의 완료")
    
    def define_exercise_properties(self) -> None:
        """운동 관련 속성들을 정의합니다."""
        # 데이터 속성 정의
        data_properties = {
            'hasMET': ('MET 값', '운동의 대사당량', self.ns.ExerciseItem, XSD.decimal),
            'hasExerciseId': ('운동 ID', 'API에서 제공하는 운동 고유 식별자', self.ns.ExerciseItem, XSD.string),
            'hasDescription': ('운동 설명', '운동에 대한 상세 설명', self.ns.ExerciseItem, XSD.string),
            'hasWeight': ('체중', '운동 수행자의 체중 (kg)', self.ns.ExerciseSession, XSD.decimal),
            'hasExerciseDuration': ('운동 시간', '실제 운동 수행 시간 (분)', self.ns.ExerciseSession, XSD.decimal),
            'caloriesBurned': ('소모 칼로리', '운동으로 소모된 칼로리 (kcal)', self.ns.ExerciseSession, XSD.decimal),
            'hasExerciseTime': ('운동 시간', '운동을 수행한 시간', self.ns.ExerciseSession, XSD.dateTime)
        }
        
        for prop_name, (label, comment, domain, range_type) in data_properties.items():
            prop_uri = self.ns[prop_name]
            
            # 속성 정의
            self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            self.graph.add((prop_uri, RDFS.label, Literal(label, lang='ko')))
            self.graph.add((prop_uri, RDFS.comment, Literal(comment, lang='ko')))
            self.graph.add((prop_uri, RDFS.domain, domain))
            self.graph.add((prop_uri, RDFS.range, range_type))
        
        # 객체 속성 정의
        object_properties = {
            'performedExercise': ('수행한 운동', '운동 세션에서 수행한 운동', self.ns.ExerciseSession, self.ns.ExerciseItem),
            'hasExerciseCategory': ('운동 카테고리', '운동이 속하는 카테고리', self.ns.ExerciseItem, self.ns.ExerciseCategory)
        }
        
        for prop_name, (label, comment, domain, range_type) in object_properties.items():
            prop_uri = self.ns[prop_name]
            
            # 속성 정의
            self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((prop_uri, RDFS.label, Literal(label, lang='ko')))
            self.graph.add((prop_uri, RDFS.comment, Literal(comment, lang='ko')))
            self.graph.add((prop_uri, RDFS.domain, domain))
            self.graph.add((prop_uri, RDFS.range, range_type))
        
        self.logger.info("운동 관련 속성 정의 완료")
    
    def extend_schema(self) -> None:
        """전체 스키마 확장을 수행합니다."""
        self.logger.info("온톨로지 스키마 확장 시작")
        
        # 클래스 정의
        self.define_food_classes()
        self.define_exercise_classes()
        
        # 속성 정의
        self.define_food_properties()
        self.define_exercise_properties()
        
        self.logger.info("온톨로지 스키마 확장 완료")
    
    def save_extended_schema(self, output_path: str = None) -> str:
        """확장된 스키마를 파일로 저장합니다."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"extended-diet-ontology_{timestamp}.ttl"
        
        try:
            # TTL 형식으로 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self.graph.serialize(format='turtle'))
            
            self.logger.info(f"확장된 스키마 저장 완료: {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"스키마 저장 실패: {str(e)}"
            self.logger.error(error_msg)
            raise OntologyError(error_msg)
    
    def validate_schema(self) -> Dict[str, Union[bool, List[str]]]:
        """정의된 스키마의 유효성을 검증합니다."""
        errors = []
        warnings = []
        
        try:
            # 클래스 정의 검증
            classes = list(self.graph.subjects(RDF.type, OWL.Class))
            if not classes:
                errors.append("정의된 클래스가 없습니다.")
            
            # 속성 정의 검증
            data_properties = list(self.graph.subjects(RDF.type, OWL.DatatypeProperty))
            object_properties = list(self.graph.subjects(RDF.type, OWL.ObjectProperty))
            
            if not data_properties and not object_properties:
                errors.append("정의된 속성이 없습니다.")
            
            # TTL 문법 검증
            try:
                temp_ttl = self.graph.serialize(format='turtle')
                temp_graph = Graph()
                temp_graph.parse(data=temp_ttl, format='turtle')
            except Exception as e:
                errors.append(f"TTL 문법 오류: {str(e)}")
            
            is_valid = len(errors) == 0
            
            self.logger.info(f"스키마 검증 완료: 유효={is_valid}, 오류={len(errors)}")
            
            return {
                'is_valid': is_valid,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            error_msg = f"스키마 검증 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            return {
                'is_valid': False,
                'errors': [error_msg],
                'warnings': warnings
            }
    
    def get_schema_statistics(self) -> Dict[str, int]:
        """스키마 통계 정보를 반환합니다."""
        stats = {
            'total_triples': len(self.graph),
            'classes': len(list(self.graph.subjects(RDF.type, OWL.Class))),
            'data_properties': len(list(self.graph.subjects(RDF.type, OWL.DatatypeProperty))),
            'object_properties': len(list(self.graph.subjects(RDF.type, OWL.ObjectProperty)))
        }
        
        return stats