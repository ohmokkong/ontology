"""SPARQL 디버깅."""

from test_sparql_manager import create_test_ontology
from sparql_manager import SPARQLManager
import os

# 테스트 온톨로지 생성
test_ontology_path = create_test_ontology()

try:
    manager = SPARQLManager(ontology_path=test_ontology_path)
    
    # 쿼리 생성
    query = manager.get_query_template("food_by_name", food_name="사과", limit=10)
    print("=== 생성된 쿼리 ===")
    print(query)
    
    # 쿼리 실행
    result = manager.execute_query(query)
    print(f"\\n=== 쿼리 결과 ===")
    print(f"성공: {result.success}")
    print(f"행 수: {result.row_count}")
    print(f"데이터: {result.data}")
    
    # 직접 쿼리 실행
    print("\\n=== 직접 쿼리 실행 ===")
    direct_query = """
        PREFIX : <http://example.org/diet#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?food ?name ?category
        WHERE {
            ?food rdf:type :Food .
            ?food rdfs:label ?name .
            ?food :hasCategory ?category .
        }
    """
    
    direct_results = manager.graph.query(direct_query)
    print(f"직접 쿼리 결과 수: {len(direct_results)}")
    for row in direct_results:
        print(f"Food: {row.food}, Name: {row.name}, Category: {row.category}")
    
    # 모든 트리플 출력 (처음 10개만)
    print("\\n=== 온톨로지 트리플 (처음 10개) ===")
    count = 0
    for s, p, o in manager.graph:
        if count >= 10:
            break
        print(f"{s} {p} {o}")
        count += 1

finally:
    # 임시 파일 정리
    if os.path.exists(test_ontology_path):
        os.unlink(test_ontology_path)