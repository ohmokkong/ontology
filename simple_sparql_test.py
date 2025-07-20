"""간단한 SPARQL 테스트."""

import tempfile
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

# 테스트 온톨로지 생성
graph = Graph()
diet_ns = Namespace("http://example.org/diet#")
graph.bind("", diet_ns)
graph.bind("rdf", RDF)
graph.bind("rdfs", RDFS)
graph.bind("owl", OWL)
graph.bind("xsd", XSD)

# 클래스 정의
graph.add((diet_ns.Food, RDF.type, OWL.Class))
graph.add((diet_ns.hasCategory, RDF.type, OWL.DatatypeProperty))

# 사과 인스턴스 추가
apple = diet_ns.Food_Apple
graph.add((apple, RDF.type, diet_ns.Food))
graph.add((apple, RDFS.label, Literal("사과", lang="ko")))
graph.add((apple, diet_ns.hasCategory, Literal("과일")))

print(f"그래프 트리플 수: {len(graph)}")

# 간단한 쿼리 테스트
query1 = """
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

print("\\n=== 쿼리 1 실행 ===")
results1 = graph.query(query1)
for row in results1:
    print(f"Food: {row.food}, Name: {row.name}, Category: {row.category}")

# 사과 검색 쿼리
query2 = """
    PREFIX : <http://example.org/diet#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?food ?name ?category
    WHERE {
        ?food rdf:type :Food .
        ?food rdfs:label ?name .
        FILTER(REGEX(?name, "사과", "i"))
        OPTIONAL { ?food :hasCategory ?category }
    }
"""

print("\\n=== 쿼리 2 실행 (사과 검색) ===")
results2 = graph.query(query2)
for row in results2:
    print(f"Food: {row.food}, Name: {row.name}, Category: {row.category}")

# 모든 트리플 출력
print("\\n=== 모든 트리플 ===")
for s, p, o in graph:
    print(f"{s} {p} {o}")