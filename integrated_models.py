"""
통합 데이터 모델 모듈.

식약처 식품영양성분 API와 한국건강증진개발원 운동 API에서 받은 
데이터를 처리하기 위한 통합 데이터클래스들과 검증 로직을 포함합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Union, List
from rdflib import URIRef, Namespace
import re


# ==================== 음식 관련 데이터 모델 ====================

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


# ==================== 운동 관련 데이터 모델 ====================

@dataclass
class ExerciseItem:
    """
    한국건강증진개발원 API에서 받은 운동 정보를 나타내는 데이터 클래스.
    
    Attributes:
        name: 운동명 (한국어)
        description: 운동에 대한 상세 설명
        met_value: 대사당량(MET) 계수
        category: 운동 분류 (예: 유산소, 근력 등)
        exercise_id: API에서 제공하는 고유 운동 ID (선택사항)
    """
    name: str
    description: str
    met_value: float
    category: Optional[str] = None
    exercise_id: Optional[str] = None
    
    def __post_init__(self):
        """데이터 초기화 후 검증 수행."""
        self.validate()
    
    def validate(self) -> None:
        """
        운동 아이템 데이터 검증.
        
        Raises:
            ValueError: 검증 실패 시
        """
        if not self.name or not self.name.strip():
            raise ValueError("운동명은 필수입니다")
        
        if not self.description or not self.description.strip():
            raise ValueError("운동 설명은 필수입니다")
        
        if not isinstance(self.met_value, (int, float)) or self.met_value <= 0:
            raise ValueError("MET 값은 양수여야 합니다")
        
        if self.met_value > 20:  # 매우 격렬한 운동도 20 MET 정도
            raise ValueError("MET 값이 너무 높습니다 (>20)")
        
        # 데이터 정리
        self.name = self.name.strip()
        self.description = self.description.strip()
        if self.category:
            self.category = self.category.strip()
        if self.exercise_id:
            self.exercise_id = self.exercise_id.strip()
    
    def to_uri(self, namespace: Namespace) -> URIRef:
        """
        운동명을 RDF URI로 변환.
        
        Args:
            namespace: 사용할 RDF 네임스페이스
            
        Returns:
            URIRef: 생성된 URI
        """
        # 한국어 운동명을 URI에 적합한 형태로 변환
        normalized_name = re.sub(r'[^\w\s-]', '', self.name)
        normalized_name = re.sub(r'\s+', '_', normalized_name)
        normalized_name = normalized_name.strip('_')
        
        if not normalized_name:
            # 한국어가 제거된 경우 exercise_id 또는 기본값 사용
            if self.exercise_id:
                normalized_name = f"Exercise_{self.exercise_id}"
            else:
                normalized_name = f"Exercise_{hash(self.name) % 10000}"
        else:
            normalized_name = f"Exercise_{normalized_name}"
        
        return namespace[normalized_name]


@dataclass
class ExerciseSession:
    """
    사용자의 운동 세션 기록을 나타내는 데이터 클래스.
    
    Attributes:
        exercise_uri: 수행한 운동의 RDF URI
        weight: 사용자 체중 (kg)
        duration: 운동 시간 (분)
        calories_burned: 소모된 칼로리 (kcal)
        timestamp: 운동 수행 시간
    """
    exercise_uri: URIRef
    weight: float
    duration: float
    calories_burned: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """데이터 초기화 후 검증 수행."""
        self.validate()
    
    def validate(self) -> None:
        """
        운동 세션 데이터 검증.
        
        Raises:
            ValueError: 검증 실패 시
        """
        if not isinstance(self.exercise_uri, URIRef):
            raise ValueError("exercise_uri는 URIRef 타입이어야 합니다")
        
        if not isinstance(self.weight, (int, float)) or self.weight <= 0:
            raise ValueError("체중은 0보다 큰 숫자여야 합니다")
        
        if self.weight > 500:  # 합리적인 상한선
            raise ValueError("체중이 너무 높습니다 (>500kg)")
        
        if not isinstance(self.duration, (int, float)) or self.duration <= 0:
            raise ValueError("운동 시간은 0보다 큰 숫자여야 합니다")
        
        if self.duration > 1440:  # 24시간 이상은 비현실적
            raise ValueError("운동 시간이 너무 깁니다 (>24시간)")
        
        if not isinstance(self.calories_burned, (int, float)) or self.calories_burned < 0:
            raise ValueError("소모 칼로리는 0 이상의 숫자여야 합니다")
        
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp는 datetime 객체여야 합니다")
    
    @classmethod
    def create_with_calculation(
        cls,
        exercise_item: ExerciseItem,
        weight: float,
        duration: float,
        namespace: Namespace,
        timestamp: Optional[datetime] = None
    ) -> 'ExerciseSession':
        """
        자동 칼로리 계산을 통한 운동 세션 생성.
        
        Args:
            exercise_item: 운동 아이템
            weight: 사용자 체중 (kg)
            duration: 운동 시간 (분)
            namespace: RDF 네임스페이스
            timestamp: 운동 시간 (기본값: 현재 시간)
            
        Returns:
            ExerciseSession: 생성된 운동 세션
        """
        exercise_uri = exercise_item.to_uri(namespace)
        calories_burned = cls.calculate_calories(exercise_item.met_value, weight, duration)
        
        return cls(
            exercise_uri=exercise_uri,
            weight=weight,
            duration=duration,
            calories_burned=calories_burned,
            timestamp=timestamp or datetime.now()
        )
    
    @staticmethod
    def calculate_calories(met_value: float, weight: float, duration_minutes: float) -> float:
        """
        MET 공식을 사용한 칼로리 계산.
        
        공식: MET × 체중(kg) × 시간(시간)
        
        Args:
            met_value: 대사당량 계수
            weight: 체중 (kg)
            duration_minutes: 운동 시간 (분)
            
        Returns:
            float: 소모된 칼로리 (kcal)
        """
        if met_value <= 0 or weight <= 0 or duration_minutes <= 0:
            raise ValueError("모든 값은 양수여야 합니다")
        
        duration_hours = duration_minutes / 60.0
        return met_value * weight * duration_hours


# ==================== 통합 분석 데이터 모델 ====================

@dataclass
class NetCalorieResult:
    """
    순 칼로리 계산 결과를 나타내는 데이터 클래스.
    
    Attributes:
        total_consumed: 총 섭취 칼로리
        total_burned: 총 소모 칼로리
        net_calories: 순 칼로리 (섭취 - 소모)
        date: 계산 대상 날짜
        food_consumptions: 음식 섭취 기록들
        exercise_sessions: 운동 세션 기록들
    """
    total_consumed: float
    total_burned: float
    net_calories: float
    date: datetime.date
    food_consumptions: List[FoodConsumption] = field(default_factory=list)
    exercise_sessions: List[ExerciseSession] = field(default_factory=list)
    
    def __post_init__(self):
        """계산 결과 검증."""
        if abs(self.net_calories - (self.total_consumed - self.total_burned)) > 0.01:
            raise ValueError("순 칼로리 계산이 일치하지 않습니다")


@dataclass
class DailyAnalysis:
    """
    일일 칼로리 분석 결과를 나타내는 데이터 클래스.
    
    Attributes:
        date: 분석 날짜
        net_calorie_result: 순 칼로리 계산 결과
        goal_calories: 목표 칼로리 (선택사항)
        achievement_rate: 목표 달성률 (선택사항)
        recommendations: 권장사항 목록
    """
    date: datetime.date
    net_calorie_result: NetCalorieResult
    goal_calories: Optional[float] = None
    achievement_rate: Optional[float] = None
    recommendations: List[str] = field(default_factory=list)
    
    def calculate_achievement_rate(self, goal: float) -> float:
        """
        목표 칼로리 대비 달성률 계산.
        
        Args:
            goal: 목표 칼로리
            
        Returns:
            float: 달성률 (%)
        """
        if goal <= 0:
            raise ValueError("목표 칼로리는 0보다 커야 합니다")
        
        self.goal_calories = goal
        self.achievement_rate = (self.net_calorie_result.net_calories / goal) * 100
        return self.achievement_rate


# 타입 별칭
FoodData = Union[FoodItem, NutritionInfo, FoodConsumption]
ExerciseData = Union[ExerciseItem, ExerciseSession]
AnalysisData = Union[NetCalorieResult, DailyAnalysis]