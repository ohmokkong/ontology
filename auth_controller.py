"""
API 인증 및 키 관리 컨트롤러.

식약처 식품영양성분 API와 한국건강증진개발원 운동 API의 
인증 키를 관리하고 검증하는 기능을 제공합니다.
"""

import os
import json
from typing import Dict, Optional, Any
from pathlib import Path
from exceptions import (
    APIKeyError, EnvironmentError, InvalidAPIKeyError,
    ConfigurationError, FileSystemError
)


class AuthController:
    """
    API 인증 및 키 관리 컨트롤러.
    
    환경변수, 설정파일, 직접 입력을 통해 API 키를 로드하고 관리합니다.
    """
    
    def __init__(self, config_file_path: Optional[str] = None):
        """
        AuthController 초기화.
        
        Args:
            config_file_path: 설정 파일 경로 (기본값: config.json)
        """
        self.config_file_path = config_file_path or "config.json"
        self.api_keys: Dict[str, str] = {}
        self.config_data: Dict[str, Any] = {}
        
        # 지원하는 API 목록
        self.supported_apis = {
            "food_api": {
                "name": "식약처 식품영양성분 API",
                "env_var": "FOOD_API_KEY",
                "config_key": "food_api_key"
            },
            "exercise_api": {
                "name": "한국건강증진개발원 운동 API", 
                "env_var": "EXERCISE_API_KEY",
                "config_key": "exercise_api_key"
            }
        }
    
    def load_api_keys(self) -> Dict[str, str]:
        """
        모든 API 키를 로드합니다.
        
        우선순위: 환경변수 > 설정파일 > 직접입력
        
        Returns:
            Dict[str, str]: API 이름과 키의 매핑
            
        Raises:
            APIKeyError: API 키 로드 실패 시
        """
        try:
            # 1. 환경변수에서 로드
            self._load_from_environment()
            
            # 2. 설정파일에서 로드 (환경변수에 없는 것만)
            self._load_from_config_file()
            
            # 3. 누락된 키 확인
            missing_keys = self._check_missing_keys()
            
            if missing_keys:
                raise APIKeyError(
                    f"다음 API 키가 누락되었습니다: {', '.join(missing_keys)}",
                    f"환경변수 또는 {self.config_file_path} 파일에 설정해주세요."
                )
            
            return self.api_keys.copy()
            
        except Exception as e:
            if isinstance(e, APIKeyError):
                raise
            raise APIKeyError(f"API 키 로드 중 오류 발생: {str(e)}")
    
    def _load_from_environment(self) -> None:
        """환경변수에서 API 키 로드."""
        for api_name, api_info in self.supported_apis.items():
            env_var = api_info["env_var"]
            api_key = os.getenv(env_var)
            
            if api_key and api_key.strip():
                self.api_keys[api_name] = api_key.strip()
                print(f"✓ {api_info['name']} 키를 환경변수에서 로드했습니다.")
    
    def _load_from_config_file(self) -> None:
        """설정파일에서 API 키 로드."""
        if not Path(self.config_file_path).exists():
            print(f"설정파일 {self.config_file_path}이 없습니다. 환경변수만 사용합니다.")
            return
        
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            for api_name, api_info in self.supported_apis.items():
                # 환경변수에서 이미 로드된 경우 건너뛰기
                if api_name in self.api_keys:
                    continue
                
                config_key = api_info["config_key"]
                api_key = self.config_data.get(config_key)
                
                if api_key and str(api_key).strip():
                    self.api_keys[api_name] = str(api_key).strip()
                    print(f"✓ {api_info['name']} 키를 설정파일에서 로드했습니다.")
        
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"설정파일 JSON 형식 오류: {str(e)}")
        except Exception as e:
            raise FileSystemError(f"설정파일 읽기 오류: {str(e)}")
    
    def _check_missing_keys(self) -> list:
        """누락된 API 키 확인."""
        missing = []
        for api_name, api_info in self.supported_apis.items():
            if api_name not in self.api_keys:
                missing.append(api_info["name"])
        return missing
    
    def get_api_key(self, api_name: str) -> str:
        """
        특정 API의 키를 반환합니다.
        
        Args:
            api_name: API 이름 ('food_api' 또는 'exercise_api')
            
        Returns:
            str: API 키
            
        Raises:
            APIKeyError: API 키가 없거나 유효하지 않은 경우
        """
        if api_name not in self.supported_apis:
            raise APIKeyError(f"지원하지 않는 API입니다: {api_name}")
        
        if api_name not in self.api_keys:
            api_info = self.supported_apis[api_name]
            raise APIKeyError(
                f"{api_info['name']} 키가 설정되지 않았습니다.",
                f"환경변수 {api_info['env_var']} 또는 설정파일에 {api_info['config_key']}를 설정해주세요."
            )
        
        return self.api_keys[api_name]
    
    def validate_credentials(self, api_name: str) -> bool:
        """
        API 키의 기본적인 형식을 검증합니다.
        
        Args:
            api_name: API 이름
            
        Returns:
            bool: 검증 성공 여부
            
        Raises:
            InvalidAPIKeyError: API 키가 유효하지 않은 경우
        """
        try:
            api_key = self.get_api_key(api_name)
            
            # 기본적인 형식 검증
            if len(api_key) < 10:
                raise InvalidAPIKeyError(f"{api_name} API 키가 너무 짧습니다 (최소 10자)")
            
            if not api_key.replace('-', '').replace('_', '').isalnum():
                raise InvalidAPIKeyError(f"{api_name} API 키에 허용되지 않는 문자가 포함되어 있습니다")
            
            # API별 특별한 검증 규칙
            if api_name == "food_api":
                # 식약처 API 키 형식 검증 (예시)
                if not (20 <= len(api_key) <= 50):
                    raise InvalidAPIKeyError("식약처 API 키는 20-50자 사이여야 합니다")
            
            elif api_name == "exercise_api":
                # 건강증진원 API 키 형식 검증 (예시)
                if not (15 <= len(api_key) <= 40):
                    raise InvalidAPIKeyError("운동 API 키는 15-40자 사이여야 합니다")
            
            return True
            
        except APIKeyError:
            raise
        except Exception as e:
            raise InvalidAPIKeyError(f"API 키 검증 중 오류 발생: {str(e)}")
    
    def handle_auth_error(self, error: Exception, api_name: str) -> str:
        """
        인증 오류에 대한 사용자 친화적인 메시지를 생성합니다.
        
        Args:
            error: 발생한 오류
            api_name: API 이름
            
        Returns:
            str: 사용자 친화적인 오류 메시지
        """
        api_info = self.supported_apis.get(api_name, {})
        api_display_name = api_info.get("name", api_name)
        
        if isinstance(error, APIKeyError):
            return f"""
{api_display_name} 인증 오류가 발생했습니다.

문제: {str(error)}

해결 방법:
1. 환경변수 설정: {api_info.get('env_var', 'API_KEY')}=your_api_key
2. 설정파일 생성: {self.config_file_path}
   {{
     "{api_info.get('config_key', 'api_key')}": "your_api_key"
   }}
3. API 키 재발급 확인

도움말: API 키는 해당 기관의 공식 웹사이트에서 발급받을 수 있습니다.
"""
        
        elif isinstance(error, InvalidAPIKeyError):
            return f"""
{api_display_name} API 키가 유효하지 않습니다.

문제: {str(error)}

해결 방법:
1. API 키 형식 확인
2. 새로운 API 키 재발급
3. 키에 특수문자나 공백이 포함되지 않았는지 확인

현재 설정된 키: {self.api_keys.get(api_name, '없음')[:10]}...
"""
        
        else:
            return f"""
{api_display_name} 인증 처리 중 예상치 못한 오류가 발생했습니다.

오류: {str(error)}

해결 방법:
1. 네트워크 연결 확인
2. API 서비스 상태 확인
3. 잠시 후 다시 시도
"""
    
    def refresh_token_if_needed(self, api_name: str) -> bool:
        """
        필요시 토큰을 새로고침합니다.
        
        현재는 기본 구현으로, 향후 OAuth 등이 필요한 경우 확장 가능합니다.
        
        Args:
            api_name: API 이름
            
        Returns:
            bool: 새로고침 성공 여부
        """
        # 현재는 정적 API 키를 사용하므로 새로고침이 필요하지 않음
        # 향후 OAuth 토큰 등을 지원할 때 구현
        return True
    
    def create_sample_config(self) -> None:
        """
        샘플 설정파일을 생성합니다.
        """
        sample_config = {
            "food_api_key": "your_food_api_key_here",
            "exercise_api_key": "your_exercise_api_key_here",
            "api_endpoints": {
                "food_api_base_url": "https://openapi.foodsafetykorea.go.kr/api",
                "exercise_api_base_url": "https://openapi.k-health.or.kr/api"
            },
            "settings": {
                "timeout": 30,
                "retry_count": 3,
                "cache_ttl": 3600
            }
        }
        
        try:
            with open(f"{self.config_file_path}.sample", 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            
            print(f"✓ 샘플 설정파일을 생성했습니다: {self.config_file_path}.sample")
            print("이 파일을 참고하여 실제 설정파일을 만들어주세요.")
            
        except Exception as e:
            raise FileSystemError(f"샘플 설정파일 생성 실패: {str(e)}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        설정파일에서 값을 가져옵니다.
        
        Args:
            key: 설정 키
            default: 기본값
            
        Returns:
            Any: 설정값
        """
        return self.config_data.get(key, default)
    
    def list_configured_apis(self) -> Dict[str, Dict[str, str]]:
        """
        설정된 API 목록을 반환합니다.
        
        Returns:
            Dict: API 정보 딕셔너리
        """
        result = {}
        for api_name, api_info in self.supported_apis.items():
            result[api_name] = {
                "name": api_info["name"],
                "configured": api_name in self.api_keys,
                "source": "환경변수" if os.getenv(api_info["env_var"]) else "설정파일" if api_name in self.api_keys else "없음"
            }
        return result