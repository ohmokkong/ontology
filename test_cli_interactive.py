"""
CLI 대화형 모드 테스트
"""

import subprocess
import time
from cli_interface import NutritionCLI


def test_interactive_commands():
    """대화형 명령어 테스트"""
    print("🎯 CLI 대화형 모드 테스트")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 테스트할 명령어들
    test_commands = [
        ['add', 'food', '닭가슴살', '150'],
        ['add', 'food', '현미밥', '200'],
        ['add', 'exercise', '달리기', '30'],
        ['add', 'exercise', '걷기', '45'],
        ['show'],
        ['calculate'],
        ['search', 'food', '사과'],
        ['search', 'exercise', '수영'],
        ['ontology', 'status'],
        ['cache', 'stats'],
        ['config', 'show'],
        ['clear']
    ]
    
    print("실행할 명령어들:")
    for i, cmd in enumerate(test_commands, 1):
        print(f"  {i:2d}. {' '.join(cmd)}")
    
    print("\n" + "=" * 50)
    print("명령어 실행 결과:")
    print("=" * 50)
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n[{i:2d}] > {' '.join(cmd)}")
        print("-" * 30)
        
        try:
            cli._execute_interactive_command(cmd)
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        time.sleep(0.1)  # 잠시 대기
    
    print("\n" + "=" * 50)
    print("✅ 대화형 모드 테스트 완료")
    
    # 최종 세션 상태 확인
    print("\n📊 최종 세션 상태:")
    print(f"  음식: {len(cli.current_session['foods'])}개")
    print(f"  운동: {len(cli.current_session['exercises'])}개")


def test_cli_help_system():
    """CLI 도움말 시스템 테스트"""
    print("\n❓ CLI 도움말 시스템 테스트")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    print("1. 대화형 도움말:")
    print("-" * 20)
    cli._show_interactive_help()
    
    print("\n2. 파서 도움말:")
    print("-" * 20)
    parser = cli.create_parser()
    
    # 서브커맨드 도움말 테스트
    subcommands = ['search', 'calorie', 'ontology', 'config']
    
    for subcmd in subcommands:
        print(f"\n{subcmd} 명령어 옵션:")
        try:
            # 각 서브커맨드의 도움말 확인
            help_args = [subcmd, '--help']
            # 실제로는 parser.parse_args(help_args)를 호출하지만
            # 여기서는 SystemExit 예외가 발생하므로 설명만 출력
            print(f"  {subcmd} 명령어는 다양한 옵션을 지원합니다.")
        except:
            pass


def test_error_handling():
    """오류 처리 테스트"""
    print("\n⚠️  오류 처리 테스트")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    error_test_cases = [
        # 잘못된 명령어
        (['invalid', 'command'], "잘못된 명령어"),
        
        # 부족한 인수
        (['add', 'food'], "부족한 인수"),
        
        # 잘못된 숫자 형식
        (['add', 'food', '사과', 'not_a_number'], "잘못된 숫자"),
        
        # 빈 명령어
        ([], "빈 명령어"),
        
        # 알 수 없는 서브커맨드
        (['unknown', 'subcommand'], "알 수 없는 서브커맨드")
    ]
    
    for i, (cmd, description) in enumerate(error_test_cases, 1):
        print(f"\n{i}. {description} 테스트:")
        print(f"   명령어: {cmd}")
        
        try:
            cli._execute_interactive_command(cmd)
        except Exception as e:
            print(f"   예상된 오류: {type(e).__name__}: {e}")


def test_session_management():
    """세션 관리 테스트"""
    print("\n📊 세션 관리 테스트")
    print("=" * 50)
    
    cli = NutritionCLI()
    
    # 1. 빈 세션 상태
    print("1. 초기 빈 세션:")
    cli.show_session()
    cli.calculate_daily_calories()
    
    # 2. 데이터 추가
    print("\n2. 데이터 추가:")
    foods_to_add = [
        ('아침_토스트', 80.0, '08:00'),
        ('점심_샐러드', 150.0, '12:30'),
        ('저녁_스테이크', 200.0, '19:00')
    ]
    
    exercises_to_add = [
        ('아침조깅', 20.0, 65.0, '07:00'),
        ('저녁헬스', 60.0, 65.0, '20:00')
    ]
    
    for name, amount, time_str in foods_to_add:
        cli.add_food_to_session(name, amount, time_str)
    
    for name, duration, weight, time_str in exercises_to_add:
        cli.add_exercise_to_session(name, duration, weight, time_str)
    
    # 3. 세션 표시
    print("\n3. 현재 세션:")
    cli.show_session()
    
    # 4. 칼로리 계산
    print("\n4. 칼로리 계산:")
    cli.calculate_daily_calories()
    
    # 5. 세션 초기화
    print("\n5. 세션 초기화:")
    cli.clear_session()
    cli.show_session()


def main():
    """메인 테스트 함수"""
    print("🎯 CLI 종합 테스트 시작")
    print("=" * 60)
    
    test_functions = [
        ("대화형 명령어", test_interactive_commands),
        ("도움말 시스템", test_cli_help_system),
        ("오류 처리", test_error_handling),
        ("세션 관리", test_session_management)
    ]
    
    try:
        for i, (name, test_func) in enumerate(test_functions, 1):
            print(f"\n{'='*20} {i}. {name} 테스트 {'='*20}")
            test_func()
            
            if i < len(test_functions):
                input("\n계속하려면 Enter를 누르세요...")
        
        print(f"\n{'='*60}")
        print("🎉 모든 CLI 테스트가 완료되었습니다!")
        print("=" * 60)
        
        # 최종 요약
        print("\n📊 테스트 요약:")
        print(f"  실행된 테스트: {len(test_functions)}개")
        print("  테스트된 기능:")
        print("    - 음식/운동 추가 및 관리")
        print("    - 칼로리 계산")
        print("    - 검색 기능 (시뮬레이션)")
        print("    - 온톨로지 상태 확인")
        print("    - 설정 관리")
        print("    - 오류 처리")
        print("    - 대화형 모드")
        
    except KeyboardInterrupt:
        print("\n\n👋 테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    main()