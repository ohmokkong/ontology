"""
칼로리 매니저.

음식 섭취량 기반 칼로리 계산, MET 공식 기반 운동 소모 칼로리 계산,
순 칼로리(섭취-소모) 계산 기능을 제공합니다.
"""

import math
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from enum import Enum

from integrated_models import FoodItem, NutritionInfo, ExerciseItem, FoodConsumption, ExerciseSession
from exceptions import (
    CalorieCalculationError, InvalidMETValueError, InvalidWeightError, 
    InvalidAmountError, DataValidationError
)


class ActivityLevel(Enum):
    """활동 수준 분류."""
    SEDENTARY = "sedentary"      # 좌식 생활
    LIGHTLY_ACTIVE = "lightly"   # 가벼운 활동
    MODERATELY_ACTIVE = "moderate"  # 보통 활동
    VERY_ACTIVE = "very"         # 활발한 활동
    EXTREMELY_ACTIVE = "extreme"  # 매우 활발한 활동


@dataclass
class CalorieGoal:
    """칼로리 목표 설정."""
    daily_intake_goal: float  # 일일 섭취 목표 (kcal)
    daily_burn_goal: float    # 일일 소모 목표 (kcal)
    weight_goal: Optional[float] = None  # 목표 체중 (kg)
    target_date: Optional[date] = None   # 목표 달성 날짜
    activity_level: ActivityLevel = ActivityLevel.MODERATELY_ACTIVE


@dataclass
class NetCalorieResult:
    """순 칼로리 계산 결과."""
    total_intake: float       # 총 섭취 칼로리
    total_burned: float       # 총 소모 칼로리
    net_calories: float       # 순 칼로리 (섭취 - 소모)
    food_count: int          # 음식 섭취 횟수
    exercise_count: int      # 운동 세션 수
    calculation_date: datetime = field(default_factory=datetime.now)


@dataclass
class GoalComparison:
    """목표 대비 실제 성과 비교."""
    actual_value: float
    goal_value: float
    achievement_rate: float  # 달성률 (%)
    difference: float        # 차이 (실제 - 목표)
    status: str             # "달성", "미달성", "초과달성"
    recommendation: str     # 권장사항


@dataclass
class DailyAnalysis:
    """일일 칼로리 분석 결과."""
    analysis_date: date
    total_intake: float
    total_burned: float
    net_calories: float
    goal_intake: Optional[float] = None
    goal_burn: Optional[float] = None
    intake_achievement_rate: Optional[float] = None  # 섭취 목표 달성률 (%)
    burn_achievement_rate: Optional[float] = None    # 소모 목표 달성률 (%)
    food_breakdown: Dict[str, float] = field(default_factory=dict)  # 음식별 칼로리
    exercise_breakdown: Dict[str, float] = field(default_factory=dict)  # 운동별 칼로리
    recommendations: List[str] = field(default_factory=list)  # 권장사항


class CalorieManager:
    """
    칼로리 계산 및 분석 매니저.
    
    음식 섭취량 기반 칼로리 계산, MET 공식 기반 운동 소모 칼로리 계산,
    순 칼로리 분석 및 목표 대비 성과 분석 기능을 제공합니다.
    """
    
    def __init__(self, default_weight: float = 70.0):
        """
        CalorieManager 초기화.
        
        Args:
            default_weight: 기본 체중 (kg)
        """
        self.default_weight = default_weight
        
        # 칼로리 계산 통계
        self.calculation_stats = {
            "total_calculations": 0,
            "food_calculations": 0,
            "exercise_calculations": 0,
            "net_calculations": 0,
            "average_intake": 0.0,
            "average_burn": 0.0
        }
        
        # BMR 계산을 위한 기본 상수
        self.bmr_constants = {
            "male": {"base": 88.362, "weight": 13.397, "height": 4.799, "age": 5.677},
            "female": {"base": 447.593, "weight": 9.247, "height": 3.098, "age": 4.330}
        }
        
        # 활동 수준별 계수
        self.activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHTLY_ACTIVE: 1.375,
            ActivityLevel.MODERATELY_ACTIVE: 1.55,
            ActivityLevel.VERY_ACTIVE: 1.725,
            ActivityLevel.EXTREMELY_ACTIVE: 1.9
        }
        
        print("✓ 칼로리 매니저 초기화 완료")
        print(f"  - 기본 체중: {default_weight}kg")
    
    def calculate_food_calories(self, food: FoodItem, nutrition: NutritionInfo, amount: float) -> float:
        """
        음식 섭취량 기반 칼로리 계산.
        
        Args:
            food: 음식 아이템
            nutrition: 영양정보 (100g 기준)
            amount: 섭취량 (g)
            
        Returns:
            float: 계산된 칼로리 (kcal)
            
        Raises:
            InvalidAmountError: 잘못된 섭취량
            CalorieCalculationError: 계산 오류
        """
        if amount <= 0:
            raise InvalidAmountError(f"섭취량은 0보다 커야 합니다: {amount}g")
        
        if amount > 10000:  # 10kg 이상은 비현실적
            raise InvalidAmountError(f"섭취량이 너무 큽니다: {amount}g")
        
        try:
            # 100g 기준 칼로리를 실제 섭취량에 맞게 계산
            calories_per_100g = nutrition.calories_per_100g
            calculated_calories = (calories_per_100g * amount) / 100.0
            
            # 통계 업데이트
            self.calculation_stats["food_calculations"] += 1
            self.calculation_stats["total_calculations"] += 1
            self._update_average_intake(calculated_calories)
            
            print(f"🍽️ 음식 칼로리 계산: {food.name} {amount}g = {calculated_calories:.1f}kcal")
            return round(calculated_calories, 1)
            
        except Exception as e:
            raise CalorieCalculationError(f"음식 칼로리 계산 실패: {str(e)}")
    
    def calculate_exercise_calories(self, exercise: ExerciseItem, weight: float, duration: float) -> float:
        """
        MET 공식 기반 운동 소모 칼로리 계산.
        
        공식: 소모 칼로리 = MET × 체중(kg) × 시간(h)
        
        Args:
            exercise: 운동 아이템
            weight: 체중 (kg)
            duration: 운동 시간 (분)
            
        Returns:
            float: 계산된 소모 칼로리 (kcal)
            
        Raises:
            InvalidMETValueError: 잘못된 MET 값
            InvalidWeightError: 잘못된 체중
            InvalidAmountError: 잘못된 운동 시간
        """
        # 입력값 검증
        if not exercise.met_value or exercise.met_value <= 0:
            raise InvalidMETValueError(f"유효하지 않은 MET 값: {exercise.met_value}")
        
        if weight <= 0 or weight > 500:  # 현실적인 체중 범위
            raise InvalidWeightError(f"유효하지 않은 체중: {weight}kg")
        
        if duration <= 0 or duration > 1440:  # 최대 24시간
            raise InvalidAmountError(f"유효하지 않은 운동 시간: {duration}분")
        
        try:
            # MET 공식 적용: MET × 체중(kg) × 시간(h)
            duration_hours = duration / 60.0
            burned_calories = exercise.met_value * weight * duration_hours
            
            # 통계 업데이트
            self.calculation_stats["exercise_calculations"] += 1
            self.calculation_stats["total_calculations"] += 1
            self._update_average_burn(burned_calories)
            
            print(f"🏃 운동 칼로리 계산: {exercise.name} {duration}분 (체중 {weight}kg) = {burned_calories:.1f}kcal")
            print(f"  - MET: {exercise.met_value}, 공식: {exercise.met_value} × {weight} × {duration_hours:.2f}")
            
            return round(burned_calories, 1)
            
        except Exception as e:
            raise CalorieCalculationError(f"운동 칼로리 계산 실패: {str(e)}")
    
    def calculate_net_calories(self, consumptions: List[FoodConsumption], 
                             sessions: List[ExerciseSession]) -> NetCalorieResult:
        """
        순 칼로리(섭취-소모) 계산.
        
        Args:
            consumptions: 음식 섭취 목록
            sessions: 운동 세션 목록
            
        Returns:
            NetCalorieResult: 순 칼로리 계산 결과
        """
        print(f"📊 순 칼로리 계산: 음식 {len(consumptions)}개, 운동 {len(sessions)}개")
        
        try:
            # 총 섭취 칼로리 계산
            total_intake = sum(consumption.calories_consumed for consumption in consumptions)
            
            # 총 소모 칼로리 계산
            total_burned = sum(session.calories_burned for session in sessions)
            
            # 순 칼로리 계산 (섭취 - 소모)
            net_calories = total_intake - total_burned
            
            # 결과 생성
            result = NetCalorieResult(
                total_intake=round(total_intake, 1),
                total_burned=round(total_burned, 1),
                net_calories=round(net_calories, 1),
                food_count=len(consumptions),
                exercise_count=len(sessions)
            )
            
            # 통계 업데이트
            self.calculation_stats["net_calculations"] += 1
            self.calculation_stats["total_calculations"] += 1
            
            print(f"✓ 순 칼로리 계산 완료:")
            print(f"  - 총 섭취: {result.total_intake}kcal")
            print(f"  - 총 소모: {result.total_burned}kcal")
            print(f"  - 순 칼로리: {result.net_calories}kcal")
            
            return result
            
        except Exception as e:
            raise CalorieCalculationError(f"순 칼로리 계산 실패: {str(e)}")
    
    def analyze_daily_balance(self, analysis_date: date, consumptions: List[FoodConsumption],
                            sessions: List[ExerciseSession], goal: Optional[CalorieGoal] = None) -> DailyAnalysis:
        """
        일일 칼로리 밸런스 분석.
        
        Args:
            analysis_date: 분석 날짜
            consumptions: 해당 날짜의 음식 섭취 목록
            sessions: 해당 날짜의 운동 세션 목록
            goal: 칼로리 목표 (선택사항)
            
        Returns:
            DailyAnalysis: 일일 분석 결과
        """
        print(f"📈 일일 칼로리 분석: {analysis_date}")
        
        try:
            # 순 칼로리 계산
            net_result = self.calculate_net_calories(consumptions, sessions)
            
            # 음식별 칼로리 분석
            food_breakdown = {}
            for consumption in consumptions:
                food_name = consumption.food_uri.split('/')[-1] if hasattr(consumption.food_uri, 'split') else str(consumption.food_uri)
                if food_name in food_breakdown:
                    food_breakdown[food_name] += consumption.calories_consumed
                else:
                    food_breakdown[food_name] = consumption.calories_consumed
            
            # 운동별 칼로리 분석
            exercise_breakdown = {}
            for session in sessions:
                exercise_name = session.exercise_uri.split('/')[-1] if hasattr(session.exercise_uri, 'split') else str(session.exercise_uri)
                if exercise_name in exercise_breakdown:
                    exercise_breakdown[exercise_name] += session.calories_burned
                else:
                    exercise_breakdown[exercise_name] = session.calories_burned
            
            # 목표 대비 달성률 계산
            intake_achievement_rate = None
            burn_achievement_rate = None
            goal_intake = None
            goal_burn = None
            
            if goal:
                goal_intake = goal.daily_intake_goal
                goal_burn = goal.daily_burn_goal
                
                if goal_intake > 0:
                    intake_achievement_rate = (net_result.total_intake / goal_intake) * 100
                
                if goal_burn > 0:
                    burn_achievement_rate = (net_result.total_burned / goal_burn) * 100
            
            # 권장사항 생성
            recommendations = self._generate_recommendations(
                net_result, goal, intake_achievement_rate, burn_achievement_rate
            )
            
            # 분석 결과 생성
            analysis = DailyAnalysis(
                analysis_date=analysis_date,
                total_intake=net_result.total_intake,
                total_burned=net_result.total_burned,
                net_calories=net_result.net_calories,
                goal_intake=goal_intake,
                goal_burn=goal_burn,
                intake_achievement_rate=intake_achievement_rate,
                burn_achievement_rate=burn_achievement_rate,
                food_breakdown=food_breakdown,
                exercise_breakdown=exercise_breakdown,
                recommendations=recommendations
            )
            
            print(f"✓ 일일 분석 완료:")
            print(f"  - 섭취 칼로리: {analysis.total_intake}kcal")
            print(f"  - 소모 칼로리: {analysis.total_burned}kcal")
            print(f"  - 순 칼로리: {analysis.net_calories}kcal")
            if intake_achievement_rate:
                print(f"  - 섭취 목표 달성률: {intake_achievement_rate:.1f}%")
            if burn_achievement_rate:
                print(f"  - 소모 목표 달성률: {burn_achievement_rate:.1f}%")
            
            return analysis
            
        except Exception as e:
            raise CalorieCalculationError(f"일일 분석 실패: {str(e)}")
    
    def compare_with_goal(self, actual: float, goal: float, metric_name: str = "칼로리") -> GoalComparison:
        """
        목표 대비 실제 성과 비교.
        
        Args:
            actual: 실제 값
            goal: 목표 값
            metric_name: 지표 이름
            
        Returns:
            GoalComparison: 목표 비교 결과
        """
        if goal <= 0:
            raise CalorieCalculationError(f"목표 값은 0보다 커야 합니다: {goal}")
        
        try:
            achievement_rate = (actual / goal) * 100
            difference = actual - goal
            
            # 상태 결정
            if achievement_rate >= 95 and achievement_rate <= 105:
                status = "달성"
            elif achievement_rate < 95:
                status = "미달성"
            else:
                status = "초과달성"
            
            # 권장사항 생성
            recommendation = self._generate_goal_recommendation(
                achievement_rate, difference, metric_name
            )
            
            comparison = GoalComparison(
                actual_value=round(actual, 1),
                goal_value=round(goal, 1),
                achievement_rate=round(achievement_rate, 1),
                difference=round(difference, 1),
                status=status,
                recommendation=recommendation
            )
            
            print(f"🎯 목표 비교 ({metric_name}):")
            print(f"  - 실제: {comparison.actual_value}")
            print(f"  - 목표: {comparison.goal_value}")
            print(f"  - 달성률: {comparison.achievement_rate}%")
            print(f"  - 상태: {comparison.status}")
            
            return comparison
            
        except Exception as e:
            raise CalorieCalculationError(f"목표 비교 실패: {str(e)}")
    
    def calculate_bmr(self, weight: float, height: float, age: int, gender: str) -> float:
        """
        기초대사율(BMR) 계산 (Harris-Benedict 공식).
        
        Args:
            weight: 체중 (kg)
            height: 키 (cm)
            age: 나이
            gender: 성별 ("male" 또는 "female")
            
        Returns:
            float: 기초대사율 (kcal/day)
        """
        if gender.lower() not in ["male", "female"]:
            raise DataValidationError(f"성별은 'male' 또는 'female'이어야 합니다: {gender}")
        
        if weight <= 0 or height <= 0 or age <= 0:
            raise DataValidationError("체중, 키, 나이는 모두 양수여야 합니다")
        
        try:
            constants = self.bmr_constants[gender.lower()]
            bmr = (constants["base"] + 
                   constants["weight"] * weight + 
                   constants["height"] * height - 
                   constants["age"] * age)
            
            print(f"📊 BMR 계산: {gender} {age}세, {weight}kg, {height}cm = {bmr:.1f}kcal/day")
            return round(bmr, 1)
            
        except Exception as e:
            raise CalorieCalculationError(f"BMR 계산 실패: {str(e)}")
    
    def calculate_tdee(self, bmr: float, activity_level: ActivityLevel) -> float:
        """
        총 일일 에너지 소비량(TDEE) 계산.
        
        Args:
            bmr: 기초대사율
            activity_level: 활동 수준
            
        Returns:
            float: TDEE (kcal/day)
        """
        try:
            multiplier = self.activity_multipliers[activity_level]
            tdee = bmr * multiplier
            
            print(f"📊 TDEE 계산: BMR {bmr}kcal × {multiplier} = {tdee:.1f}kcal/day")
            return round(tdee, 1)
            
        except Exception as e:
            raise CalorieCalculationError(f"TDEE 계산 실패: {str(e)}")
    
    def _update_average_intake(self, calories: float) -> None:
        """평균 섭취 칼로리 업데이트."""
        food_count = self.calculation_stats["food_calculations"]
        if food_count == 1:
            self.calculation_stats["average_intake"] = calories
        else:
            current_avg = self.calculation_stats["average_intake"]
            new_avg = ((current_avg * (food_count - 1)) + calories) / food_count
            self.calculation_stats["average_intake"] = new_avg
    
    def _update_average_burn(self, calories: float) -> None:
        """평균 소모 칼로리 업데이트."""
        exercise_count = self.calculation_stats["exercise_calculations"]
        if exercise_count == 1:
            self.calculation_stats["average_burn"] = calories
        else:
            current_avg = self.calculation_stats["average_burn"]
            new_avg = ((current_avg * (exercise_count - 1)) + calories) / exercise_count
            self.calculation_stats["average_burn"] = new_avg
    
    def _generate_recommendations(self, net_result: NetCalorieResult, goal: Optional[CalorieGoal],
                                intake_rate: Optional[float], burn_rate: Optional[float]) -> List[str]:
        """권장사항 생성."""
        recommendations = []
        
        # 순 칼로리 기반 권장사항
        if net_result.net_calories > 500:
            recommendations.append("순 칼로리가 높습니다. 운동량을 늘리거나 섭취량을 줄이는 것을 고려해보세요.")
        elif net_result.net_calories < -500:
            recommendations.append("순 칼로리가 너무 낮습니다. 충분한 영양 섭취를 확인해보세요.")
        
        # 목표 달성률 기반 권장사항
        if intake_rate and intake_rate < 80:
            recommendations.append("섭취 칼로리가 목표보다 부족합니다. 균형 잡힌 식사를 늘려보세요.")
        elif intake_rate and intake_rate > 120:
            recommendations.append("섭취 칼로리가 목표를 초과했습니다. 포션 크기를 조절해보세요.")
        
        if burn_rate and burn_rate < 80:
            recommendations.append("운동량이 목표보다 부족합니다. 신체 활동을 늘려보세요.")
        elif burn_rate and burn_rate > 150:
            recommendations.append("운동량이 매우 높습니다. 충분한 휴식과 영양 보충을 확인해보세요.")
        
        # 기본 권장사항
        if not recommendations:
            recommendations.append("균형 잡힌 식단과 규칙적인 운동을 유지하세요.")
        
        return recommendations
    
    def _generate_goal_recommendation(self, achievement_rate: float, difference: float, metric_name: str) -> str:
        """목표 비교 권장사항 생성."""
        if achievement_rate >= 95 and achievement_rate <= 105:
            return f"목표를 잘 달성하고 있습니다. 현재 패턴을 유지하세요."
        elif achievement_rate < 80:
            return f"{metric_name}이 목표보다 {abs(difference):.1f} 부족합니다. 계획을 재검토해보세요."
        elif achievement_rate < 95:
            return f"{metric_name}이 목표에 근접했습니다. 조금만 더 노력해보세요."
        elif achievement_rate <= 120:
            return f"{metric_name}이 목표를 {difference:.1f} 초과했습니다. 적절한 조절이 필요합니다."
        else:
            return f"{metric_name}이 목표를 크게 초과했습니다. 계획을 재조정하는 것을 권장합니다."
    
    def get_calculation_stats(self) -> Dict[str, Any]:
        """
        칼로리 계산 통계 반환.
        
        Returns:
            Dict[str, Any]: 계산 통계 정보
        """
        return {
            "calculation_statistics": self.calculation_stats.copy(),
            "configuration": {
                "default_weight": self.default_weight,
                "supported_activity_levels": [level.value for level in ActivityLevel],
                "bmr_formulas": list(self.bmr_constants.keys())
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_statistics(self) -> None:
        """계산 통계 초기화."""
        self.calculation_stats = {
            "total_calculations": 0,
            "food_calculations": 0,
            "exercise_calculations": 0,
            "net_calculations": 0,
            "average_intake": 0.0,
            "average_burn": 0.0
        }
        print("✓ 칼로리 계산 통계 초기화 완료")