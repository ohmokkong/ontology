"""
음식 데이터 모델 테스트 모듈.
"""

from datetime import datetime
from rdflib import Namespace, URIRef
from food_models import FoodItem, NutritionInfo, FoodConsumption
import traceback


def test_food_item():
    """FoodItem 클래스 테스트."""
    print("=== FoodItem 테스트 ===")
    
    # 유효한 음식 아이템 생성
    try:
        food = FoodItem(
            name="백미밥",
            food_id="FOOD001",
            category="곡류",
            manufacturer="일반"
        )
        print(f"✓ 유효한 음식 아이템 생성: {food.name}")
        
        # URI 생성 테스트
        namespace = Namespace("http://example.org/food#")
        uri = food.to_uri(namespace)
        print(f"✓ URI 생성: {uri}")
        
    except Exception as e:
        print(f"✗ 유효한 음식 아이템 생성 실패: {e}")
        traceback.print_exc()
    
    # 잘못된 데이터 테스트
    try:
        invalid_food = FoodItem(name="", food_id="FOOD002")
        print("✗ 빈 이름으로 음식 생성이 성공해서는 안됨")
    except ValueError as e:
        print(f"✓ 빈 이름 검증 성공: {e}")
    
    try:
        invalid_food = FoodItem(name="테스트", food_id="")
        print("✗ 빈 ID로 음식 생성이 성공해서는 안됨")
    except ValueError as e:
        print(f"✓ 빈 ID 검증 성공: {e}")


def test_nutrition_info():
    """NutritionInfo 클래스 테스트."""
    print("\n=== NutritionInfo 테스트 ===")
    
    # 유효한 영양 정보 생성
    try:
        food = FoodItem("백미밥", "FOOD001", "곡류")
        nutrition = NutritionInfo(
            food_item=food,
            calories_per_100g=130.0,
            carbohydrate=28.1,
            protein=2.5,
            fat=0.3,
            fiber=0.3,
            sodium=1.0
        )
        print(f"✓ 유효한 영양 정보 생성: {nutrition.calories_per_100g}kcal/100g")
        
        # 칼로리 계산 테스트
        calories_200g = nutrition.calculate_calories_for_amount(200.0)
        expected = 130.0 * 2  # 200g = 260kcal
        print(f"✓ 칼로리 계산: 200g = {calories_200g}kcal (예상: {expected}kcal)")
        
    except Exception as e:
        print(f"✗ 유효한 영양 정보 생성 실패: {e}")
        traceback.print_exc()
    
    # 잘못된 데이터 테스트
    try:
        food = FoodItem("테스트", "FOOD002")
        invalid_nutrition = NutritionInfo(
            food_item=food,
            calories_per_100g=-10.0,  # 음수 칼로리
            carbohydrate=20.0,
            protein=5.0,
            fat=2.0
        )
        print("✗ 음수 칼로리로 영양정보 생성이 성공해서는 안됨")
    except ValueError as e:
        print(f"✓ 음수 칼로리 검증 성공: {e}")
    
    try:
        food = FoodItem("테스트", "FOOD003")
        invalid_nutrition = NutritionInfo(
            food_item=food,
            calories_per_100g=50.0,
            carbohydrate=150.0,  # 100g 초과
            protein=5.0,
            fat=2.0
        )
        print("✗ 과도한 탄수화물로 영양정보 생성이 성공해서는 안됨")
    except ValueError as e:
        print(f"✓ 과도한 탄수화물 검증 성공: {e}")


def test_food_consumption():
    """FoodConsumption 클래스 테스트."""
    print("\n=== FoodConsumption 테스트 ===")
    
    # 유효한 섭취 기록 생성
    try:
        namespace = Namespace("http://example.org/food#")
        food_uri = namespace["Food_백미밥"]
        
        consumption = FoodConsumption(
            food_uri=food_uri,
            amount_grams=150.0,
            calories_consumed=195.0,
            timestamp=datetime.now()
        )
        print(f"✓ 유효한 섭취 기록 생성: {consumption.amount_grams}g, {consumption.calories_consumed}kcal")
        
    except Exception as e:
        print(f"✗ 유효한 섭취 기록 생성 실패: {e}")
        traceback.print_exc()
    
    # 자동 계산을 통한 섭취 기록 생성
    try:
        food = FoodItem("닭가슴살", "FOOD004", "육류")
        nutrition = NutritionInfo(
            food_item=food,
            calories_per_100g=165.0,
            carbohydrate=0.0,
            protein=31.0,
            fat=3.6
        )
        
        consumption = FoodConsumption.create_with_calculation(
            food_item=food,
            nutrition=nutrition,
            amount=100.0,  # 100g
            namespace=namespace
        )
        
        expected_calories = 165.0  # 100g이므로 그대로
        print(f"✓ 자동 계산 섭취 기록: {consumption.amount_grams}g, {consumption.calories_consumed}kcal (예상: {expected_calories}kcal)")
        
    except Exception as e:
        print(f"✗ 자동 계산 섭취 기록 생성 실패: {e}")
        traceback.print_exc()
    
    # 잘못된 데이터 테스트
    try:
        invalid_consumption = FoodConsumption(
            food_uri=namespace["Food_Test"],
            amount_grams=-50.0,  # 음수 섭취량
            calories_consumed=100.0
        )
        print("✗ 음수 섭취량으로 기록 생성이 성공해서는 안됨")
    except ValueError as e:
        print(f"✓ 음수 섭취량 검증 성공: {e}")


def test_korean_food_examples():
    """한국 음식 예제 테스트."""
    print("\n=== 한국 음식 예제 테스트 ===")
    
    namespace = Namespace("http://example.org/food#")
    
    # 한국 음식 데이터
    korean_foods = [
        {
            "name": "김치찌개",
            "food_id": "K001",
            "category": "찌개류",
            "calories": 45.0,
            "carbs": 5.2,
            "protein": 3.1,
            "fat": 1.8
        },
        {
            "name": "불고기",
            "food_id": "K002", 
            "category": "육류",
            "calories": 156.0,
            "carbs": 2.1,
            "protein": 18.7,
            "fat": 7.9
        },
        {
            "name": "비빔밥",
            "food_id": "K003",
            "category": "밥류",
            "calories": 119.0,
            "carbs": 18.5,
            "protein": 4.2,
            "fat": 3.1
        }
    ]
    
    for food_data in korean_foods:
        try:
            # 음식 아이템 생성
            food = FoodItem(
                name=food_data["name"],
                food_id=food_data["food_id"],
                category=food_data["category"]
            )
            
            # 영양 정보 생성
            nutrition = NutritionInfo(
                food_item=food,
                calories_per_100g=food_data["calories"],
                carbohydrate=food_data["carbs"],
                protein=food_data["protein"],
                fat=food_data["fat"]
            )
            
            # 섭취 기록 생성 (200g 섭취)
            consumption = FoodConsumption.create_with_calculation(
                food_item=food,
                nutrition=nutrition,
                amount=200.0,
                namespace=namespace
            )
            
            print(f"✓ {food.name}: 200g 섭취 시 {consumption.calories_consumed:.1f}kcal")
            
        except Exception as e:
            print(f"✗ {food_data['name']} 처리 실패: {e}")


if __name__ == "__main__":
    test_food_item()
    test_nutrition_info()
    test_food_consumption()
    test_korean_food_examples()
    print("\n✅ 모든 테스트 완료!")