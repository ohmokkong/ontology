"""
API 등록 관리 시스템의 핵심 데이터 모델.

API 등록, 연결 테스트, 사용량 통계 등 API 등록 관리 시스템에서
사용되는 모든 데이터 모델을 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json
import hashlib


# ==================== 열거형 정의 ====================

class APIStatus(Enum):
    """API 상태 열거형"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"
    EXPIRED = "expired"


class AuthType(Enum):
    """인증 방식 열거형"""
    API_KEY = "api_key"
    OAUTH = "oauth"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"


class ConnectionStatus(Enum):
    """연결 상태 열거형"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


# ValidationResult는 아래에 dataclass로 정의됨


# ==================== 기본 데이터 모델 ====================

@dataclass
class APIProvider:
    """API 제공업체 정보"""
    name: str
    display_name: str
    base_url: str
    auth_type: AuthType
    required_fields: List[str]
    optional_fields: List[str] = field(default_factory=list)
    test_endpoint: str = ""
    documentation_url: str = ""
    rate_limits: Dict[str, int] = field(default_factory=dict)
    validation_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        자격증명 유효성 검사.
        
        Args:
            credentials: 검증할 자격증명
            
        Returns:
            bool: 검증 성공 여부
        """
        # 필수 필드 확인
        for field_name in self.required_fields:
            if field_name not in credentials or not credentials[field_name]:
                return False
        
        # 검증 규칙 적용
        for field_name, value in credentials.items():
            if field_name in self.validation_rules:
                rules = self.validation_rules[field_name]
                
                # 길이 검증
                if "min_length" in rules and len(value) < rules["min_length"]:
                    return False
                if "max_length" in rules and len(value) > rules["max_length"]:
                    return False
                
                # 패턴 검증
                if "pattern" in rules:
                    import re
                    try:
                        if not re.match(rules["pattern"], value):
                            return False
                    except re.error:
                        # 잘못된 정규식 패턴인 경우 통과
                        pass
        
        return True
    
    def get_test_request(self) -> Dict[str, Any]:
        """
        테스트 요청 정보 반환.
        
        Returns:
            Dict: 테스트 요청 정보
        """
        return {
            "url": f"{self.base_url.rstrip('/')}/{self.test_endpoint.lstrip('/')}",
            "method": "GET",
            "timeout": 30,
            "headers": {
                "User-Agent": "API-Registration-Manager/1.0"
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "base_url": self.base_url,
            "auth_type": self.auth_type.value,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "test_endpoint": self.test_endpoint,
            "documentation_url": self.documentation_url,
            "rate_limits": self.rate_limits,
            "validation_rules": self.validation_rules
        }


@dataclass
class EncryptedData:
    """암호화된 데이터 컨테이너"""
    encrypted_content: str
    salt: str
    algorithm: str = "AES-256-GCM"
    key_derivation: str = "PBKDF2"
    iterations: int = 100000
    integrity_hash: str = ""
    
    def __post_init__(self):
        """초기화 후 무결성 해시 생성"""
        if not self.integrity_hash:
            self.integrity_hash = self._generate_integrity_hash()
    
    def _generate_integrity_hash(self) -> str:
        """무결성 검증용 해시 생성"""
        content = f"{self.encrypted_content}{self.salt}{self.algorithm}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """무결성 검증"""
        expected_hash = self._generate_integrity_hash()
        return self.integrity_hash == expected_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "encrypted_content": self.encrypted_content,
            "salt": self.salt,
            "algorithm": self.algorithm,
            "key_derivation": self.key_derivation,
            "iterations": self.iterations,
            "integrity_hash": self.integrity_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        """딕셔너리에서 생성"""
        return cls(
            encrypted_content=data["encrypted_content"],
            salt=data["salt"],
            algorithm=data.get("algorithm", "AES-256-GCM"),
            key_derivation=data.get("key_derivation", "PBKDF2"),
            iterations=data.get("iterations", 100000),
            integrity_hash=data.get("integrity_hash", "")
        )


@dataclass
class APIRegistration:
    """API 등록 정보"""
    api_id: str
    provider: APIProvider
    encrypted_credentials: EncryptedData
    configuration: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_tested: Optional[datetime] = None
    status: APIStatus = APIStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """활성 상태 확인"""
        return self.status == APIStatus.ACTIVE
    
    def needs_testing(self, test_interval_hours: int = 24) -> bool:
        """
        테스트 필요 여부 확인.
        
        Args:
            test_interval_hours: 테스트 간격 (시간)
            
        Returns:
            bool: 테스트 필요 여부
        """
        if not self.last_tested:
            return True
        
        time_diff = datetime.now() - self.last_tested
        return time_diff.total_seconds() > (test_interval_hours * 3600)
    
    def update_status(self, new_status: APIStatus) -> None:
        """상태 업데이트"""
        self.status = new_status
        self.updated_at = datetime.now()
    
    def update_last_tested(self) -> None:
        """마지막 테스트 시간 업데이트"""
        self.last_tested = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        딕셔너리로 변환.
        
        Args:
            include_sensitive: 민감한 정보 포함 여부
            
        Returns:
            Dict: 딕셔너리 형태의 데이터
        """
        result = {
            "api_id": self.api_id,
            "provider": self.provider.to_dict(),
            "configuration": self.configuration,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "status": self.status.value,
            "metadata": self.metadata
        }
        
        if include_sensitive:
            result["encrypted_credentials"] = self.encrypted_credentials.to_dict()
        
        return result


# ==================== 연결 테스트 관련 모델 ====================

@dataclass
class ConnectionTestResult:
    """연결 테스트 결과"""
    api_id: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    tested_at: datetime = field(default_factory=datetime.now)
    suggestions: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None
    
    def is_healthy(self) -> bool:
        """
        건강 상태 확인.
        
        Returns:
            bool: 건강한 상태 여부
        """
        return self.success and self.response_time < 5.0
    
    def get_status_summary(self) -> str:
        """
        상태 요약 반환.
        
        Returns:
            str: 상태 요약
        """
        if self.success:
            return f"성공 (응답시간: {self.response_time:.2f}초)"
        else:
            error_info = f" - {self.error_message}" if self.error_message else ""
            return f"실패{error_info}"
    
    def get_connection_status(self) -> ConnectionStatus:
        """연결 상태 반환"""
        if self.success:
            return ConnectionStatus.SUCCESS
        elif self.error_type == "timeout":
            return ConnectionStatus.TIMEOUT
        elif self.error_type == "auth_error":
            return ConnectionStatus.AUTH_ERROR
        elif self.error_type == "rate_limited":
            return ConnectionStatus.RATE_LIMITED
        else:
            return ConnectionStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "api_id": self.api_id,
            "success": self.success,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "tested_at": self.tested_at.isoformat(),
            "suggestions": self.suggestions,
            "connection_status": self.get_connection_status().value
        }


@dataclass
class DiagnosisResult:
    """연결 진단 결과"""
    api_id: str
    issues_found: List[str]
    suggestions: List[str]
    severity: str  # "low", "medium", "high", "critical"
    diagnosis_time: datetime = field(default_factory=datetime.now)
    
    def is_critical(self) -> bool:
        """심각한 문제 여부"""
        return self.severity == "critical"
    
    def has_issues(self) -> bool:
        """문제 존재 여부"""
        return len(self.issues_found) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "api_id": self.api_id,
            "issues_found": self.issues_found,
            "suggestions": self.suggestions,
            "severity": self.severity,
            "diagnosis_time": self.diagnosis_time.isoformat(),
            "is_critical": self.is_critical(),
            "has_issues": self.has_issues()
        }


# ==================== 사용량 모니터링 관련 모델 ====================

@dataclass
class APICallRecord:
    """API 호출 기록"""
    api_id: str
    endpoint: str
    method: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    request_size: int = 0
    response_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "api_id": self.api_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "success": self.success,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "request_size": self.request_size,
            "response_size": self.response_size
        }


@dataclass
class UsageStats:
    """사용량 통계"""
    api_id: str
    period: str  # "hourly", "daily", "weekly", "monthly"
    start_time: datetime
    end_time: datetime
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    average_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0
    total_data_transferred: int = 0
    error_breakdown: Dict[str, int] = field(default_factory=dict)
    hourly_distribution: Dict[str, int] = field(default_factory=dict)
    
    def get_success_rate(self) -> float:
        """성공률 계산"""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100
    
    def get_failure_rate(self) -> float:
        """실패율 계산"""
        return 100.0 - self.get_success_rate()
    
    def add_call_record(self, record: APICallRecord) -> None:
        """호출 기록 추가"""
        self.total_calls += 1
        
        if record.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
            error_type = record.error_message or "unknown"
            self.error_breakdown[error_type] = self.error_breakdown.get(error_type, 0) + 1
        
        # 응답 시간 통계 업데이트
        if self.total_calls == 1:
            self.average_response_time = record.response_time
            self.max_response_time = record.response_time
            self.min_response_time = record.response_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_calls - 1) + record.response_time) 
                / self.total_calls
            )
            self.max_response_time = max(self.max_response_time, record.response_time)
            self.min_response_time = min(self.min_response_time, record.response_time)
        
        # 데이터 전송량 업데이트
        self.total_data_transferred += record.request_size + record.response_size
        
        # 시간별 분포 업데이트
        hour_key = record.timestamp.strftime("%H")
        self.hourly_distribution[hour_key] = self.hourly_distribution.get(hour_key, 0) + 1
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "api_id": self.api_id,
            "period": self.period,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": self.get_success_rate(),
            "failure_rate": self.get_failure_rate(),
            "average_response_time": self.average_response_time,
            "max_response_time": self.max_response_time,
            "min_response_time": self.min_response_time,
            "total_data_transferred": self.total_data_transferred,
            "error_breakdown": self.error_breakdown,
            "hourly_distribution": self.hourly_distribution
        }


@dataclass
class RateLimitStatus:
    """속도 제한 상태"""
    api_id: str
    current_usage: int
    limit: int
    reset_time: datetime
    remaining: int
    
    def is_exceeded(self) -> bool:
        """제한 초과 여부"""
        return self.current_usage >= self.limit
    
    def get_usage_percentage(self) -> float:
        """사용률 계산"""
        if self.limit == 0:
            return 0.0
        return (self.current_usage / self.limit) * 100
    
    def time_until_reset(self) -> int:
        """리셋까지 남은 시간 (초)"""
        time_diff = self.reset_time - datetime.now()
        return max(0, int(time_diff.total_seconds()))
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "api_id": self.api_id,
            "current_usage": self.current_usage,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_time": self.reset_time.isoformat(),
            "is_exceeded": self.is_exceeded(),
            "usage_percentage": self.get_usage_percentage(),
            "time_until_reset": self.time_until_reset()
        }


# ==================== 결과 및 응답 모델 ====================

@dataclass
class RegistrationResult:
    """API 등록 결과"""
    success: bool
    api_id: Optional[str] = None
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """오류 추가"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """경고 추가"""
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "api_id": self.api_id,
            "message": self.message,
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class ValidationResult:
    """검증 결과"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    field_results: Dict[str, bool] = field(default_factory=dict)
    
    def add_error(self, field: str, message: str) -> None:
        """필드 오류 추가"""
        self.errors.append(f"{field}: {message}")
        self.field_results[field] = False
        self.valid = False
    
    def add_warning(self, field: str, message: str) -> None:
        """필드 경고 추가"""
        self.warnings.append(f"{field}: {message}")
    
    def is_field_valid(self, field: str) -> bool:
        """특정 필드 유효성 확인"""
        return self.field_results.get(field, True)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "field_results": self.field_results
        }


@dataclass
class ExportResult:
    """내보내기 결과"""
    success: bool
    file_path: Optional[str] = None
    exported_count: int = 0
    message: str = ""
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "file_path": self.file_path,
            "exported_count": self.exported_count,
            "message": self.message,
            "errors": self.errors
        }


@dataclass
class ImportResult:
    """가져오기 결과"""
    success: bool
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "success": self.success,
            "imported_count": self.imported_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "message": self.message,
            "errors": self.errors,
            "warnings": self.warnings
        }


# ==================== 유틸리티 함수 ====================

def generate_api_id(provider_name: str, user_identifier: str = "") -> str:
    """
    API ID 생성.
    
    Args:
        provider_name: 제공업체 이름
        user_identifier: 사용자 식별자 (선택사항)
        
    Returns:
        str: 생성된 API ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_id = f"{provider_name}_{timestamp}"
    
    if user_identifier:
        base_id += f"_{user_identifier}"
    
    # 해시를 추가하여 고유성 보장
    hash_input = f"{base_id}_{datetime.now().microsecond}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    return f"{base_id}_{hash_suffix}"


def create_default_configuration() -> Dict[str, Any]:
    """
    기본 설정 생성.
    
    Returns:
        Dict: 기본 설정
    """
    return {
        "timeout": 30,
        "retry_count": 3,
        "retry_delay": 1,
        "rate_limit": 100,
        "auto_test_enabled": True,
        "auto_test_interval": 3600,  # 1시간
        "log_requests": True,
        "log_responses": False,
        "cache_enabled": True,
        "cache_ttl": 300  # 5분
    }