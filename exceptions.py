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
        
        else:
            return "로그를 확인하고 문제를 분석해주세요."