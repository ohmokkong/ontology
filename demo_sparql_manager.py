"""
SPARQL 쿼리 매니저 데모.

실제 온톨로지 파일을 사용하여 SPARQL 쿼리 매니저의 기능을 시연합니다.
"""

from sparql_manager import SPARQLManager


def demo_sparql_manager():
    """SPARQL 쿼리 매니저 데모 실행."""
    print("=== SPARQL 쿼리 매니저 데모 ===\n")
    
    # SPARQL 매니저 초기화
    manager = SPARQLManager(ontology_path="diet-ontology.ttl")
    
    print("\n1. 통계 정보 확인")
    print("-" * 30)
    stats = manager.get_statistics()
    print(f"온톨로지 트리플 수: {stats['ontology_info']['triples']}")
    print(f"사용 가능한 템플릿: {', '.join(stats['templates']['names'])}")
    
    print("\n2. 음식 카테고리 조회")
    print("-" * 30)
    food_categories = manager.get_food_categories()
    if food_categories:
        print(f"음식 카테고리: {', '.join(food_categories)}")
    else:
        print("음식 카테고리가 없습니다.")
    
    print("\n3. 운동 카테고리 조회")
    print("-" * 30)
    exercise_categories = manager.get_exercise_categories()
    if exercise_categories:
        print(f"운동 카테고리: {', '.join(exercise_categories)}")
    else:
        print("운동 카테고리가 없습니다.")
    
    print("\n4. 음식 검색 (사과)")
    print("-" * 30)
    foods = manager.get_food_by_name("사과")
    if foods:
        for food in foods:
            print(f"- {food}")
    else:
        print("검색 결과가 없습니다.")
    
    print("\n5. 운동 검색 (달리기)")
    print("-" * 30)
    exercises = manager.get_exercise_by_name("달리기")
    if exercises:
        for exercise in exercises:
            print(f"- {exercise}")
    else:
        print("검색 결과가 없습니다.")
    
    print("\n6. 사용자 정의 쿼리 실행")
    print("-" * 30)
    custom_query = """
        PREFIX : <http://example.org/diet#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        
        SELECT ?cls ?label
        WHERE {
            ?cls rdf:type owl:Class .
            OPTIONAL { ?cls rdfs:label ?label }
        }
        ORDER BY ?cls
    """
    
    result = manager.execute_query(custom_query)
    if result.success:
        print(f"클래스 목록 ({result.row_count}개):")
        for item in result.data:
            print(f"결과 항목: {item}")  # 디버깅용
            # 키 이름 확인 후 적절히 처리
            cls_key = 'cls' if 'cls' in item else list(item.keys())[0] if item else None
            label_key = 'label' if 'label' in item else None
            
            if cls_key:
                cls_value = item[cls_key]
                label_value = item.get(label_key, '라벨 없음') if label_key else '라벨 없음'
                print(f"- {cls_value}: {label_value}")
    else:
        print(f"쿼리 실행 실패: {result.error_message}")
    
    print("\n7. 최종 통계")
    print("-" * 30)
    final_stats = manager.get_statistics()
    query_stats = final_stats['query_statistics']
    print(f"총 실행된 쿼리 수: {query_stats['total_queries']}")
    print(f"캐시 히트: {query_stats['cache_hits']}")
    print(f"캐시 미스: {query_stats['cache_misses']}")
    print(f"평균 실행 시간: {query_stats['avg_execution_time']:.6f}초")


if __name__ == "__main__":
    demo_sparql_manager()