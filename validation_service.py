"""
API 등록 관리 시스템의 검증 서비스.

API 자격증명, 설정, URL 등의 유효성을 검증하고
제공업체별 검증 규칙을 관리합니다.
"""

import re
import json
import urllib.parse
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import ipaddress

from api_registration_models import (
    APIProvider, ValidationResult as ValidationResultEnum, AuthType
)
from exceptions import (
    RegistrationValidationError, ProviderNotSupportedError,
    ConfigurationError
)


@dataclass
class ValidationResult:
    """검증 결과 상세 정보"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    field_results: Dict[str, bool]
    suggestions: List[str]
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not hasattr(self, 'suggestions'):
            self.suggestions = []
    
    def add_error(self, field: str, message: str, suggestion: str = None) -> None:
        """필드 오류 추가"""
        self.errors.append(f"{field}: {message}")
        self.field_results[field] = False
        self.valid = False
        
        if suggestion:
            self.suggestions.append(f"{field}: {suggestion}")
    
    def add_warning(self, field: str, message: str, suggestion: str = None) -> None:
        """필드 경고 추가"""
        self.warnings.append(f"{field}: {message}")
        
        if suggestion:
            self.suggestions.append(f"{field}: {suggestion}")
    
    def is_field_valid(self, field: str) -> bool:
        """특정 필드 유효성 확인"""
        return self.field_results.get(field, True)
    
    def get_error_count(self) -> int:
        """오류 개수 반환"""
        return len(self.errors)
    
    def get_warning_count(self) -> int:
        """경고 개수 반환"""
        return len(self.warnings)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "field_results": self.field_results,
            "suggestions": self.suggestions,
            "error_count": self.get_error_count(),
            "warning_count": self.get_warning_count()
        }


class ValidationService:
    """
    API 자격증명 및 설정 검증 서비스.
    
    제공업체별 검증 규칙을 적용하여 API 자격증명, 엔드포인트 URL,
    설정 등의 유효성을 검증합니다.
    """
    
    def __init__(self):
        """검증 서비스 초기화"""
        self.validation_rules = self._load_default_validation_rules()
        self.url_schemes = ['http', 'https']
        self.reserved_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
    
    def _load_default_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """기본 검증 규칙 로드"""
        return {
            "food_safety_korea": {
                "api_key": {
                    "required": True,
                    "min_length": 20,
                    "max_length": 50,
                    "pattern": r"^[A-Za-z0-9]+$",
                    "description": "식약처 API 키는 20-50자의 영숫자여야 합니다"
                }
            },
            "k_health_exercise": {
                "api_key": {
                    "required": True,
                    "min_length": 15,
                    "max_length": 40,
                    "pattern": r"^[A-Za-z0-9\-_]+$",
                    "description": "건강증진원 API 키는 15-40자의 영숫자, 하이픈, 언더스코어여야 합니다"
                }
            },
            "generic_api_key": {
                "api_key": {
                    "required": True,
                    "min_length": 8,
                    "max_length": 100,
                    "pattern": r"^[A-Za-z0-9\-_\.]+$",
                    "description": "API 키는 8-100자의 영숫자, 하이픈, 언더스코어, 점이어야 합니다"
                }
            },
            "oauth": {
                "client_id": {
                    "required": True,
                    "min_length": 8,
                    "max_length": 100,
                    "description": "클라이언트 ID는 8-100자여야 합니다"
                },
                "client_secret": {
                    "required": True,
                    "min_length": 16,
                    "max_length": 200,
                    "description": "클라이언트 시크릿은 16-200자여야 합니다"
                }
            },
            "basic_auth": {
                "username": {
                    "required": True,
                    "min_length": 1,
                    "max_length": 100,
                    "pattern": r"^[A-Za-z0-9@\.\-_]+$",
                    "description": "사용자명은 1-100자의 영숫자, @, 점, 하이픈, 언더스코어여야 합니다"
                },
                "password": {
                    "required": True,
                    "min_length": 1,
                    "max_length": 200,
                    "description": "패스워드는 1-200자여야 합니다"
                }
            }
        }
    
    def validate_api_credentials(self, provider: APIProvider, 
                               credentials: Dict[str, str]) -> ValidationResult:
        """API 자격증명 검증"""
        result = ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            field_results={},
            suggestions=[]
        )
        
        try:
            rules = self._get_provider_validation_rules(provider)
            self._validate_required_fields(provider, credentials, rules, result)
            
            for field_name, field_value in credentials.items():
                if field_name in rules:
                    self._validate_field(field_name, field_value, rules[field_name], result)
                else:
                    result.add_warning(
                        field_name, 
                        "알 수 없는 필드입니다",
                        "제공업체 문서를 확인하여 올바른 필드명인지 확인하세요"
                    )
            
            self._validate_auth_type_specific(provider.auth_type, credentials, result)
            self._validate_security_requirements(credentials, result)
            
        except Exception as e:
            result.add_error("validation", f"검증 중 오류 발생: {str(e)}")
        
        return result
    
    def _get_provider_validation_rules(self, provider: APIProvider) -> Dict[str, Any]:
        """제공업체별 검증 규칙 가져오기"""
        if provider.name in self.validation_rules:
            return self.validation_rules[provider.name]
        
        auth_type_rules = {
            AuthType.API_KEY: "generic_api_key",
            AuthType.OAUTH: "oauth",
            AuthType.BASIC_AUTH: "basic_auth"
        }
        
        rule_key = auth_type_rules.get(provider.auth_type, "generic_api_key")
        return self.validation_rules.get(rule_key, {})
    
    def _validate_required_fields(self, provider: APIProvider, credentials: Dict[str, str],
                                rules: Dict[str, Any], result: ValidationResult) -> None:
        """필수 필드 검증"""
        for field_name in provider.required_fields:
            if field_name not in credentials or not credentials[field_name]:
                result.add_error(
                    field_name,
                    "필수 필드가 누락되었습니다",
                    f"{field_name} 값을 입력해주세요"
                )
        
        for field_name, field_rules in rules.items():
            if field_rules.get("required", False):
                if field_name not in credentials or not credentials[field_name]:
                    result.add_error(
                        field_name,
                        "필수 필드가 누락되었습니다",
                        field_rules.get("description", f"{field_name} 값을 입력해주세요")
                    )
    
    def _validate_field(self, field_name: str, field_value: str,
                       field_rules: Dict[str, Any], result: ValidationResult) -> None:
        """개별 필드 검증"""
        if not field_value:
            return
        
        if "min_length" in field_rules:
            if len(field_value) < field_rules["min_length"]:
                result.add_error(
                    field_name,
                    f"최소 {field_rules['min_length']}자 이상이어야 합니다 (현재: {len(field_value)}자)",
                    field_rules.get("description", "")
                )
        
        if "max_length" in field_rules:
            if len(field_value) > field_rules["max_length"]:
                result.add_error(
                    field_name,
                    f"최대 {field_rules['max_length']}자 이하여야 합니다 (현재: {len(field_value)}자)",
                    field_rules.get("description", "")
                )
        
        if "pattern" in field_rules:
            try:
                if not re.match(field_rules["pattern"], field_value):
                    result.add_error(
                        field_name,
                        "형식이 올바르지 않습니다",
                        field_rules.get("description", "올바른 형식으로 입력해주세요")
                    )
            except re.error as e:
                result.add_warning(
                    field_name,
                    f"패턴 검증 오류: {str(e)}",
                    "관리자에게 문의하세요"
                )
    
    def _validate_auth_type_specific(self, auth_type: AuthType, 
                                   credentials: Dict[str, str], 
                                   result: ValidationResult) -> None:
        """인증 방식별 특별 검증"""
        if auth_type == AuthType.OAUTH:
            if "access_token" in credentials:
                self._validate_jwt_token(credentials["access_token"], "access_token", result)
        
        elif auth_type == AuthType.BEARER_TOKEN:
            if "token" in credentials:
                token = credentials["token"]
                if token.startswith("Bearer "):
                    result.add_warning(
                        "token",
                        "토큰에 'Bearer ' 접두사가 포함되어 있습니다",
                        "토큰 값만 입력하세요 (Bearer 접두사 제외)"
                    )
    
    def _validate_jwt_token(self, token: str, field_name: str, 
                          result: ValidationResult) -> None:
        """JWT 토큰 기본 형식 검증"""
        if not token:
            return
        
        parts = token.split('.')
        if len(parts) != 3:
            result.add_error(
                field_name,
                "JWT 토큰 형식이 올바르지 않습니다",
                "JWT 토큰은 3개 부분(header.payload.signature)으로 구성되어야 합니다"
            )
            return
        
        import base64
        for i, part in enumerate(parts[:2]):
            try:
                padded = part + '=' * (4 - len(part) % 4)
                base64.urlsafe_b64decode(padded)
            except Exception:
                part_names = ["header", "payload", "signature"]
                result.add_error(
                    field_name,
                    f"JWT {part_names[i]} 부분의 base64 인코딩이 올바르지 않습니다"
                )
    
    def _validate_security_requirements(self, credentials: Dict[str, str], 
                                      result: ValidationResult) -> None:
        """보안 요구사항 검증"""
        for field_name, field_value in credentials.items():
            if not field_value:
                continue
            
            if len(field_value) < 8 and field_name in ["password", "secret", "api_key"]:
                result.add_warning(
                    field_name,
                    "보안을 위해 8자 이상 사용을 권장합니다"
                )
            
            if field_name in ["password", "secret"]:
                weak_patterns = [
                    r"^password\d*$",
                    r"^123456\d*$",
                    r"^admin\d*$",
                    r"^test\d*$"
                ]
                
                for pattern in weak_patterns:
                    if re.match(pattern, field_value.lower()):
                        result.add_warning(
                            field_name,
                            "약한 패스워드 패턴이 감지되었습니다",
                            "더 강력한 패스워드를 사용하세요"
                        )
                        break
    
    def validate_api_key_format(self, provider: str, api_key: str) -> bool:
        """API 키 형식 검증 (간단 버전)"""
        if not api_key:
            return False
        
        rules = self.validation_rules.get(provider, {}).get("api_key", {})
        
        min_length = rules.get("min_length", 8)
        max_length = rules.get("max_length", 100)
        
        if not (min_length <= len(api_key) <= max_length):
            return False
        
        pattern = rules.get("pattern")
        if pattern:
            try:
                return bool(re.match(pattern, api_key))
            except re.error:
                return False
        
        return True
    
    def validate_endpoint_url(self, url: str) -> ValidationResult:
        """엔드포인트 URL 검증"""
        result = ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            field_results={},
            suggestions=[]
        )
        
        if not url:
            result.add_error("url", "URL이 비어있습니다", "유효한 URL을 입력해주세요")
            return result
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            if parsed.scheme not in self.url_schemes:
                result.add_error(
                    "url",
                    f"지원하지 않는 프로토콜입니다: {parsed.scheme}",
                    f"다음 프로토콜을 사용하세요: {', '.join(self.url_schemes)}"
                )
            
            if not parsed.netloc:
                result.add_error(
                    "url",
                    "호스트가 지정되지 않았습니다",
                    "올바른 호스트명을 포함한 URL을 입력하세요"
                )
            else:
                self._validate_hostname(parsed.netloc, result)
            
            if parsed.scheme == "http":
                result.add_warning(
                    "url",
                    "HTTP 프로토콜은 보안에 취약합니다",
                    "가능하면 HTTPS를 사용하세요"
                )
            
            if parsed.port is not None:
                self._validate_port(parsed.port, result)
            
            if parsed.path:
                self._validate_url_path(parsed.path, result)
            
        except Exception as e:
            result.add_error("url", f"URL 파싱 오류: {str(e)}", "올바른 URL 형식을 확인하세요")
        
        return result
    
    def _validate_hostname(self, netloc: str, result: ValidationResult) -> None:
        """호스트명 검증"""
        if ':' in netloc:
            hostname = netloc.split(':')[0]
        else:
            hostname = netloc
        
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_loopback:
                result.add_warning(
                    "url",
                    "로컬호스트 주소입니다",
                    "실제 서비스에서는 공인 주소를 사용하세요"
                )
            elif ip.is_private:
                result.add_warning(
                    "url",
                    "사설 IP 주소입니다",
                    "공개 API의 경우 공인 IP 또는 도메인을 사용하세요"
                )
        except ValueError:
            domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
            if not re.match(domain_pattern, hostname):
                result.add_error(
                    "url",
                    "올바르지 않은 호스트명입니다",
                    "유효한 도메인명 또는 IP 주소를 사용하세요"
                )
    
    def _validate_port(self, port: int, result: ValidationResult) -> None:
        """포트 번호 검증"""
        if not (1 <= port <= 65535):
            result.add_error(
                "url",
                f"올바르지 않은 포트 번호입니다: {port}",
                "포트 번호는 1-65535 범위여야 합니다"
            )
        elif port in self.reserved_ports:
            result.add_warning(
                "url",
                f"예약된 포트 번호입니다: {port}",
                "일반적으로 사용되지 않는 포트인지 확인하세요"
            )
    
    def _validate_url_path(self, path: str, result: ValidationResult) -> None:
        """URL 경로 검증"""
        dangerous_patterns = [
            r'\.\./',
            r'/\.\./',
            r'<script',
            r'javascript:',
            r'data:',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                result.add_warning(
                    "url",
                    "잠재적으로 위험한 경로 패턴이 감지되었습니다",
                    "URL 경로를 다시 확인하세요"
                )
                break
    
    def validate_configuration(self, config: Dict[str, Any]) -> ValidationResult:
        """전체 설정 검증"""
        result = ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            field_results={},
            suggestions=[]
        )
        
        if "timeout" in config:
            self._validate_timeout(config["timeout"], result)
        
        if "retry_count" in config:
            self._validate_retry_count(config["retry_count"], result)
        
        if "rate_limit" in config:
            self._validate_rate_limit(config["rate_limit"], result)
        
        if "cache_ttl" in config:
            self._validate_cache_ttl(config["cache_ttl"], result)
        
        if "log_level" in config:
            self._validate_log_level(config["log_level"], result)
        
        return result
    
    def _validate_timeout(self, timeout: Any, result: ValidationResult) -> None:
        """타임아웃 설정 검증"""
        try:
            timeout_val = float(timeout)
            if timeout_val <= 0:
                result.add_error(
                    "timeout",
                    "타임아웃은 0보다 큰 값이어야 합니다",
                    "1-300초 범위의 값을 사용하세요"
                )
            elif timeout_val > 300:
                result.add_warning(
                    "timeout",
                    "타임아웃이 너무 깁니다 (300초 초과)",
                    "일반적으로 30-60초를 권장합니다"
                )
            elif timeout_val < 1:
                result.add_warning(
                    "timeout",
                    "타임아웃이 너무 짧습니다 (1초 미만)",
                    "네트워크 지연을 고려하여 최소 5초 이상을 권장합니다"
                )
        except (ValueError, TypeError):
            result.add_error(
                "timeout",
                "타임아웃은 숫자여야 합니다",
                "초 단위의 숫자 값을 입력하세요"
            )
    
    def _validate_retry_count(self, retry_count: Any, result: ValidationResult) -> None:
        """재시도 횟수 검증"""
        try:
            retry_val = int(retry_count)
            if retry_val < 0:
                result.add_error(
                    "retry_count",
                    "재시도 횟수는 0 이상이어야 합니다",
                    "0-10 범위의 값을 사용하세요"
                )
            elif retry_val > 10:
                result.add_warning(
                    "retry_count",
                    "재시도 횟수가 너무 많습니다 (10회 초과)",
                    "일반적으로 3-5회를 권장합니다"
                )
        except (ValueError, TypeError):
            result.add_error(
                "retry_count",
                "재시도 횟수는 정수여야 합니다",
                "0 이상의 정수를 입력하세요"
            )
    
    def _validate_rate_limit(self, rate_limit: Any, result: ValidationResult) -> None:
        """속도 제한 검증"""
        try:
            rate_val = int(rate_limit)
            if rate_val <= 0:
                result.add_error(
                    "rate_limit",
                    "속도 제한은 0보다 큰 값이어야 합니다",
                    "시간당 요청 수를 양의 정수로 입력하세요"
                )
            elif rate_val > 10000:
                result.add_warning(
                    "rate_limit",
                    "속도 제한이 매우 높습니다 (10,000 초과)",
                    "API 제공업체의 제한을 확인하세요"
                )
        except (ValueError, TypeError):
            result.add_error(
                "rate_limit",
                "속도 제한은 정수여야 합니다",
                "시간당 요청 수를 정수로 입력하세요"
            )
    
    def _validate_cache_ttl(self, cache_ttl: Any, result: ValidationResult) -> None:
        """캐시 TTL 검증"""
        try:
            ttl_val = int(cache_ttl)
            if ttl_val < 0:
                result.add_error(
                    "cache_ttl",
                    "캐시 TTL은 0 이상이어야 합니다",
                    "초 단위의 양의 정수를 입력하세요 (0은 캐시 비활성화)"
                )
            elif ttl_val > 86400:
                result.add_warning(
                    "cache_ttl",
                    "캐시 TTL이 매우 깁니다 (24시간 초과)",
                    "데이터 신선도를 고려하여 적절한 값을 설정하세요"
                )
        except (ValueError, TypeError):
            result.add_error(
                "cache_ttl",
                "캐시 TTL은 정수여야 합니다",
                "초 단위의 정수를 입력하세요"
            )
    
    def _validate_log_level(self, log_level: Any, result: ValidationResult) -> None:
        """로그 레벨 검증"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        if not isinstance(log_level, str):
            result.add_error(
                "log_level",
                "로그 레벨은 문자열이어야 합니다",
                f"다음 중 하나를 선택하세요: {', '.join(valid_levels)}"
            )
        elif log_level.upper() not in valid_levels:
            result.add_error(
                "log_level",
                f"올바르지 않은 로그 레벨입니다: {log_level}",
                f"다음 중 하나를 선택하세요: {', '.join(valid_levels)}"
            )
    
    def get_validation_rules(self, provider: str) -> Dict[str, Any]:
        """제공업체별 검증 규칙 조회"""
        return self.validation_rules.get(provider, {})
    
    def add_custom_validation_rule(self, provider: str, field: str, 
                                 rules: Dict[str, Any]) -> None:
        """커스텀 검증 규칙 추가"""
        if provider not in self.validation_rules:
            self.validation_rules[provider] = {}
        
        self.validation_rules[provider][field] = rules
    
    def validate_json_format(self, json_str: str, field_name: str = "json") -> ValidationResult:
        """JSON 형식 검증"""
        result = ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            field_results={},
            suggestions=[]
        )
        
        if not json_str:
            result.add_error(field_name, "JSON 데이터가 비어있습니다")
            return result
        
        try:
            json.loads(json_str)
            result.field_results[field_name] = True
        except json.JSONDecodeError as e:
            result.add_error(
                field_name,
                f"JSON 형식 오류: {str(e)}",
                "올바른 JSON 형식으로 입력하세요"
            )
        except Exception as e:
            result.add_error(
                field_name,
                f"JSON 파싱 오류: {str(e)}"
            )
        
        return result
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """여러 검증 결과 요약"""
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        valid_count = sum(1 for r in results if r.valid)
        
        return {
            "total_validations": len(results),
            "valid_count": valid_count,
            "invalid_count": len(results) - valid_count,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "success_rate": (valid_count / len(results) * 100) if results else 0,
            "has_errors": total_errors > 0,
            "has_warnings": total_warnings > 0
        }