"""
API 등록 관리 시스템 데이터 모델 테스트.

핵심 데이터 모델들의 기본 기능을 테스트합니다.
"""

import unittest
from datetime import datetime, timedelta
from api_registration_models import (
    APIProvider, APIRegistration, EncryptedData, ConnectionTestResult,
    UsageStats, APICallRecord, RateLimitStatus, RegistrationResult,
    ValidationResult, AuthType, APIStatus, ConnectionStatus,
    generate_api_id, create_default_configuration
)
from exceptions import RegistrationValidationError


class TestAPIProvider(unittest.TestCase):
    """APIProvider 모델 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.provider = APIProvider(
            name="test_provider",
            display_name="테스트 API 제공업체",
            base_url="https://api.test.com",
            auth_type=AuthType.API_KEY,
            required_fields=["api_key"],
            optional_fields=["service_id"],
            test_endpoint="/test",
            validation_rules={
                "api_key": {
                    "min_length": 10,
                    "max_length": 50,
                    "pattern": "^[A-Za-z0-9_]+$"
                }
            }
        )
    
    def test_validate_credentials_success(self):
        """자격증명 검증 성공 테스트"""
        credentials = {"api_key": "valid_api_key_123"}
        self.assertTrue(self.provider.validate_credentials(credentials))
    
    def test_validate_credentials_missing_required(self):
        """필수 필드 누락 테스트"""
        credentials = {"service_id": "test"}
        self.assertFalse(self.provider.validate_credentials(credentials))
    
    def test_validate_credentials_invalid_length(self):
        """길이 검증 실패 테스트"""
        credentials = {"api_key": "short"}  # 너무 짧음
        self.assertFalse(self.provider.validate_credentials(credentials))
    
    def test_get_test_request(self):
        """테스트 요청 정보 생성 테스트"""
        request_info = self.provider.get_test_request()
        self.assertEqual(request_info["url"], "https://api.test.com/test")
        self.assertEqual(request_info["method"], "GET")
        self.assertIn("User-Agent", request_info["headers"])
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        provider_dict = self.provider.to_dict()
        self.assertEqual(provider_dict["name"], "test_provider")
        self.assertEqual(provider_dict["auth_type"], "api_key")
        self.assertIn("validation_rules", provider_dict)


class TestEncryptedData(unittest.TestCase):
    """EncryptedData 모델 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.encrypted_data = EncryptedData(
            encrypted_content="encrypted_test_data",
            salt="test_salt_123"
        )
    
    def test_integrity_hash_generation(self):
        """무결성 해시 생성 테스트"""
        self.assertIsNotNone(self.encrypted_data.integrity_hash)
        self.assertTrue(len(self.encrypted_data.integrity_hash) > 0)
    
    def test_verify_integrity_success(self):
        """무결성 검증 성공 테스트"""
        self.assertTrue(self.encrypted_data.verify_integrity())
    
    def test_verify_integrity_failure(self):
        """무결성 검증 실패 테스트"""
        # 데이터 변조
        self.encrypted_data.encrypted_content = "tampered_data"
        self.assertFalse(self.encrypted_data.verify_integrity())
    
    def test_to_dict_and_from_dict(self):
        """딕셔너리 변환 및 복원 테스트"""
        data_dict = self.encrypted_data.to_dict()
        restored_data = EncryptedData.from_dict(data_dict)
        
        self.assertEqual(restored_data.encrypted_content, self.encrypted_data.encrypted_content)
        self.assertEqual(restored_data.salt, self.encrypted_data.salt)
        self.assertEqual(restored_data.integrity_hash, self.encrypted_data.integrity_hash)


class TestAPIRegistration(unittest.TestCase):
    """APIRegistration 모델 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.provider = APIProvider(
            name="test_provider",
            display_name="테스트 제공업체",
            base_url="https://api.test.com",
            auth_type=AuthType.API_KEY,
            required_fields=["api_key"]
        )
        
        self.encrypted_credentials = EncryptedData(
            encrypted_content="encrypted_credentials",
            salt="test_salt"
        )
        
        self.registration = APIRegistration(
            api_id="test_api_001",
            provider=self.provider,
            encrypted_credentials=self.encrypted_credentials
        )
    
    def test_is_active(self):
        """활성 상태 확인 테스트"""
        self.assertTrue(self.registration.is_active())
        
        self.registration.status = APIStatus.INACTIVE
        self.assertFalse(self.registration.is_active())
    
    def test_needs_testing(self):
        """테스트 필요 여부 확인 테스트"""
        # 처음에는 테스트가 필요함
        self.assertTrue(self.registration.needs_testing())
        
        # 최근에 테스트했으면 불필요
        self.registration.last_tested = datetime.now()
        self.assertFalse(self.registration.needs_testing())
        
        # 오래된 테스트는 다시 필요
        self.registration.last_tested = datetime.now() - timedelta(hours=25)
        self.assertTrue(self.registration.needs_testing())
    
    def test_update_status(self):
        """상태 업데이트 테스트"""
        old_updated_at = self.registration.updated_at
        self.registration.update_status(APIStatus.ERROR)
        
        self.assertEqual(self.registration.status, APIStatus.ERROR)
        self.assertGreater(self.registration.updated_at, old_updated_at)
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        # 민감한 정보 제외
        result_dict = self.registration.to_dict(include_sensitive=False)
        self.assertNotIn("encrypted_credentials", result_dict)
        
        # 민감한 정보 포함
        result_dict = self.registration.to_dict(include_sensitive=True)
        self.assertIn("encrypted_credentials", result_dict)


class TestConnectionTestResult(unittest.TestCase):
    """ConnectionTestResult 모델 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.success_result = ConnectionTestResult(
            api_id="test_api",
            success=True,
            response_time=1.5,
            status_code=200
        )
        
        self.failure_result = ConnectionTestResult(
            api_id="test_api",
            success=False,
            response_time=5.0,
            error_message="Connection timeout",
            error_type="timeout"
        )
    
    def test_is_healthy(self):
        """건강 상태 확인 테스트"""
        self.assertTrue(self.success_result.is_healthy())
        self.assertFalse(self.failure_result.is_healthy())
    
    def test_get_status_summary(self):
        """상태 요약 테스트"""
        success_summary = self.success_result.get_status_summary()
        self.assertIn("성공", success_summary)
        self.assertIn("1.50", success_summary)
        
        failure_summary = self.failure_result.get_status_summary()
        self.assertIn("실패", failure_summary)
        self.assertIn("Connection timeout", failure_summary)
    
    def test_get_connection_status(self):
        """연결 상태 반환 테스트"""
        self.assertEqual(self.success_result.get_connection_status(), ConnectionStatus.SUCCESS)
        self.assertEqual(self.failure_result.get_connection_status(), ConnectionStatus.TIMEOUT)


class TestUsageStats(unittest.TestCase):
    """UsageStats 모델 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.stats = UsageStats(
            api_id="test_api",
            period="daily",
            start_time=datetime.now() - timedelta(days=1),
            end_time=datetime.now()
        )
    
    def test_success_rate_calculation(self):
        """성공률 계산 테스트"""
        self.assertEqual(self.stats.get_success_rate(), 0.0)  # 호출이 없을 때
        
        # 성공 호출 추가
        success_record = APICallRecord(
            api_id="test_api",
            endpoint="/test",
            method="GET",
            success=True,
            response_time=1.0
        )
        self.stats.add_call_record(success_record)
        self.assertEqual(self.stats.get_success_rate(), 100.0)
        
        # 실패 호출 추가
        failure_record = APICallRecord(
            api_id="test_api",
            endpoint="/test",
            method="GET",
            success=False,
            response_time=2.0,
            error_message="API Error"
        )
        self.stats.add_call_record(failure_record)
        self.assertEqual(self.stats.get_success_rate(), 50.0)
    
    def test_add_call_record(self):
        """호출 기록 추가 테스트"""
        record = APICallRecord(
            api_id="test_api",
            endpoint="/test",
            method="GET",
            success=True,
            response_time=1.5,
            request_size=100,
            response_size=200
        )
        
        self.stats.add_call_record(record)
        
        self.assertEqual(self.stats.total_calls, 1)
        self.assertEqual(self.stats.successful_calls, 1)
        self.assertEqual(self.stats.average_response_time, 1.5)
        self.assertEqual(self.stats.total_data_transferred, 300)


class TestRateLimitStatus(unittest.TestCase):
    """RateLimitStatus 모델 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.rate_limit = RateLimitStatus(
            api_id="test_api",
            current_usage=75,
            limit=100,
            reset_time=datetime.now() + timedelta(minutes=30),
            remaining=25
        )
    
    def test_is_exceeded(self):
        """제한 초과 여부 테스트"""
        self.assertFalse(self.rate_limit.is_exceeded())
        
        self.rate_limit.current_usage = 100
        self.assertTrue(self.rate_limit.is_exceeded())
    
    def test_get_usage_percentage(self):
        """사용률 계산 테스트"""
        self.assertEqual(self.rate_limit.get_usage_percentage(), 75.0)
    
    def test_time_until_reset(self):
        """리셋까지 시간 테스트"""
        time_left = self.rate_limit.time_until_reset()
        self.assertGreater(time_left, 0)
        self.assertLessEqual(time_left, 1800)  # 30분 이하


class TestUtilityFunctions(unittest.TestCase):
    """유틸리티 함수 테스트"""
    
    def test_generate_api_id(self):
        """API ID 생성 테스트"""
        api_id = generate_api_id("test_provider")
        self.assertIn("test_provider", api_id)
        self.assertTrue(len(api_id) > len("test_provider"))
        
        # 사용자 식별자 포함
        api_id_with_user = generate_api_id("test_provider", "user123")
        self.assertIn("test_provider", api_id_with_user)
        self.assertIn("user123", api_id_with_user)
        
        # 고유성 테스트
        api_id1 = generate_api_id("test_provider")
        api_id2 = generate_api_id("test_provider")
        self.assertNotEqual(api_id1, api_id2)
    
    def test_create_default_configuration(self):
        """기본 설정 생성 테스트"""
        config = create_default_configuration()
        
        # 필수 설정 항목 확인
        required_keys = ["timeout", "retry_count", "rate_limit", "auto_test_enabled"]
        for key in required_keys:
            self.assertIn(key, config)
        
        # 기본값 확인
        self.assertEqual(config["timeout"], 30)
        self.assertEqual(config["retry_count"], 3)
        self.assertTrue(config["auto_test_enabled"])


class TestResultModels(unittest.TestCase):
    """결과 모델 테스트"""
    
    def test_registration_result(self):
        """등록 결과 테스트"""
        result = RegistrationResult(success=True, api_id="test_001")
        self.assertTrue(result.success)
        
        result.add_error("테스트 오류")
        self.assertFalse(result.success)
        self.assertIn("테스트 오류", result.errors)
        
        result.add_warning("테스트 경고")
        self.assertIn("테스트 경고", result.warnings)
    
    def test_validation_result(self):
        """검증 결과 테스트"""
        result = ValidationResult(valid=True)
        self.assertTrue(result.valid)
        
        result.add_error("api_key", "키가 너무 짧습니다")
        self.assertFalse(result.valid)
        self.assertFalse(result.is_field_valid("api_key"))
        
        result.add_warning("endpoint", "엔드포인트가 느릴 수 있습니다")
        self.assertIn("endpoint: 엔드포인트가 느릴 수 있습니다", result.warnings)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)