"""
CLI 인터페이스 데모

이 모듈은 CLI 기능을 시연하고 테스트합니다.
"""

import asyncio
import sys
import time
from cli_interface import NutritionCLI


def demo_basic_commands():
    """기본 명령어 데모"""
    print("🎯 CLI 기본 명령어 데모")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 1. 음식 추가
    print("\n1. 음식 추가 테스트")
    cli.add_food_to_session("닭가슴살", 150.0)
    cli.add_food_to_session("현미밥", 200.0)
    cli.add_food_to_session("브로콜리", 100.0)
    
    # 2. 운동 추가
    print("\n2. 운동 추가 테스트")
    cli.add_exercise_to_session("달리기", 30.0, 70.0)
    cli.add_exercise_to_session("걷기", 45.0, 70.0)
    
    # 3. 세션 표시
    print("\n3. 현재 세션 표시")
    cli.show_session()
    
    # 4. 칼로리 계산
    print("\n4. 칼로리 계산")
    cli.calculate_daily_calories()
    
    # 5. 캐시 통계
    print("\n5. 캐시 통계")
    cli.show_cache_stats()
    
    # 6. 온톨로지 상태
    print("\n6. 온톨로지 상태")
    cli.show_ontology_status()
    
    print("\n✅ 기본 명령어 데모 완료")


def demo_search_commands():
    """검색 명령어 데모"""
    print("\n🔍 검색 명령어 데모")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # Mock 데이터 설정
    from unittest.mock import MagicMock, AsyncMock
    
    # 음식 검색 결과 모킹
    mock_food = MagicMock()
    mock_food.__dict__ = {
        'name': '닭가슴살',
        'food_id': '123',
        'category': '육류',
        'manufacturer': '테스트'
    }
    
    mock_nutrition = MagicMock()
    mock_nutrition.__dict__ = {
        'calories_per_100g': 165.0,
        'carbohydrate': 0.0,
        'protein': 31.0,
        'fat': 3.6
    }
    
    cli.search_manager.search_food_with_cache = AsyncMock(return_value=[mock_food])
    cli.search_manager.get_nutrition_info = AsyncMock(return_value=mock_nutrition)
    
    # 운동 검색 결과 모킹
    mock_exercise = MagicMock()
    mock_exercise.__dict__ = {
        'name': '달리기',
        'exercise_id': '456',
        'category': '유산소'
    }
    mock_exercise.met_value = 8.0
    
    cli.search_manager.search_exercise_with_cache = AsyncMock(return_value=[mock_exercise])
    
    async def run_search_demo():
        print("\n1. 음식 검색 테스트")
        food_results = await cli.search_food("닭가슴살", limit=3, detailed=True)
        cli._print_search_results('음식', food_results)
        
        print("\n2. 운동 검색 테스트")
        exercise_results = await cli.search_exercise("달리기", limit=3, detailed=True)
        cli._print_search_results('운동', exercise_results)
    
    asyncio.run(run_search_demo())
    print("\n✅ 검색 명령어 데모 완료")


def demo_interactive_commands():
    """대화형 명령어 데모"""
    print("\n💬 대화형 명령어 데모")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 대화형 명령어 시뮬레이션
    test_commands = [
        ['add', 'food', '사과', '120'],
        ['add', 'food', '바나나', '100'],
        ['add', 'exercise', '수영', '40'],
        ['show'],
        ['calculate'],
        ['ontology', 'status'],
        ['cache', 'stats'],
        ['config', 'show']
    ]
    
    print("시뮬레이션할 명령어들:")
    for i, cmd in enumerate(test_commands, 1):
        print(f"  {i}. {' '.join(cmd)}")
    
    print("\n명령어 실행 결과:")
    print("-" * 30)
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n[{i}] > {' '.join(cmd)}")
        try:
            cli._execute_interactive_command(cmd)
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    print("\n✅ 대화형 명령어 데모 완료")


def demo_error_handling():
    """오류 처리 데모"""
    print("\n⚠️  오류 처리 데모")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 1. 잘못된 명령어
    print("\n1. 잘못된 명령어 테스트")
    cli._execute_interactive_command(['invalid', 'command'])
    
    # 2. 부족한 인수
    print("\n2. 부족한 인수 테스트")
    cli._execute_interactive_command(['add', 'food'])
    
    # 3. 잘못된 숫자 형식
    print("\n3. 잘못된 숫자 형식 테스트")
    try:
        cli._execute_interactive_command(['add', 'food', '사과', 'invalid_number'])
    except ValueError as e:
        print(f"예상된 오류 발생: {e}")
    
    # 4. 잘못된 시간 형식
    print("\n4. 잘못된 시간 형식 테스트")
    cli.add_food_to_session("테스트음식", 100.0, "25:70")  # 잘못된 시간
    
    print("\n✅ 오류 처리 데모 완료")


def demo_session_management():
    """세션 관리 데모"""
    print("\n📊 세션 관리 데모")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 1. 빈 세션 상태
    print("\n1. 초기 빈 세션")
    cli.show_session()
    cli.calculate_daily_calories()
    
    # 2. 데이터 추가
    print("\n2. 데이터 추가 후")
    cli.add_food_to_session("아침식사_토스트", 80.0, "08:00")
    cli.add_food_to_session("점심식사_샐러드", 150.0, "12:30")
    cli.add_food_to_session("저녁식사_스테이크", 200.0, "19:00")
    
    cli.add_exercise_to_session("아침운동_조깅", 20.0, 65.0, "07:00")
    cli.add_exercise_to_session("저녁운동_헬스", 60.0, 65.0, "20:00")
    
    cli.show_session()
    
    # 3. 칼로리 계산
    print("\n3. 칼로리 계산")
    cli.calculate_daily_calories()
    
    # 4. 세션 초기화
    print("\n4. 세션 초기화")
    cli.clear_session()
    cli.show_session()
    
    print("\n✅ 세션 관리 데모 완료")


def demo_help_system():
    """도움말 시스템 데모"""
    print("\n❓ 도움말 시스템 데모")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 1. 대화형 도움말
    print("\n1. 대화형 모드 도움말")
    cli._show_interactive_help()
    
    # 2. 파서 도움말
    print("\n2. 명령줄 파서 도움말")
    parser = cli.create_parser()
    print("\n" + "="*30 + " CLI 도움말 " + "="*30)
    parser.print_help()
    
    print("\n✅ 도움말 시스템 데모 완료")


def demo_performance_features():
    """성능 기능 데모"""
    print("\n⚡ 성능 기능 데모")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 1. 대량 데이터 처리 시뮬레이션
    print("\n1. 대량 데이터 처리 시뮬레이션")
    
    start_time = time.time()
    
    # 100개 음식 추가
    for i in range(100):
        cli.add_food_to_session(f"음식_{i}", 100.0 + i)
        if i % 20 == 0:
            print(f"  진행률: {i+1}/100 ({(i+1)/100*100:.1f}%)")
    
    # 50개 운동 추가
    for i in range(50):
        cli.add_exercise_to_session(f"운동_{i}", 30.0 + i, 70.0)
        if i % 10 == 0:
            print(f"  운동 진행률: {i+1}/50 ({(i+1)/50*100:.1f}%)")
    
    end_time = time.time()
    
    print(f"\n처리 완료:")
    print(f"  음식: {len(cli.current_session['foods'])}개")
    print(f"  운동: {len(cli.current_session['exercises'])}개")
    print(f"  처리 시간: {end_time - start_time:.2f}초")
    print(f"  처리 속도: {(len(cli.current_session['foods']) + len(cli.current_session['exercises']))/(end_time - start_time):.1f} items/sec")
    
    # 2. 메모리 사용량 확인
    print("\n2. 메모리 사용량 확인")
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    print(f"  현재 메모리 사용량: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"  가상 메모리: {memory_info.vms / 1024 / 1024:.2f} MB")
    
    # 3. 세션 초기화 후 메모리 확인
    cli.clear_session()
    
    memory_info_after = process.memory_info()
    print(f"  초기화 후 메모리: {memory_info_after.rss / 1024 / 1024:.2f} MB")
    print(f"  메모리 절약: {(memory_info.rss - memory_info_after.rss) / 1024 / 1024:.2f} MB")
    
    print("\n✅ 성능 기능 데모 완료")


def main():
    """메인 데모 함수"""
    print("🎯 영양 관리 CLI 종합 데모")
    print("=" * 60)
    print("이 데모는 CLI의 주요 기능들을 시연합니다.")
    print("=" * 60)
    
    demos = [
        ("기본 명령어", demo_basic_commands),
        ("검색 기능", demo_search_commands),
        ("대화형 명령어", demo_interactive_commands),
        ("오류 처리", demo_error_handling),
        ("세션 관리", demo_session_management),
        ("도움말 시스템", demo_help_system),
        ("성능 기능", demo_performance_features)
    ]
    
    try:
        for i, (name, demo_func) in enumerate(demos, 1):
            print(f"\n{'='*20} {i}. {name} {'='*20}")
            demo_func()
            
            if i < len(demos):
                input("\n계속하려면 Enter를 누르세요...")
        
        print(f"\n{'='*60}")
        print("🎉 모든 데모가 완료되었습니다!")
        print("=" * 60)
        
        # 최종 통계
        print("\n📊 데모 통계:")
        print(f"  실행된 데모: {len(demos)}개")
        print(f"  테스트된 기능: 음식/운동 관리, 검색, 칼로리 계산, 온톨로지 관리")
        print(f"  지원되는 명령어: search, calorie, ontology, config, cache, interactive")
        
    except KeyboardInterrupt:
        print("\n\n👋 데모가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 데모 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    main()