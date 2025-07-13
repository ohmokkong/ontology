from rdflib import Graph

g = Graph()
g.parse("diet-ontology.ttl", format="ttl")

# 예: 모든 음식 개념 추출
for s, p, o in g.triples((None, None, None)):
    print(s, p, o)
