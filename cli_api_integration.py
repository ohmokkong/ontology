"""
CLI에서 실제 API 연동을 위한 헬퍼 함수들
"""

import logging
from typing import Optional, List, Dict, Any
from auth_controller import AuthController
from food_api_client import FoodAPIClient
from exercise_api_client import ExerciseAPIClient
from search_manager import SearchManager
from cache_manager import CacheManager
from config_manager import ConfigManager

logger = logging.getLogger(__name__)


def initialize_api_clients(config_manager: ConfigManager, cache_manager: CacheManager) -> tuple:
    """
    실제 API 클라이언트들을 초기화합니다.
    
    Returns:
        tuple: (food_client, exercise_client, search_manager)
    """
    try:
        # 인증 컨트롤러 초기화
        auth_controller = AuthController()
        
        # 설정에서 API 키 로드
        config = config_manager.get_config()
        food_api_key = config.get('food_api_key', '')
        exercise_api_key = config.get('exercise_api_key', '')
        
        # API 클라이언트 초기화
        food_client = None
        exercise_client = None
        
        if food_api_key:
            try:
                food_client = FoodAPIClient(auth_controller)
                logger.info("✅ 음식 API 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️  음식 API 클라이언트 초기화 실패: {e}")
        else:
            logger.info("ℹ️  음식 API 키가 설정되지 않음 - 시뮬레이션 모드")
        
        if exercise_api_key:
            try:
                exercise_client = ExerciseAPIClient(auth_controller)
                logger.info("✅ 운동 API 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️  운동 API 클라이언트 초기화 실패: {e}")
        else:
            logger.info("ℹ️  운동 API 키가 설정되지 않음 - 시뮬레이션 모드")
        
        # 검색 매니저 초기화
        search_manager = SearchManager(food_client, exercise_client, cache_manager)
        
        return food_client, exercise_client, search_manager
        
    except Exception as e:
        logger.error(f"❌ API 클라이언트 초기화 실패: {e}")
        return None, None, None


async def search_food_with_api(search_manager: SearchManager, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    실제 API를 사용하여 음식을 검색합니다.
    
    Args:
        search_manager: 검색 매니저
        query: 검색 쿼리
        limit: 결과 개수 제한
        
    Returns:
        List[Dict]: 검색 결과 리스트
    """
    try:
        if search_manager and search_manager.food_client:
            # 실제 API 호출
            results = await search_manager.search_food_with_cache(query)
            return [food.__dict__ for food in results[:limit]]
        else:
            # 시뮬레이션 모드
            return get_simulated_food_results(query, limit)
    except Exception as e:
        logger.error(f"음식 검색 오류: {e}")
        return get_simulated_food_results(query, limit)


async def search_exercise_with_api(search_manager: SearchManager, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    실제 API를 사용하여 운동을 검색합니다.
    
    Args:
        search_manager: 검색 매니저
        query: 검색 쿼리
        limit: 결과 개수 제한
        
    Returns:
        List[Dict]: 검색 결과 리스트
    """
    try:
        if search_manager and search_manager.exercise_client:
            # 실제 API 호출
            results = await search_manager.search_exercise_with_cache(query)
            return [exercise.__dict__ for exercise in results[:limit]]
        else:
            # 시뮬레이션 모드
            return get_simulated_exercise_results(query, limit)
    except Exception as e:
        logger.error(f"운동 검색 오류: {e}")
        return get_simulated_exercise_results(query, limit)


def get_simulated_food_results(query: str, limit: int) -> List[Dict[str, Any]]:
    """시뮬레이션 음식 검색 결과"""
    simulated_foods = [
        {"name": "닭가슴살", "calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},
        {"name": "현미밥", "calories": 130, "protein": 2.5, "carbs": 28, "fat": 0.3},
        {"name": "브로콜리", "calories": 34, "protein": 2.8, "carbs": 7, "fat": 0.4},
        {"name": "사과", "calories": 52, "protein": 0.3, "carbs": 13.8, "fat": 0.2},
        {"name": "연어", "calories": 208, "protein": 25, "carbs": 0, "fat": 12},
        {"name": "아보카도", "calories": 160, "protein": 2, "carbs": 9, "fat": 15},
        {"name": "고구마", "calories": 86, "protein": 1.6, "carbs": 20, "fat": 0.1},
        {"name": "계란", "calories": 155, "protein": 13, "carbs": 1.1, "fat": 11}
    ]
    
    # 쿼리와 관련된 결과 필터링
    filtered_results = []
    for food in simulated_foods:
        if query.lower() in food["name"].lower():
            filtered_results.append(food)
    
    # 쿼리와 정확히 일치하지 않으면 모든 결과 반환
    if not filtered_results:
        filtered_results = simulated_foods
    
    return filtered_results[:limit]


def get_simulated_exercise_results(query: str, limit: int) -> List[Dict[str, Any]]:
    """시뮬레이션 운동 검색 결과"""
    simulated_exercises = [
        {"name": "달리기", "met": 8.0, "category": "유산소", "calories_per_hour": 560},
        {"name": "걷기", "met": 3.5, "category": "유산소", "calories_per_hour": 245},
        {"name": "수영", "met": 6.0, "category": "유산소", "calories_per_hour": 420},
        {"name": "자전거", "met": 7.5, "category": "유산소", "calories_per_hour": 525},
        {"name": "요가", "met": 2.5, "category": "유연성", "calories_per_hour": 175},
        {"name": "헬스", "met": 6.0, "category": "근력", "calories_per_hour": 420},
        {"name": "테니스", "met": 7.0, "category": "구기", "calories_per_hour": 490},
        {"name": "농구", "met": 8.0, "category": "구기", "calories_per_hour": 560}
    ]
    
    # 쿼리와 관련된 결과 필터링
    filtered_results = []
    for exercise in simulated_exercises:
        if query.lower() in exercise["name"].lower():
            filtered_results.append(exercise)
    
    # 쿼리와 정확히 일치하지 않으면 모든 결과 반환
    if not filtered_results:
        filtered_results = simulated_exercises
    
    return filtered_results[:limit]


def check_api_status(config_manager: ConfigManager) -> Dict[str, Any]:
    """
    API 연동 상태를 확인합니다.
    
    Returns:
        Dict: API 상태 정보
    """
    config = config_manager.get_config()
    
    food_api_key = config.get('food_api_key', '')
    exercise_api_key = config.get('exercise_api_key', '')
    
    status = {
        "food_api": {
            "configured": bool(food_api_key),
            "key_length": len(food_api_key) if food_api_key else 0,
            "status": "✅ 설정됨" if food_api_key else "❌ 미설정"
        },
        "exercise_api": {
            "configured": bool(exercise_api_key),
            "key_length": len(exercise_api_key) if exercise_api_key else 0,
            "status": "✅ 설정됨" if exercise_api_key else "❌ 미설정"
        },
        "overall_status": "실제 API 모드" if (food_api_key and exercise_api_key) else "시뮬레이션 모드"
    }
    
    return status


def print_api_setup_guide():
    """API 설정 가이드를 출력합니다."""
    guide = """
🔧 실제 API 연동 설정 가이드

1️⃣ 식약처 식품영양성분 API 키 발급:
   - 사이트: https://www.foodsafetykorea.go.kr/api/openApiInfo.do
   - 회원가입 → 로그인 → Open API 신청 → 승인 후 키 발급

2️⃣ 한국건강증진개발원 운동 API 키 발급:
   - 사이트: https://www.khealth.or.kr/
   - 개발자 등록 → API 신청 → 승인 후 키 발급

3️⃣ CLI에서 API 키 설정:
   python cli_interface.py config set-api-key food "your-food-api-key"
   python cli_interface.py config set-api-key exercise "your-exercise-api-key"

4️⃣ 설정 확인:
   python cli_interface.py config show

5️⃣ API 상태 확인:
   python cli_interface.py api-status

💡 API 키가 설정되지 않으면 시뮬레이션 모드로 작동합니다.
"""
    print(guide)


if __name__ == "__main__":
    # API 설정 가이드 출력
    print_api_setup_guide()