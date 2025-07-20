"""
플러그인 시스템 테스트 모듈.
이 모듈은 플러그인 시스템의 기능을 테스트합니다.
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from plugin_system import (
    PluginInterface, APIClientPlugin, DataConverterPlugin, ProcessorPlugin,
    PluginRegistry, PluginManager, get_plugin_manager
)
from exceptions import DataProcessingError


# 테스트용 플러그인 클래스들
class TestAPIClient(APIClientPlugin):
    """테스트용 API 클라이언트 플러그인."""
    
    @property
    def name(self) -> str:
        return "test_api"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "테스트용 API 클라이언트"
    
    def initialize(self, config):
        self.config = config
        self.initialized = True
    
    def cleanup(self):
        self.initialized = False
    
    def search(self, query, **kwargs):
        return [{"id": "1", "name": f"result for {query}"}]
    
    def get_detail(self, item_id, **kwargs):
        return {"id": item_id, "details": "test details"}
    
    def validate_response(self, response):
        return isinstance(response, dict) and "id" in response


class TestDataConverter(DataConverterPlugin):
    """테스트용 데이터 변환기 플러그인."""
    
    @property
    def name(self) -> str:
        return "test_converter"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "테스트용 데이터 변환기"
    
    @property
    def supported_formats(self):
        return ["json", "xml"]
    
    def initialize(self, config):
        self.config = config
        self.initialized = True
    
    def cleanup(self):
        self.initialized = False
    
    def convert(self, data, source_format, target_format, **kwargs):
        return {"converted": data, "from": source_format, "to": target_format}
    
    def validate_input(self, data, format_type):
        return data is not None


class TestProcessor(ProcessorPlugin):
    """테스트용 데이터 처리기 플러그인."""
    
    @property
    def name(self) -> str:
        return "test_processor"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "테스트용 데이터 처리기"
    
    def initialize(self, config):
        self.config = config
        self.initialized = True
    
    def cleanup(self):
        self.initialized = False
    
    def process(self, data, **kwargs):
        return {"processed": data, "processor": self.name}
    
    def can_process(self, data):
        return isinstance(data, (dict, list, str))


class TestPluginRegistry(unittest.TestCase):
    """플러그인 레지스트리 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        self.registry = PluginRegistry()
        self.test_api_client = TestAPIClient()
        self.test_converter = TestDataConverter()
        self.test_processor = TestProcessor()
    
    def test_register_plugin(self):
        """플러그인 등록 테스트."""
        # API 클라이언트 등록
        self.registry.register_plugin('api_client', self.test_api_client)
        
        # 등록된 플러그인 확인
        registered_plugin = self.registry.get_plugin('api_client', 'test_api')
        self.assertIs(registered_plugin, self.test_api_client)
    
    def test_register_invalid_plugin_type(self):
        """잘못된 플러그인 타입 등록 테스트."""
        with self.assertRaises(ValueError):
            self.registry.register_plugin('invalid_type', self.test_api_client)
    
    def test_get_plugin(self):
        """플러그인 조회 테스트."""
        # 플러그인 등록
        self.registry.register_plugin('data_converter', self.test_converter)
        
        # 등록된 플러그인 조회
        plugin = self.registry.get_plugin('data_converter', 'test_converter')
        self.assertIs(plugin, self.test_converter)
        
        # 존재하지 않는 플러그인 조회
        plugin = self.registry.get_plugin('data_converter', 'non_existent')
        self.assertIsNone(plugin)
    
    def test_list_plugins(self):
        """플러그인 목록 조회 테스트."""
        # 플러그인들 등록
        self.registry.register_plugin('api_client', self.test_api_client)
        self.registry.register_plugin('data_converter', self.test_converter)
        self.registry.register_plugin('processor', self.test_processor)
        
        # 전체 플러그인 목록 조회
        all_plugins = self.registry.list_plugins()
        self.assertIn('test_api', all_plugins['api_client'])
        self.assertIn('test_converter', all_plugins['data_converter'])
        self.assertIn('test_processor', all_plugins['processor'])
        
        # 특정 타입 플러그인 목록 조회
        api_plugins = self.registry.list_plugins('api_client')
        self.assertIn('test_api', api_plugins['api_client'])
        self.assertNotIn('data_converter', api_plugins)
    
    def test_unregister_plugin(self):
        """플러그인 등록 해제 테스트."""
        # 플러그인 등록
        self.registry.register_plugin('processor', self.test_processor)
        
        # 등록 해제
        result = self.registry.unregister_plugin('processor', 'test_processor')
        self.assertTrue(result)
        
        # 등록 해제 확인
        plugin = self.registry.get_plugin('processor', 'test_processor')
        self.assertIsNone(plugin)
        
        # 존재하지 않는 플러그인 등록 해제
        result = self.registry.unregister_plugin('processor', 'non_existent')
        self.assertFalse(result)


class TestPluginManager(unittest.TestCase):
    """플러그인 매니저 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.plugin_dir = os.path.join(self.test_dir, "test_plugins")
        
        # 플러그인 매니저 초기화
        self.plugin_manager = PluginManager(
            plugin_dirs=[self.plugin_dir],
            config={}
        )
    
    def tearDown(self):
        """테스트 정리."""
        # 임시 디렉토리 삭제
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """초기화 테스트."""
        self.assertEqual(self.plugin_manager.plugin_dirs, [self.plugin_dir])
        self.assertTrue(os.path.exists(self.plugin_dir))
        self.assertIsInstance(self.plugin_manager.registry, PluginRegistry)
    
    def test_manual_plugin_registration(self):
        """수동 플러그인 등록 테스트."""
        # 플러그인 수동 등록
        test_api = TestAPIClient()
        test_api.initialize({})
        self.plugin_manager.registry.register_plugin('api_client', test_api)
        
        # 등록된 플러그인 조회
        api_client = self.plugin_manager.get_api_client('test_api')
        self.assertIs(api_client, test_api)
    
    def test_get_plugin_methods(self):
        """플러그인 조회 메서드 테스트."""
        # 테스트 플러그인들 등록
        test_api = TestAPIClient()
        test_converter = TestDataConverter()
        test_processor = TestProcessor()
        
        test_api.initialize({})
        test_converter.initialize({})
        test_processor.initialize({})
        
        self.plugin_manager.registry.register_plugin('api_client', test_api)
        self.plugin_manager.registry.register_plugin('data_converter', test_converter)
        self.plugin_manager.registry.register_plugin('processor', test_processor)
        
        # 각 타입별 플러그인 조회
        self.assertIs(self.plugin_manager.get_api_client('test_api'), test_api)
        self.assertIs(self.plugin_manager.get_data_converter('test_converter'), test_converter)
        self.assertIs(self.plugin_manager.get_processor('test_processor'), test_processor)
        
        # 존재하지 않는 플러그인 조회
        self.assertIsNone(self.plugin_manager.get_api_client('non_existent'))
    
    def test_find_converter_for_format(self):
        """형식별 변환기 찾기 테스트."""
        # 테스트 변환기 등록
        test_converter = TestDataConverter()
        test_converter.initialize({})
        self.plugin_manager.registry.register_plugin('data_converter', test_converter)
        
        # 지원하는 형식 변환기 찾기
        converter = self.plugin_manager.find_converter_for_format('json', 'xml')
        self.assertIs(converter, test_converter)
        
        # 지원하지 않는 형식 변환기 찾기
        converter = self.plugin_manager.find_converter_for_format('json', 'yaml')
        self.assertIsNone(converter)
    
    def test_find_processor_for_data(self):
        """데이터별 처리기 찾기 테스트."""
        # 테스트 처리기 등록
        test_processor = TestProcessor()
        test_processor.initialize({})
        self.plugin_manager.registry.register_plugin('processor', test_processor)
        
        # 처리 가능한 데이터
        processor = self.plugin_manager.find_processor_for_data({"test": "data"})
        self.assertIs(processor, test_processor)
        
        # 처리 불가능한 데이터 (TestProcessor는 dict, list, str만 처리)
        processor = self.plugin_manager.find_processor_for_data(123)
        self.assertIsNone(processor)
    
    def test_execute_api_search(self):
        """API 검색 실행 테스트."""
        # 테스트 API 클라이언트 등록
        test_api = TestAPIClient()
        test_api.initialize({})
        self.plugin_manager.registry.register_plugin('api_client', test_api)
        
        # API 검색 실행
        results = self.plugin_manager.execute_api_search('test_api', 'test query')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'result for test query')
        
        # 존재하지 않는 API 클라이언트로 검색
        with self.assertRaises(ValueError):
            self.plugin_manager.execute_api_search('non_existent', 'query')
    
    def test_convert_data(self):
        """데이터 변환 테스트."""
        # 테스트 변환기 등록
        test_converter = TestDataConverter()
        test_converter.initialize({})
        self.plugin_manager.registry.register_plugin('data_converter', test_converter)
        
        # 데이터 변환 (변환기 이름 지정)
        result = self.plugin_manager.convert_data(
            {"test": "data"}, 'json', 'xml', converter_name='test_converter'
        )
        self.assertEqual(result['converted'], {"test": "data"})
        self.assertEqual(result['from'], 'json')
        self.assertEqual(result['to'], 'xml')
        
        # 데이터 변환 (자동 변환기 선택)
        result = self.plugin_manager.convert_data({"test": "data"}, 'json', 'xml')
        self.assertIsNotNone(result)
        
        # 지원하지 않는 형식 변환
        with self.assertRaises(ValueError):
            self.plugin_manager.convert_data({"test": "data"}, 'json', 'yaml')
    
    def test_process_data(self):
        """데이터 처리 테스트."""
        # 테스트 처리기 등록
        test_processor = TestProcessor()
        test_processor.initialize({})
        self.plugin_manager.registry.register_plugin('processor', test_processor)
        
        # 데이터 처리 (처리기 이름 지정)
        result = self.plugin_manager.process_data(
            {"test": "data"}, processor_name='test_processor'
        )
        self.assertEqual(result['processed'], {"test": "data"})
        self.assertEqual(result['processor'], 'test_processor')
        
        # 데이터 처리 (자동 처리기 선택)
        result = self.plugin_manager.process_data({"test": "data"})
        self.assertIsNotNone(result)
    
    def test_get_plugin_info(self):
        """플러그인 정보 조회 테스트."""
        # 테스트 플러그인들 등록
        test_api = TestAPIClient()
        test_converter = TestDataConverter()
        
        test_api.initialize({})
        test_converter.initialize({})
        
        self.plugin_manager.registry.register_plugin('api_client', test_api)
        self.plugin_manager.registry.register_plugin('data_converter', test_converter)
        
        # 플러그인 정보 조회
        info = self.plugin_manager.get_plugin_info()
        
        self.assertEqual(info['plugin_dirs'], [self.plugin_dir])
        self.assertEqual(info['total_plugins'], 2)
        self.assertIn('api_client', info['loaded_plugins'])
        self.assertIn('data_converter', info['loaded_plugins'])
        
        # API 클라이언트 정보 확인
        api_info = info['loaded_plugins']['api_client'][0]
        self.assertEqual(api_info['name'], 'test_api')
        self.assertEqual(api_info['version'], '1.0.0')
    
    def test_create_plugin_template(self):
        """플러그인 템플릿 생성 테스트."""
        # API 클라이언트 템플릿 생성
        template_path = self.plugin_manager.create_plugin_template(
            'api_client', 'my_api', self.test_dir
        )
        
        # 템플릿 파일이 생성되었는지 확인
        self.assertTrue(os.path.exists(template_path))
        
        # 템플릿 내용 확인
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertIn('MyApiAPIClient', content)
        self.assertIn('APIClientPlugin', content)
        self.assertIn('def search(self', content)
        
        # 지원하지 않는 플러그인 타입
        with self.assertRaises(ValueError):
            self.plugin_manager.create_plugin_template('invalid_type', 'test', self.test_dir)


class TestGlobalPluginManager(unittest.TestCase):
    """전역 플러그인 매니저 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 전역 플러그인 매니저 초기화
        import plugin_system
        plugin_system._plugin_manager = None
    
    def test_get_plugin_manager(self):
        """전역 플러그인 매니저 조회 테스트."""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        
        # 싱글톤 패턴 확인
        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, PluginManager)


if __name__ == '__main__':
    unittest.main()