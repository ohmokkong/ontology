"""
온톨로지 스키마 확장 데모 스크립트.
이 스크립트는 온톨로지 스키마 매니저를 사용하여 기존 온톨로지를 확장하는 예제입니다.
"""

import logging
from ontology_schema_manager import OntologySchemaManager

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    """메인 함수."""
    print("=== 온톨로지 스키마 확장 데모 ===")
    
    try:
        # 온톨로지 스키마 매니저 초기화
        print("\n1. 온톨로지 스키마 매니저 초기화...")
        schema_manager = OntologySchemaManager(
            base_ontology_path="diet-ontology.ttl",
            namespace_uri="http://example.org/diet#"
        )
        
        # 초기 통계 출력
        initial_stats = schema_manager.get_schema_statistics()
        print(f"초기 스키마 통계:")
        print(f"  - 총 트리플 수: {initial_stats['total_triples']}")
        print(f"  - 클래스 수: {initial_stats['classes']}")
        print(f"  - 데이터 속성 수: {initial_stats['data_properties']}")
        print(f"  - 객체 속성 수: {initial_stats['object_properties']}")
        
        # 스키마 확장 수행
        print("\n2. 스키마 확장 수행...")
        schema_manager.extend_schema()
        
        # 확장 후 통계 출력
        final_stats = schema_manager.get_schema_statistics()
        print(f"확장 후 스키마 통계:")
        print(f"  - 총 트리플 수: {final_stats['total_triples']} (+{final_stats['total_triples'] - initial_stats['total_triples']})")
        print(f"  - 클래스 수: {final_stats['classes']} (+{final_stats['classes'] - initial_stats['classes']})")
        print(f"  - 데이터 속성 수: {final_stats['data_properties']} (+{final_stats['data_properties'] - initial_stats['data_properties']})")
        print(f"  - 객체 속성 수: {final_stats['object_properties']} (+{final_stats['object_properties'] - initial_stats['object_properties']})")
        
        # 스키마 검증
        print("\n3. 스키마 검증...")
        validation_result = schema_manager.validate_schema()
        
        if validation_result['is_valid']:
            print("✅ 스키마 검증 성공!")
        else:
            print("❌ 스키마 검증 실패:")
            for error in validation_result['errors']:
                print(f"  - 오류: {error}")
        
        if validation_result['warnings']:
            print("⚠️ 경고사항:")
            for warning in validation_result['warnings']:
                print(f"  - 경고: {warning}")
        
        # 확장된 스키마 저장
        print("\n4. 확장된 스키마 저장...")
        output_path = schema_manager.save_extended_schema("extended-diet-ontology.ttl")
        print(f"✅ 확장된 스키마 저장 완료: {output_path}")
        
        # 추가된 클래스들 출력
        print("\n5. 추가된 주요 클래스들:")
        added_classes = [
            "FoodItem", "NutritionInfo", "FoodConsumption", "FoodCategory", "Manufacturer",
            "ExerciseItem", "ExerciseSession", "ExerciseCategory", "METValue"
        ]
        
        for class_name in added_classes:
            print(f"  - {class_name}: {schema_manager.ns[class_name]}")
        
        # 추가된 주요 속성들 출력
        print("\n6. 추가된 주요 속성들:")
        added_properties = [
            "hasMET", "hasServingSize", "hasFiber", "hasSodium", "hasCaloriesPer100g",
            "hasAmount", "hasConsumedCalories", "performedExercise", "hasNutritionInfo"
        ]
        
        for prop_name in added_properties:
            print(f"  - {prop_name}: {schema_manager.ns[prop_name]}")
        
        print("\n=== 온톨로지 스키마 확장 완료 ===")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()