"""
일일 칼로리 분석 기능.

하루 동안의 음식/운동 데이터 집계, 목표 칼로리 대비 달성률 계산,
칼로리 밸런스 분석 리포트 생성 기능을 제공합니다.
"""

import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import statistics

from calorie_manager import CalorieManager, GoalComparison, NetCalorieResult, DailyAnalysis
from integrated_models import (
    FoodItem, NutritionInfo, FoodConsumption,
    ExerciseItem, ExerciseSession
)
from exceptions import CalorieCalculationError, DataValidationError


@dataclass
class MealAnalysis:
    """식사별 분석 데이터."""
    meal_type: str  # "아침", "점심", "저녁", "간식"
    foods: List[FoodConsumption]
    total_calories: float
    total_carbs: float
    total_protein: float
    total_fat: float
    meal_time_range: Tuple[datetime, datetime]
    
    @property
    def food_count(self) -> int:
        """식사에 포함된 음식 수."""
        return len(self.foods)
    
    @property
    def average_calories_per_food(self) -> float:
        """음식당 평균 칼로리."""
        return self.total_calories / max(1, self.food_count)


@dataclass
class ExerciseAnalysis:
    """운동 분석 데이터."""
    exercise_type: str  # "유산소", "근력", "유연성" 등
    sessions: List[ExerciseSession]
    total_calories_burned: float
    total_duration: float
    average_intensity: float  # 평균 MET 값
    exercise_time_range: Tuple[datetime, datetime]
    
    @property
    def session_count(self) -> int:
        """운동 세션 수."""
        return len(self.sessions)
    
    @property
    def calories_per_minute(self) -> float:
        """분당 소모 칼로리."""
        return self.total_calories_burned / max(1, self.total_duration)


@dataclass
class CalorieBalanceReport:
    """칼로리 밸런스 분석 리포트."""
    analysis_date: date
    total_consumed: float
    total_burned: float
    net_calories: float
    goal_calories: Optional[float]
    goal_comparison: Optional[GoalComparison]
    
    # 식사별 분석
    meal_analyses: List[MealAnalysis]
    
    # 운동별 분석
    exercise_analyses: List[ExerciseAnalysis]
    
    # 영양소 분석
    nutrient_summary: Dict[str, float]
    
    # 시간대별 분석
    hourly_consumption: Dict[int, float]  # 시간별 섭취 칼로리
    hourly_exercise: Dict[int, float]     # 시간별 소모 칼로리
    
    # 권장사항 및 인사이트
    recommendations: List[str]
    insights: List[str]
    health_score: float  # 0-100 건강 점수
    
    def to_dict(self) -> Dict[str, Any]:
        """리포트를 딕셔너리로 변환."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "calorie_summary": {
                "total_consumed": self.total_consumed,
                "total_burned": self.total_burned,
                "net_calories": self.net_calories,
                "goal_calories": self.goal_calories,
                "goal_achievement": asdict(self.goal_comparison) if self.goal_comparison else None
            },
            "meal_analysis": [
                {
                    "meal_type": meal.meal_type,
                    "food_count": meal.food_count,
                    "total_calories": meal.total_calories,
                    "nutrition": {
                        "carbs": meal.total_carbs,
                        "protein": meal.total_protein,
                        "fat": meal.total_fat
                    },
                    "average_calories_per_food": meal.average_calories_per_food
                }
                for meal in self.meal_analyses
            ],
            "exercise_analysis": [
                {
                    "exercise_type": ex.exercise_type,
                    "session_count": ex.session_count,
                    "total_calories_burned": ex.total_calories_burned,
                    "total_duration": ex.total_duration,
                    "average_intensity": ex.average_intensity,
                    "calories_per_minute": ex.calories_per_minute
                }
                for ex in self.exercise_analyses
            ],
            "nutrient_summary": self.nutrient_summary,
            "time_analysis": {
                "hourly_consumption": self.hourly_consumption,
                "hourly_exercise": self.hourly_exercise
            },
            "recommendations": self.recommendations,
            "insights": self.insights,
            "health_score": self.health_score
        }


class DailyAnalysisManager:
    """
    일일 칼로리 분석 매니저.
    
    하루 동안의 음식/운동 데이터를 종합 분석하여
    상세한 리포트와 인사이트를 제공합니다.
    """
    
    def __init__(self, calorie_manager: CalorieManager):
        """
        DailyAnalysisManager 초기화.
        
        Args:
            calorie_manager: 칼로리 매니저 인스턴스
        """
        self.calorie_manager = calorie_manager
        
        # 식사 시간대 정의
        self.meal_time_ranges = {
            "아침": (5, 10),   # 5시-10시
            "점심": (11, 14),  # 11시-14시
            "저녁": (17, 22),  # 17시-22시
            "간식": [(10, 11), (14, 17), (22, 24), (0, 5)]  # 나머지 시간
        }
        
        # 운동 강도 분류
        self.exercise_intensity_ranges = {
            "저강도": (0, 3.0),
            "중강도": (3.0, 6.0),
            "고강도": (6.0, float('inf'))
        }
        
        print("✓ 일일 분석 매니저 초기화 완료")
    
    def generate_daily_report(self, 
                            consumptions: List[FoodConsumption],
                            sessions: List[ExerciseSession],
                            nutrition_data: Dict[str, NutritionInfo],
                            target_date: date,
                            goal_calories: Optional[float] = None) -> CalorieBalanceReport:
        """
        일일 칼로리 밸런스 리포트 생성.
        
        Args:
            consumptions: 음식 섭취 기록 목록
            sessions: 운동 세션 기록 목록
            nutrition_data: 음식별 영양정보 매핑
            target_date: 분석 대상 날짜
            goal_calories: 목표 칼로리
            
        Returns:
            CalorieBalanceReport: 종합 분석 리포트
        """
        print(f"📊 일일 분석 리포트 생성: {target_date}")
        
        try:
            # 날짜별 데이터 필터링
            daily_consumptions = [
                c for c in consumptions 
                if c.timestamp.date() == target_date
            ]
            daily_sessions = [
                s for s in sessions 
                if s.timestamp.date() == target_date
            ]
            
            # 기본 칼로리 계산
            net_result = self.calorie_manager.calculate_net_calories(
                daily_consumptions, daily_sessions
            )
            
            # 목표 비교
            goal_comparison = None
            if goal_calories:
                goal_comparison = self.calorie_manager.compare_with_goal(
                    net_result.net_calories, goal_calories
                )
            
            # 식사별 분석
            meal_analyses = self._analyze_meals(daily_consumptions, nutrition_data)
            
            # 운동별 분석
            exercise_analyses = self._analyze_exercises(daily_sessions)
            
            # 영양소 요약
            nutrient_summary = self._calculate_nutrient_summary(
                daily_consumptions, nutrition_data
            )
            
            # 시간대별 분석
            hourly_consumption, hourly_exercise = self._analyze_hourly_patterns(
                daily_consumptions, daily_sessions
            )
            
            # 권장사항 및 인사이트 생성
            recommendations = self._generate_recommendations(
                net_result, meal_analyses, exercise_analyses, goal_comparison
            )
            insights = self._generate_insights(
                daily_consumptions, daily_sessions, meal_analyses, exercise_analyses
            )
            
            # 건강 점수 계산
            health_score = self._calculate_health_score(
                net_result, meal_analyses, exercise_analyses, goal_comparison
            )
            
            # 리포트 생성
            report = CalorieBalanceReport(
                analysis_date=target_date,
                total_consumed=net_result.total_intake,
                total_burned=net_result.total_burned,
                net_calories=net_result.net_calories,
                goal_calories=goal_calories,
                goal_comparison=goal_comparison,
                meal_analyses=meal_analyses,
                exercise_analyses=exercise_analyses,
                nutrient_summary=nutrient_summary,
                hourly_consumption=hourly_consumption,
                hourly_exercise=hourly_exercise,
                recommendations=recommendations,
                insights=insights,
                health_score=health_score
            )
            
            print(f"✓ 리포트 생성 완료")
            print(f"  - 식사 분석: {len(meal_analyses)}개 식사")
            print(f"  - 운동 분석: {len(exercise_analyses)}개 운동 타입")
            print(f"  - 권장사항: {len(recommendations)}개")
            print(f"  - 인사이트: {len(insights)}개")
            print(f"  - 건강 점수: {health_score:.1f}/100")
            
            return report
            
        except Exception as e:
            raise CalorieCalculationError(f"일일 리포트 생성 실패: {str(e)}")
    
    def _analyze_meals(self, 
                      consumptions: List[FoodConsumption],
                      nutrition_data: Dict[str, NutritionInfo]) -> List[MealAnalysis]:
        """식사별 분석 수행."""
        meal_groups = defaultdict(list)
        
        # 시간대별로 음식 섭취 분류
        for consumption in consumptions:
            hour = consumption.timestamp.hour
            meal_type = self._classify_meal_time(hour)
            meal_groups[meal_type].append(consumption)
        
        meal_analyses = []
        
        for meal_type, foods in meal_groups.items():
            if not foods:
                continue
            
            # 식사별 영양소 계산
            total_calories = sum(f.calories_consumed for f in foods)
            total_carbs = 0.0
            total_protein = 0.0
            total_fat = 0.0
            
            for food in foods:
                food_key = str(food.food_uri).split('/')[-1]
                if food_key in nutrition_data:
                    nutrition = nutrition_data[food_key]
                    ratio = food.amount_grams / 100.0
                    total_carbs += nutrition.carbohydrate * ratio
                    total_protein += nutrition.protein * ratio
                    total_fat += nutrition.fat * ratio
            
            # 시간 범위 계산
            timestamps = [f.timestamp for f in foods]
            time_range = (min(timestamps), max(timestamps))
            
            meal_analysis = MealAnalysis(
                meal_type=meal_type,
                foods=foods,
                total_calories=total_calories,
                total_carbs=total_carbs,
                total_protein=total_protein,
                total_fat=total_fat,
                meal_time_range=time_range
            )
            
            meal_analyses.append(meal_analysis)
        
        return meal_analyses
    
    def _analyze_exercises(self, sessions: List[ExerciseSession]) -> List[ExerciseAnalysis]:
        """운동별 분석 수행."""
        # 운동 타입별로 그룹화 (임시로 강도별 분류)
        exercise_groups = defaultdict(list)
        
        for session in sessions:
            # 운동 강도에 따른 분류 (MET 값 기준)
            intensity_type = self._classify_exercise_intensity(session.calories_burned / session.duration * 60)
            exercise_groups[intensity_type].append(session)
        
        exercise_analyses = []
        
        for exercise_type, group_sessions in exercise_groups.items():
            if not group_sessions:
                continue
            
            total_calories = sum(s.calories_burned for s in group_sessions)
            total_duration = sum(s.duration for s in group_sessions)
            
            # 평균 강도 계산 (간접적으로 MET 추정)
            avg_intensity = statistics.mean([
                s.calories_burned / (s.weight * (s.duration / 60.0))
                for s in group_sessions
            ])
            
            # 시간 범위
            timestamps = [s.timestamp for s in group_sessions]
            time_range = (min(timestamps), max(timestamps))
            
            exercise_analysis = ExerciseAnalysis(
                exercise_type=exercise_type,
                sessions=group_sessions,
                total_calories_burned=total_calories,
                total_duration=total_duration,
                average_intensity=avg_intensity,
                exercise_time_range=time_range
            )
            
            exercise_analyses.append(exercise_analysis)
        
        return exercise_analyses
    
    def _analyze_hourly_patterns(self, 
                                consumptions: List[FoodConsumption],
                                sessions: List[ExerciseSession]) -> Tuple[Dict[int, float], Dict[int, float]]:
        """시간대별 패턴 분석."""
        hourly_consumption = defaultdict(float)
        hourly_exercise = defaultdict(float)
        
        # 시간별 섭취 칼로리
        for consumption in consumptions:
            hour = consumption.timestamp.hour
            hourly_consumption[hour] += consumption.calories_consumed
        
        # 시간별 소모 칼로리
        for session in sessions:
            hour = session.timestamp.hour
            hourly_exercise[hour] += session.calories_burned
        
        return dict(hourly_consumption), dict(hourly_exercise)
    
    def _classify_meal_time(self, hour: int) -> str:
        """시간대를 기준으로 식사 타입 분류."""
        if self.meal_time_ranges["아침"][0] <= hour <= self.meal_time_ranges["아침"][1]:
            return "아침"
        elif self.meal_time_ranges["점심"][0] <= hour <= self.meal_time_ranges["점심"][1]:
            return "점심"
        elif self.meal_time_ranges["저녁"][0] <= hour <= self.meal_time_ranges["저녁"][1]:
            return "저녁"
        else:
            return "간식"
    
    def _classify_exercise_intensity(self, calories_per_minute: float) -> str:
        """분당 소모 칼로리를 기준으로 운동 강도 분류."""
        if calories_per_minute < 5:
            return "저강도 운동"
        elif calories_per_minute < 10:
            return "중강도 운동"
        else:
            return "고강도 운동"
    
    def _generate_recommendations(self, 
                                net_result: NetCalorieResult,
                                meal_analyses: List[MealAnalysis],
                                exercise_analyses: List[ExerciseAnalysis],
                                goal_comparison: Optional[GoalComparison]) -> List[str]:
        """개인화된 권장사항 생성."""
        recommendations = []
        
        # 칼로리 밸런스 기반 권장사항
        if net_result.net_calories > 300:
            recommendations.append("칼로리 섭취가 소모보다 많습니다. 운동량을 늘리거나 식사량을 조절해보세요.")
        elif net_result.net_calories < -300:
            recommendations.append("칼로리 소모가 섭취보다 많습니다. 충분한 영양 섭취를 권장합니다.")
        
        # 식사 패턴 기반 권장사항
        meal_types = [meal.meal_type for meal in meal_analyses]
        if "아침" not in meal_types:
            recommendations.append("아침 식사를 거르셨네요. 규칙적인 아침 식사는 신진대사에 도움이 됩니다.")
        
        # 과도한 간식 섭취 체크
        snack_meals = [meal for meal in meal_analyses if meal.meal_type == "간식"]
        if snack_meals and sum(meal.total_calories for meal in snack_meals) > 500:
            recommendations.append("간식 섭취량이 많습니다. 건강한 간식으로 대체해보세요.")
        
        # 운동 패턴 기반 권장사항
        if not exercise_analyses:
            recommendations.append("오늘은 운동 기록이 없습니다. 규칙적인 운동을 시작해보세요.")
        else:
            total_exercise_time = sum(ex.total_duration for ex in exercise_analyses)
            if total_exercise_time < 30:
                recommendations.append("운동 시간이 부족합니다. 하루 30분 이상의 운동을 권장합니다.")
        
        # 목표 기반 권장사항
        if goal_comparison:
            if goal_comparison.status == "미달성":
                recommendations.append(f"목표 칼로리보다 {abs(goal_comparison.difference):.0f} kcal 부족합니다. 영양가 있는 음식 섭취를 늘려보세요.")
            elif goal_comparison.status == "초과달성":
                recommendations.append(f"목표 칼로리보다 {goal_comparison.difference:.0f} kcal 초과했습니다. 내일은 운동을 늘리거나 식사량을 조절해보세요.")
        
        return recommendations
    
    def _generate_insights(self, 
                          consumptions: List[FoodConsumption],
                          sessions: List[ExerciseSession],
                          meal_analyses: List[MealAnalysis],
                          exercise_analyses: List[ExerciseAnalysis]) -> List[str]:
        """데이터 기반 인사이트 생성."""
        insights = []
        
        # 식사 패턴 인사이트
        if meal_analyses:
            most_caloric_meal = max(meal_analyses, key=lambda x: x.total_calories)
            insights.append(f"가장 많은 칼로리를 섭취한 식사는 {most_caloric_meal.meal_type}입니다 ({most_caloric_meal.total_calories:.0f} kcal).")
            
            # 식사 시간 분석
            meal_times = [meal.meal_time_range[0].hour for meal in meal_analyses]
            if meal_times:
                avg_meal_time = statistics.mean(meal_times)
                if avg_meal_time < 12:
                    insights.append("오전에 식사를 많이 하셨네요. 이른 식사는 신진대사에 좋습니다.")
                elif avg_meal_time > 18:
                    insights.append("저녁 늦게 식사를 많이 하셨네요. 소화를 위해 취침 3시간 전에는 식사를 마치는 것이 좋습니다.")
        
        # 운동 패턴 인사이트
        if exercise_analyses:
            total_exercise_calories = sum(ex.total_calories_burned for ex in exercise_analyses)
            total_exercise_time = sum(ex.total_duration for ex in exercise_analyses)
            
            if total_exercise_time > 0:
                avg_intensity = total_exercise_calories / total_exercise_time
                if avg_intensity > 8:
                    insights.append("고강도 운동을 많이 하셨네요! 근력과 지구력 향상에 도움이 됩니다.")
                elif avg_intensity < 4:
                    insights.append("저강도 운동 위주로 하셨네요. 점진적으로 강도를 높여보세요.")
        
        # 영양 밸런스 인사이트
        if meal_analyses:
            total_carbs = sum(meal.total_carbs for meal in meal_analyses)
            total_protein = sum(meal.total_protein for meal in meal_analyses)
            total_fat = sum(meal.total_fat for meal in meal_analyses)
            
            total_macros = total_carbs + total_protein + total_fat
            if total_macros > 0:
                protein_ratio = (total_protein / total_macros) * 100
                if protein_ratio > 30:
                    insights.append("단백질 섭취 비율이 높습니다. 근육 건강에 도움이 됩니다.")
                elif protein_ratio < 15:
                    insights.append("단백질 섭취가 부족할 수 있습니다. 단백질 섭취를 늘려보세요.")
        
        return insights
    
    def _calculate_nutrient_summary(self, 
                                   consumptions: List[FoodConsumption],
                                   nutrition_data: Dict[str, NutritionInfo]) -> Dict[str, float]:
        """영양소 요약 계산."""
        summary = {
            "total_calories": 0.0,
            "total_carbohydrate": 0.0,
            "total_protein": 0.0,
            "total_fat": 0.0,
            "total_fiber": 0.0,
            "total_sodium": 0.0
        }
        
        for consumption in consumptions:
            food_key = str(consumption.food_uri).split('/')[-1]
            if food_key in nutrition_data:
                nutrition = nutrition_data[food_key]
                ratio = consumption.amount_grams / 100.0
                
                summary["total_calories"] += consumption.calories_consumed
                summary["total_carbohydrate"] += nutrition.carbohydrate * ratio
                summary["total_protein"] += nutrition.protein * ratio
                summary["total_fat"] += nutrition.fat * ratio
                summary["total_fiber"] += nutrition.fiber * ratio
                summary["total_sodium"] += nutrition.sodium * ratio
        
        return summary
    
    def _calculate_health_score(self, 
                               net_result: NetCalorieResult,
                               meal_analyses: List[MealAnalysis],
                               exercise_analyses: List[ExerciseAnalysis],
                               goal_comparison: Optional[GoalComparison]) -> float:
        """종합 건강 점수 계산 (0-100)."""
        score = 100.0
        
        # 칼로리 밸런스 점수 (30점)
        if abs(net_result.net_calories) > 500:
            score -= 15  # 칼로리 불균형 시 감점
        elif abs(net_result.net_calories) > 300:
            score -= 8
        
        # 식사 패턴 점수 (25점)
        meal_types = [meal.meal_type for meal in meal_analyses]
        if "아침" not in meal_types:
            score -= 10  # 아침 거르면 감점
        if len(meal_types) < 3:
            score -= 8   # 식사 횟수 부족 시 감점
        
        # 운동 점수 (25점)
        if not exercise_analyses:
            score -= 20  # 운동 없으면 큰 감점
        else:
            total_exercise_time = sum(ex.total_duration for ex in exercise_analyses)
            if total_exercise_time < 30:
                score -= 10  # 운동 시간 부족 시 감점
        
        # 목표 달성 점수 (20점)
        if goal_comparison:
            if goal_comparison.status == "달성":
                score += 5   # 목표 달성 시 보너스
            elif abs(goal_comparison.difference) > 500:
                score -= 15  # 목표와 큰 차이 시 감점
            elif abs(goal_comparison.difference) > 200:
                score -= 8
        
        return max(0.0, min(100.0, score))
    
    def export_report_to_json(self, report: CalorieBalanceReport, file_path: str) -> None:
        """리포트를 JSON 파일로 내보내기."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
            print(f"✓ 리포트 JSON 파일 저장: {file_path}")
        except Exception as e:
            raise CalorieCalculationError(f"리포트 저장 실패: {str(e)}")
    
    def generate_summary_text(self, report: CalorieBalanceReport) -> str:
        """리포트 요약 텍스트 생성."""
        summary_lines = [
            f"📊 {report.analysis_date} 일일 칼로리 분석 리포트",
            "=" * 50,
            "",
            "🍽️ 칼로리 요약:",
            f"  • 총 섭취: {report.total_consumed:.1f} kcal",
            f"  • 총 소모: {report.total_burned:.1f} kcal",
            f"  • 순 칼로리: {report.net_calories:+.1f} kcal",
        ]
        
        if report.goal_calories:
            summary_lines.extend([
                f"  • 목표 칼로리: {report.goal_calories:.1f} kcal",
                f"  • 달성률: {report.goal_comparison.achievement_rate:.1f}% ({report.goal_comparison.status})"
            ])
        
        summary_lines.extend([
            "",
            "🥗 식사 분석:",
        ])
        
        for meal in report.meal_analyses:
            summary_lines.append(f"  • {meal.meal_type}: {meal.total_calories:.1f} kcal ({meal.food_count}개 음식)")
        
        if report.exercise_analyses:
            summary_lines.extend([
                "",
                "🏃 운동 분석:",
            ])
            for exercise in report.exercise_analyses:
                summary_lines.append(f"  • {exercise.exercise_type}: {exercise.total_calories_burned:.1f} kcal ({exercise.total_duration:.0f}분)")
        
        summary_lines.extend([
            "",
            f"💯 건강 점수: {report.health_score:.1f}/100",
            "",
            "💡 주요 권장사항:",
        ])
        
        for i, rec in enumerate(report.recommendations[:3], 1):
            summary_lines.append(f"  {i}. {rec}")
        
        if report.insights:
            summary_lines.extend([
                "",
                "🔍 인사이트:",
            ])
            for insight in report.insights[:2]:
                summary_lines.append(f"  • {insight}")
        
        return "\n".join(summary_lines)