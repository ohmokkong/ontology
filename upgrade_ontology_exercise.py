import os, requests
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD

# 설정
MET_API_KEY = os.getenv("MET_API_KEY", "YOUR_MET_KEY")
MET_URL = f"https://api.odcloud.kr/api/15068730/v1/healthExercise"
EX = Namespace("http://example.org/diet#")

def fetch_met_data():
    params = {"serviceKey": MET_API_KEY, "page": 1, "perPage": 100}
    resp = requests.get(MET_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("data", [])

def build_met_graph(met_list):
    g = Graph()
    g.bind("", EX)
    g.bind("rdfs", RDFS)
    for item in met_list:
        name = item.get("운동명")
        met = item.get("METS")
        if not name or met is None: continue
        uri = EX[name.replace(" ", "_")]
        g.add((uri, RDF.type, EX.Exercise))
        g.add((uri, RDFS.label, Literal(name, lang="ko")))
        try:
            g.add((uri, EX.hasMET, Literal(float(met), datatype=XSD.decimal)))
        except:
            pass
    return g

def main():
    data = fetch_met_data()
    g = build_met_graph(data)
    output = "exercise_met_data.ttl"
    g.serialize(destination=output, format="turtle")
    print(f"완료: {output} 생성됨 ({len(data)}건 포함)")

if __name__ == "__main__":
    if MET_API_KEY in ("", "YOUR_MET_KEY"):
        print("MET_API_KEY 환경변수를 설정해주세요.")
    else:
        main()
        
"""
 실행 안내
API 키 발급

공공데이터포털에서 "보건소 모바일 헬스케어 운동" OpenAPI 신청 후 서비스키 발급

환경 변수 설정

bash
복사
편집
export MET_API_KEY=발급받은_API_키
필수 라이브러리 설치

bash
복사
편집
pip install requests rdflib
스크립트 실행

bash
복사
편집
python upgrade_ontology_exercise.py
결과: exercise_met_data.ttl 파일이 생성되며, <http://example.org/diet#운동명> URI로 온톨로지가 구축됩니다.
"""
