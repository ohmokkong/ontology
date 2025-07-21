"""
CLI 인터페이스 테스트

이 모듈은 명령줄 인터페이스의 기능을 테스트합니다.
"""

import unittest
import asyncio
import sys
import io
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import redirect_stdout, redirect_stderr

from cli_interface import NutritionCLI


class TestNutritionCLI(unittest.TestCase):
    """NutritionCLI 클래스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.cli = NutritionCLI()
        # API 클라이언트 모킹
        self.cli.food_client = MagicMock()
        self.cli.exercise_client = MagicMock()
        self.cli.search_manager = MagicMock()
    
    def test_cli_initialization(self):
        """CLI 초기화 테스트"""
        self.assertIsNotNone(self.cli.config_manager)
        self.assertIsNotNone(self.cli.cache_manager)
        self.assertIsNotNone(self.cli.calorie_manager)
        self.assertIsNotNone(self.cli.ontology_manager)
        
        # 세션 초기 상태 확인
        self.assertEqual(len(self.cli.current_session['foods']), 0)
        self.assertEqual(len(self.cli.current_session['exercises']), 0)
        self.assertFalse(self.cli.interactive_mode)
    
    def test_parser_creation(self):
        """파서 생성 테스트"""
        parser = self.cli.create_parser()
        
        self.assertIsNotNone(parser)
        
        # 기본 옵션 확인
        help_text = parser.format_help()
        self.assertIn('search', help_text)
        self.assertIn('calorie', help_text)
        self.assertIn('ontology', help_text)
        self.assertIn('config', help_text)
        self.assertIn('interactive', help_text)
    
    def test_add_food_to_session(self):
        """세션에 음식 추가 테스트"""
        initial_count = len(self.cli.current_session['foods'])
        
        self.cli.add_food_to_session("닭가슴살", 150.0)
        
        self.assertEqual(len(self.cli.current_session['foods']), initial_count + 1)
        
        added_food = self.cli.current_session['foods'][-1]
        self.assertEqual(added_food['name'], "닭가슴살")
        self.assertEqual(added_food['amount'], 150.0)
    
    def test_add_exercise_to_session(self):
        """세션에 운동 추가 테스트"""
        initial_count = len(self.cli.current_session['exercises'])
        
        self.cli.add_exercise_to_session("달리기", 30.0, 70.0)
        
        self.assertEqual(len(self.cli.current_session['exercises']), initial_count + 1)
        
        added_exercise = self.cli.current_session['exercises'][-1]
        self.assertEqual(added_exercise['name'], "달리기")
        self.assertEqual(added_exercise['duration'], 30.0)
        self.assertEqual(added_exercise['weight'], 70.0)
    
    def test_clear_session(self):
        """세션 초기화 테스트"""
        # 데이터 추가
        self.cli.add_food_to_session("사과", 100.0)
        self.cli.add_exercise_to_session("걷기", 20.0)
        
        # 초기화
        self.cli.clear_session()
        
        self.assertEqual(len(self.cli.current_session['foods']), 0)
        self.assertEqual(len(self.cli.current_session['exercises']), 0)
    
    @patch('builtins.print')
    def test_show_session(self, mock_print):
        """세션 표시 테스트"""
        # 데이터 추가
        self.cli.add_food_to_session("바나나", 120.0)
        self.cli.add_exercise_to_session("수영", 45.0)
        
        self.cli.show_session()
        
        # print가 호출되었는지 확인
        mock_print.assert_called()
        
        # 출력 내용 확인
        call_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
        output_text = ' '.join(str(arg) for arg in call_args)
        
        self.assertIn("바나나", output_text)
        self.assertIn("수영", output_text)
    
    @patch('builtins.print')
    def test_calculate_daily_calories(self, mock_print):
        """일일 칼로리 계산 테스트"""
        # 데이터 추가 (칼로리 값 포함)
        self.cli.current_session['foods'] = [
            {'name': '밥', 'amount': 150, 'calories': 200},
            {'name': '닭가슴살', 'amount': 100, 'calories': 165}
        ]
        self.cli.current_session['exercises'] = [
            {'name': '달리기', 'duration': 30, 'calories_burned': 300},
            {'name': '걷기', 'duration': 20, 'calories_burned': 100}
        ]
        
        self.cli.calculate_daily_calories()
        
        # print가 호출되었는지 확인
        mock_print.assert_called()
        
        # 출력 내용 확인
        call_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
        output_text = ' '.join(str(arg) for arg in call_args)
        
        self.assertIn("섭취 칼로리", output_text)
        self.assertIn("소모 칼로리", output_text)
        self.assertIn("순 칼로리", output_text)
    
    @patch('builtins.print')
    def test_calculate_daily_calories_empty(self, mock_print):
        """빈 세션에서 칼로리 계산 테스트"""
        self.cli.calculate_daily_calories()
        
        # 데이터 없음 메시지 확인
        mock_print.assert_called_with("📊 계산할 데이터가 없습니다. 음식이나 운동을 먼저 추가해주세요.")
    
    @patch('pathlib.Path.exists')
    @patch('builtins.print')
    def test_show_ontology_status(self, mock_print, mock_exists):
        """온톨로지 상태 표시 테스트"""
        # 파일 존재 시뮬레이션
        mock_exists.return_value = True
        
        # 온톨로지 매니저 모킹
        self.cli.ontology_manager.load_existing_ontology = MagicMock(return_value=MagicMock())
        
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 1024
            mock_stat.return_value.st_mtime = 1640995200  # 2022-01-01
            
            self.cli.show_ontology_status()
        
        # print가 호출되었는지 확인
        mock_print.assert_called()
        
        # 출력 내용 확인
        call_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
        output_text = ' '.join(str(arg) for arg in call_args)
        
        self.assertIn("온톨로지 상태", output_text)
    
    @patch('builtins.print')
    def test_show_cache_stats(self, mock_print):
        """캐시 통계 표시 테스트"""
        # 캐시 매니저 모킹
        self.cli.cache_manager.get_cache_stats = MagicMock(return_value={
            'total_items': 100,
            'hit_rate': 75.5,
            'memory_usage': 2.5,
            'expired_items': 5
        })
        
        self.cli.show_cache_stats()
        
        # print가 호출되었는지 확인
        mock_print.assert_called()
        
        # 출력 내용 확인
        call_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
        output_text = ' '.join(str(arg) for arg in call_args)
        
        self.assertIn("캐시 통계", output_text)
        self.assertIn("100", output_text)  # total_items
        self.assertIn("75.5", output_text)  # hit_rate
    
    def test_search_food_mock(self):
        """음식 검색 모킹 테스트"""
        # 검색 매니저 모킹
        mock_food = MagicMock()
        mock_food.__dict__ = {'name': '닭가슴살', 'food_id': '123'}
        
        self.cli.search_manager.search_food_with_cache = AsyncMock(return_value=[mock_food])
        
        # 비동기 함수 테스트
        async def test_search():
            results = await self.cli.search_food("닭가슴살", limit=5)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['name'], '닭가슴살')
        
        asyncio.run(test_search())
    
    def test_search_exercise_mock(self):
        """운동 검색 모킹 테스트"""
        # 검색 매니저 모킹
        mock_exercise = MagicMock()
        mock_exercise.__dict__ = {'name': '달리기', 'exercise_id': '456'}
        
        self.cli.search_manager.search_exercise_with_cache = AsyncMock(return_value=[mock_exercise])
        
        # 비동기 함수 테스트
        async def test_search():
            results = await self.cli.search_exercise("달리기", limit=5)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['name'], '달리기')
        
        asyncio.run(test_search())
    
    def test_interactive_command_parsing(self):
        """대화형 명령어 파싱 테스트"""
        # 음식 추가 명령어
        with patch('builtins.print') as mock_print:
            self.cli._execute_interactive_command(['add', 'food', '사과', '100'])
            
            # 음식이 추가되었는지 확인
            self.assertEqual(len(self.cli.current_session['foods']), 1)
            self.assertEqual(self.cli.current_session['foods'][0]['name'], '사과')
        
        # 운동 추가 명령어
        with patch('builtins.print') as mock_print:
            self.cli._execute_interactive_command(['add', 'exercise', '달리기', '30'])
            
            # 운동이 추가되었는지 확인
            self.assertEqual(len(self.cli.current_session['exercises']), 1)
            self.assertEqual(self.cli.current_session['exercises'][0]['name'], '달리기')
        
        # 세션 표시 명령어
        with patch('builtins.print') as mock_print:
            self.cli._execute_interactive_command(['show'])
            mock_print.assert_called()
        
        # 세션 초기화 명령어
        with patch('builtins.print') as mock_print:
            self.cli._execute_interactive_command(['clear'])
            self.assertEqual(len(self.cli.current_session['foods']), 0)
            self.assertEqual(len(self.cli.current_session['exercises']), 0)
    
    @patch('builtins.print')
    def test_interactive_help(self, mock_print):
        """대화형 도움말 테스트"""
        self.cli._show_interactive_help()
        
        # print가 호출되었는지 확인
        mock_print.assert_called()
        
        # 도움말 내용 확인
        call_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
        help_text = ' '.join(str(arg) for arg in call_args)
        
        self.assertIn("대화형 모드 명령어", help_text)
        self.assertIn("search food", help_text)
        self.assertIn("add food", help_text)
        self.assertIn("calculate", help_text)
    
    def test_print_search_results(self):
        """검색 결과 출력 테스트"""
        # 음식 검색 결과
        food_results = [
            {
                'food': {'name': '닭가슴살', 'food_id': '123'},
                'nutrition': {
                    'calories_per_100g': 165,
                    'carbohydrate': 0,
                    'protein': 31,
                    'fat': 3.6
                }
            }
        ]
        
        with patch('builtins.print') as mock_print:
            self.cli._print_search_results('음식', food_results)
            
            # 출력 확인
            call_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
            output_text = ' '.join(str(arg) for arg in call_args)
            
            self.assertIn("닭가슴살", output_text)
            self.assertIn("165", output_text)  # 칼로리
        
        # 운동 검색 결과
        exercise_results = [
            {
                'exercise': {'name': '달리기', 'exercise_id': '456'},
                'met_value': 8.0,
                'category': '유산소'
            }
        ]
        
        with patch('builtins.print') as mock_print:
            self.cli._print_search_results('운동', exercise_results)
            
            # 출력 확인
            call_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
            output_text = ' '.join(str(arg) for arg in call_args)
            
            self.assertIn("달리기", output_text)
            self.assertIn("8.0", output_text)  # MET 값
    
    @patch('builtins.print')
    def test_print_search_results_empty(self, mock_print):
        """빈 검색 결과 출력 테스트"""
        self.cli._print_search_results('음식', [])
        
        # 결과 없음 메시지 확인
        mock_print.assert_called_with("🔍 음식 검색 결과가 없습니다.")


class TestCLICommands(unittest.TestCase):
    """CLI 명령어 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.cli = NutritionCLI()
        # API 클라이언트 모킹
        self.cli.food_client = MagicMock()
        self.cli.exercise_client = MagicMock()
        self.cli.search_manager = MagicMock()
    
    def test_command_parsing(self):
        """명령어 파싱 테스트"""
        parser = self.cli.create_parser()
        
        # 음식 검색 명령어
        args = parser.parse_args(['search', 'food', '닭가슴살', '--limit', '5'])
        self.assertEqual(args.command, 'search')
        self.assertEqual(args.search_type, 'food')
        self.assertEqual(args.query, '닭가슴살')
        self.assertEqual(args.limit, 5)
        
        # 칼로리 추가 명령어
        args = parser.parse_args(['calorie', 'add-food', '밥', '150'])
        self.assertEqual(args.command, 'calorie')
        self.assertEqual(args.calorie_action, 'add-food')
        self.assertEqual(args.food_name, '밥')
        self.assertEqual(args.amount, 150.0)
        
        # 온톨로지 상태 명령어
        args = parser.parse_args(['ontology', 'status'])
        self.assertEqual(args.command, 'ontology')
        self.assertEqual(args.ontology_action, 'status')
    
    @patch('builtins.print')
    def test_calorie_command_handling(self, mock_print):
        """칼로리 명령어 처리 테스트"""
        # add-food 명령어
        args = MagicMock()
        args.calorie_action = 'add-food'
        args.food_name = '사과'
        args.amount = 100.0
        args.time = None
        
        self.cli._handle_calorie_command(args)
        
        # 음식이 추가되었는지 확인
        self.assertEqual(len(self.cli.current_session['foods']), 1)
        self.assertEqual(self.cli.current_session['foods'][0]['name'], '사과')
        
        # show 명령어
        args.calorie_action = 'show'
        self.cli._handle_calorie_command(args)
        mock_print.assert_called()
        
        # clear 명령어
        args.calorie_action = 'clear'
        self.cli._handle_calorie_command(args)
        self.assertEqual(len(self.cli.current_session['foods']), 0)
    
    @patch('builtins.print')
    def test_config_command_handling(self, mock_print):
        """설정 명령어 처리 테스트"""
        # show 명령어
        args = MagicMock()
        args.config_action = 'show'
        
        # config_manager 모킹
        self.cli.config_manager.get_config = MagicMock(return_value={
            'food_api_key': 'test_key',
            'cache_ttl': 3600
        })
        
        self.cli._handle_config_command(args)
        mock_print.assert_called()
        
        # set 명령어
        args.config_action = 'set'
        args.key = 'test_key'
        args.value = 'test_value'
        
        self.cli.config_manager.set_config = MagicMock()
        self.cli._handle_config_command(args)
        
        self.cli.config_manager.set_config.assert_called_with('test_key', 'test_value')
    
    @patch('builtins.print')
    def test_cache_command_handling(self, mock_print):
        """캐시 명령어 처리 테스트"""
        # stats 명령어
        args = MagicMock()
        args.cache_action = 'stats'
        
        self.cli.cache_manager.get_cache_stats = MagicMock(return_value={
            'total_items': 50,
            'hit_rate': 80.0
        })
        
        self.cli._handle_cache_command(args)
        mock_print.assert_called()
        
        # clear 명령어
        args.cache_action = 'clear'
        self.cli.cache_manager.clear_cache = MagicMock()
        
        self.cli._handle_cache_command(args)
        self.cli.cache_manager.clear_cache.assert_called()


class TestCLIIntegration(unittest.TestCase):
    """CLI 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.cli = NutritionCLI()
        # API 클라이언트 모킹
        self.cli.food_client = MagicMock()
        self.cli.exercise_client = MagicMock()
        self.cli.search_manager = MagicMock()
    
    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        # 1. 음식 추가
        self.cli.add_food_to_session("닭가슴살", 150.0)
        self.cli.add_food_to_session("브로콜리", 100.0)
        
        # 2. 운동 추가
        self.cli.add_exercise_to_session("달리기", 30.0, 70.0)
        self.cli.add_exercise_to_session("걷기", 20.0, 70.0)
        
        # 3. 세션 확인
        self.assertEqual(len(self.cli.current_session['foods']), 2)
        self.assertEqual(len(self.cli.current_session['exercises']), 2)
        
        # 4. 칼로리 계산 (출력 캡처)
        with patch('builtins.print') as mock_print:
            self.cli.calculate_daily_calories()
            mock_print.assert_called()
        
        # 5. 세션 초기화
        self.cli.clear_session()
        self.assertEqual(len(self.cli.current_session['foods']), 0)
        self.assertEqual(len(self.cli.current_session['exercises']), 0)
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_mode_simulation(self, mock_print, mock_input):
        """대화형 모드 시뮬레이션 테스트"""
        # 사용자 입력 시뮬레이션
        mock_input.side_effect = [
            'add food 사과 100',
            'add exercise 달리기 30',
            'show',
            'calculate',
            'exit'
        ]
        
        # 대화형 모드 실행
        self.cli.interactive_mode()
        
        # 결과 확인
        self.assertEqual(len(self.cli.current_session['foods']), 1)
        self.assertEqual(len(self.cli.current_session['exercises']), 1)
        self.assertFalse(self.cli.interactive_mode)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)