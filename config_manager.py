"""
설정 관리 시스템 모듈.

이 모듈은 API 엔드포인트 및 매개변수 설정 파일 관리,
환경별 설정 분리, 설정 변경 시 동적 로드 기능을 제공합니다.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
import threading

from exceptions import ConfigurationError, EnvironmentError


# 파일 감시 기능은 선택적으로 구현 (watchdog 의존성 제거)


class ConfigManager:
    """
    설정 관리 시스템 클래스.
    
    API 엔드포인트 및 매개변수 설정 파일 관리,
    환경별 설정 분리, 설정 변경 시 동적 로드 기능을 제공합니다.
    """
    
    def __init__(self, 
                 config_dir: str = "config",
                 environment: str = None,
                 auto_reload: bool = True):
        """
        ConfigManager 초기화.
        
        Args:
            config_dir: 설정 파일 디렉토리 경로
            environment: 환경 설정 (development, production 등)
            auto_reload: 자동 재로드 활성화 여부
        """
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.auto_reload = auto_reload
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # 설정 데이터 저장소
        self.config_data = {}
        self.watched_files = set()
        
        # 스레드 락
        self._lock = threading.RLock()
        
        # 설정 디렉토리 생성
        self._ensure_config_dir()
        
        # 초기 설정 로드
        self.load_config()
        
        self.logger.info(f"설정 매니저 초기화 완료: 환경={self.environment}, 자동재로드={self.auto_reload}")
    
    def _ensure_config_dir(self) -> None:
        """설정 디렉토리가 존재하는지 확인하고, 없으면 생성합니다."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"설정 디렉토리 확인/생성 완료: {self.config_dir}")
        except Exception as e:
            error_msg = f"설정 디렉토리 생성 실패: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def _setup_file_watcher(self) -> None:
        """파일 감시자를 설정합니다. (현재 구현에서는 비활성화)"""
        self.logger.info("파일 감시자 기능은 현재 비활성화되어 있습니다.")
    
    def load_config(self) -> None:
        """설정 파일들을 로드합니다."""
        with self._lock:
            self.logger.info("설정 파일 로드 시작")
            
            # 기본 설정 파일들 (JSON만 지원)
            config_files = [
                "default.json",
                f"{self.environment}.json",
                "local.json"
            ]
            
            # 설정 데이터 초기화
            self.config_data = {}
            self.watched_files.clear()
            
            # 각 설정 파일 로드
            for config_file in config_files:
                config_path = self.config_dir / config_file
                if config_path.exists():
                    try:
                        config_data = self._load_config_file(config_path)
                        self._merge_config(self.config_data, config_data)
                        self.watched_files.add(str(config_path))
                        self.logger.debug(f"설정 파일 로드 완료: {config_path}")
                    except Exception as e:
                        self.logger.error(f"설정 파일 로드 실패: {config_path}, 오류: {str(e)}")
            
            # 환경 변수로 설정 오버라이드
            self._load_environment_variables()
            
            self.logger.info(f"설정 로드 완료: {len(self.config_data)}개 설정 항목")
    
    def _load_config_file(self, config_path: Path) -> Dict[str, Any]:
        """개별 설정 파일을 로드합니다."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    raise ConfigurationError(f"지원하지 않는 설정 파일 형식: {config_path.suffix}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"JSON 파싱 오류: {config_path}, {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"설정 파일 읽기 오류: {config_path}, {str(e)}")
    
    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """설정 데이터를 병합합니다."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
    
    def _load_environment_variables(self) -> None:
        """환경 변수로 설정을 오버라이드합니다."""
        # API 관련 환경 변수
        env_mappings = {
            'FOOD_API_KEY': 'api.food.key',
            'FOOD_API_URL': 'api.food.base_url',
            'EXERCISE_API_KEY': 'api.exercise.key',
            'EXERCISE_API_URL': 'api.exercise.base_url',
            'API_TIMEOUT': 'api.timeout',
            'API_RETRY_COUNT': 'api.retry_count',
            'CACHE_TTL': 'cache.ttl',
            'LOG_LEVEL': 'logging.level',
            'DATABASE_URL': 'database.url'
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self._set_nested_config(config_path, env_value)
                self.logger.debug(f"환경 변수 설정 적용: {env_var} -> {config_path}")
    
    def _set_nested_config(self, path: str, value: Any) -> None:
        """중첩된 설정 경로에 값을 설정합니다."""
        keys = path.split('.')
        current = self.config_data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 타입 변환 시도
        final_key = keys[-1]
        if isinstance(value, str):
            # 숫자 변환 시도
            if value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
            # 불린 변환 시도
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
        
        current[final_key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        설정 값을 조회합니다.
        
        Args:
            key: 설정 키 (점으로 구분된 중첩 경로 지원)
            default: 기본값
            
        Returns:
            Any: 설정 값
        """
        with self._lock:
            keys = key.split('.')
            current = self.config_data
            
            try:
                for k in keys:
                    current = current[k]
                return current
            except (KeyError, TypeError):
                return default
    
    def set(self, key: str, value: Any) -> None:
        """
        설정 값을 설정합니다.
        
        Args:
            key: 설정 키 (점으로 구분된 중첩 경로 지원)
            value: 설정 값
        """
        with self._lock:
            self._set_nested_config(key, value)
            self.logger.debug(f"설정 값 변경: {key} = {value}")
    
    def get_api_config(self, api_name: str) -> Dict[str, Any]:
        """
        특정 API의 설정을 조회합니다.
        
        Args:
            api_name: API 이름 (food, exercise 등)
            
        Returns:
            Dict[str, Any]: API 설정
        """
        api_config = self.get(f'api.{api_name}', {})
        
        # 기본 API 설정과 병합
        default_api_config = self.get('api.default', {})
        merged_config = default_api_config.copy()
        merged_config.update(api_config)
        
        return merged_config
    
    def get_database_config(self) -> Dict[str, Any]:
        """데이터베이스 설정을 조회합니다."""
        return self.get('database', {})
    
    def get_cache_config(self) -> Dict[str, Any]:
        """캐시 설정을 조회합니다."""
        return self.get('cache', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 설정을 조회합니다."""
        return self.get('logging', {})
    
    def reload_config(self) -> None:
        """설정을 다시 로드합니다."""
        self.logger.info("설정 재로드 시작")
        try:
            self.load_config()
            self.logger.info("설정 재로드 완료")
        except Exception as e:
            error_msg = f"설정 재로드 실패: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def save_config(self, config_name: str = None) -> None:
        """
        현재 설정을 파일로 저장합니다.
        
        Args:
            config_name: 저장할 설정 파일명 (기본값: 현재 환경)
        """
        if config_name is None:
            config_name = f"{self.environment}.json"
        
        config_path = self.config_dir / config_name
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"설정 저장 완료: {config_path}")
        except Exception as e:
            error_msg = f"설정 저장 실패: {str(e)}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def create_default_config(self) -> None:
        """기본 설정 파일을 생성합니다."""
        default_config = {
            "api": {
                "default": {
                    "timeout": 30,
                    "retry_count": 3,
                    "retry_delay": 1.0,
                    "max_concurrent_requests": 10
                },
                "food": {
                    "base_url": "https://apis.data.go.kr/1471000/FoodNtrIrdntInfoService1",
                    "key": "YOUR_FOOD_API_KEY",
                    "endpoints": {
                        "search": "/getFoodNtrItdntList1",
                        "detail": "/getFoodNtrItdntList1"
                    },
                    "params": {
                        "serviceKey": "{key}",
                        "type": "json",
                        "numOfRows": 100,
                        "pageNo": 1
                    }
                },
                "exercise": {
                    "base_url": "https://apis.data.go.kr/B551011/KorService1",
                    "key": "YOUR_EXERCISE_API_KEY",
                    "endpoints": {
                        "search": "/searchKeyword1",
                        "detail": "/detailCommon1"
                    },
                    "params": {
                        "serviceKey": "{key}",
                        "MobileOS": "ETC",
                        "MobileApp": "DietApp",
                        "_type": "json",
                        "numOfRows": 100,
                        "pageNo": 1
                    }
                }
            },
            "cache": {
                "enabled": True,
                "ttl": 3600,
                "max_size": 1000,
                "cleanup_interval": 300
            },
            "database": {
                "type": "sqlite",
                "path": "data/diet_app.db",
                "pool_size": 5,
                "timeout": 30
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/app.log",
                "max_size": "10MB",
                "backup_count": 5
            },
            "ontology": {
                "base_file": "diet-ontology.ttl",
                "output_dir": "ontology_output",
                "backup_enabled": True,
                "validation_enabled": True
            },
            "features": {
                "auto_backup": True,
                "schema_validation": True,
                "performance_monitoring": True,
                "debug_mode": False
            }
        }
        
        # 개발 환경 설정
        dev_config = {
            "api": {
                "default": {
                    "timeout": 10,
                    "retry_count": 1
                }
            },
            "logging": {
                "level": "DEBUG"
            },
            "features": {
                "debug_mode": True
            }
        }
        
        # 운영 환경 설정
        prod_config = {
            "api": {
                "default": {
                    "timeout": 60,
                    "retry_count": 5,
                    "max_concurrent_requests": 20
                }
            },
            "cache": {
                "ttl": 7200,
                "max_size": 5000
            },
            "logging": {
                "level": "WARNING"
            },
            "features": {
                "debug_mode": False,
                "performance_monitoring": True
            }
        }
        
        # 설정 파일들 생성
        configs = [
            ("default.json", default_config),
            ("development.json", dev_config),
            ("production.json", prod_config)
        ]
        
        for filename, config in configs:
            config_path = self.config_dir / filename
            if not config_path.exists():
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"기본 설정 파일 생성: {config_path}")
                except Exception as e:
                    self.logger.error(f"설정 파일 생성 실패: {config_path}, 오류: {str(e)}")
    
    def validate_config(self) -> Dict[str, Union[bool, List[str]]]:
        """
        설정의 유효성을 검증합니다.
        
        Returns:
            Dict: 검증 결과
        """
        errors = []
        warnings = []
        
        try:
            # API 설정 검증
            api_config = self.get('api', {})
            if not api_config:
                errors.append("API 설정이 없습니다.")
            else:
                # 필수 API 설정 확인
                required_apis = ['food', 'exercise']
                for api_name in required_apis:
                    api_settings = api_config.get(api_name, {})
                    if not api_settings:
                        warnings.append(f"{api_name} API 설정이 없습니다.")
                    else:
                        # API 키 확인
                        api_key = api_settings.get('key', '')
                        if not api_key or api_key.startswith('YOUR_'):
                            warnings.append(f"{api_name} API 키가 설정되지 않았습니다.")
                        
                        # 기본 URL 확인
                        base_url = api_settings.get('base_url', '')
                        if not base_url:
                            errors.append(f"{api_name} API 기본 URL이 설정되지 않았습니다.")
            
            # 캐시 설정 검증
            cache_config = self.get('cache', {})
            if cache_config:
                ttl = cache_config.get('ttl', 0)
                if ttl <= 0:
                    warnings.append("캐시 TTL이 0 이하로 설정되어 있습니다.")
                
                max_size = cache_config.get('max_size', 0)
                if max_size <= 0:
                    warnings.append("캐시 최대 크기가 0 이하로 설정되어 있습니다.")
            
            # 로깅 설정 검증
            logging_config = self.get('logging', {})
            if logging_config:
                log_level = logging_config.get('level', '').upper()
                valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                if log_level not in valid_levels:
                    warnings.append(f"유효하지 않은 로그 레벨: {log_level}")
            
            is_valid = len(errors) == 0
            
            self.logger.info(f"설정 검증 완료: 유효={is_valid}, 오류={len(errors)}, 경고={len(warnings)}")
            
            return {
                'is_valid': is_valid,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            error_msg = f"설정 검증 중 오류 발생: {str(e)}"
            self.logger.error(error_msg)
            return {
                'is_valid': False,
                'errors': [error_msg],
                'warnings': warnings
            }
    
    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 정보를 반환합니다."""
        return {
            'environment': self.environment,
            'config_dir': str(self.config_dir),
            'auto_reload': self.auto_reload,
            'watched_files': list(self.watched_files),
            'config_keys': list(self.config_data.keys()),
            'total_settings': len(self._flatten_dict(self.config_data))
        }
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """중첩된 딕셔너리를 평면화합니다."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def __del__(self):
        """소멸자."""
        pass


# 전역 설정 매니저 인스턴스
_config_manager = None


def get_config_manager() -> ConfigManager:
    """전역 설정 매니저 인스턴스를 반환합니다."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """설정 값을 조회하는 편의 함수."""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any) -> None:
    """설정 값을 설정하는 편의 함수."""
    get_config_manager().set(key, value)