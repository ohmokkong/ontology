"""
음식 관련 데이터 모델 모듈.

식약처 식품영양성분 API에서 받은 데이터를 처리하기 위한 
데이터클래스들과 검증 로직을 포함합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Union
from rdflib import URIRef, Namespace
import re


@dataclass
class FoodItem:
    """
    식약처 API에서 받은 음식 정보를 나타내는 데이터 클래스.
    
    Attributes:
        name: 음식명 (한국어)
        food_id: API에서 제공하는 고유 식품 ID
        category: 식품 분류 (예: 곡류, 육류 등)
        manufacturer: 제조사 또는 브랜드명
    """
    name: str
    food_id: str
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    
    def __post_init__(self):
        """데이터 초기화 후 검증 수행."""
        self.validate()
    
    def validate(self) -> None:
        """
        음식 아이템 데이터 검증.
        
        Raises:
            ValueError: 검증 실패 시
        """
        if not self.name or not self.name.strip():
            raise ValueError("음식명은 필수입니다")
        
        if not self.food_id or not self.food_id.strip():
            raise ValueError("식품 ID는 필수입니다")
        
        # 데이터 정리
        self.name = self.name.strip()
        self.food_id = self.food_id.strip()
        
        if self.category:
            self.category = self.category.strip()
        if self.manufacturer:
            self.manufacturer = self.manufacturer.strip()
    
    def to_uri(self, namespace: Namespace) -> URIRef:
        """
        음식명을 RDF URI로 변환.
        
        Args:
            namespace: 사용할 RDF 네임스페이스
            
        Returns:
            URIRef: 생성된 URI
        """
        # 한국어 음식명을 URI에 적합한 형태로 변환
        normalized_name = re.sub(r'[^\w\s-]', '', self.name)
        normalized_name = re.sub(r'\s+', '_', normalized_name)
        normalized_name = normalized_name.strip('_')
        
        if not normalized_name:
            # 한국어가 제거된 경우 food_id 사용
            normalized_name = f"Food_{self.food_id}"
        else:
            normalized_name = f"Food_{normalized_name}"
        
        return namespace[normalized_name]


@dataclass
class NutritionInfo:
    """
    음식의 영양 정보를 나타내는 데이터 클래스.
    
    Attributes:
        food_item: 해당 음식 아이템
        calories_per_100g: 100g당 칼로리 (kcal)
        carbohydrate: 탄수화물 함량 (g/100g)
        protein: 단백질 함량 (g/100g)
        fat: 지방 함량 (g/100g)
        fiber: 식이섬유 함량 (g/100g, 선택사항)
        sodium: 나트륨 함량 (mg/100g, 선택사항)
    """
    food_item: FoodItem
    calories_per_100g: float
    carbohydrate: float
    protein: float
    fat: float
    fiber: Optional[float] = None
    sodium: Optional[float] = None
    
    def __post_init__(self):
        """데이터 초기화 후 검증 수행."""
        self.validate_nutrition_data()
    
    def validate_nutrition_data(self) -> None:
        """
        영양 정보 데이터 검증.
        
        Raises:
            ValueError: 검증 실패 시
        """
        if not isinstance(self.food_item, FoodItem):
            raise ValueError("food_item은 FoodItem 인스턴스여야 합니다")
        
        # 필수 영양소 검증
        required_nutrients = {
            'calories_per_100g': self.calories_per_100g,
            'carbohydrate': self.carbohydrate,
            'protein': self.protein,
            'fat': self.fat
        }
        
        for name, value in required_nutrients.items():
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"{name}은 0 이상의 숫자여야 합니다")
        
        # 합리적인 범위 검증
        if self.calories_per_100g > 900:  # 기름류도 900kcal 정도
            raise ValueError("칼로리가 너무 높습니다 (>900kcal/100g)")
        
        if self.carbohydrate > 100:
            raise ValueError("탄수화물 함량이 100g을 초과할 수 없습니다")
        
        if self.protein > 100:
            raise ValueError("단백질 함량이 100g을 초과할 수 없습니다")
        
        if self.fat > 100:
            raise ValueError("지방 함량이 100g을 초과할 수 없습니다")
        
        # 선택적 영양소 검증
        if self.fiber is not None:
            if not isinstance(self.fiber, (int, float)) or self.fiber < 0:
                raise ValueError("식이섬유는 0 이상의 숫자여야 합니다")
            if self.fiber > 100:
                raise ValueError("식이섬유 함량이 100g을 초과할 수 없습니다")
        
        if self.sodium is not None:
            if not isinstance(self.sodium, (int, float)) or self.sodium < 0:
                raise ValueError("나트륨은 0 이상의 숫자여야 합니다")
            if self.sodium > 50000:  # 50g = 50,000mg (매우 짠 음식도 이 정도)
                raise ValueError("나트륨 함량이 너무 높습니다 (>50,000mg/100g)")
    
    def calculate_calories_for_amount(self, amount_grams: float) -> float:
        """
        특정 양에 대한 칼로리 계산.
        
        Args:
            amount_grams: 음식의 양 (그램)
            
        Returns:
            float: 계산된 칼로리
        """
        if amount_grams <= 0:
            raise ValueError("음식의 양은 0보다 커야 합니다")
        
        return (self.calories_per_100g * amount_grams) / 100.0


@dataclass
class FoodConsumption:
    """
    사용자의 음식 섭취 기록을 나타내는 데이터 클래스.
    
    Attributes:
        food_uri: 섭취한 음식의 RDF URI
        amount_grams: 섭취량 (그램)
        calories_consumed: 섭취한 칼로리
        timestamp: 섭취 시간
    """
    food_uri: URIRef
    amount_grams: float
    calories_consumed: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """데이터 초기화 후 검증 수행."""
        self.validate()
    
    def validate(self) -> None:
        """
        음식 섭취 데이터 검증.
        
        Raises:
            ValueError: 검증 실패 시
        """
        if not isinstance(self.food_uri, URIRef):
            raise ValueError("food_uri는 URIRef 타입이어야 합니다")
        
        if not isinstance(self.amount_grams, (int, float)) or self.amount_grams <= 0:
            raise ValueError("섭취량은 0보다 큰 숫자여야 합니다")
        
        if self.amount_grams > 5000:  # 5kg 이상은 비현실적
            raise ValueError("섭취량이 너무 많습니다 (>5000g)")
        
        if not isinstance(self.calories_consumed, (int, float)) or self.calories_consumed < 0:
            raise ValueError("섭취 칼로리는 0 이상의 숫자여야 합니다")
        
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp는 datetime 객체여야 합니다")
    
    @classmethod
    def create_with_calculation(
        cls,
        food_item: FoodItem,
        nutrition: NutritionInfo,
        amount: float,
        namespace: Namespace,
        timestamp: Optional[datetime] = None
    ) -> 'FoodConsumption':
        """
        자동 칼로리 계산을 통한 음식 섭취 기록 생성.
        
        Args:
            food_item: 음식 아이템
            nutrition: 영양 정보
            amount: 섭취량 (그램)
            namespace: RDF 네임스페이스
            timestamp: 섭취 시간 (기본값: 현재 시간)
            
        Returns:
            FoodConsumption: 생성된 섭취 기록
        """
        food_uri = food_item.to_uri(namespace)
        calories = nutrition.calculate_calories_for_amount(amount)
        
        return cls(
            food_uri=food_uri,
            amount_grams=amount,
            calories_consumed=calories,
            timestamp=timestamp or datetime.now()
        )


# 타입 별칭
FoodData = Union[FoodItem, NutritionInfo, FoodConsumption]