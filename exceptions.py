"""
통합 API 시스템 예외 처리 클래스.

식약처 식품영양성분 API와 한국건강증진개발원 운동 API 통합 시스템에서
발생할 수 있는 다양한 오류 상황을 처리하기 위한 예외 클래스들을 정의합니다.
"""


class IntegratedAPIError(Exception):
    """통합 API 시스템의 모든 오류에 대한 기본 예외 클래스."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


# ==================== 설정 관련 예외 ====================

class ConfigurationError(IntegratedAPIError):
    """설정 관련 문제가 발생했을 때 발생하는 예외."""
    pass


class APIKeyError(ConfigurationError):
    """API 키 관련 오류 (누락, 잘못된 형식 등)."""
    pass


class EnvironmentError(ConfigurationError):
    """환경 설정 오류 (환경변수, 설정파일 등)."""
    pass


# ==================== API 연결 관련 예외 ====================

class APIConnectionError(IntegratedAPIError):
    """API 연결 실패 시 발생하는 예외."""
    pass


class NetworkError(APIConnectionError):
    """네트워크 연결 문제로 인한 오류."""
    pass


class TimeoutError(APIConnectionError):
    """API 응답 시간 초과 오류."""
    pass


class APIAuthenticationError(IntegratedAPIError):
    """API 인증 실패 시 발생하는 예외."""
    pass


class InvalidAPIKeyError(APIAuthenticationError):
    """유효하지 않은 API 키 오류."""
    pass


class APIQuotaExceededError(APIAuthenticationError):
    """API 호출 한도 초과 오류."""
    pass


# ==================== API 응답 관련 예외 ====================

class APIResponseError(IntegratedAPIError):
    """API가 잘못된 응답을 반환했을 때 발생하는 예외."""
    
    def __init__(self, message: str, status_code: int = None, response_data: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
    
    def __str__(self):
        base_msg = super().__str__()
        if self.status_code:
            base_msg += f" (HTTP {self.status_code})"
        return base_msg


class FoodAPIError(APIResponseError):
    """식약처 식품영양성분 API 관련 오류."""
    pass


class ExerciseAPIError(APIResponseError):
    """한국건강증진개발원 운동 API 관련 오류."""
    pass


class NoSearchResultsError(APIResponseError):
    """검색 결과가 없을 때 발생하는 예외."""
    pass


# ==================== 데이터 처리 관련 예외 ====================

class DataValidationError(IntegratedAPIError):
    """데이터 검증 실패 시 발생하는 예외."""
    
    def __init__(self, message: str, field_name: str = None, invalid_value=None):
        super().__init__(message)
        self.field_name = field_name
        self.invalid_value = invalid_value
    
    def __str__(self):
        base_msg = super().__str__()
        if self.field_name:
            base_msg += f" (필드: {self.field_name})"
        if self.invalid_value is not None:
            base_msg += f" (값: {self.invalid_value})"
        return base_msg


class NutritionDataError(DataValidationError):
    """영양 정보 데이터 검증 오류."""
    pass


class ExerciseDataError(DataValidationError):
    """운동 데이터 검증 오류."""
    pass


class DataProcessingError(IntegratedAPIError):
    """데이터 처리 중 오류가 발생했을 때 발생하는 예외."""
    pass


class JSONParsingError(DataProcessingError):
    """JSON 파싱 오류."""
    pass


class DataConversionError(DataProcessingError):
    """데이터 형변환 오류."""
    pass


# ==================== 계산 관련 예외 ====================

class CalorieCalculationError(IntegratedAPIError):
    """칼로리 계산 실패 시 발생하는 예외."""
    pass


class InvalidMETValueError(CalorieCalculationError):
    """잘못된 MET 값으로 인한 계산 오류."""
    pass


class InvalidWeightError(CalorieCalculationError):
    """잘못된 체중 값으로 인한 계산 오류."""
    pass


class InvalidAmountError(CalorieCalculationError):
    """잘못된 섭취량/운동시간으로 인한 계산 오류."""
    pass


# ==================== 온톨로지 관련 예외 ====================

class OntologyError(IntegratedAPIError):
    """온톨로지 작업 실패 시 발생하는 예외."""
    pass


class TTLSyntaxError(OntologyError):
    """TTL 파일 문법 오류."""
    pass


class URIGenerationError(OntologyError):
    """URI 생성 오류."""
    pass


class OntologyMergeError(OntologyError):
    """온톨로지 병합 오류."""
    pass


class DuplicateDataError(OntologyError):
    """중복 데이터 처리 오류."""
    pass


# ==================== 파일 시스템 관련 예외 ====================

class FileSystemError(IntegratedAPIError):
    """파일 시스템 작업 실패 시 발생하는 예외."""
    pass


class FileNotFoundError(FileSystemError):
    """파일을 찾을 수 없는 오류."""
    pass


class FilePermissionError(FileSystemError):
    """파일 권한 오류."""
    pass


class DiskSpaceError(FileSystemError):
    """디스크 공간 부족 오류."""
    pass


class BackupError(FileSystemError):
    """백업 파일 생성 오류."""
    pass


# ==================== 캐시 관련 예외 ====================

class CacheError(IntegratedAPIError):
    """캐시 시스템 오류."""
    pass


class CacheExpiredError(CacheError):
    """캐시 만료 오류."""
    pass


class CacheCorruptedError(CacheError):
    """캐시 데이터 손상 오류."""
    pass


# ==================== 검색 관련 예외 ====================

class SearchError(IntegratedAPIError):
    """검색 시스템 관련 오류."""
    pass


class SearchTimeoutError(SearchError):
    """검색 시간 초과 오류."""
    pass


class BatchSearchError(SearchError):
    """배치 검색 오류."""
    pass


# ==================== API 등록 관리 관련 예외 ====================

class APIRegistrationError(IntegratedAPIError):
    """API 등록 관리 시스템 관련 오류."""
    pass


class RegistrationValidationError(APIRegistrationError):
    """API 등록 검증 실패 오류."""
    
    def __init__(self, message: str, provider: str = None, field: str = None):
        super().__init__(message)
        self.provider = provider
        self.field = field
    
    def __str__(self):
        base_msg = super().__str__()
        if self.provider:
            base_msg += f" (제공업체: {self.provider})"
        if self.field:
            base_msg += f" (필드: {self.field})"
        return base_msg


class DuplicateAPIRegistrationError(APIRegistrationError):
    """중복 API 등록 오류."""
    pass


class APINotFoundError(APIRegistrationError):
    """등록된 API를 찾을 수 없는 오류."""
    pass


class ProviderNotSupportedError(APIRegistrationError):
    """지원하지 않는 API 제공업체 오류."""
    pass


# ==================== 보안 및 암호화 관련 예외 ====================

class SecurityError(IntegratedAPIError):
    """보안 관련 오류."""
    pass


class EncryptionError(SecurityError):
    """암호화/복호화 오류."""
    
    def __init__(self, message: str, error_type: str = None, details: str = None):
        super().__init__(message, details)
        self.error_type = error_type
    
    def __str__(self):
        base_msg = super().__str__()
        if self.error_type:
            base_msg += f" (유형: {self.error_type})"
        return base_msg


class DecryptionError(EncryptionError):
    """복호화 실패 오류."""
    pass


class KeyDerivationError(EncryptionError):
    """키 유도 실패 오류."""
    pass


class IntegrityCheckError(SecurityError):
    """데이터 무결성 검증 실패 오류."""
    pass


class PermissionError(SecurityError):
    """파일 권한 설정 오류."""
    pass


class MasterPasswordError(SecurityError):
    """마스터 패스워드 관련 오류."""
    pass


# ==================== 연결 테스트 관련 예외 ====================

class ConnectionTestError(IntegratedAPIError):
    """API 연결 테스트 관련 오류."""
    
    def __init__(self, message: str, api_id: str = None, status_code: int = None):
        super().__init__(message)
        self.api_id = api_id
        self.status_code = status_code


class TestEndpointError(ConnectionTestError):
    """테스트 엔드포인트 호출 실패 오류."""
    pass


class ConnectionDiagnosisError(ConnectionTestError):
    """연결 진단 실패 오류."""
    pass


# ==================== 사용량 모니터링 관련 예외 ====================

class UsageMonitoringError(IntegratedAPIError):
    """사용량 모니터링 관련 오류."""
    pass


class UsageDataCorruptedError(UsageMonitoringError):
    """사용량 데이터 손상 오류."""
    pass


class RateLimitError(UsageMonitoringError):
    """속도 제한 관련 오류."""
    
    def __init__(self, message: str, api_id: str = None, limit: int = None, reset_time: int = None):
        super().__init__(message)
        self.api_id = api_id
        self.limit = limit
        self.reset_time = reset_time


class UsageReportError(UsageMonitoringError):
    """사용량 리포트 생성 오류."""
    pass


# ==================== 설정 가져오기/내보내기 관련 예외 ====================

class ConfigurationImportExportError(IntegratedAPIError):
    """설정 가져오기/내보내기 관련 오류."""
    pass


class ConfigurationExportError(ConfigurationImportExportError):
    """설정 내보내기 오류."""
    pass


class ConfigurationImportError(ConfigurationImportExportError):
    """설정 가져오기 오류."""
    pass


class ConfigurationFormatError(ConfigurationImportExportError):
    """설정 파일 형식 오류."""
    pass


class BackupCorruptedError(ConfigurationImportExportError):
    """백업 파일 손상 오류."""
    pass


# ==================== 사용자 인터페이스 관련 예외 ====================

class UserInterfaceError(IntegratedAPIError):
    """사용자 인터페이스 관련 오류."""
    pass


class InvalidCommandError(UserInterfaceError):
    """잘못된 명령어 오류."""
    pass


class MissingArgumentError(UserInterfaceError):
    """필수 인자 누락 오류."""
    pass


# ==================== 예외 처리 유틸리티 ====================

class ErrorHandler:
    """통합 오류 처리 유틸리티 클래스."""
    
    @staticmethod
    def get_user_friendly_message(error: Exception) -> str:
        """
        사용자 친화적인 오류 메시지 생성.
        
        Args:
            error: 발생한 예외
            
        Returns:
            str: 사용자 친화적인 오류 메시지
        """
        if isinstance(error, InvalidAPIKeyError):
            return "API 키가 유효하지 않습니다. 환경변수나 설정파일을 확인해주세요."
        
        elif isinstance(error, NetworkError):
            return "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인해주세요."
        
        elif isinstance(error, APIQuotaExceededError):
            return "API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
        
        elif isinstance(error, NoSearchResultsError):
            return "검색 결과를 찾을 수 없습니다. 다른 검색어를 시도해보세요."
        
        elif isinstance(error, NutritionDataError):
            return "영양 정보 데이터에 문제가 있습니다. 데이터를 확인해주세요."
        
        elif isinstance(error, CalorieCalculationError):
            return "칼로리 계산 중 오류가 발생했습니다. 입력값을 확인해주세요."
        
        elif isinstance(error, TTLSyntaxError):
            return "TTL 파일 형식에 오류가 있습니다. 파일을 확인해주세요."
        
        elif isinstance(error, FilePermissionError):
            return "파일 접근 권한이 없습니다. 권한을 확인해주세요."
        
        # API 등록 관리 관련 오류
        elif isinstance(error, RegistrationValidationError):
            provider_msg = f" ({error.provider})" if error.provider else ""
            field_msg = f" - 필드: {error.field}" if error.field else ""
            return f"API 등록 검증에 실패했습니다{provider_msg}{field_msg}"
        
        elif isinstance(error, DuplicateAPIRegistrationError):
            return "이미 등록된 API입니다. 기존 등록을 업데이트하거나 삭제 후 다시 등록해주세요."
        
        elif isinstance(error, APINotFoundError):
            return "요청한 API를 찾을 수 없습니다. 등록된 API 목록을 확인해주세요."
        
        elif isinstance(error, ProviderNotSupportedError):
            return "지원하지 않는 API 제공업체입니다. 지원 가능한 제공업체 목록을 확인해주세요."
        
        # 보안 관련 오류
        elif isinstance(error, EncryptionError):
            error_type_msg = f" ({error.error_type})" if error.error_type else ""
            return f"데이터 암호화 중 오류가 발생했습니다{error_type_msg}"
        
        elif isinstance(error, DecryptionError):
            return "데이터 복호화에 실패했습니다. 마스터 패스워드나 암호화 키를 확인해주세요."
        
        elif isinstance(error, IntegrityCheckError):
            return "데이터 무결성 검증에 실패했습니다. 데이터가 손상되었을 수 있습니다."
        
        elif isinstance(error, MasterPasswordError):
            return "마스터 패스워드 관련 오류가 발생했습니다. 패스워드를 확인해주세요."
        
        # 연결 테스트 관련 오류
        elif isinstance(error, ConnectionTestError):
            api_msg = f" (API: {error.api_id})" if error.api_id else ""
            status_msg = f" (HTTP {error.status_code})" if error.status_code else ""
            return f"API 연결 테스트 중 오류가 발생했습니다{api_msg}{status_msg}"
        
        elif isinstance(error, TestEndpointError):
            return "테스트 엔드포인트 호출에 실패했습니다. API 키와 엔드포인트를 확인해주세요."
        
        # 사용량 모니터링 관련 오류
        elif isinstance(error, UsageDataCorruptedError):
            return "사용량 데이터가 손상되었습니다. 데이터를 재설정해주세요."
        
        elif isinstance(error, RateLimitError):
            api_msg = f" (API: {error.api_id})" if error.api_id else ""
            limit_msg = f" - 제한: {error.limit}회" if error.limit else ""
            reset_msg = f" - 재설정: {error.reset_time}초 후" if error.reset_time else ""
            return f"API 호출 속도 제한에 도달했습니다{api_msg}{limit_msg}{reset_msg}"
        
        # 설정 가져오기/내보내기 관련 오류
        elif isinstance(error, ConfigurationExportError):
            return "설정 내보내기에 실패했습니다. 파일 권한과 디스크 공간을 확인해주세요."
        
        elif isinstance(error, ConfigurationImportError):
            return "설정 가져오기에 실패했습니다. 파일 형식과 내용을 확인해주세요."
        
        elif isinstance(error, BackupCorruptedError):
            return "백업 파일이 손상되었습니다. 다른 백업 파일을 사용해주세요."
        
        else:
            return f"예상치 못한 오류가 발생했습니다: {str(error)}"
    
    @staticmethod
    def get_solution_suggestion(error: Exception) -> str:
        """
        오류 해결 방법 제안.
        
        Args:
            error: 발생한 예외
            
        Returns:
            str: 해결 방법 제안
        """
        if isinstance(error, InvalidAPIKeyError):
            return "1. 환경변수 FOOD_API_KEY 설정 확인\n2. config.json 파일의 API 키 확인\n3. API 키 재발급"
        
        elif isinstance(error, NetworkError):
            return "1. 인터넷 연결 상태 확인\n2. 방화벽 설정 확인\n3. 프록시 설정 확인"
        
        elif isinstance(error, NoSearchResultsError):
            return "1. 검색어 철자 확인\n2. 다른 유사한 검색어 시도\n3. 영어/한국어 검색어 변경"
        
        elif isinstance(error, FilePermissionError):
            return "1. 파일 권한 확인 (chmod 644)\n2. 관리자 권한으로 실행\n3. 파일 소유권 확인"
        
        # API 등록 관리 관련 해결 방법
        elif isinstance(error, RegistrationValidationError):
            solutions = ["1. 입력한 API 키 형식 확인", "2. 제공업체 문서 참조", "3. 필수 필드 누락 확인"]
            if error.provider:
                solutions.append(f"4. {error.provider} 제공업체 특별 요구사항 확인")
            if error.field:
                solutions.append(f"5. '{error.field}' 필드 형식 재확인")
            return "\n".join(solutions)
        
        elif isinstance(error, DuplicateAPIRegistrationError):
            return "1. 기존 등록 업데이트 사용\n2. 기존 API 삭제 후 재등록\n3. 다른 API ID 사용"
        
        elif isinstance(error, ProviderNotSupportedError):
            return "1. 지원 제공업체 목록 확인\n2. 커스텀 제공업체 설정 추가\n3. 기존 제공업체 확장"
        
        # 보안 관련 해결 방법
        elif isinstance(error, EncryptionError):
            solutions = ["1. 암호화 설정 확인", "2. 시스템 보안 상태 점검"]
            if error.error_type:
                if error.error_type == "key_not_found":
                    solutions.extend(["3. 마스터 키 재생성", "4. 백업에서 키 복원"])
                elif error.error_type == "algorithm_error":
                    solutions.extend(["3. 암호화 알고리즘 설정 확인", "4. 시스템 업데이트"])
            return "\n".join(solutions)
        
        elif isinstance(error, DecryptionError):
            return "1. 마스터 패스워드 재확인\n2. 백업에서 복원\n3. 암호화 키 재생성"
        
        elif isinstance(error, IntegrityCheckError):
            return "1. 백업 파일에서 복원\n2. 손상된 데이터 재등록\n3. 시스템 무결성 검사"
        
        elif isinstance(error, MasterPasswordError):
            return "1. 패스워드 재설정\n2. 보안 질문 사용\n3. 관리자 권한으로 복구"
        
        # 연결 테스트 관련 해결 방법
        elif isinstance(error, ConnectionTestError):
            solutions = ["1. API 키 유효성 확인", "2. 네트워크 연결 테스트", "3. 엔드포인트 URL 확인"]
            if error.api_id:
                solutions.append(f"4. '{error.api_id}' API 설정 재확인")
            if error.status_code:
                if error.status_code == 401:
                    solutions.append("5. 인증 정보 재확인")
                elif error.status_code == 403:
                    solutions.append("5. API 권한 설정 확인")
                elif error.status_code == 429:
                    solutions.append("5. 속도 제한 대기 후 재시도")
            return "\n".join(solutions)
        
        elif isinstance(error, TestEndpointError):
            return "1. 테스트 엔드포인트 URL 확인\n2. API 키 권한 확인\n3. 방화벽 설정 확인"
        
        # 사용량 모니터링 관련 해결 방법
        elif isinstance(error, UsageDataCorruptedError):
            return "1. 사용량 데이터 재설정\n2. 백업에서 복원\n3. 새로운 모니터링 시작"
        
        elif isinstance(error, RateLimitError):
            solutions = ["1. 호출 간격 조정", "2. 배치 처리 사용"]
            if error.limit:
                solutions.append(f"3. 현재 제한({error.limit}회) 고려한 호출 계획")
            if error.reset_time:
                solutions.append(f"4. {error.reset_time}초 후 재시도")
            solutions.append("5. API 플랜 업그레이드 고려")
            return "\n".join(solutions)
        
        # 설정 관련 해결 방법
        elif isinstance(error, ConfigurationExportError):
            return "1. 디스크 공간 확인\n2. 파일 권한 설정\n3. 다른 경로로 내보내기"
        
        elif isinstance(error, ConfigurationImportError):
            return "1. 파일 형식 확인\n2. 파일 무결성 검증\n3. 백업 파일 사용"
        
        elif isinstance(error, BackupCorruptedError):
            return "1. 다른 백업 파일 사용\n2. 수동 설정 복구\n3. 새로운 설정 생성"
        
        else:
            return "로그를 확인하고 문제를 분석해주세요."