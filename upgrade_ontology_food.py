import os
import requests
import json
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

# --- 설정 (Configuration) ---
# 발급받은 식약처 API 키를 입력하세요.
# 보안을 위해 환경 변수에서 가져오는 것을 권장합니다.
API_KEY = os.getenv("MFDS_API_KEY", "YOUR_API_KEY_HERE") 
API_URL = f"http://openapi.foodsafetykorea.go.kr/api/{API_KEY}/I2790/json"

# 온톨로지 네임스페이스 정의
EX = Namespace("http://example.org/diet#")

def fetch_nutrition_data_from_api(food_name, start_index=1, end_index=5):
    """
    식약처 Open API를 호출하여 특정 음식의 영양 정보를 가져옵니다.
    
    :param food_name: 검색할 음식 이름
    :param start_index: 가져올 데이터 시작 위치
    :param end_index: 가져올 데이터 끝 위치
    :return: API 응답 JSON 객체 또는 None
    """
    params = {
        'DESC_KOR': food_name
    }
    url = f"{API_URL}/{start_index}/{end_index}"
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # 200 OK가 아니면 에러 발생
        
        data = response.json()

        # API 응답 유효성 검사
        if "I2790" in data and "row" in data["I2790"]:
            return data["I2790"]["row"]
        elif "RESULT" in data and "MSG" in data["RESULT"]:
            print(f"API 오류: {data['RESULT']['MSG']}")
            return None
        else:
            print("알 수 없는 API 응답 형식입니다.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류가 발생했습니다: {e}")
        return None
    except json.JSONDecodeError:
        print("API 응답을 파싱하는 중 오류가 발생했습니다. (응답이 JSON이 아님)")
        return None

def convert_api_data_to_graph(api_data_list):
    """
    API로부터 받은 영양 정보 리스트를 rdflib 그래프로 변환합니다.
    """
    g_new = Graph()
    g_new.bind("", EX)
    g_new.bind("rdfs", RDFS)
    
    if not api_data_list:
        return g_new

    for item in api_data_list:
        food_name = item.get("DESC_KOR")
        if not food_name:
            continue

        # URI 생성 (식품 코드를 사용하여 고유성 보장)
        food_code = item.get("FOOD_CD", food_name.replace(" ", "_"))
        local_uri = EX[food_code]

        g_new.add((local_uri, RDF.type, EX.Food))
        g_new.add((local_uri, RDFS.label, Literal(food_name, lang="ko")))

        # 숫자형 데이터 속성 추가 (값이 비어있지 않을 경우)
        def add_decimal_property(prop, value):
            if value and value.replace('.', '', 1).isdigit():
                g_new.add((local_uri, prop, Literal(float(value), datatype=XSD.decimal)))

        add_decimal_property(EX.hasCalorie, item.get("NUTR_CONT1"))  # 열량(kcal)
        add_decimal_property(EX.hasCarbohydrate, item.get("NUTR_CONT2")) # 탄수화물(g)
        add_decimal_property(EX.hasProtein, item.get("NUTR_CONT3")) # 단백질(g)
        add_decimal_property(EX.hasFat, item.get("NUTR_CONT4")) # 지방(g)

    return g_new

def main():
    """
    메인 실행 함수
    """
    if API_KEY == "YOUR_API_KEY_HERE":
        print("오류: 스크립트 상단의 API_KEY를 실제 발급받은 키로 변경해주세요.")
        return
        
    search_keyword = input("영양 정보를 검색할 음식 이름을 입력하세요 (예: 바나나): ")
    if not search_keyword:
        print("음식 이름이 입력되지 않았습니다.")
        return

    print(f"'{search_keyword}'에 대한 영양 정보를 식약처 API에서 검색합니다...")
    api_data = fetch_nutrition_data_from_api(search_keyword)

    if api_data:
        ontology_graph = convert_api_data_to_graph(api_data)
        
        # 변환된 데이터를 새 파일에 저장
        output_filename = f"new_{search_keyword}_data.ttl"
        ontology_graph.serialize(destination=output_filename, format="turtle")
        print(f"\n성공! 검색 결과를 온톨로지 형식으로 '{output_filename}' 파일에 저장했습니다.")
        print(f"이 파일을 기존 `diet-ontology.ttl`에 통합하거나 owl:imports를 사용하세요.")
    else:
        print(f"'{search_keyword}'에 대한 데이터를 가져오지 못했습니다.")

if __name__ == "__main__":
    main()