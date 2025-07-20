"""
설정 관리 시스템 테스트 모듈.
이 모듈은 설정 관리 시스템의 기능을 테스트합니다.
"""

import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from config_manager import ConfigManager, get_config_manager, get_config, set_config
from exceptions import ConfigurationError


class TestConfigManager(unittest.TestCase):
    """설정 관리 시스템 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, "config")
        
        # 설정 매니저 초기화 (자동 재로드 비활성화)
        self.config_manager = ConfigManager(
            config_dir=self.config_dir,
            environment="test",
            auto_reload=False
        )
    
    def tearDown(self):
        """테스트 정리."""
        # 임시 디렉토리 삭제
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_config_file(self, filename: str, config_data: dict):
        """테스트용 설정 파일을 생성합니다."""
        config_path = os.path.join(self.config_dir, filename)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        return config_path
    
    def test_initialization(self):
        """초기화 테스트."""
        self.assertEqual(self.config_manager.environment, "test")
        self.assertEqual(str(self.config_manager.config_dir), self.config_dir)
        self.assertFalse(self.config_manager.auto_reload)
        self.assertTrue(os.path.exists(self.config_dir))
    
    def test_create_default_config(self):
        """기본 설정 파일 생성 테스트."""
        self.config_manager.create_default_config()
        
        # 기본 설정 파일들이 생성되었는지 확인
        expected_files = ["default.json", "development.json", "production.json"]
        for filename in expected_files:
            config_path = os.path.join(self.config_dir, filename)
            self.assertTrue(os.path.exists(config_path))
            
            # 파일 내용이 유효한 JSON인지 확인
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self.assertIsInstance(config_data, dict)
                self.assertIn('api', config_data)
    
    def test_load_config_json(self):
        """JSON 설정 파일 로드 테스트."""
        test_config = {
            "api": {
                "food": {
                    "base_url": "https://test-api.com",
                    "key": "test-key"
                }
            },
            "cache": {
                "ttl": 1800
            }
        }
        
        self._create_test_config_file("test.json", test_config)
        self.config_manager.load_config()
        
        # 설정이 올바르게 로드되었는지 확인
        self.assertEqual(self.config_manager.get("api.food.base_url"), "https://test-api.com")
        self.assertEqual(self.config_manager.get("api.food.key"), "test-key")
        self.assertEqual(self.config_manager.get("cache.ttl"), 1800)
    
    def test_get_config_with_default(self):
        """기본값을 사용한 설정 조회 테스트."""
        # 존재하지 않는 설정 키
        result = self.config_manager.get("non.existent.key", "default_value")
        self.assertEqual(result, "default_value")
        
        # 존재하는 설정 키
        test_config = {"existing": {"key": "value"}}
        self._create_test_config_file("test.json", test_config)
        self.config_manager.load_config()
        
        result = self.config_manager.get("existing.key", "default_value")
        self.assertEqual(result, "value")
    
    def test_set_config(self):
        """설정 값 설정 테스트."""
        # 새로운 설정 값 설정
        self.config_manager.set("new.setting", "new_value")
        self.assertEqual(self.config_manager.get("new.setting"), "new_value")
        
        # 기존 설정 값 변경
        self.config_manager.set("new.setting", "updated_value")
        self.assertEqual(self.config_manager.get("new.setting"), "updated_value")
        
        # 중첩된 설정 값 설정
        self.config_manager.set("nested.deep.setting", 42)
        self.assertEqual(self.config_manager.get("nested.deep.setting"), 42)
    
    def test_get_api_config(self):
        """API 설정 조회 테스트."""
        test_config = {
            "api": {
                "default": {
                    "timeout": 30,
                    "retry_count": 3
                },
                "food": {
                    "base_url": "https://food-api.com",
                    "key": "food-key"
                }
            }
        }
        
        self._create_test_config_file("test.json", test_config)
        self.config_manager.load_config()
        
        # 특정 API 설정 조회
        food_config = self.config_manager.get_api_config("food")
        self.assertEqual(food_config["base_url"], "https://food-api.com")
        self.assertEqual(food_config["key"], "food-key")
        self.assertEqual(food_config["timeout"], 30)  # 기본 설정에서 상속
        self.assertEqual(food_config["retry_count"], 3)  # 기본 설정에서 상속
        
        # 존재하지 않는 API 설정 조회
        unknown_config = self.config_manager.get_api_config("unknown")
        self.assertEqual(unknown_config["timeout"], 30)  # 기본 설정만 반환
    
    def test_environment_variables_override(self):
        """환경 변수 오버라이드 테스트."""
        test_config = {
            "api": {
                "food": {
                    "key": "original-key"
                }
            }
        }
        
        self._create_test_config_file("test.json", test_config)
        
        # 환경 변수 설정
        with patch.dict(os.environ, {'FOOD_API_KEY': 'env-override-key'}):
            self.config_manager.load_config()
            
            # 환경 변수로 오버라이드된 값 확인
            self.assertEqual(self.config_manager.get("api.food.key"), "env-override-key")
    
    def test_config_merge(self):
        """설정 병합 테스트."""
        # 기본 설정 파일
        default_config = {
            "api": {
                "default": {
                    "timeout": 30,
                    "retry_count": 3
                },
                "food": {
                    "base_url": "https://default-food-api.com"
                }
            },
            "cache": {
                "ttl": 3600
            }
        }
        
        # 환경별 설정 파일
        test_config = {
            "api": {
                "food": {
                    "key": "test-key"
                }
            },
            "cache": {
                "ttl": 1800  # 기본값 오버라이드
            },
            "logging": {
                "level": "DEBUG"
            }
        }
        
        self._create_test_config_file("default.json", default_config)
        self._create_test_config_file("test.json", test_config)
        
        self.config_manager.load_config()
        
        # 병합된 설정 확인
        self.assertEqual(self.config_manager.get("api.default.timeout"), 30)  # 기본값 유지
        self.assertEqual(self.config_manager.get("api.food.base_url"), "https://default-food-api.com")  # 기본값 유지
        self.assertEqual(self.config_manager.get("api.food.key"), "test-key")  # 환경별 설정 추가
        self.assertEqual(self.config_manager.get("cache.ttl"), 1800)  # 환경별 설정으로 오버라이드
        self.assertEqual(self.config_manager.get("logging.level"), "DEBUG")  # 환경별 설정 추가
    
    def test_validate_config_success(self):
        """설정 검증 성공 테스트."""
        valid_config = {
            "api": {
                "food": {
                    "base_url": "https://food-api.com",
                    "key": "valid-key"
                },
                "exercise": {
                    "base_url": "https://exercise-api.com",
                    "key": "valid-key"
                }
            },
            "cache": {
                "ttl": 3600,
                "max_size": 1000
            },
            "logging": {
                "level": "INFO"
            }
        }
        
        self._create_test_config_file("test.json", valid_config)
        self.config_manager.load_config()
        
        validation_result = self.config_manager.validate_config()
        
        self.assertTrue(validation_result['is_valid'])
        self.assertEqual(len(validation_result['errors']), 0)
    
    def test_validate_config_with_warnings(self):
        """설정 검증 경고 테스트."""
        config_with_warnings = {
            "api": {
                "food": {
                    "base_url": "https://food-api.com",
                    "key": "YOUR_FOOD_API_KEY"  # 기본값으로 설정되어 경고 발생
                }
            },
            "cache": {
                "ttl": 0,  # 0 이하 값으로 경고 발생
                "max_size": -1  # 0 이하 값으로 경고 발생
            },
            "logging": {
                "level": "INVALID_LEVEL"  # 유효하지 않은 로그 레벨로 경고 발생
            }
        }
        
        self._create_test_config_file("test.json", config_with_warnings)
        self.config_manager.load_config()
        
        validation_result = self.config_manager.validate_config()
        
        self.assertTrue(validation_result['is_valid'])  # 경고만 있고 오류는 없음
        self.assertGreater(len(validation_result['warnings']), 0)
    
    def test_validate_config_with_errors(self):
        """설정 검증 오류 테스트."""
        config_with_errors = {
            "api": {
                "food": {
                    # base_url 누락으로 오류 발생
                    "key": "valid-key"
                }
            }
        }
        
        self._create_test_config_file("test.json", config_with_errors)
        self.config_manager.load_config()
        
        validation_result = self.config_manager.validate_config()
        
        self.assertFalse(validation_result['is_valid'])
        self.assertGreater(len(validation_result['errors']), 0)
    
    def test_save_config(self):
        """설정 저장 테스트."""
        # 설정 값 설정
        self.config_manager.set("test.setting", "test_value")
        self.config_manager.set("nested.setting", {"key": "value"})
        
        # 설정 저장
        self.config_manager.save_config("saved_config.json")
        
        # 저장된 파일 확인
        saved_path = os.path.join(self.config_dir, "saved_config.json")
        self.assertTrue(os.path.exists(saved_path))
        
        # 저장된 내용 확인
        with open(saved_path, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config["test"]["setting"], "test_value")
        self.assertEqual(saved_config["nested"]["setting"]["key"], "value")
    
    def test_get_config_summary(self):
        """설정 요약 정보 조회 테스트."""
        test_config = {
            "api": {"food": {"key": "value"}},
            "cache": {"ttl": 3600}
        }
        
        self._create_test_config_file("test.json", test_config)
        self.config_manager.load_config()
        
        summary = self.config_manager.get_config_summary()
        
        self.assertEqual(summary['environment'], "test")
        self.assertEqual(summary['config_dir'], self.config_dir)
        self.assertFalse(summary['auto_reload'])
        self.assertIn('api', summary['config_keys'])
        self.assertIn('cache', summary['config_keys'])
        self.assertGreater(summary['total_settings'], 0)
    
    @patch('config_manager.json.load')
    def test_load_config_file_json_error(self, mock_json_load):
        """JSON 파일 로드 오류 테스트."""
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        # 잘못된 JSON 파일 생성
        invalid_json_path = os.path.join(self.config_dir, "invalid.json")
        with open(invalid_json_path, 'w') as f:
            f.write("{ invalid json }")
        
        with self.assertRaises(ConfigurationError):
            self.config_manager._load_config_file(invalid_json_path)
    
    def test_type_conversion_from_env_vars(self):
        """환경 변수 타입 변환 테스트."""
        env_vars = {
            'API_TIMEOUT': '60',        # 정수 변환
            'API_RETRY_DELAY': '1.5',   # 실수 변환
            'CACHE_ENABLED': 'true',    # 불린 변환
            'DEBUG_MODE': 'false'       # 불린 변환
        }
        
        with patch.dict(os.environ, env_vars):
            # 환경 변수 매핑 추가
            original_mappings = self.config_manager._ConfigManager__dict__.get('env_mappings', {})
            test_mappings = {
                'API_TIMEOUT': 'api.timeout',
                'API_RETRY_DELAY': 'api.retry_delay',
                'CACHE_ENABLED': 'cache.enabled',
                'DEBUG_MODE': 'debug.mode'
            }
            
            # 환경 변수 로드 메서드 직접 호출
            for env_var, config_path in test_mappings.items():
                env_value = os.getenv(env_var)
                if env_value is not None:
                    self.config_manager._set_nested_config(config_path, env_value)
            
            # 타입 변환 확인
            self.assertEqual(self.config_manager.get('api.timeout'), 60)
            self.assertEqual(self.config_manager.get('api.retry_delay'), 1.5)
            self.assertEqual(self.config_manager.get('cache.enabled'), True)
            self.assertEqual(self.config_manager.get('debug.mode'), False)


class TestConfigManagerGlobalFunctions(unittest.TestCase):
    """전역 설정 관리 함수 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 전역 설정 매니저 초기화
        import config_manager
        config_manager._config_manager = None
    
    def test_get_config_manager(self):
        """전역 설정 매니저 조회 테스트."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        # 싱글톤 패턴 확인
        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, ConfigManager)
    
    def test_get_config_function(self):
        """전역 설정 조회 함수 테스트."""
        # 설정 값 설정
        set_config("test.key", "test_value")
        
        # 설정 값 조회
        result = get_config("test.key")
        self.assertEqual(result, "test_value")
        
        # 기본값 사용
        result = get_config("non.existent.key", "default")
        self.assertEqual(result, "default")
    
    def test_set_config_function(self):
        """전역 설정 설정 함수 테스트."""
        # 설정 값 설정
        set_config("global.setting", "global_value")
        
        # 설정 값 확인
        manager = get_config_manager()
        result = manager.get("global.setting")
        self.assertEqual(result, "global_value")


if __name__ == '__main__':
    unittest.main()