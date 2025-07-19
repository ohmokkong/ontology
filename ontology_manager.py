"""
온톨로지 매니저.

기존 TTL 파일 로드 및 파싱, 새로운 RDF 그래프와 기존 온톨로지 병합,
중복 데이터 검출 및 처리 로직을 제공합니다.
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
from rdflib.exceptions import ParserError
from rdflib.plugins.parsers.notation3 import BadSyntax

from integrated_models import FoodItem, NutritionInfo, ExerciseItem, FoodConsumption, ExerciseSession
from exceptions import DataValidationError, CalorieCalculationError


# 네임스페이스 정의
DIET_NS = Namespace("http://example.org/diet#")
RDF_NS = RDF
RDFS_NS = RDFS
OWL_NS = OWL
XSD_NS = XSD


@dataclass
class ValidationResult:
    """TTL 파일 검증 결과."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    triples_count: int = 0
    classes_count: int = 0
    properties_count: int = 0


@dataclass
class MergeResult:
    """온톨로지 병합 결과."""
    success: bool
    merged_triples: int
    duplicate_triples: int
    new_triples: int
    backup_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Duplicate:
    """중복 데이터 정보."""
    subject: URIRef
    predicate: URIRef
    object: Any
    source_graph: str
    duplicate_type: str  # "exact", "similar", "conflict"


class OntologyManager:
    """
    온톨로지 파일 관리 매니저.
    
    기존 TTL 파일 로드 및 파싱, 새로운 RDF 그래프와 기존 온톨로지 병합,
    중복 데이터 검출 및 처리 로직을 제공합니다.
    """
    
    def __init__(self, base_namespace: str = "http://example.org/diet#"):
        """
        OntologyManager 초기화.
        
        Args:
            base_namespace: 기본 네임스페이스 URI
        """
        self.base_namespace = Namespace(base_namespace)
        self.graph = Graph()
        
        # 네임스페이스 바인딩
        self.graph.bind("", self.base_namespace)
        self.graph.bind("rdf", RDF_NS)
        self.graph.bind("rdfs", RDFS_NS)
        self.graph.bind("owl", OWL_NS)
        self.graph.bind("xsd", XSD_NS)
        
        # 통계 정보
        self.stats = {
            "loaded_files": 0,
            "merged_graphs": 0,
            "created_backups": 0,
            "validation_checks": 0
        }
        
        print("✓ 온톨로지 매니저 초기화 완료")
        print(f"  - 기본 네임스페이스: {base_namespace}")
    
    def load_existing_ontology(self, file_path: str) -> Graph:
        """
        기존 TTL 파일을 로드하고 파싱합니다.
        
        Args:
            file_path: TTL 파일 경로
            
        Returns:
            Graph: 로드된 RDF 그래프
            
        Raises:
            DataValidationError: 파일 로드 실패 시
        """
        if not os.path.exists(file_path):
            raise DataValidationError(f"온톨로지 파일을 찾을 수 없습니다: {file_path}")
        
        try:
            graph = Graph()
            
            # 네임스페이스 바인딩
            graph.bind("", self.base_namespace)
            graph.bind("rdf", RDF_NS)
            graph.bind("rdfs", RDFS_NS)
            graph.bind("owl", OWL_NS)
            graph.bind("xsd", XSD_NS)
            
            # TTL 파일 파싱
            graph.parse(file_path, format="turtle")
            
            # 통계 업데이트
            self.stats["loaded_files"] += 1
            
            print(f"✓ 온톨로지 파일 로드 완료: {file_path}")
            print(f"  - 트리플 수: {len(graph)}")
            print(f"  - 클래스 수: {len(list(graph.subjects(RDF.type, OWL.Class)))}")
            print(f"  - 속성 수: {len(list(graph.subjects(RDF.type, OWL.DatatypeProperty))) + len(list(graph.subjects(RDF.type, OWL.ObjectProperty)))}")
            
            return graph
            
        except (ParserError, BadSyntax) as e:
            raise DataValidationError(f"TTL 파일 파싱 오류: {str(e)}")
        except Exception as e:
            raise DataValidationError(f"온톨로지 로드 실패: {str(e)}")
    
    def merge_with_existing(self, new_graph: Graph, existing_path: str) -> MergeResult:
        """
        새로운 RDF 그래프를 기존 온톨로지와 병합합니다.
        
        Args:
            new_graph: 병합할 새로운 그래프
            existing_path: 기존 온톨로지 파일 경로
            
        Returns:
            MergeResult: 병합 결과
        """
        print(f"📊 온톨로지 병합 시작: {existing_path}")
        
        try:
            # 기존 온톨로지 로드
            existing_graph = self.load_existing_ontology(existing_path)
            
            # 백업 생성
            backup_path = self.create_backup(existing_path)
            
            # 중복 검출
            duplicates = self.detect_duplicates(new_graph, existing_graph)
            
            # 병합 수행
            merged_graph = Graph()
            
            # 네임스페이스 바인딩 복사
            for prefix, namespace in existing_graph.namespaces():
                merged_graph.bind(prefix, namespace)
            
            # 기존 그래프의 모든 트리플 추가
            for triple in existing_graph:
                merged_graph.add(triple)
            
            # 새로운 그래프에서 중복되지 않은 트리플만 추가
            new_triples = 0
            duplicate_triples = 0
            
            for triple in new_graph:
                if triple in existing_graph:
                    duplicate_triples += 1
                else:
                    merged_graph.add(triple)
                    new_triples += 1
            
            # 병합된 그래프를 원본 파일에 저장
            self.save_ontology(merged_graph, existing_path)
            
            # 통계 업데이트
            self.stats["merged_graphs"] += 1
            
            result = MergeResult(
                success=True,
                merged_triples=len(merged_graph),
                duplicate_triples=duplicate_triples,
                new_triples=new_triples,
                backup_path=backup_path
            )
            
            print(f"✓ 온톨로지 병합 완료:")
            print(f"  - 총 트리플: {result.merged_triples}")
            print(f"  - 새로운 트리플: {result.new_triples}")
            print(f"  - 중복 트리플: {result.duplicate_triples}")
            print(f"  - 백업 파일: {backup_path}")
            
            return result
            
        except Exception as e:
            return MergeResult(
                success=False,
                merged_triples=0,
                duplicate_triples=0,
                new_triples=0,
                errors=[f"병합 실패: {str(e)}"]
            )
    
    def detect_duplicates(self, graph1: Graph, graph2: Graph) -> List[Duplicate]:
        """
        두 그래프 간의 중복 데이터를 검출합니다.
        
        Args:
            graph1: 첫 번째 그래프
            graph2: 두 번째 그래프
            
        Returns:
            List[Duplicate]: 검출된 중복 데이터 목록
        """
        duplicates = []
        
        # 정확한 중복 검출
        for triple in graph1:
            if triple in graph2:
                duplicates.append(Duplicate(
                    subject=triple[0],
                    predicate=triple[1],
                    object=triple[2],
                    source_graph="both",
                    duplicate_type="exact"
                ))
        
        # 유사한 중복 검출 (같은 주어와 술어를 가지지만 다른 객체)
        subjects_predicates_1 = set((s, p) for s, p, o in graph1)
        subjects_predicates_2 = set((s, p) for s, p, o in graph2)
        
        common_sp = subjects_predicates_1.intersection(subjects_predicates_2)
        
        for s, p in common_sp:
            objects_1 = set(graph1.objects(s, p))
            objects_2 = set(graph2.objects(s, p))
            
            if objects_1 != objects_2:
                # 충돌하는 값들
                for obj in objects_1.union(objects_2):
                    duplicates.append(Duplicate(
                        subject=s,
                        predicate=p,
                        object=obj,
                        source_graph="graph1" if obj in objects_1 else "graph2",
                        duplicate_type="conflict" if len(objects_1.intersection(objects_2)) == 0 else "similar"
                    ))
        
        print(f"🔍 중복 검출 완료: {len(duplicates)}개 발견")
        return duplicates
    
    def create_backup(self, file_path: str) -> str:
        """
        온톨로지 파일의 백업을 생성합니다.
        
        Args:
            file_path: 백업할 파일 경로
            
        Returns:
            str: 생성된 백업 파일 경로
            
        Raises:
            DataValidationError: 백업 생성 실패 시
        """
        if not os.path.exists(file_path):
            raise DataValidationError(f"백업할 파일을 찾을 수 없습니다: {file_path}")
        
        try:
            # 백업 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path_obj = Path(file_path)
            backup_filename = f"{file_path_obj.stem}_backup_{timestamp}{file_path_obj.suffix}"
            backup_path = file_path_obj.parent / backup_filename
            
            # 파일 복사
            shutil.copy2(file_path, backup_path)
            
            # 통계 업데이트
            self.stats["created_backups"] += 1
            
            print(f"✓ 백업 파일 생성: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            raise DataValidationError(f"백업 생성 실패: {str(e)}")
    
    def save_ontology(self, graph: Graph, output_path: str) -> bool:
        """
        RDF 그래프를 TTL 파일로 저장합니다.
        
        Args:
            graph: 저장할 RDF 그래프
            output_path: 출력 파일 경로
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 디렉토리가 없으면 생성
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # TTL 형식으로 저장
            graph.serialize(destination=output_path, format="turtle")
            
            print(f"✓ 온톨로지 저장 완료: {output_path}")
            print(f"  - 트리플 수: {len(graph)}")
            
            return True
            
        except Exception as e:
            print(f"❌ 온톨로지 저장 실패: {str(e)}")
            return False
    
    def validate_ttl_syntax(self, file_path: str) -> ValidationResult:
        """
        TTL 파일의 문법을 검증합니다.
        
        Args:
            file_path: 검증할 TTL 파일 경로
            
        Returns:
            ValidationResult: 검증 결과
        """
        print(f"🔍 TTL 문법 검증: {file_path}")
        
        result = ValidationResult(is_valid=False)
        
        if not os.path.exists(file_path):
            result.errors.append(f"파일을 찾을 수 없습니다: {file_path}")
            return result
        
        try:
            # 임시 그래프로 파싱 시도
            temp_graph = Graph()
            temp_graph.parse(file_path, format="turtle")
            
            # 기본 통계 수집
            result.triples_count = len(temp_graph)
            result.classes_count = len(list(temp_graph.subjects(RDF.type, OWL.Class)))
            result.properties_count = (
                len(list(temp_graph.subjects(RDF.type, OWL.DatatypeProperty))) +
                len(list(temp_graph.subjects(RDF.type, OWL.ObjectProperty)))
            )
            
            # 스키마 검증
            self._validate_schema(temp_graph, result)
            
            result.is_valid = len(result.errors) == 0
            
            # 통계 업데이트
            self.stats["validation_checks"] += 1
            
            print(f"✓ TTL 검증 완료:")
            print(f"  - 유효성: {'통과' if result.is_valid else '실패'}")
            print(f"  - 트리플 수: {result.triples_count}")
            print(f"  - 클래스 수: {result.classes_count}")
            print(f"  - 속성 수: {result.properties_count}")
            print(f"  - 오류 수: {len(result.errors)}")
            print(f"  - 경고 수: {len(result.warnings)}")
            
            return result
            
        except (ParserError, BadSyntax) as e:
            result.errors.append(f"TTL 문법 오류: {str(e)}")
            return result
        except Exception as e:
            result.errors.append(f"검증 중 오류 발생: {str(e)}")
            return result
    
    def _validate_schema(self, graph: Graph, result: ValidationResult) -> None:
        """스키마 유효성 검증."""
        # 클래스 검증
        for cls in graph.subjects(RDF.type, OWL.Class):
            # 클래스에 라벨이 있는지 확인
            if not list(graph.objects(cls, RDFS.label)):
                result.warnings.append(f"클래스 {cls}에 라벨이 없습니다")
        
        # 속성 검증
        for prop in graph.subjects(RDF.type, OWL.DatatypeProperty):
            # 도메인과 범위 확인
            domains = list(graph.objects(prop, RDFS.domain))
            ranges = list(graph.objects(prop, RDFS.range))
            
            if not domains:
                result.warnings.append(f"데이터 속성 {prop}에 도메인이 정의되지 않았습니다")
            if not ranges:
                result.warnings.append(f"데이터 속성 {prop}에 범위가 정의되지 않았습니다")
        
        for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
            # 도메인과 범위 확인
            domains = list(graph.objects(prop, RDFS.domain))
            ranges = list(graph.objects(prop, RDFS.range))
            
            if not domains:
                result.warnings.append(f"객체 속성 {prop}에 도메인이 정의되지 않았습니다")
            if not ranges:
                result.warnings.append(f"객체 속성 {prop}에 범위가 정의되지 않았습니다")
    
    def extend_ontology_schema(self, graph: Graph) -> Graph:
        """
        온톨로지 스키마를 확장하여 음식/운동 관련 클래스와 속성을 추가합니다.
        
        Args:
            graph: 확장할 그래프
            
        Returns:
            Graph: 확장된 그래프
        """
        print("🔧 온톨로지 스키마 확장 중...")
        
        # 새로운 클래스 정의
        new_classes = [
            (self.base_namespace.NutritionInfo, "영양 정보"),
            (self.base_namespace.FoodConsumption, "음식 섭취"),
            (self.base_namespace.ExerciseSession, "운동 세션"),
            (self.base_namespace.User, "사용자")
        ]
        
        for cls_uri, label in new_classes:
            graph.add((cls_uri, RDF.type, OWL.Class))
            graph.add((cls_uri, RDFS.label, Literal(label, lang="ko")))
            graph.add((cls_uri, RDFS.subClassOf, self.base_namespace.DietConcept))
        
        # 새로운 데이터 속성 정의
        new_data_properties = [
            # 영양 정보 속성
            (self.base_namespace.hasCaloriesPer100g, self.base_namespace.NutritionInfo, XSD.decimal, "100g당 칼로리"),
            (self.base_namespace.hasFiber, self.base_namespace.NutritionInfo, XSD.decimal, "식이섬유(g)"),
            (self.base_namespace.hasSodium, self.base_namespace.NutritionInfo, XSD.decimal, "나트륨(mg)"),
            
            # 음식 섭취 속성
            (self.base_namespace.consumedAmount, self.base_namespace.FoodConsumption, XSD.decimal, "섭취량(g)"),
            (self.base_namespace.consumedCalories, self.base_namespace.FoodConsumption, XSD.decimal, "섭취 칼로리"),
            (self.base_namespace.consumedAt, self.base_namespace.FoodConsumption, XSD.dateTime, "섭취 시간"),
            
            # 운동 세션 속성
            (self.base_namespace.hasMET, self.base_namespace.Exercise, XSD.decimal, "MET 값"),
            (self.base_namespace.hasWeight, self.base_namespace.ExerciseSession, XSD.decimal, "체중(kg)"),
            (self.base_namespace.sessionDuration, self.base_namespace.ExerciseSession, XSD.decimal, "세션 시간(분)"),
            (self.base_namespace.caloriesBurned, self.base_namespace.ExerciseSession, XSD.decimal, "소모 칼로리"),
            (self.base_namespace.performedAt, self.base_namespace.ExerciseSession, XSD.dateTime, "운동 시간"),
            
            # 사용자 속성
            (self.base_namespace.hasAge, self.base_namespace.User, XSD.integer, "나이"),
            (self.base_namespace.hasHeight, self.base_namespace.User, XSD.decimal, "키(cm)"),
            (self.base_namespace.hasCurrentWeight, self.base_namespace.User, XSD.decimal, "현재 체중(kg)")
        ]
        
        for prop_uri, domain, range_type, label in new_data_properties:
            graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            graph.add((prop_uri, RDFS.domain, domain))
            graph.add((prop_uri, RDFS.range, range_type))
            graph.add((prop_uri, RDFS.label, Literal(label, lang="ko")))
        
        # 새로운 객체 속성 정의
        new_object_properties = [
            (self.base_namespace.hasNutritionInfo, self.base_namespace.Food, self.base_namespace.NutritionInfo, "영양 정보 포함"),
            (self.base_namespace.consumedFood, self.base_namespace.FoodConsumption, self.base_namespace.Food, "섭취한 음식"),
            (self.base_namespace.performedExercise, self.base_namespace.ExerciseSession, self.base_namespace.Exercise, "수행한 운동"),
            (self.base_namespace.hasConsumption, self.base_namespace.User, self.base_namespace.FoodConsumption, "음식 섭취 기록"),
            (self.base_namespace.hasExerciseSession, self.base_namespace.User, self.base_namespace.ExerciseSession, "운동 세션 기록")
        ]
        
        for prop_uri, domain, range_type, label in new_object_properties:
            graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            graph.add((prop_uri, RDFS.domain, domain))
            graph.add((prop_uri, RDFS.range, range_type))
            graph.add((prop_uri, RDFS.label, Literal(label, lang="ko")))
        
        print(f"✓ 스키마 확장 완료:")
        print(f"  - 새로운 클래스: {len(new_classes)}개")
        print(f"  - 새로운 데이터 속성: {len(new_data_properties)}개")
        print(f"  - 새로운 객체 속성: {len(new_object_properties)}개")
        
        return graph
    
    def convert_food_to_rdf(self, food: FoodItem, nutrition: NutritionInfo) -> Graph:
        """
        음식 데이터를 RDF 그래프로 변환합니다.
        
        Args:
            food: 음식 아이템
            nutrition: 영양 정보
            
        Returns:
            Graph: 변환된 RDF 그래프
        """
        graph = Graph()
        
        # 네임스페이스 바인딩
        graph.bind("", self.base_namespace)
        graph.bind("rdf", RDF_NS)
        graph.bind("rdfs", RDFS_NS)
        graph.bind("owl", OWL_NS)
        graph.bind("xsd", XSD_NS)
        
        # 음식 URI 생성
        food_uri = food.to_uri(self.base_namespace)
        nutrition_uri = URIRef(f"{food_uri}_nutrition")
        
        # 음식 인스턴스
        graph.add((food_uri, RDF.type, self.base_namespace.Food))
        graph.add((food_uri, RDFS.label, Literal(food.name, lang="ko")))
        
        if food.category:
            graph.add((food_uri, self.base_namespace.hasCategory, Literal(food.category)))
        if food.manufacturer:
            graph.add((food_uri, self.base_namespace.hasManufacturer, Literal(food.manufacturer)))
        
        # 영양 정보 인스턴스
        graph.add((nutrition_uri, RDF.type, self.base_namespace.NutritionInfo))
        graph.add((nutrition_uri, self.base_namespace.hasCaloriesPer100g, Literal(nutrition.calories_per_100g)))
        graph.add((nutrition_uri, self.base_namespace.hasCarbohydrate, Literal(nutrition.carbohydrate)))
        graph.add((nutrition_uri, self.base_namespace.hasProtein, Literal(nutrition.protein)))
        graph.add((nutrition_uri, self.base_namespace.hasFat, Literal(nutrition.fat)))
        graph.add((nutrition_uri, self.base_namespace.hasFiber, Literal(nutrition.fiber)))
        graph.add((nutrition_uri, self.base_namespace.hasSodium, Literal(nutrition.sodium)))
        
        # 관계 설정
        graph.add((food_uri, self.base_namespace.hasNutritionInfo, nutrition_uri))
        
        return graph
    
    def convert_exercise_to_rdf(self, exercise: ExerciseItem) -> Graph:
        """
        운동 데이터를 RDF 그래프로 변환합니다.
        
        Args:
            exercise: 운동 아이템
            
        Returns:
            Graph: 변환된 RDF 그래프
        """
        graph = Graph()
        
        # 네임스페이스 바인딩
        graph.bind("", self.base_namespace)
        graph.bind("rdf", RDF_NS)
        graph.bind("rdfs", RDFS_NS)
        graph.bind("owl", OWL_NS)
        graph.bind("xsd", XSD_NS)
        
        # 운동 URI 생성
        exercise_uri = exercise.to_uri(self.base_namespace)
        
        # 운동 인스턴스
        graph.add((exercise_uri, RDF.type, self.base_namespace.Exercise))
        graph.add((exercise_uri, RDFS.label, Literal(exercise.name, lang="ko")))
        graph.add((exercise_uri, self.base_namespace.hasMET, Literal(exercise.met_value)))
        
        if exercise.description:
            graph.add((exercise_uri, RDFS.comment, Literal(exercise.description, lang="ko")))
        if exercise.category:
            graph.add((exercise_uri, self.base_namespace.hasCategory, Literal(exercise.category)))
        
        return graph
    
    def convert_consumption_to_rdf(self, consumption: FoodConsumption) -> Graph:
        """
        음식 섭취 데이터를 RDF 그래프로 변환합니다.
        
        Args:
            consumption: 음식 섭취 기록
            
        Returns:
            Graph: 변환된 RDF 그래프
        """
        graph = Graph()
        
        # 네임스페이스 바인딩
        graph.bind("", self.base_namespace)
        graph.bind("rdf", RDF_NS)
        graph.bind("rdfs", RDFS_NS)
        graph.bind("owl", OWL_NS)
        graph.bind("xsd", XSD_NS)
        
        # 섭취 기록 URI 생성
        consumption_uri = URIRef(f"{self.base_namespace}consumption_{hash(str(consumption.food_uri) + str(consumption.timestamp))}")
        
        # 섭취 기록 인스턴스
        graph.add((consumption_uri, RDF.type, self.base_namespace.FoodConsumption))
        graph.add((consumption_uri, self.base_namespace.consumedFood, consumption.food_uri))
        graph.add((consumption_uri, self.base_namespace.consumedAmount, Literal(consumption.amount_grams)))
        graph.add((consumption_uri, self.base_namespace.consumedCalories, Literal(consumption.calories_consumed)))
        graph.add((consumption_uri, self.base_namespace.consumedAt, Literal(consumption.timestamp)))
        
        return graph
    
    def convert_exercise_session_to_rdf(self, session: ExerciseSession) -> Graph:
        """
        운동 세션 데이터를 RDF 그래프로 변환합니다.
        
        Args:
            session: 운동 세션 기록
            
        Returns:
            Graph: 변환된 RDF 그래프
        """
        graph = Graph()
        
        # 네임스페이스 바인딩
        graph.bind("", self.base_namespace)
        graph.bind("rdf", RDF_NS)
        graph.bind("rdfs", RDFS_NS)
        graph.bind("owl", OWL_NS)
        graph.bind("xsd", XSD_NS)
        
        # 운동 세션 URI 생성
        session_uri = URIRef(f"{self.base_namespace}session_{hash(str(session.exercise_uri) + str(session.timestamp))}")
        
        # 운동 세션 인스턴스
        graph.add((session_uri, RDF.type, self.base_namespace.ExerciseSession))
        graph.add((session_uri, self.base_namespace.performedExercise, session.exercise_uri))
        graph.add((session_uri, self.base_namespace.hasWeight, Literal(session.weight)))
        graph.add((session_uri, self.base_namespace.sessionDuration, Literal(session.duration)))
        graph.add((session_uri, self.base_namespace.caloriesBurned, Literal(session.calories_burned)))
        graph.add((session_uri, self.base_namespace.performedAt, Literal(session.timestamp)))
        
        return graph
    
    def merge_graphs(self, graphs: List[Graph]) -> Graph:
        """
        여러 RDF 그래프를 하나로 병합합니다.
        
        Args:
            graphs: 병합할 그래프 목록
            
        Returns:
            Graph: 병합된 그래프
        """
        if not graphs:
            return Graph()
        
        merged_graph = Graph()
        
        # 네임스페이스 바인딩
        merged_graph.bind("", self.base_namespace)
        merged_graph.bind("rdf", RDF_NS)
        merged_graph.bind("rdfs", RDFS_NS)
        merged_graph.bind("owl", OWL_NS)
        merged_graph.bind("xsd", XSD_NS)
        
        # 모든 그래프의 트리플을 병합
        total_triples = 0
        for graph in graphs:
            for triple in graph:
                merged_graph.add(triple)
                total_triples += 1
        
        print(f"✓ {len(graphs)}개 그래프 병합 완료: {total_triples}개 트리플")
        return merged_graph
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        온톨로지 매니저 통계 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            "manager_statistics": self.stats.copy(),
            "configuration": {
                "base_namespace": str(self.base_namespace),
                "supported_formats": ["turtle", "xml", "n3", "nt"]
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_statistics(self) -> None:
        """통계 정보를 초기화합니다."""
        self.stats = {
            "loaded_files": 0,
            "merged_graphs": 0,
            "created_backups": 0,
            "validation_checks": 0
        }
        print("✓ 온톨로지 매니저 통계 초기화 완료")