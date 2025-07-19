"""
SPARQL 쿼리 매니저.

온톨로지 데이터에 대한 SPARQL 쿼리 실행 및 결과 처리 기능을 제공합니다.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

# 네임스페이스 정의
DIET_NS = Namespace("http://example.org/diet#")


@dataclass
class QueryResult:
    """SPARQL 쿼리 결과."""
    success: bool
    data: Any
    execution_time: float
    row_count: int = 0
    query: str = ""
    error_message: Optional[str] = None


@dataclass
class QueryTemplate:
    """SPARQL 쿼리 템플릿."""
    name: str
    description: str
    template: str
    parameters: List[str]


class SPARQLManager:
    """SPARQL 쿼리 매니저."""
    
    def __init__(self, ontology_path: str = "diet-ontology.ttl", cache_enabled: bool = True):
        """초기화."""
        self.ontology_path = ontology_path
        self.cache_enabled = cache_enabled
        
        # 그래프 로드
        try:
            if os.path.exists(ontology_path):
                self.graph = Graph()
                self.graph.parse(ontology_path, format="turtle")
                print(f"✓ 온톨로지 파일 로드 완료: {ontology_path}")
                print(f"  - 트리플 수: {len(self.graph)}")
            else:
                self.graph = Graph()
                print(f"⚠️ 온톨로지 파일을 찾을 수 없습니다: {ontology_path}")
        except Exception as e:
            self.graph = Graph()
            print(f"⚠️ 온톨로지 로드 실패: {str(e)}")
        
        # 네임스페이스 바인딩
        self.graph.bind("", DIET_NS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("xsd", XSD)
        
        # 쿼리 캐시
        self.query_cache = {}
        self.cache_ttl = 3600
        
        # 템플릿 초기화
        self.templates = self._initialize_templates()
        
        # 통계
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_execution_time": 0.0
        }
        
        print("✓ SPARQL 쿼리 매니저 초기화 완료")
        print(f"  - 캐싱 활성화: {cache_enabled}")
    
    def _initialize_templates(self) -> Dict[str, QueryTemplate]:
        """템플릿 초기화."""
        templates = {}
        
        templates["food_by_name"] = QueryTemplate(
            name="food_by_name",
            description="이름으로 음식 검색",
            template="""
                PREFIX : <http://example.org/diet#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?food ?name ?category
                WHERE {
                    ?food rdf:type :Food .
                    ?food rdfs:label ?name .
                    FILTER(REGEX(?name, "${food_name}", "i"))
                    OPTIONAL { ?food :hasCategory ?category }
                }
                ORDER BY ?name
                LIMIT ${limit}
            """,
            parameters=["food_name", "limit"]
        )
        
        templates["exercise_by_name"] = QueryTemplate(
            name="exercise_by_name",
            description="이름으로 운동 검색",
            template="""
                PREFIX : <http://example.org/diet#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?exercise ?name ?category ?met_value
                WHERE {
                    ?exercise rdf:type :Exercise .
                    ?exercise rdfs:label ?name .
                    FILTER(REGEX(?name, "${exercise_name}", "i"))
                    OPTIONAL { ?exercise :hasCategory ?category }
                    OPTIONAL { ?exercise :hasMET ?met_value }
                }
                ORDER BY ?name
                LIMIT ${limit}
            """,
            parameters=["exercise_name", "limit"]
        )
        
        templates["food_categories"] = QueryTemplate(
            name="food_categories",
            description="음식 카테고리 목록",
            template="""
                PREFIX : <http://example.org/diet#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                
                SELECT DISTINCT ?category
                WHERE {
                    ?food rdf:type :Food .
                    ?food :hasCategory ?category .
                }
                ORDER BY ?category
            """,
            parameters=[]
        )
        
        templates["exercise_categories"] = QueryTemplate(
            name="exercise_categories",
            description="운동 카테고리 목록",
            template="""
                PREFIX : <http://example.org/diet#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                
                SELECT DISTINCT ?category
                WHERE {
                    ?exercise rdf:type :Exercise .
                    ?exercise :hasCategory ?category .
                }
                ORDER BY ?category
            """,
            parameters=[]
        )
        
        return templates
    
    def execute_query(self, query: str, format: str = "json") -> QueryResult:
        """쿼리 실행."""
        # 캐시 확인
        cache_key = f"{query}_{format}"
        if self.cache_enabled and cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            if datetime.now() < cache_entry["expiry"]:
                self.stats["cache_hits"] += 1
                self.stats["total_queries"] += 1
                print(f"✓ 캐시에서 쿼리 결과 로드 (캐시 히트)")
                return cache_entry["result"]
            else:
                # 만료된 캐시 항목 제거
                del self.query_cache[cache_key]
        
        self.stats["cache_misses"] += 1
        self.stats["total_queries"] += 1
        
        start_time = time.time()
        
        try:
            results = self.graph.query(query)
            execution_time = time.time() - start_time
            
            # 결과 변환
            data = self._convert_to_json(results)
            
            result = QueryResult(
                success=True,
                data=data,
                execution_time=execution_time,
                row_count=len(data),
                query=query
            )
            
            # 캐시에 결과 저장
            if self.cache_enabled:
                self.query_cache[cache_key] = {
                    "result": result,
                    "expiry": datetime.now() + timedelta(seconds=self.cache_ttl)
                }
            
            print(f"✓ 쿼리 실행 완료: {result.row_count}개 결과, {result.execution_time:.3f}초")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ 쿼리 실행 실패: {str(e)}")
            
            return QueryResult(
                success=False,
                data=None,
                execution_time=execution_time,
                error_message=str(e),
                query=query
            )
    
    def get_query_template(self, template_name: str, **params) -> str:
        """템플릿 가져오기."""
        if template_name not in self.templates:
            raise ValueError(f"템플릿을 찾을 수 없습니다: {template_name}")
        
        template = self.templates[template_name]
        query_template = template.template
        
        # 필수 매개변수 확인
        for param in template.parameters:
            if param not in params and "${" + param + "}" in query_template:
                raise ValueError(f"필수 매개변수가 누락되었습니다: {param}")
        
        # 기본값 설정
        if "limit" in template.parameters and "limit" not in params:
            params["limit"] = 100
        
        # 매개변수 적용
        for param, value in params.items():
            query_template = query_template.replace("${" + param + "}", str(value))
        
        return query_template.strip()
    
    def format_results(self, results: QueryResult, format: str = "table") -> str:
        """결과 포맷팅."""
        if not results.success:
            return f"쿼리 실행 실패: {results.error_message}"
        
        if format == "json":
            return json.dumps(results.data, ensure_ascii=False, indent=2)
        elif format == "table":
            return self._format_as_table(results.data)
        else:
            return str(results.data)
    
    def _format_as_table(self, data: List[Dict[str, Any]]) -> str:
        """테이블 형식으로 포맷팅."""
        if not data:
            return "결과 없음"
        
        headers = list(data[0].keys())
        col_widths = [max(len(str(h)), max([len(str(row[h])) for row in data])) for h in headers]
        
        # 헤더 행
        header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        separator = "-+-".join("-" * w for w in col_widths)
        
        # 데이터 행
        data_rows = []
        for row in data:
            data_rows.append(" | ".join(str(row[h]).ljust(col_widths[i]) for i, h in enumerate(headers)))
        
        return f"{header_row}\\n{separator}\\n" + "\\n".join(data_rows)
    
    def get_food_by_name(self, food_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """음식 검색."""
        query = self.get_query_template("food_by_name", food_name=food_name, limit=limit)
        result = self.execute_query(query)
        return result.data if result.success else []
    
    def get_exercise_by_name(self, exercise_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """운동 검색."""
        query = self.get_query_template("exercise_by_name", exercise_name=exercise_name, limit=limit)
        result = self.execute_query(query)
        return result.data if result.success else []
    
    def get_food_categories(self) -> List[str]:
        """음식 카테고리 목록."""
        query = self.get_query_template("food_categories")
        result = self.execute_query(query)
        if result.success:
            return [item["category"] for item in result.data if "category" in item]
        return []
    
    def get_exercise_categories(self) -> List[str]:
        """운동 카테고리 목록."""
        query = self.get_query_template("exercise_categories")
        result = self.execute_query(query)
        if result.success:
            return [item["category"] for item in result.data if "category" in item]
        return []
    
    def _convert_to_json(self, results) -> List[Dict[str, Any]]:
        """JSON 변환."""
        json_results = []
        
        for row in results:
            json_row = {}
            # 행의 모든 항목을 직접 접근
            for i, var in enumerate(results.vars):
                var_name = str(var)
                try:
                    # 인덱스로 접근
                    value = row[i] if i < len(row) else None
                    # 또는 변수명으로 접근
                    if value is None:
                        value = getattr(row, var_name, None)
                    
                    if isinstance(value, URIRef):
                        json_row[var_name] = str(value)
                    elif isinstance(value, Literal):
                        json_row[var_name] = str(value)
                    else:
                        json_row[var_name] = str(value) if value is not None else None
                except:
                    json_row[var_name] = None
                    
            json_results.append(json_row)
        
        return json_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보."""
        return {
            "query_statistics": self.stats.copy(),
            "cache_info": {
                "enabled": self.cache_enabled,
                "entries": len(self.query_cache)
            },
            "ontology_info": {
                "path": self.ontology_path,
                "triples": len(self.graph)
            },
            "templates": {
                "count": len(self.templates),
                "names": list(self.templates.keys())
            }
        }
    
    def clear_cache(self) -> int:
        """캐시 초기화."""
        cache_size = len(self.query_cache)
        self.query_cache = {}
        print(f"✓ 쿼리 캐시 초기화 완료: {cache_size}개 항목 제거")
        return cache_size