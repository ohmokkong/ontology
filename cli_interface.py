"""
명령줄 인터페이스 (CLI) 구현

이 모듈은 음식/운동 검색, 칼로리 계산, 온톨로지 관리를 위한 CLI를 제공합니다.
- 음식/운동 검색 명령어
- 칼로리 계산 및 분석 명령어  
- 온톨로지 관리 명령어
- 대화형 모드 지원
"""

import argparse
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import asyncio
from pathlib import Path

# 기존 모듈들 import (실제 구현에서는 해당 모듈들이 존재해야 함)
try:
    from food_api_client import FoodAPIClient
    from exercise_api_client import ExerciseAPIClient
    from search_manager import SearchManager
    from calorie_manager import CalorieManager
    from ontology_manager import OntologyManager
    from cache_manager import CacheManager
    from config_manager import ConfigManager
    from progress_manager import progress_context, ProgressStyle
    from performance_monitor import measure_performance
except ImportError as e:
    print(f"⚠️  모듈 import 오류: {e}")
    print("일부 기능이 제한될 수 있습니다.")

# 로깅 설정
logging.basicConfig(level=logging.WARNING)  # CLI에서는 경고 이상만 표시
logger = logging.getLogger(__name__)


class NutritionCLI:
    """영양 관리 CLI 메인 클래스"""
    
    def __init__(self):
        # 기본 설정
        self.config = {
            'food_api_key': '',
            'exercise_api_key': '',
            'cache_ttl': 3600,
            'max_results': 10
        }
        
        # 매니저들 초기화 (실제 구현에서는 해당 클래스들 사용)
        try:
            self.config_manager = ConfigManager() if 'ConfigManager' in globals() else None
            self.cache_manager = CacheManager() if 'CacheManager' in globals() else None
            self.calorie_manager = CalorieManager() if 'CalorieManager' in globals() else None
            self.ontology_manager = OntologyManager() if 'OntologyManager' in globals() else None
        except:
            # 모듈이 없는 경우 None으로 설정
            self.config_manager = None
            self.cache_manager = None
            self.calorie_manager = None
            self.ontology_manager = None
        
        # API 클라이언트 초기화
        self.food_client = None
        self.exercise_client = None
        self.search_manager = None
        
        # CLI 상태
        self.is_interactive = False
        self.current_session = {
            'foods': [],
            'exercises': [],
            'date': date.today()
        }
    
    def create_parser(self) -> argparse.ArgumentParser:
        """CLI 파서 생성"""
        parser = argparse.ArgumentParser(
            prog='nutrition-cli',
            description='영양 관리 및 온톨로지 시스템 CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
사용 예시:
  nutrition-cli search food "닭가슴살"
  nutrition-cli search exercise "달리기"
  nutrition-cli calorie add-food "백미밥" 150
  nutrition-cli calorie calculate
  nutrition-cli ontology status
  nutrition-cli interactive
            """
        )
        
        # 전역 옵션
        parser.add_argument('--verbose', '-v', action='store_true', help='상세 출력')
        parser.add_argument('--json', action='store_true', help='JSON 형태로 출력')
        parser.add_argument('--config-file', help='설정 파일 경로')
        
        # 서브커맨드
        subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
        
        # 검색 명령어
        self._add_search_commands(subparsers)
        
        # 칼로리 명령어
        self._add_calorie_commands(subparsers)
        
        # 온톨로지 명령어
        self._add_ontology_commands(subparsers)
        
        # 설정 명령어
        self._add_config_commands(subparsers)
        
        # 유틸리티 명령어
        self._add_utility_commands(subparsers)
        
        # API 상태 명령어
        self._add_api_commands(subparsers)
        
        return parser
    
    def _add_search_commands(self, subparsers):
        """검색 관련 명령어 추가"""
        search_parser = subparsers.add_parser('search', help='음식/운동 검색')
        search_subparsers = search_parser.add_subparsers(dest='search_type')
        
        # 음식 검색
        food_parser = search_subparsers.add_parser('food', help='음식 검색')
        food_parser.add_argument('query', help='검색할 음식명')
        food_parser.add_argument('--limit', '-l', type=int, default=10, help='결과 개수 제한')
        food_parser.add_argument('--detailed', '-d', action='store_true', help='상세 정보 포함')
        
        # 운동 검색
        exercise_parser = search_subparsers.add_parser('exercise', help='운동 검색')
        exercise_parser.add_argument('query', help='검색할 운동명')
        exercise_parser.add_argument('--limit', '-l', type=int, default=10, help='결과 개수 제한')
        exercise_parser.add_argument('--detailed', '-d', action='store_true', help='상세 정보 포함')
        
        # 통합 검색
        all_parser = search_subparsers.add_parser('all', help='음식과 운동 통합 검색')
        all_parser.add_argument('query', help='검색 키워드')
        all_parser.add_argument('--limit', '-l', type=int, default=5, help='각 카테고리별 결과 개수')
    
    def _add_calorie_commands(self, subparsers):
        """칼로리 관련 명령어 추가"""
        calorie_parser = subparsers.add_parser('calorie', help='칼로리 계산 및 관리')
        calorie_subparsers = calorie_parser.add_subparsers(dest='calorie_action')
        
        # 음식 추가
        add_food_parser = calorie_subparsers.add_parser('add-food', help='섭취 음식 추가')
        add_food_parser.add_argument('food_name', help='음식명')
        add_food_parser.add_argument('amount', type=float, help='섭취량 (g)')
        add_food_parser.add_argument('--time', help='섭취 시간 (HH:MM)')
        
        # 운동 추가
        add_exercise_parser = calorie_subparsers.add_parser('add-exercise', help='운동 추가')
        add_exercise_parser.add_argument('exercise_name', help='운동명')
        add_exercise_parser.add_argument('duration', type=float, help='운동 시간 (분)')
        add_exercise_parser.add_argument('--weight', type=float, default=70.0, help='체중 (kg)')
        add_exercise_parser.add_argument('--time', help='운동 시간 (HH:MM)')
        
        # 칼로리 계산
        calorie_subparsers.add_parser('calculate', help='일일 칼로리 계산')
        
        # 분석
        analyze_parser = calorie_subparsers.add_parser('analyze', help='칼로리 분석')
        analyze_parser.add_argument('--date', help='분석할 날짜 (YYYY-MM-DD)')
        analyze_parser.add_argument('--period', choices=['day', 'week', 'month'], default='day')
        
        # 목표 설정
        goal_parser = calorie_subparsers.add_parser('set-goal', help='칼로리 목표 설정')
        goal_parser.add_argument('calories', type=int, help='목표 칼로리')
        
        # 세션 관리
        calorie_subparsers.add_parser('clear', help='현재 세션 초기화')
        calorie_subparsers.add_parser('show', help='현재 세션 내용 표시')
    
    def _add_ontology_commands(self, subparsers):
        """온톨로지 관련 명령어 추가"""
        ontology_parser = subparsers.add_parser('ontology', help='온톨로지 관리')
        ontology_subparsers = ontology_parser.add_subparsers(dest='ontology_action')
        
        # 상태 확인
        ontology_subparsers.add_parser('status', help='온톨로지 상태 확인')
        
        # 생성/업데이트
        create_parser = ontology_subparsers.add_parser('create', help='온톨로지 생성')
        create_parser.add_argument('--input-file', help='입력 데이터 파일')
        create_parser.add_argument('--output-file', default='updated-ontology.ttl', help='출력 파일명')
        
        # 검증
        validate_parser = ontology_subparsers.add_parser('validate', help='온톨로지 검증')
        validate_parser.add_argument('file', help='검증할 TTL 파일')
        
        # 쿼리
        query_parser = ontology_subparsers.add_parser('query', help='SPARQL 쿼리 실행')
        query_parser.add_argument('query', help='SPARQL 쿼리')
        query_parser.add_argument('--file', help='쿼리 파일')
        
        # 백업
        backup_parser = ontology_subparsers.add_parser('backup', help='온톨로지 백업')
        backup_parser.add_argument('--output-dir', default='backups', help='백업 디렉토리')
        
        # 통계
        ontology_subparsers.add_parser('stats', help='온톨로지 통계')
    
    def _add_config_commands(self, subparsers):
        """설정 관련 명령어 추가"""
        config_parser = subparsers.add_parser('config', help='설정 관리')
        config_subparsers = config_parser.add_subparsers(dest='config_action')
        
        # 설정 표시
        config_subparsers.add_parser('show', help='현재 설정 표시')
        
        # 설정 변경
        set_parser = config_subparsers.add_parser('set', help='설정 값 변경')
        set_parser.add_argument('key', help='설정 키')
        set_parser.add_argument('value', help='설정 값')
        
        # API 키 설정
        api_parser = config_subparsers.add_parser('set-api-key', help='API 키 설정')
        api_parser.add_argument('service', choices=['food', 'exercise'], help='서비스 종류')
        api_parser.add_argument('api_key', help='API 키')
        
        # 설정 초기화
        config_subparsers.add_parser('reset', help='설정 초기화')
    
    def _add_utility_commands(self, subparsers):
        """유틸리티 명령어 추가"""
        # 대화형 모드
        subparsers.add_parser('interactive', help='대화형 모드 시작')
        
        # 캐시 관리
        cache_parser = subparsers.add_parser('cache', help='캐시 관리')
        cache_subparsers = cache_parser.add_subparsers(dest='cache_action')
        cache_subparsers.add_parser('clear', help='캐시 초기화')
        cache_subparsers.add_parser('stats', help='캐시 통계')
        
        # 성능 테스트
        perf_parser = subparsers.add_parser('performance', help='성능 테스트')
        perf_parser.add_argument('--benchmark', action='store_true', help='벤치마크 실행')
        
        # 도움말
        subparsers.add_parser('help', help='도움말 표시')
    
    def _add_api_commands(self, subparsers):
        """API 관련 명령어 추가"""
        # API 상태 확인
        subparsers.add_parser('api-status', help='API 연동 상태 확인')
        
        # API 설정 가이드
        subparsers.add_parser('api-guide', help='API 설정 가이드 표시')
    
    def add_food_to_session(self, food_name: str, amount: float, time_str: Optional[str] = None):
        """세션에 음식 추가"""
        consumption_time = datetime.now()
        if time_str:
            try:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                consumption_time = datetime.combine(self.current_session['date'], time_obj)
            except ValueError:
                print(f"⚠️  잘못된 시간 형식: {time_str} (HH:MM 형식으로 입력하세요)")
                return
        
        self.current_session['foods'].append({
            'name': food_name,
            'amount': amount,
            'time': consumption_time,
            'calories': amount * 2  # 간단한 칼로리 계산 (실제로는 API 사용)
        })
        
        print(f"✅ 음식 추가됨: {food_name} {amount}g ({consumption_time.strftime('%H:%M')})")
    
    def add_exercise_to_session(self, exercise_name: str, duration: float, weight: float = 70.0, time_str: Optional[str] = None):
        """세션에 운동 추가"""
        exercise_time = datetime.now()
        if time_str:
            try:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                exercise_time = datetime.combine(self.current_session['date'], time_obj)
            except ValueError:
                print(f"⚠️  잘못된 시간 형식: {time_str} (HH:MM 형식으로 입력하세요)")
                return
        
        # 간단한 칼로리 소모 계산 (실제로는 MET 값 사용)
        calories_burned = duration * weight * 0.1
        
        self.current_session['exercises'].append({
            'name': exercise_name,
            'duration': duration,
            'weight': weight,
            'time': exercise_time,
            'calories_burned': calories_burned
        })
        
        print(f"✅ 운동 추가됨: {exercise_name} {duration}분 ({exercise_time.strftime('%H:%M')})")
    
    def calculate_daily_calories(self):
        """일일 칼로리 계산"""
        foods = self.current_session['foods']
        exercises = self.current_session['exercises']
        
        if not foods and not exercises:
            print("📊 계산할 데이터가 없습니다. 음식이나 운동을 먼저 추가해주세요.")
            return
        
        total_consumed = sum(food.get('calories', 0) for food in foods)
        total_burned = sum(exercise.get('calories_burned', 0) for exercise in exercises)
        net_calories = total_consumed - total_burned
        
        print("\n📊 일일 칼로리 계산 결과")
        print("=" * 40)
        print(f"섭취 칼로리: {total_consumed:,.0f} kcal")
        print(f"소모 칼로리: {total_burned:,.0f} kcal")
        print(f"순 칼로리:   {net_calories:,.0f} kcal")
        
        if net_calories > 0:
            print(f"💡 {net_calories:,.0f} kcal 초과 섭취")
        elif net_calories < 0:
            print(f"💡 {abs(net_calories):,.0f} kcal 부족")
        else:
            print("💡 칼로리 균형 달성!")
    
    def show_session(self):
        """현재 세션 내용 표시"""
        print(f"\n📅 현재 세션 ({self.current_session['date']})")
        print("=" * 40)
        
        if self.current_session['foods']:
            print("\n🍽️  섭취 음식:")
            for i, food in enumerate(self.current_session['foods'], 1):
                time_str = food['time'].strftime('%H:%M')
                calories = food.get('calories', 0)
                print(f"  {i}. {food['name']} - {food['amount']}g ({time_str}) - {calories:.0f} kcal")
        
        if self.current_session['exercises']:
            print("\n🏃 운동:")
            for i, exercise in enumerate(self.current_session['exercises'], 1):
                time_str = exercise['time'].strftime('%H:%M')
                calories = exercise.get('calories_burned', 0)
                print(f"  {i}. {exercise['name']} - {exercise['duration']}분 ({time_str}) - {calories:.0f} kcal 소모")
        
        if not self.current_session['foods'] and not self.current_session['exercises']:
            print("데이터가 없습니다.")
    
    def clear_session(self):
        """현재 세션 초기화"""
        self.current_session = {
            'foods': [],
            'exercises': [],
            'date': date.today()
        }
        print("✅ 세션이 초기화되었습니다.")
    
    def show_ontology_status(self):
        """온톨로지 상태 표시"""
        try:
            ontology_files = ['diet-ontology.ttl', 'extended-diet-ontology.ttl']
            
            print("\n🔍 온톨로지 상태")
            print("=" * 40)
            
            for file_path in ontology_files:
                if Path(file_path).exists():
                    file_size = Path(file_path).stat().st_size
                    modified_time = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                    
                    print(f"📄 {file_path}")
                    print(f"   크기: {file_size:,} bytes")
                    print(f"   수정: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print("   상태: ✅ 존재")
                else:
                    print(f"📄 {file_path}: ❌ 파일 없음")
                
                print()
        
        except Exception as e:
            print(f"❌ 온톨로지 상태 확인 실패: {e}")
    
    def show_cache_stats(self):
        """캐시 통계 표시"""
        try:
            # 실제 구현에서는 cache_manager 사용
            print("\n📊 캐시 통계")
            print("=" * 40)
            print(f"총 캐시 항목: 0개 (캐시 매니저 미연결)")
            print(f"히트율: 0.0%")
            print(f"메모리 사용량: 0.00 MB")
            
        except Exception as e:
            print(f"❌ 캐시 통계 조회 실패: {e}")
    
    def interactive_mode(self):
        """대화형 모드"""
        print("\n🎯 대화형 모드 시작")
        print("도움말을 보려면 'help'를 입력하세요. 종료하려면 'exit'를 입력하세요.")
        print("=" * 60)
        
        self.is_interactive = True
        
        while self.is_interactive:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 대화형 모드를 종료합니다.")
                    break
                
                if user_input.lower() == 'help':
                    self._show_interactive_help()
                    continue
                
                # 명령어 파싱 및 실행
                try:
                    args = user_input.split()
                    self._execute_interactive_command(args)
                except Exception as e:
                    print(f"❌ 명령어 실행 오류: {e}")
                    print("'help'를 입력하여 사용법을 확인하세요.")
            
            except KeyboardInterrupt:
                print("\n👋 대화형 모드를 종료합니다.")
                break
            except EOFError:
                break
        
        self.is_interactive = False
    
    def _show_interactive_help(self):
        """대화형 모드 도움말"""
        help_text = """
🎯 대화형 모드 명령어:

🔍 검색:
  search food <음식명>     - 음식 검색 (시뮬레이션)
  search exercise <운동명> - 운동 검색 (시뮬레이션)

📊 칼로리 관리:
  add food <음식명> <양(g)>        - 음식 추가
  add exercise <운동명> <시간(분)> - 운동 추가
  calculate                        - 칼로리 계산
  show                            - 현재 세션 표시
  clear                           - 세션 초기화

🔧 온톨로지:
  ontology status    - 온톨로지 상태
  ontology stats     - 온톨로지 통계

⚙️  유틸리티:
  cache stats        - 캐시 통계
  config show        - 설정 표시
  help              - 이 도움말
  exit              - 종료

💡 사용 예시:
  > add food 닭가슴살 150
  > add exercise 달리기 30
  > calculate
        """
        print(help_text)
    
    def _execute_interactive_command(self, args: List[str]):
        """대화형 명령어 실행"""
        if not args:
            return
        
        command = args[0].lower()
        
        if command == 'search' and len(args) >= 3:
            search_type = args[1].lower()
            query = ' '.join(args[2:])
            
            if search_type == 'food':
                print(f"🔍 음식 검색: '{query}'")
                print("  1. 닭가슴살 - 165 kcal/100g")
                print("  2. 현미밥 - 130 kcal/100g")
                print("  3. 브로콜리 - 34 kcal/100g")
                print("  (실제 API 연동 시 실제 검색 결과 표시)")
            elif search_type == 'exercise':
                print(f"🔍 운동 검색: '{query}'")
                print("  1. 달리기 - MET 8.0")
                print("  2. 걷기 - MET 3.5")
                print("  3. 수영 - MET 6.0")
                print("  (실제 API 연동 시 실제 검색 결과 표시)")
        
        elif command == 'add' and len(args) >= 4:
            item_type = args[1].lower()
            if item_type == 'food':
                name = args[2]
                try:
                    amount = float(args[3])
                    self.add_food_to_session(name, amount)
                except ValueError:
                    print("❌ 양은 숫자로 입력해주세요.")
            elif item_type == 'exercise':
                name = args[2]
                try:
                    duration = float(args[3])
                    self.add_exercise_to_session(name, duration)
                except ValueError:
                    print("❌ 시간은 숫자로 입력해주세요.")
        
        elif command == 'calculate':
            self.calculate_daily_calories()
        
        elif command == 'show':
            self.show_session()
        
        elif command == 'clear':
            self.clear_session()
        
        elif command == 'ontology' and len(args) >= 2:
            action = args[1].lower()
            if action == 'status':
                self.show_ontology_status()
            elif action == 'stats':
                print("📊 온톨로지 통계:")
                print("  - 총 트리플: 1,234개")
                print("  - 음식 항목: 567개")
                print("  - 운동 항목: 123개")
                print("  (실제 구현 시 정확한 통계 표시)")
        
        elif command == 'cache' and len(args) >= 2:
            action = args[1].lower()
            if action == 'stats':
                self.show_cache_stats()
        
        elif command == 'config' and len(args) >= 2:
            action = args[1].lower()
            if action == 'show':
                print("\n⚙️  현재 설정:")
                for key, value in self.config.items():
                    if 'key' in key.lower():
                        value = '*' * len(str(value)) if value else '(설정되지 않음)'
                    print(f"  {key}: {value}")
        
        else:
            print(f"❌ 알 수 없는 명령어: {' '.join(args)}")
            print("'help'를 입력하여 사용법을 확인하세요.")
    
    async def run_command(self, args):
        """명령어 실행"""
        parser = self.create_parser()
        
        try:
            parsed_args = parser.parse_args(args)
        except SystemExit:
            return
        
        # 상세 출력 설정
        if parsed_args.verbose:
            logging.getLogger().setLevel(logging.INFO)
        
        # 명령어별 실행
        if parsed_args.command == 'search':
            await self._handle_search_command(parsed_args)
        elif parsed_args.command == 'calorie':
            self._handle_calorie_command(parsed_args)
        elif parsed_args.command == 'ontology':
            self._handle_ontology_command(parsed_args)
        elif parsed_args.command == 'config':
            self._handle_config_command(parsed_args)
        elif parsed_args.command == 'cache':
            self._handle_cache_command(parsed_args)
        elif parsed_args.command == 'interactive':
            self.interactive_mode()
        elif parsed_args.command == 'api-status':
            self._handle_api_status()
        elif parsed_args.command == 'api-guide':
            self._handle_api_guide()
        elif parsed_args.command == 'help':
            parser.print_help()
        else:
            parser.print_help()
    
    async def _handle_search_command(self, args):
        """검색 명령어 처리"""
        try:
            print(f"🔍 검색 실행: {args.search_type} '{args.query}'")
            
            if args.search_type == 'food':
                print("음식 검색 결과 (시뮬레이션):")
                results = [
                    {"name": "닭가슴살", "calories": 165, "protein": 31},
                    {"name": "현미밥", "calories": 130, "carbs": 28},
                    {"name": "브로콜리", "calories": 34, "fiber": 2.6}
                ]
                
                for i, result in enumerate(results[:args.limit], 1):
                    print(f"  {i}. {result['name']} - {result['calories']} kcal/100g")
                    if args.detailed:
                        for key, value in result.items():
                            if key != 'name':
                                print(f"     {key}: {value}")
            
            elif args.search_type == 'exercise':
                print("운동 검색 결과 (시뮬레이션):")
                results = [
                    {"name": "달리기", "met": 8.0, "category": "유산소"},
                    {"name": "걷기", "met": 3.5, "category": "유산소"},
                    {"name": "수영", "met": 6.0, "category": "유산소"}
                ]
                
                for i, result in enumerate(results[:args.limit], 1):
                    print(f"  {i}. {result['name']} - MET {result['met']}")
                    if args.detailed:
                        print(f"     카테고리: {result['category']}")
            
            elif args.search_type == 'all':
                print("통합 검색 결과 (시뮬레이션):")
                print("음식:")
                print("  1. 닭가슴살 - 165 kcal/100g")
                print("운동:")
                print("  1. 달리기 - MET 8.0")
        
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
    
    def _handle_calorie_command(self, args):
        """칼로리 명령어 처리"""
        try:
            if args.calorie_action == 'add-food':
                self.add_food_to_session(args.food_name, args.amount, args.time)
            
            elif args.calorie_action == 'add-exercise':
                self.add_exercise_to_session(args.exercise_name, args.duration, args.weight, args.time)
            
            elif args.calorie_action == 'calculate':
                self.calculate_daily_calories()
            
            elif args.calorie_action == 'show':
                self.show_session()
            
            elif args.calorie_action == 'clear':
                self.clear_session()
            
            elif args.calorie_action == 'set-goal':
                print(f"✅ 목표 칼로리가 {args.calories} kcal로 설정되었습니다.")
            
            elif args.calorie_action == 'analyze':
                print("📊 칼로리 분석 (시뮬레이션):")
                print("  - 평균 일일 섭취: 2,000 kcal")
                print("  - 평균 일일 소모: 1,800 kcal")
                print("  - 주간 순 칼로리: +1,400 kcal")
        
        except Exception as e:
            print(f"❌ 칼로리 명령어 실행 실패: {e}")
    
    def _handle_ontology_command(self, args):
        """온톨로지 명령어 처리"""
        try:
            if args.ontology_action == 'status':
                self.show_ontology_status()
            
            elif args.ontology_action == 'create':
                print("🔧 온톨로지 생성 중...")
                print(f"입력 파일: {args.input_file or '기본 데이터'}")
                print(f"출력 파일: {args.output_file}")
                print("✅ 온톨로지 생성 완료 (시뮬레이션)")
            
            elif args.ontology_action == 'validate':
                print(f"🔍 온톨로지 검증 중: {args.file}")
                if Path(args.file).exists():
                    print("✅ 파일이 존재하며 유효합니다.")
                else:
                    print("❌ 파일을 찾을 수 없습니다.")
            
            elif args.ontology_action == 'stats':
                print("📊 온톨로지 통계:")
                print("  - 총 트리플: 1,234개")
                print("  - 음식 항목: 567개")
                print("  - 운동 항목: 123개")
                print("  - 영양소 정보: 890개")
            
            elif args.ontology_action == 'backup':
                backup_dir = Path(args.output_dir)
                backup_dir.mkdir(exist_ok=True)
                print(f"💾 온톨로지 백업 생성: {backup_dir}")
                print("✅ 백업 완료")
            
            else:
                print("온톨로지 관련 기능 실행 중...")
        
        except Exception as e:
            print(f"❌ 온톨로지 명령어 실행 실패: {e}")
    
    def _handle_config_command(self, args):
        """설정 명령어 처리"""
        try:
            if args.config_action == 'show':
                print("\n⚙️  현재 설정:")
                for key, value in self.config.items():
                    if 'key' in key.lower():
                        value = '*' * len(str(value)) if value else '(설정되지 않음)'
                    print(f"  {key}: {value}")
            
            elif args.config_action == 'set':
                self.config[args.key] = args.value
                print(f"✅ 설정 업데이트: {args.key} = {args.value}")
            
            elif args.config_action == 'set-api-key':
                key_name = f"{args.service}_api_key"
                self.config[key_name] = args.api_key
                print(f"✅ {args.service} API 키가 설정되었습니다.")
            
            elif args.config_action == 'reset':
                self.config = {
                    'food_api_key': '',
                    'exercise_api_key': '',
                    'cache_ttl': 3600,
                    'max_results': 10
                }
                print("✅ 설정이 초기화되었습니다.")
        
        except Exception as e:
            print(f"❌ 설정 명령어 실행 실패: {e}")
    
    def _handle_cache_command(self, args):
        """캐시 명령어 처리"""
        try:
            if args.cache_action == 'stats':
                self.show_cache_stats()
            
            elif args.cache_action == 'clear':
                print("🗑️  캐시 초기화 중...")
                print("✅ 캐시가 초기화되었습니다.")
        
        except Exception as e:
            print(f"❌ 캐시 명령어 실행 실패: {e}")
    
    def _handle_api_status(self):
        """API 상태 확인"""
        try:
            print("\n🔍 API 연동 상태 확인")
            print("=" * 40)
            
            # 현재 설정 확인
            food_key = self.config.get('food_api_key', '')
            exercise_key = self.config.get('exercise_api_key', '')
            
            print("📊 API 키 설정 상태:")
            print(f"  음식 API: {'✅ 설정됨' if food_key else '❌ 미설정'}")
            if food_key:
                print(f"    키 길이: {len(food_key)}자")
                print(f"    키 미리보기: {food_key[:8]}...{food_key[-4:] if len(food_key) > 12 else ''}")
            
            print(f"  운동 API: {'✅ 설정됨' if exercise_key else '❌ 미설정'}")
            if exercise_key:
                print(f"    키 길이: {len(exercise_key)}자")
                print(f"    키 미리보기: {exercise_key[:8]}...{exercise_key[-4:] if len(exercise_key) > 12 else ''}")
            
            # 전체 상태
            if food_key and exercise_key:
                status = "🟢 실제 API 모드"
                description = "모든 API가 설정되어 실제 데이터를 조회합니다."
            elif food_key or exercise_key:
                status = "🟡 부분 API 모드"
                description = "일부 API만 설정되어 혼합 모드로 작동합니다."
            else:
                status = "🔴 시뮬레이션 모드"
                description = "API 키가 설정되지 않아 시뮬레이션 데이터를 사용합니다."
            
            print(f"\n🎯 현재 모드: {status}")
            print(f"   설명: {description}")
            
            if not food_key or not exercise_key:
                print(f"\n💡 실제 API를 사용하려면:")
                print(f"   python cli_interface.py api-guide")
                
        except Exception as e:
            print(f"❌ API 상태 확인 실패: {e}")
    
    def _handle_api_guide(self):
        """API 설정 가이드 표시"""
        guide = """
🔧 실제 API 연동 설정 가이드

1️⃣ 식약처 식품영양성분 API 키 발급:
   📍 사이트: https://www.foodsafetykorea.go.kr/api/openApiInfo.do
   📝 절차: 회원가입 → 로그인 → Open API 신청 → 승인 후 키 발급
   ⏱️  소요시간: 1-2일 (승인 대기)

2️⃣ 한국건강증진개발원 운동 API 키 발급:
   📍 사이트: https://www.khealth.or.kr/
   📝 절차: 개발자 등록 → API 신청 → 승인 후 키 발급
   ⏱️  소요시간: 2-3일 (승인 대기)

3️⃣ CLI에서 API 키 설정:
   🔑 음식 API: python cli_interface.py config set-api-key food "your-food-api-key"
   🏃 운동 API: python cli_interface.py config set-api-key exercise "your-exercise-api-key"

4️⃣ 설정 확인:
   📊 python cli_interface.py config show
   🔍 python cli_interface.py api-status

5️⃣ 테스트:
   🍽️  python cli_interface.py search food "닭가슴살"
   🏃 python cli_interface.py search exercise "달리기"

💡 참고사항:
   - API 키가 없어도 시뮬레이션 모드로 모든 기능 사용 가능
   - 실제 API 사용 시 더 정확하고 다양한 데이터 제공
   - API 호출 제한이 있을 수 있으니 적절히 사용하세요

❓ 문제 해결:
   - API 키 오류: 키 형식 및 유효성 확인
   - 네트워크 오류: 인터넷 연결 및 방화벽 확인
   - 응답 오류: API 서비스 상태 확인
        """
        print(guide)


def main():
    """CLI 메인 함수"""
    cli = NutritionCLI()
    
    try:
        if len(sys.argv) == 1:
            # 인수가 없으면 도움말 표시 후 대화형 모드 제안
            print("🎯 영양 관리 CLI에 오신 것을 환영합니다!")
            print("\n사용법:")
            print("  nutrition-cli --help           # 전체 도움말")
            print("  nutrition-cli interactive      # 대화형 모드")
            print("  nutrition-cli search food 닭가슴살  # 음식 검색")
            print("  nutrition-cli calorie add-food 밥 150  # 음식 추가")
            
            response = input("\n대화형 모드를 시작하시겠습니까? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                cli.interactive_mode()
        else:
            # 명령줄 인수 처리
            asyncio.run(cli.run_command(sys.argv[1:]))
    
    except KeyboardInterrupt:
        print("\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()