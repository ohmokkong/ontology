"""
플러그인 시스템 모듈.

이 모듈은 새로운 API 데이터 소스 추가를 위한 인터페이스 정의,
다양한 데이터 형식 변환기 플러그인 시스템,
기존 코드 수정 없이 확장 가능한 구조를 제공합니다.
"""

import os
import importlib
import inspect
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Union, Callable
from pathlib import Path
import json

from exceptions import ConfigurationError, DataProcessingError


class PluginInterface(ABC):
    """플러그인 기본 인터페이스."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """플러그인 이름을 반환합니다."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """플러그인 버전을 반환합니다."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """플러그인 설명을 반환합니다."""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """플러그인을 초기화합니다."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """플러그인 정리 작업을 수행합니다."""
        pass


class APIClientPlugin(PluginInterface):
    """API 클라이언트 플러그인 인터페이스."""
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """데이터를 검색합니다."""
        pass
    
    @abstractmethod
    def get_detail(self, item_id: str, **kwargs) -> Dict[str, Any]:
        """상세 정보를 조회합니다."""
        pass
    
    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """응답 데이터의 유효성을 검증합니다."""
        pass


class DataConverterPlugin(PluginInterface):
    """데이터 변환기 플러그인 인터페이스."""
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """지원하는 데이터 형식 목록을 반환합니다."""
        pass
    
    @abstractmethod
    def convert(self, data: Any, source_format: str, target_format: str, **kwargs) -> Any:
        """데이터를 변환합니다."""
        pass
    
    @abstractmethod
    def validate_input(self, data: Any, format_type: str) -> bool:
        """입력 데이터의 유효성을 검증합니다."""
        pass


class ProcessorPlugin(PluginInterface):
    """데이터 처리기 플러그인 인터페이스."""
    
    @abstractmethod
    def process(self, data: Any, **kwargs) -> Any:
        """데이터를 처리합니다."""
        pass
    
    @abstractmethod
    def can_process(self, data: Any) -> bool:
        """데이터 처리 가능 여부를 확인합니다."""
        pass


class PluginRegistry:
    """플러그인 레지스트리 클래스."""
    
    def __init__(self):
        """PluginRegistry 초기화."""
        self.plugins: Dict[str, Dict[str, PluginInterface]] = {
            'api_client': {},
            'data_converter': {},
            'processor': {}
        }
        self.logger = logging.getLogger(__name__)
    
    def register_plugin(self, plugin_type: str, plugin: PluginInterface) -> None:
        """
        플러그인을 등록합니다.
        
        Args:
            plugin_type: 플러그인 타입 (api_client, data_converter, processor)
            plugin: 플러그인 인스턴스
        """
        if plugin_type not in self.plugins:
            raise ValueError(f"지원하지 않는 플러그인 타입: {plugin_type}")
        
        plugin_name = plugin.name
        if plugin_name in self.plugins[plugin_type]:
            self.logger.warning(f"플러그인 '{plugin_name}'이 이미 등록되어 있습니다. 덮어씁니다.")
        
        self.plugins[plugin_type][plugin_name] = plugin
        self.logger.info(f"플러그인 등록 완료: {plugin_type}.{plugin_name} v{plugin.version}")
    
    def get_plugin(self, plugin_type: str, plugin_name: str) -> Optional[PluginInterface]:
        """
        플러그인을 조회합니다.
        
        Args:
            plugin_type: 플러그인 타입
            plugin_name: 플러그인 이름
            
        Returns:
            Optional[PluginInterface]: 플러그인 인스턴스
        """
        return self.plugins.get(plugin_type, {}).get(plugin_name)
    
    def list_plugins(self, plugin_type: str = None) -> Dict[str, List[str]]:
        """
        등록된 플러그인 목록을 반환합니다.
        
        Args:
            plugin_type: 특정 타입의 플러그인만 조회 (None이면 모든 타입)
            
        Returns:
            Dict[str, List[str]]: 플러그인 타입별 플러그인 이름 목록
        """
        if plugin_type:
            return {plugin_type: list(self.plugins.get(plugin_type, {}).keys())}
        
        return {ptype: list(plugins.keys()) for ptype, plugins in self.plugins.items()}
    
    def unregister_plugin(self, plugin_type: str, plugin_name: str) -> bool:
        """
        플러그인을 등록 해제합니다.
        
        Args:
            plugin_type: 플러그인 타입
            plugin_name: 플러그인 이름
            
        Returns:
            bool: 등록 해제 성공 여부
        """
        if plugin_type in self.plugins and plugin_name in self.plugins[plugin_type]:
            plugin = self.plugins[plugin_type][plugin_name]
            try:
                plugin.cleanup()
            except Exception as e:
                self.logger.warning(f"플러그인 정리 중 오류 발생: {str(e)}")
            
            del self.plugins[plugin_type][plugin_name]
            self.logger.info(f"플러그인 등록 해제 완료: {plugin_type}.{plugin_name}")
            return True
        
        return False


class PluginManager:
    """
    플러그인 매니저 클래스.
    
    플러그인의 로드, 관리, 실행을 담당합니다.
    """
    
    def __init__(self, plugin_dirs: List[str] = None, config: Dict[str, Any] = None):
        """
        PluginManager 초기화.
        
        Args:
            plugin_dirs: 플러그인 디렉토리 목록
            config: 플러그인 설정
        """
        self.plugin_dirs = plugin_dirs or ["plugins"]
        self.config = config or {}
        self.registry = PluginRegistry()
        self.logger = logging.getLogger(__name__)
        
        # 플러그인 디렉토리 생성
        self._ensure_plugin_dirs()
        
        self.logger.info(f"플러그인 매니저 초기화 완료: {len(self.plugin_dirs)}개 디렉토리")
    
    def _ensure_plugin_dirs(self) -> None:
        """플러그인 디렉토리들이 존재하는지 확인하고, 없으면 생성합니다."""
        for plugin_dir in self.plugin_dirs:
            try:
                Path(plugin_dir).mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"플러그인 디렉토리 확인/생성: {plugin_dir}")
            except Exception as e:
                self.logger.warning(f"플러그인 디렉토리 생성 실패: {plugin_dir}, 오류: {str(e)}")
    
    def load_plugins(self) -> None:
        """모든 플러그인 디렉토리에서 플러그인을 로드합니다."""
        self.logger.info("플러그인 로드 시작")
        
        for plugin_dir in self.plugin_dirs:
            self._load_plugins_from_directory(plugin_dir)
        
        loaded_plugins = self.registry.list_plugins()
        total_plugins = sum(len(plugins) for plugins in loaded_plugins.values())
        self.logger.info(f"플러그인 로드 완료: 총 {total_plugins}개 플러그인")
    
    def _load_plugins_from_directory(self, plugin_dir: str) -> None:
        """특정 디렉토리에서 플러그인을 로드합니다."""
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            self.logger.debug(f"플러그인 디렉토리가 존재하지 않습니다: {plugin_dir}")
            return
        
        # Python 파일 검색
        for py_file in plugin_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                self._load_plugin_from_file(py_file)
            except Exception as e:
                self.logger.error(f"플러그인 로드 실패: {py_file}, 오류: {str(e)}")
    
    def _load_plugin_from_file(self, plugin_file: Path) -> None:
        """파일에서 플러그인을 로드합니다."""
        module_name = plugin_file.stem
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        
        if spec is None or spec.loader is None:
            raise ImportError(f"모듈 스펙을 생성할 수 없습니다: {plugin_file}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 플러그인 클래스 검색
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if self._is_plugin_class(obj):
                try:
                    plugin_instance = obj()
                    plugin_type = self._determine_plugin_type(obj)
                    
                    # 플러그인 초기화
                    plugin_config = self.config.get(plugin_instance.name, {})
                    plugin_instance.initialize(plugin_config)
                    
                    # 플러그인 등록
                    self.registry.register_plugin(plugin_type, plugin_instance)
                    
                except Exception as e:
                    self.logger.error(f"플러그인 인스턴스 생성 실패: {name}, 오류: {str(e)}")
    
    def _is_plugin_class(self, cls: Type) -> bool:
        """클래스가 플러그인 클래스인지 확인합니다."""
        return (inspect.isclass(cls) and 
                issubclass(cls, PluginInterface) and 
                cls != PluginInterface and
                not inspect.isabstract(cls))
    
    def _determine_plugin_type(self, cls: Type) -> str:
        """플러그인 클래스의 타입을 결정합니다."""
        if issubclass(cls, APIClientPlugin):
            return 'api_client'
        elif issubclass(cls, DataConverterPlugin):
            return 'data_converter'
        elif issubclass(cls, ProcessorPlugin):
            return 'processor'
        else:
            return 'generic'
    
    def get_api_client(self, name: str) -> Optional[APIClientPlugin]:
        """API 클라이언트 플러그인을 조회합니다."""
        return self.registry.get_plugin('api_client', name)
    
    def get_data_converter(self, name: str) -> Optional[DataConverterPlugin]:
        """데이터 변환기 플러그인을 조회합니다."""
        return self.registry.get_plugin('data_converter', name)
    
    def get_processor(self, name: str) -> Optional[ProcessorPlugin]:
        """데이터 처리기 플러그인을 조회합니다."""
        return self.registry.get_plugin('processor', name)
    
    def find_converter_for_format(self, source_format: str, target_format: str) -> Optional[DataConverterPlugin]:
        """특정 형식 변환을 지원하는 변환기를 찾습니다."""
        converters = self.registry.plugins.get('data_converter', {})
        
        for converter in converters.values():
            if (source_format in converter.supported_formats and 
                target_format in converter.supported_formats):
                return converter
        
        return None
    
    def find_processor_for_data(self, data: Any) -> Optional[ProcessorPlugin]:
        """특정 데이터를 처리할 수 있는 처리기를 찾습니다."""
        processors = self.registry.plugins.get('processor', {})
        
        for processor in processors.values():
            if processor.can_process(data):
                return processor
        
        return None
    
    def execute_api_search(self, api_name: str, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        API 클라이언트 플러그인을 사용하여 검색을 실행합니다.
        
        Args:
            api_name: API 클라이언트 이름
            query: 검색 쿼리
            **kwargs: 추가 매개변수
            
        Returns:
            List[Dict[str, Any]]: 검색 결과
        """
        api_client = self.get_api_client(api_name)
        if not api_client:
            raise ValueError(f"API 클라이언트를 찾을 수 없습니다: {api_name}")
        
        try:
            results = api_client.search(query, **kwargs)
            self.logger.debug(f"API 검색 완료: {api_name}, 결과 수: {len(results)}")
            return results
        except Exception as e:
            self.logger.error(f"API 검색 실패: {api_name}, 오류: {str(e)}")
            raise DataProcessingError(f"API 검색 실패: {str(e)}")
    
    def convert_data(self, data: Any, source_format: str, target_format: str, 
                    converter_name: str = None, **kwargs) -> Any:
        """
        데이터 변환기 플러그인을 사용하여 데이터를 변환합니다.
        
        Args:
            data: 변환할 데이터
            source_format: 원본 형식
            target_format: 대상 형식
            converter_name: 사용할 변환기 이름 (None이면 자동 선택)
            **kwargs: 추가 매개변수
            
        Returns:
            Any: 변환된 데이터
        """
        if converter_name:
            converter = self.get_data_converter(converter_name)
        else:
            converter = self.find_converter_for_format(source_format, target_format)
        
        if not converter:
            raise ValueError(f"데이터 변환기를 찾을 수 없습니다: {source_format} -> {target_format}")
        
        try:
            if not converter.validate_input(data, source_format):
                raise ValueError(f"입력 데이터가 유효하지 않습니다: {source_format}")
            
            result = converter.convert(data, source_format, target_format, **kwargs)
            self.logger.debug(f"데이터 변환 완료: {source_format} -> {target_format}")
            return result
        except Exception as e:
            self.logger.error(f"데이터 변환 실패: {str(e)}")
            raise DataProcessingError(f"데이터 변환 실패: {str(e)}")
    
    def process_data(self, data: Any, processor_name: str = None, **kwargs) -> Any:
        """
        데이터 처리기 플러그인을 사용하여 데이터를 처리합니다.
        
        Args:
            data: 처리할 데이터
            processor_name: 사용할 처리기 이름 (None이면 자동 선택)
            **kwargs: 추가 매개변수
            
        Returns:
            Any: 처리된 데이터
        """
        if processor_name:
            processor = self.get_processor(processor_name)
        else:
            processor = self.find_processor_for_data(data)
        
        if not processor:
            raise ValueError("적절한 데이터 처리기를 찾을 수 없습니다.")
        
        try:
            result = processor.process(data, **kwargs)
            self.logger.debug(f"데이터 처리 완료: {processor.name}")
            return result
        except Exception as e:
            self.logger.error(f"데이터 처리 실패: {str(e)}")
            raise DataProcessingError(f"데이터 처리 실패: {str(e)}")
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """플러그인 정보를 반환합니다."""
        info = {
            'plugin_dirs': self.plugin_dirs,
            'loaded_plugins': {},
            'total_plugins': 0
        }
        
        for plugin_type, plugins in self.registry.plugins.items():
            plugin_info = []
            for plugin_name, plugin in plugins.items():
                plugin_info.append({
                    'name': plugin.name,
                    'version': plugin.version,
                    'description': plugin.description
                })
            
            info['loaded_plugins'][plugin_type] = plugin_info
            info['total_plugins'] += len(plugin_info)
        
        return info
    
    def create_plugin_template(self, plugin_type: str, plugin_name: str, output_dir: str = "plugins") -> str:
        """
        플러그인 템플릿을 생성합니다.
        
        Args:
            plugin_type: 플러그인 타입 (api_client, data_converter, processor)
            plugin_name: 플러그인 이름
            output_dir: 출력 디렉토리
            
        Returns:
            str: 생성된 템플릿 파일 경로
        """
        templates = {
            'api_client': self._get_api_client_template(plugin_name),
            'data_converter': self._get_data_converter_template(plugin_name),
            'processor': self._get_processor_template(plugin_name)
        }
        
        if plugin_type not in templates:
            raise ValueError(f"지원하지 않는 플러그인 타입: {plugin_type}")
        
        template_content = templates[plugin_type]
        output_path = Path(output_dir) / f"{plugin_name}_plugin.py"
        
        # 출력 디렉토리 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 템플릿 파일 생성
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        self.logger.info(f"플러그인 템플릿 생성 완료: {output_path}")
        return str(output_path)
    
    def _get_api_client_template(self, plugin_name: str) -> str:
        """API 클라이언트 플러그인 템플릿을 반환합니다."""
        class_name = ''.join(word.capitalize() for word in plugin_name.split('_'))
        
        return f'''"""
{plugin_name} API 클라이언트 플러그인.
"""

from typing import Dict, Any, List
from plugin_system import APIClientPlugin


class {class_name}APIClient(APIClientPlugin):
    """
    {plugin_name} API 클라이언트 플러그인.
    """
    
    @property
    def name(self) -> str:
        return "{plugin_name}"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "{plugin_name} API 클라이언트"
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """플러그인을 초기화합니다."""
        self.config = config
        self.base_url = config.get('base_url', '')
        self.api_key = config.get('api_key', '')
        
        # TODO: API 클라이언트 초기화 로직 구현
    
    def cleanup(self) -> None:
        """플러그인 정리 작업을 수행합니다."""
        # TODO: 정리 작업 구현
        pass
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """데이터를 검색합니다."""
        # TODO: 검색 로직 구현
        return []
    
    def get_detail(self, item_id: str, **kwargs) -> Dict[str, Any]:
        """상세 정보를 조회합니다."""
        # TODO: 상세 정보 조회 로직 구현
        return {{}}
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """응답 데이터의 유효성을 검증합니다."""
        # TODO: 응답 검증 로직 구현
        return True
'''
    
    def _get_data_converter_template(self, plugin_name: str) -> str:
        """데이터 변환기 플러그인 템플릿을 반환합니다."""
        class_name = ''.join(word.capitalize() for word in plugin_name.split('_'))
        
        return f'''"""
{plugin_name} 데이터 변환기 플러그인.
"""

from typing import Dict, Any, List
from plugin_system import DataConverterPlugin


class {class_name}Converter(DataConverterPlugin):
    """
    {plugin_name} 데이터 변환기 플러그인.
    """
    
    @property
    def name(self) -> str:
        return "{plugin_name}"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "{plugin_name} 데이터 변환기"
    
    @property
    def supported_formats(self) -> List[str]:
        return ["json", "xml", "csv"]  # TODO: 지원하는 형식 정의
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """플러그인을 초기화합니다."""
        self.config = config
        # TODO: 변환기 초기화 로직 구현
    
    def cleanup(self) -> None:
        """플러그인 정리 작업을 수행합니다."""
        # TODO: 정리 작업 구현
        pass
    
    def convert(self, data: Any, source_format: str, target_format: str, **kwargs) -> Any:
        """데이터를 변환합니다."""
        # TODO: 데이터 변환 로직 구현
        return data
    
    def validate_input(self, data: Any, format_type: str) -> bool:
        """입력 데이터의 유효성을 검증합니다."""
        # TODO: 입력 검증 로직 구현
        return True
'''
    
    def _get_processor_template(self, plugin_name: str) -> str:
        """데이터 처리기 플러그인 템플릿을 반환합니다."""
        class_name = ''.join(word.capitalize() for word in plugin_name.split('_'))
        
        return f'''"""
{plugin_name} 데이터 처리기 플러그인.
"""

from typing import Dict, Any
from plugin_system import ProcessorPlugin


class {class_name}Processor(ProcessorPlugin):
    """
    {plugin_name} 데이터 처리기 플러그인.
    """
    
    @property
    def name(self) -> str:
        return "{plugin_name}"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "{plugin_name} 데이터 처리기"
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """플러그인을 초기화합니다."""
        self.config = config
        # TODO: 처리기 초기화 로직 구현
    
    def cleanup(self) -> None:
        """플러그인 정리 작업을 수행합니다."""
        # TODO: 정리 작업 구현
        pass
    
    def process(self, data: Any, **kwargs) -> Any:
        """데이터를 처리합니다."""
        # TODO: 데이터 처리 로직 구현
        return data
    
    def can_process(self, data: Any) -> bool:
        """데이터 처리 가능 여부를 확인합니다."""
        # TODO: 처리 가능 여부 확인 로직 구현
        return True
'''


# 전역 플러그인 매니저 인스턴스
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """전역 플러그인 매니저 인스턴스를 반환합니다."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager