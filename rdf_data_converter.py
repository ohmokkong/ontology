"""
RDF 데이터 변환기.

음식과 운동 데이터를 RDF/Turtle 형식으로 변환하고 온톨로지 스키마와 
호환되도록 처리하는 기능을 제공합니다.
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
from integrated_models import (
    FoodItem, NutritionInfo, FoodConsumption,
    ExerciseItem, ExerciseSession,
    NetCalorieResult, DailyAnalysis
)
from exceptions import (
    OntologyError, URIGenerationError, DataConversionError,
    TTLSyntaxError
)


class RDFDataConverter:
    """
    RDF/Turtle 형식 데이터 변환기.
    
    음식, 운동, 영양정보, 세션 데이터를 RDF 그래프로 변환하고
    기존 온톨로지와 호환되는 형식으로 처리합니다.
    """
    
    def __init__(self, base_namespace: str = "http://example.org/diet#"):
        """
        RDFDataConverter 초기화.
        
        Args:
            base_namespace: 기본 네임스페이스 URI
        """
        # 네임스페이스 설정
        self.base_ns = Namespace(base_namespace)
        self.food_ns = Namespace(f"{base_namespace}food/")
        self.exercise_ns = Namespace(f"{base_namespace}exercise/")
        self.session_ns = Namespace(f"{base_namespace}session/")
        self.nutrition_ns = Namespace(f"{base_namespace}nutrition/")
        
        # 온톨로지 클래스 정의
        self.classes = {
            "Food": self.base_ns.Food,
            "NutritionInfo": self.base_ns.NutritionInfo,
            "FoodConsumption": self.base_ns.FoodConsumption,
            "Exercise": self.base_ns.Exercise,
            "ExerciseSession": self.base_ns.ExerciseSession,
            "DailyRecord": self.base_ns.DailyRecord,
            "CalorieBalance": self.base_ns.CalorieBalance
        }
        
        # 온톨로지 속성 정의
        self.properties = {
            # 음식 관련 속성
            "hasNutrition": self.base_ns.hasNutrition,
            "hasCalories": self.base_ns.hasCalories,
            "hasCarbohydrate": self.base_ns.hasCarbohydrate,
            "hasProtein": self.base_ns.hasProtein,
            "hasFat": self.base_ns.hasFat,
            "hasFiber": self.base_ns.hasFiber,
            "hasSodium": self.base_ns.hasSodium,
            "foodCategory": self.base_ns.foodCategory,
            "manufacturer": self.base_ns.manufacturer,
            
            # 운동 관련 속성
            "hasMET": self.base_ns.hasMET,
            "exerciseCategory": self.base_ns.exerciseCategory,
            "performedExercise": self.base_ns.performedExercise,
            "hasWeight": self.base_ns.hasWeight,
            "hasDuration": self.base_ns.hasDuration,
            "caloriesBurned": self.base_ns.caloriesBurned,
            
            # 소비/세션 관련 속성
            "consumedFood": self.base_ns.consumedFood,
            "consumedAmount": self.base_ns.consumedAmount,
            "consumedAt": self.base_ns.consumedAt,
            "performedAt": self.base_ns.performedAt,
            
            # 분석 관련 속성
            "totalConsumed": self.base_ns.totalConsumed,
            "totalBurned": self.base_ns.totalBurned,
            "netCalories": self.base_ns.netCalories,
            "analysisDate": self.base_ns.analysisDate,
            "goalCalories": self.base_ns.goalCalories,
            "achievementRate": self.base_ns.achievementRate
        }
        
        # 변환 통계
        self.conversion_stats = {
            "foods_converted": 0,
            "exercises_converted": 0,
            "consumptions_converted": 0,
            "sessions_converted": 0,
            "graphs_merged": 0,
            "errors_encountered": 0
        }
    
    def convert_food_to_rdf(self, food: FoodItem, nutrition: Optional[NutritionInfo] = None) -> Graph:
        """
        음식 아이템을 RDF 그래프로 변환합니다.
        
        Args:
            food: 변환할 음식 아이템
            nutrition: 선택적 영양정보
            
        Returns:
            Graph: 생성된 RDF 그래프
            
        Raises:
            URIGenerationError: URI 생성 실패 시
            DataConversionError: 데이터 변환 실패 시
        """
        print(f"🍎 음식 RDF 변환: {food.name}")
        
        try:
            graph = Graph()
            
            # 네임스페이스 바인딩
            self._bind_namespaces(graph)
            
            # 음식 URI 생성
            food_uri = self._generate_food_uri(food)
            
            # 음식 클래스 선언
            graph.add((food_uri, RDF.type, self.classes["Food"]))
            graph.add((food_uri, RDFS.label, Literal(food.name, lang="ko")))
            
            # 음식 기본 속성
            if food.category:
                graph.add((food_uri, self.properties["foodCategory"], 
                          Literal(food.category, lang="ko")))
            
            if food.manufacturer:
                graph.add((food_uri, self.properties["manufacturer"], 
                          Literal(food.manufacturer, lang="ko")))
            
            # 음식 ID
            graph.add((food_uri, self.base_ns.foodId, Literal(food.food_id)))
            
            # 영양정보 추가
            if nutrition:
                nutrition_uri = self._add_nutrition_info(graph, food_uri, nutrition)
                graph.add((food_uri, self.properties["hasNutrition"], nutrition_uri))
            
            self.conversion_stats["foods_converted"] += 1
            print(f"  ✓ 음식 RDF 변환 완료: {len(graph)} 트리플")
            
            return graph
            
        except Exception as e:
            self.conversion_stats["errors_encountered"] += 1
            if isinstance(e, (URIGenerationError, DataConversionError)):
                raise
            raise DataConversionError(f"음식 RDF 변환 실패: {str(e)}")
    
    def convert_exercise_to_rdf(self, exercise: ExerciseItem) -> Graph:
        """
        운동 아이템을 RDF 그래프로 변환합니다.
        
        Args:
            exercise: 변환할 운동 아이템
            
        Returns:
            Graph: 생성된 RDF 그래프
            
        Raises:
            URIGenerationError: URI 생성 실패 시
            DataConversionError: 데이터 변환 실패 시
        """
        print(f"🏃 운동 RDF 변환: {exercise.name}")
        
        try:
            graph = Graph()
            
            # 네임스페이스 바인딩
            self._bind_namespaces(graph)
            
            # 운동 URI 생성
            exercise_uri = self._generate_exercise_uri(exercise)
            
            # 운동 클래스 선언
            graph.add((exercise_uri, RDF.type, self.classes["Exercise"]))
            graph.add((exercise_uri, RDFS.label, Literal(exercise.name, lang="ko")))
            
            # 운동 속성
            graph.add((exercise_uri, RDFS.comment, 
                      Literal(exercise.description, lang="ko")))
            graph.add((exercise_uri, self.properties["hasMET"], 
                      Literal(exercise.met_value, datatype=XSD.float)))
            
            if exercise.category:
                graph.add((exercise_uri, self.properties["exerciseCategory"], 
                          Literal(exercise.category, lang="ko")))
            
            if exercise.exercise_id:
                graph.add((exercise_uri, self.base_ns.exerciseId, 
                          Literal(exercise.exercise_id)))
            
            self.conversion_stats["exercises_converted"] += 1
            print(f"  ✓ 운동 RDF 변환 완료: {len(graph)} 트리플")
            
            return graph
            
        except Exception as e:
            self.conversion_stats["errors_encountered"] += 1
            if isinstance(e, (URIGenerationError, DataConversionError)):
                raise
            raise DataConversionError(f"운동 RDF 변환 실패: {str(e)}")
    
    def convert_consumption_to_rdf(self, consumption: FoodConsumption) -> Graph:
        """
        음식 섭취 기록을 RDF 그래프로 변환합니다.
        
        Args:
            consumption: 변환할 음식 섭취 기록
            
        Returns:
            Graph: 생성된 RDF 그래프
        """
        print(f"🍽️ 음식 섭취 RDF 변환: {consumption.amount_grams}g")
        
        try:
            graph = Graph()
            
            # 네임스페이스 바인딩
            self._bind_namespaces(graph)
            
            # 섭취 기록 URI 생성
            consumption_uri = self._generate_consumption_uri(consumption)
            
            # 섭취 기록 클래스 선언
            graph.add((consumption_uri, RDF.type, self.classes["FoodConsumption"]))
            
            # 섭취 기록 속성
            graph.add((consumption_uri, self.properties["consumedFood"], 
                      consumption.food_uri))
            graph.add((consumption_uri, self.properties["consumedAmount"], 
                      Literal(consumption.amount_grams, datatype=XSD.float)))
            graph.add((consumption_uri, self.properties["hasCalories"], 
                      Literal(consumption.calories_consumed, datatype=XSD.float)))
            graph.add((consumption_uri, self.properties["consumedAt"], 
                      Literal(consumption.timestamp, datatype=XSD.dateTime)))
            
            self.conversion_stats["consumptions_converted"] += 1
            print(f"  ✓ 섭취 기록 RDF 변환 완료: {len(graph)} 트리플")
            
            return graph
            
        except Exception as e:
            self.conversion_stats["errors_encountered"] += 1
            raise DataConversionError(f"섭취 기록 RDF 변환 실패: {str(e)}")
    
    def convert_session_to_rdf(self, session: ExerciseSession) -> Graph:
        """
        운동 세션을 RDF 그래프로 변환합니다.
        
        Args:
            session: 변환할 운동 세션
            
        Returns:
            Graph: 생성된 RDF 그래프
        """
        print(f"💪 운동 세션 RDF 변환: {session.duration}분")
        
        try:
            graph = Graph()
            
            # 네임스페이스 바인딩
            self._bind_namespaces(graph)
            
            # 세션 URI 생성
            session_uri = self._generate_session_uri(session)
            
            # 세션 클래스 선언
            graph.add((session_uri, RDF.type, self.classes["ExerciseSession"]))
            
            # 세션 속성
            graph.add((session_uri, self.properties["performedExercise"], 
                      session.exercise_uri))
            graph.add((session_uri, self.properties["hasWeight"], 
                      Literal(session.weight, datatype=XSD.float)))
            graph.add((session_uri, self.properties["hasDuration"], 
                      Literal(session.duration, datatype=XSD.float)))
            graph.add((session_uri, self.properties["caloriesBurned"], 
                      Literal(session.calories_burned, datatype=XSD.float)))
            graph.add((session_uri, self.properties["performedAt"], 
                      Literal(session.timestamp, datatype=XSD.dateTime)))
            
            self.conversion_stats["sessions_converted"] += 1
            print(f"  ✓ 운동 세션 RDF 변환 완료: {len(graph)} 트리플")
            
            return graph
            
        except Exception as e:
            self.conversion_stats["errors_encountered"] += 1
            raise DataConversionError(f"운동 세션 RDF 변환 실패: {str(e)}")
    
    def convert_daily_analysis_to_rdf(self, analysis: DailyAnalysis) -> Graph:
        """
        일일 분석 결과를 RDF 그래프로 변환합니다.
        
        Args:
            analysis: 변환할 일일 분석 결과
            
        Returns:
            Graph: 생성된 RDF 그래프
        """
        print(f"📊 일일 분석 RDF 변환: {analysis.date}")
        
        try:
            graph = Graph()
            
            # 네임스페이스 바인딩
            self._bind_namespaces(graph)
            
            # 일일 기록 URI 생성
            daily_uri = self._generate_daily_record_uri(analysis.date)
            
            # 일일 기록 클래스 선언
            graph.add((daily_uri, RDF.type, self.classes["DailyRecord"]))
            graph.add((daily_uri, self.properties["analysisDate"], 
                      Literal(analysis.date, datatype=XSD.date)))
            
            # 칼로리 밸런스 정보
            result = analysis.net_calorie_result
            balance_uri = BNode()
            
            graph.add((daily_uri, self.base_ns.hasCalorieBalance, balance_uri))
            graph.add((balance_uri, RDF.type, self.classes["CalorieBalance"]))
            graph.add((balance_uri, self.properties["totalConsumed"], 
                      Literal(result.total_consumed, datatype=XSD.float)))
            graph.add((balance_uri, self.properties["totalBurned"], 
                      Literal(result.total_burned, datatype=XSD.float)))
            graph.add((balance_uri, self.properties["netCalories"], 
                      Literal(result.net_calories, datatype=XSD.float)))
            
            # 목표 및 달성률
            if analysis.goal_calories:
                graph.add((balance_uri, self.properties["goalCalories"], 
                          Literal(analysis.goal_calories, datatype=XSD.float)))
            
            if analysis.achievement_rate:
                graph.add((balance_uri, self.properties["achievementRate"], 
                          Literal(analysis.achievement_rate, datatype=XSD.float)))
            
            # 섭취 및 운동 기록 연결
            for consumption in result.food_consumptions:
                consumption_graph = self.convert_consumption_to_rdf(consumption)
                graph += consumption_graph
                
                # 일일 기록과 연결
                consumption_uri = self._generate_consumption_uri(consumption)
                graph.add((daily_uri, self.base_ns.hasConsumption, consumption_uri))
            
            for session in result.exercise_sessions:
                session_graph = self.convert_session_to_rdf(session)
                graph += session_graph
                
                # 일일 기록과 연결
                session_uri = self._generate_session_uri(session)
                graph.add((daily_uri, self.base_ns.hasSession, session_uri))
            
            print(f"  ✓ 일일 분석 RDF 변환 완료: {len(graph)} 트리플")
            
            return graph
            
        except Exception as e:
            self.conversion_stats["errors_encountered"] += 1
            raise DataConversionError(f"일일 분석 RDF 변환 실패: {str(e)}")
    
    def merge_graphs(self, graphs: List[Graph]) -> Graph:
        """
        여러 RDF 그래프를 병합합니다.
        
        Args:
            graphs: 병합할 그래프 목록
            
        Returns:
            Graph: 병합된 그래프
        """
        print(f"🔗 {len(graphs)}개 그래프 병합 시작")
        
        try:
            merged_graph = Graph()
            
            # 네임스페이스 바인딩
            self._bind_namespaces(merged_graph)
            
            # 그래프 병합
            total_triples = 0
            for i, graph in enumerate(graphs, 1):
                if graph and len(graph) > 0:
                    merged_graph += graph
                    total_triples += len(graph)
                    print(f"  - 그래프 {i}: {len(graph)} 트리플 추가")
            
            self.conversion_stats["graphs_merged"] += 1
            print(f"✓ 그래프 병합 완료: 총 {total_triples} 트리플")
            
            return merged_graph
            
        except Exception as e:
            self.conversion_stats["errors_encountered"] += 1
            raise DataConversionError(f"그래프 병합 실패: {str(e)}")
    
    def create_ontology_schema(self) -> Graph:
        """
        온톨로지 스키마를 생성합니다.
        
        Returns:
            Graph: 온톨로지 스키마 그래프
        """
        print("📋 온톨로지 스키마 생성")
        
        try:
            schema_graph = Graph()
            
            # 네임스페이스 바인딩
            self._bind_namespaces(schema_graph)
            
            # 클래스 정의
            self._define_classes(schema_graph)
            
            # 속성 정의
            self._define_properties(schema_graph)
            
            print(f"✓ 온톨로지 스키마 생성 완료: {len(schema_graph)} 트리플")
            
            return schema_graph
            
        except Exception as e:
            raise OntologyError(f"온톨로지 스키마 생성 실패: {str(e)}")
    
    def _bind_namespaces(self, graph: Graph) -> None:
        """그래프에 네임스페이스를 바인딩합니다."""
        graph.bind("diet", self.base_ns)
        graph.bind("food", self.food_ns)
        graph.bind("exercise", self.exercise_ns)
        graph.bind("session", self.session_ns)
        graph.bind("nutrition", self.nutrition_ns)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("owl", OWL)
        graph.bind("xsd", XSD)
    
    def _generate_food_uri(self, food: FoodItem) -> URIRef:
        """음식 URI를 생성합니다."""
        try:
            return food.to_uri(self.food_ns)
        except Exception as e:
            raise URIGenerationError(f"음식 URI 생성 실패: {str(e)}")
    
    def _generate_exercise_uri(self, exercise: ExerciseItem) -> URIRef:
        """운동 URI를 생성합니다."""
        try:
            return exercise.to_uri(self.exercise_ns)
        except Exception as e:
            raise URIGenerationError(f"운동 URI 생성 실패: {str(e)}")
    
    def _generate_consumption_uri(self, consumption: FoodConsumption) -> URIRef:
        """섭취 기록 URI를 생성합니다."""
        timestamp_str = consumption.timestamp.strftime("%Y%m%d_%H%M%S")
        food_id = str(consumption.food_uri).split("/")[-1]
        return self.session_ns[f"consumption_{food_id}_{timestamp_str}"]
    
    def _generate_session_uri(self, session: ExerciseSession) -> URIRef:
        """운동 세션 URI를 생성합니다."""
        timestamp_str = session.timestamp.strftime("%Y%m%d_%H%M%S")
        exercise_id = str(session.exercise_uri).split("/")[-1]
        return self.session_ns[f"session_{exercise_id}_{timestamp_str}"]
    
    def _generate_daily_record_uri(self, date) -> URIRef:
        """일일 기록 URI를 생성합니다."""
        date_str = date.strftime("%Y%m%d")
        return self.session_ns[f"daily_{date_str}"]
    
    def _add_nutrition_info(self, graph: Graph, food_uri: URIRef, 
                           nutrition: NutritionInfo) -> URIRef:
        """영양정보를 그래프에 추가합니다."""
        nutrition_uri = BNode()
        
        # 영양정보 클래스 선언
        graph.add((nutrition_uri, RDF.type, self.classes["NutritionInfo"]))
        
        # 영양소 속성 추가
        graph.add((nutrition_uri, self.properties["hasCalories"], 
                  Literal(nutrition.calories_per_100g, datatype=XSD.float)))
        graph.add((nutrition_uri, self.properties["hasCarbohydrate"], 
                  Literal(nutrition.carbohydrate, datatype=XSD.float)))
        graph.add((nutrition_uri, self.properties["hasProtein"], 
                  Literal(nutrition.protein, datatype=XSD.float)))
        graph.add((nutrition_uri, self.properties["hasFat"], 
                  Literal(nutrition.fat, datatype=XSD.float)))
        
        # 선택적 영양소
        if nutrition.fiber is not None:
            graph.add((nutrition_uri, self.properties["hasFiber"], 
                      Literal(nutrition.fiber, datatype=XSD.float)))
        
        if nutrition.sodium is not None:
            graph.add((nutrition_uri, self.properties["hasSodium"], 
                      Literal(nutrition.sodium, datatype=XSD.float)))
        
        return nutrition_uri
    
    def _define_classes(self, graph: Graph) -> None:
        """온톨로지 클래스를 정의합니다."""
        for class_name, class_uri in self.classes.items():
            graph.add((class_uri, RDF.type, OWL.Class))
            graph.add((class_uri, RDFS.label, Literal(class_name, lang="en")))
    
    def _define_properties(self, graph: Graph) -> None:
        """온톨로지 속성을 정의합니다."""
        # 데이터 속성 정의
        data_properties = [
            "hasCalories", "hasCarbohydrate", "hasProtein", "hasFat", 
            "hasFiber", "hasSodium", "hasMET", "hasWeight", "hasDuration",
            "caloriesBurned", "consumedAmount", "totalConsumed", "totalBurned",
            "netCalories", "goalCalories", "achievementRate"
        ]
        
        for prop_name in data_properties:
            prop_uri = self.properties[prop_name]
            graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            graph.add((prop_uri, RDFS.label, Literal(prop_name, lang="en")))
        
        # 객체 속성 정의
        object_properties = [
            "hasNutrition", "consumedFood", "performedExercise"
        ]
        
        for prop_name in object_properties:
            prop_uri = self.properties[prop_name]
            graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            graph.add((prop_uri, RDFS.label, Literal(prop_name, lang="en")))
    
    def export_to_turtle(self, graph: Graph, output_path: str) -> bool:
        """
        RDF 그래프를 Turtle 파일로 내보냅니다.
        
        Args:
            graph: 내보낼 그래프
            output_path: 출력 파일 경로
            
        Returns:
            bool: 내보내기 성공 여부
            
        Raises:
            TTLSyntaxError: TTL 파일 생성 실패 시
        """
        print(f"💾 TTL 파일 내보내기: {output_path}")
        
        try:
            # TTL 형식으로 직렬화
            ttl_content = graph.serialize(format="turtle")
            
            # 파일 저장
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(ttl_content)
            
            print(f"✓ TTL 파일 저장 완료: {len(graph)} 트리플")
            return True
            
        except Exception as e:
            raise TTLSyntaxError(f"TTL 파일 내보내기 실패: {str(e)}")
    
    def validate_graph_syntax(self, graph: Graph) -> bool:
        """
        RDF 그래프의 문법을 검증합니다.
        
        Args:
            graph: 검증할 그래프
            
        Returns:
            bool: 검증 통과 여부
        """
        try:
            # TTL 직렬화 시도로 문법 검증
            graph.serialize(format="turtle")
            return True
        except Exception:
            return False
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """
        변환 통계를 반환합니다.
        
        Returns:
            Dict[str, Any]: 변환 통계 정보
        """
        stats = self.conversion_stats.copy()
        stats["timestamp"] = datetime.now().isoformat()
        stats["total_converted"] = (stats["foods_converted"] + 
                                  stats["exercises_converted"] + 
                                  stats["consumptions_converted"] + 
                                  stats["sessions_converted"])
        
        if stats["total_converted"] > 0:
            stats["success_rate"] = ((stats["total_converted"] - stats["errors_encountered"]) / 
                                   stats["total_converted"]) * 100
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """변환 통계를 초기화합니다."""
        for key in self.conversion_stats:
            self.conversion_stats[key] = 0