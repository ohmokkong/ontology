"""
검증 서비스 테스트.

ValidationService의 기능을 테스트합니다.
"""

import unittest
from unittest.mock import patch
import json

from validation_service import ValidationService, ValidationResult
from api_registration_models import APIProvider, AuthType
from exceptions import RegistrationValidationError


class TestValidationResult(unittest.TestCase):
    """ValidationResult 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.result = ValidationResult(
            valid=True,
            errors=[],
            warnings=[],
            field_results={},
            suggestions=[]
        )
    
    def test_add_error(self):
        """오류 추가 테스트"""
        self.result.add_error("api_key", "키가 너무 짧습니다", "최소 8자 이상 입력하세요")
        
        self.assertFalse(self.result.valid)
        self.assertEqual(len(self.result.errors), 1)
        self.assertIn("api_key: 키가 너무 짧습니다", self.result.errors)
        self.assertFalse(self.result.is_field_valid("api_key"))
        self.assertIn("api_key: 최소 8자 이상 입력하세요", self.result.suggestions)
    
    def test_add_warning(self):
        """경고 추가 테스트"""
        self.result.add_warning("timeout", "타임아웃이 길습니다", "30초 이하를 권장합니다")
        
        self.assertTrue(self.result.valid)  # 경고는 valid 상태를 변경하지 않음
        self.assertEqual(len(self.result.warnings), 1)
        self.assertIn("timeout: 타임아웃이 길습니다", self.result.warnings)
        self.assertIn("timeout: 30초 이하를 권장합니다", self.result.suggestions)
    
    def test_get_counts(self):
        """개수 조회 테스트"""
        self.result.add_error("field1", "오류1")
        self.result.add_error("field2", "오류2")
        self.result.add_warning("field3", "경고1")
        
        self.assertEqual(self.result.get_error_count(), 2)
        self.assertEqual(self.result.get_warning_count(), 1)
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        self.result.add_error("api_key", "오류")
        self.result.add_warning("timeout", "경고")
        
        result_dict = self.result.to_dict()
        
        required_keys = ["valid", "errors", "warnings", "field_results", 
                        "suggestions", "error_count", "warning_count"]
        for key in required_keys:
            self.assertIn(key, result_dict)
        
        self.assertFalse(result_dict["valid"])
        self.assertEqual(result_dict["error_count"], 1)
        self.assertEqual(result_dict["warning_count"], 1)


class TestValidationService(unittest.TestCase):
    """ValidationService 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.validation_service = ValidationService()
        
        # 테스트용 API 제공업체
        self.test_provider = APIProvider(
            name="test_provider",
            display_name="테스트 제공업체",
            base_url="https://api.test.com",
            auth_type=AuthType.API_KEY,
            required_fields=["api_key"],
            optional_fields=["service_id"]
        )
        
        self.food_provider = APIProvider(
            name="food_safety_korea",
            display_name="식약처 API",
            base_url="https://openapi.foodsafetykorea.go.kr/api",
            auth_type=AuthType.API_KEY,
            required_fields=["api_key"]
        )
    
    def test_validate_api_credentials_success(self):
        """API 자격증명 검증 성공 테스트"""
        credentials = {
            "api_key": "validapikey12345678901234567890123456789012345678"  # 50자, 언더스코어 제거
        }
        
        result = self.validation_service.validate_api_credentials(
            self.food_provider, credentials
        )
        
        # 디버깅을 위해 오류 출력
        if not result.valid:
            print(f"검증 실패 - 오류: {result.errors}")
            print(f"경고: {result.warnings}")
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_api_credentials_missing_required(self):
        """필수 필드 누락 테스트"""
        credentials = {
            "service_id": "test_service"  # api_key 누락
        }
        
        result = self.validation_service.validate_api_credentials(
            self.food_provider, credentials
        )
        
        self.assertFalse(result.valid)
        self.assertGreater(len(result.errors), 0)
        self.assertFalse(result.is_field_valid("api_key"))
    
    def test_validate_api_credentials_invalid_length(self):
        """API 키 길이 검증 실패 테스트"""
        credentials = {
            "api_key": "short"  # 너무 짧음 (20자 미만)
        }
        
        result = self.validation_service.validate_api_credentials(
            self.food_provider, credentials
        )
        
        self.assertFalse(result.valid)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("최소", result.errors[0])
    
    def test_validate_api_credentials_invalid_pattern(self):
        """API 키 패턴 검증 실패 테스트"""
        credentials = {
            "api_key": "invalid_key_with_special_chars!@#$%"  # 특수문자 포함
        }
        
        result = self.validation_service.validate_api_credentials(
            self.food_provider, credentials
        )
        
        self.assertFalse(result.valid)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("형식", result.errors[0])
    
    def test_validate_api_credentials_unknown_field(self):
        """알 수 없는 필드 경고 테스트"""
        credentials = {
            "api_key": "validapikey12345678901234567890123456789012345678",  # 50자, 언더스코어 제거
            "unknown_field": "some_value"
        }
        
        result = self.validation_service.validate_api_credentials(
            self.food_provider, credentials
        )
        
        self.assertTrue(result.valid)  # 경고는 valid를 false로 만들지 않음
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("알 수 없는 필드", result.warnings[0])
    
    def test_validate_api_key_format_simple(self):
        """간단한 API 키 형식 검증 테스트"""
        # 유효한 키
        self.assertTrue(
            self.validation_service.validate_api_key_format(
                "food_safety_korea", 
                "validapikey12345678901234567890123456789012345678"  # 50자, 언더스코어 제거
            )
        )
        
        # 너무 짧은 키
        self.assertFalse(
            self.validation_service.validate_api_key_format(
                "food_safety_korea", 
                "short"
            )
        )
        
        # 빈 키
        self.assertFalse(
            self.validation_service.validate_api_key_format(
                "food_safety_korea", 
                ""
            )
        )
    
    def test_validate_endpoint_url_success(self):
        """엔드포인트 URL 검증 성공 테스트"""
        valid_urls = [
            "https://api.example.com/v1/data",
            "http://localhost:8080/api",
            "https://192.168.1.1:3000/endpoint"
        ]
        
        for url in valid_urls:
            result = self.validation_service.validate_endpoint_url(url)
            self.assertTrue(result.valid, f"URL should be valid: {url}")
    
    def test_validate_endpoint_url_invalid_scheme(self):
        """잘못된 프로토콜 URL 테스트"""
        invalid_url = "ftp://example.com/data"
        
        result = self.validation_service.validate_endpoint_url(invalid_url)
        
        self.assertFalse(result.valid)
        self.assertIn("지원하지 않는 프로토콜", result.errors[0])
    
    def test_validate_endpoint_url_no_host(self):
        """호스트 없는 URL 테스트"""
        invalid_url = "https:///path/to/resource"
        
        result = self.validation_service.validate_endpoint_url(invalid_url)
        
        self.assertFalse(result.valid)
        self.assertIn("호스트가 지정되지 않았습니다", result.errors[0])
    
    def test_validate_endpoint_url_http_warning(self):
        """HTTP 프로토콜 경고 테스트"""
        http_url = "http://api.example.com/data"
        
        result = self.validation_service.validate_endpoint_url(http_url)
        
        self.assertTrue(result.valid)  # 유효하지만 경고 있음
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("HTTP 프로토콜은 보안에 취약", result.warnings[0])
    
    def test_validate_endpoint_url_private_ip_warning(self):
        """사설 IP 경고 테스트"""
        private_ip_url = "https://192.168.1.100/api"
        
        result = self.validation_service.validate_endpoint_url(private_ip_url)
        
        self.assertTrue(result.valid)
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("사설 IP 주소", result.warnings[0])
    
    def test_validate_endpoint_url_localhost_warning(self):
        """로컬호스트 경고 테스트"""
        localhost_url = "https://127.0.0.1:8080/api"
        
        result = self.validation_service.validate_endpoint_url(localhost_url)
        
        self.assertTrue(result.valid)
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("로컬호스트 주소", result.warnings[0])
    
    def test_validate_endpoint_url_invalid_port(self):
        """잘못된 포트 번호 테스트"""
        invalid_port_url = "https://example.com:99999/api"
        
        result = self.validation_service.validate_endpoint_url(invalid_port_url)
        
        self.assertFalse(result.valid)
        # 포트 범위 오류 또는 파싱 오류 모두 허용
        error_found = any("포트" in error or "Port out of range" in error for error in result.errors)
        self.assertTrue(error_found, f"포트 관련 오류를 찾을 수 없습니다: {result.errors}")
    
    def test_validate_endpoint_url_reserved_port_warning(self):
        """예약된 포트 경고 테스트"""
        reserved_port_url = "https://example.com:22/api"
        
        result = self.validation_service.validate_endpoint_url(reserved_port_url)
        
        self.assertTrue(result.valid)
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("예약된 포트 번호", result.warnings[0])
    
    def test_validate_endpoint_url_dangerous_path(self):
        """위험한 경로 패턴 테스트"""
        dangerous_url = "https://example.com/../../../etc/passwd"
        
        result = self.validation_service.validate_endpoint_url(dangerous_url)
        
        self.assertTrue(result.valid)  # 유효하지만 경고
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("잠재적으로 위험한 경로", result.warnings[0])
    
    def test_validate_configuration_success(self):
        """설정 검증 성공 테스트"""
        valid_config = {
            "timeout": 30,
            "retry_count": 3,
            "rate_limit": 1000,
            "cache_ttl": 300,
            "log_level": "INFO"
        }
        
        result = self.validation_service.validate_configuration(valid_config)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_configuration_invalid_timeout(self):
        """잘못된 타임아웃 설정 테스트"""
        invalid_configs = [
            {"timeout": 0},      # 0 이하
            {"timeout": -5},     # 음수
            {"timeout": "abc"},  # 문자열
            {"timeout": 500}     # 너무 큰 값 (경고)
        ]
        
        for config in invalid_configs:
            result = self.validation_service.validate_configuration(config)
            if config["timeout"] == 500:
                # 경고만 있고 유효함
                self.assertTrue(result.valid)
                self.assertGreater(len(result.warnings), 0)
            else:
                # 오류가 있어서 무효함
                self.assertFalse(result.valid)
                self.assertGreater(len(result.errors), 0)
    
    def test_validate_configuration_invalid_retry_count(self):
        """잘못된 재시도 횟수 테스트"""
        invalid_config = {"retry_count": -1}
        
        result = self.validation_service.validate_configuration(invalid_config)
        
        self.assertFalse(result.valid)
        self.assertIn("재시도 횟수는 0 이상", result.errors[0])
    
    def test_validate_configuration_invalid_log_level(self):
        """잘못된 로그 레벨 테스트"""
        invalid_config = {"log_level": "INVALID_LEVEL"}
        
        result = self.validation_service.validate_configuration(invalid_config)
        
        self.assertFalse(result.valid)
        self.assertIn("올바르지 않은 로그 레벨", result.errors[0])
    
    def test_validate_json_format_success(self):
        """JSON 형식 검증 성공 테스트"""
        valid_json = '{"key": "value", "number": 123, "array": [1, 2, 3]}'
        
        result = self.validation_service.validate_json_format(valid_json)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_json_format_invalid(self):
        """JSON 형식 검증 실패 테스트"""
        invalid_json = '{"key": "value", "invalid": }'
        
        result = self.validation_service.validate_json_format(invalid_json)
        
        self.assertFalse(result.valid)
        self.assertIn("JSON 형식 오류", result.errors[0])
    
    def test_validate_json_format_empty(self):
        """빈 JSON 테스트"""
        empty_json = ""
        
        result = self.validation_service.validate_json_format(empty_json)
        
        self.assertFalse(result.valid)
        self.assertIn("JSON 데이터가 비어있습니다", result.errors[0])
    
    def test_get_validation_rules(self):
        """검증 규칙 조회 테스트"""
        rules = self.validation_service.get_validation_rules("food_safety_korea")
        
        self.assertIn("api_key", rules)
        self.assertIn("required", rules["api_key"])
        self.assertTrue(rules["api_key"]["required"])
    
    def test_add_custom_validation_rule(self):
        """커스텀 검증 규칙 추가 테스트"""
        custom_rules = {
            "required": True,
            "min_length": 5,
            "max_length": 20,
            "description": "커스텀 필드는 5-20자여야 합니다"
        }
        
        self.validation_service.add_custom_validation_rule(
            "custom_provider", "custom_field", custom_rules
        )
        
        provider_rules = self.validation_service.get_validation_rules("custom_provider")
        self.assertIn("custom_field", provider_rules)
        self.assertEqual(provider_rules["custom_field"]["min_length"], 5)
    
    def test_get_validation_summary(self):
        """검증 결과 요약 테스트"""
        results = []
        
        # 성공 결과
        success_result = ValidationResult(True, [], [], {}, [])
        results.append(success_result)
        
        # 실패 결과
        fail_result = ValidationResult(False, ["오류1", "오류2"], ["경고1"], {}, [])
        results.append(fail_result)
        
        summary = self.validation_service.get_validation_summary(results)
        
        self.assertEqual(summary["total_validations"], 2)
        self.assertEqual(summary["valid_count"], 1)
        self.assertEqual(summary["invalid_count"], 1)
        self.assertEqual(summary["total_errors"], 2)
        self.assertEqual(summary["total_warnings"], 1)
        self.assertEqual(summary["success_rate"], 50.0)
        self.assertTrue(summary["has_errors"])
        self.assertTrue(summary["has_warnings"])


class TestOAuthValidation(unittest.TestCase):
    """OAuth 관련 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.validation_service = ValidationService()
        self.oauth_provider = APIProvider(
            name="oauth_test",
            display_name="OAuth 테스트",
            base_url="https://oauth.example.com",
            auth_type=AuthType.OAUTH,
            required_fields=["client_id", "client_secret"]
        )
    
    def test_validate_oauth_credentials_success(self):
        """OAuth 자격증명 검증 성공 테스트"""
        credentials = {
            "client_id": "valid_client_id_12345",
            "client_secret": "valid_client_secret_1234567890123456"
        }
        
        result = self.validation_service.validate_api_credentials(
            self.oauth_provider, credentials
        )
        
        self.assertTrue(result.valid)
    
    def test_validate_jwt_token_valid(self):
        """유효한 JWT 토큰 테스트"""
        # 실제 JWT 형식 (테스트용)
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        credentials = {
            "client_id": "valid_client_id_12345",
            "client_secret": "valid_client_secret_1234567890123456",
            "access_token": valid_jwt
        }
        
        result = self.validation_service.validate_api_credentials(
            self.oauth_provider, credentials
        )
        
        self.assertTrue(result.valid)
    
    def test_validate_jwt_token_invalid_format(self):
        """잘못된 JWT 토큰 형식 테스트"""
        invalid_jwt = "invalid.jwt"  # 3개 부분이 아님
        
        credentials = {
            "client_id": "valid_client_id_12345",
            "client_secret": "valid_client_secret_1234567890123456",
            "access_token": invalid_jwt
        }
        
        result = self.validation_service.validate_api_credentials(
            self.oauth_provider, credentials
        )
        
        self.assertFalse(result.valid)
        self.assertIn("JWT 토큰 형식", result.errors[0])
    
    def test_validate_bearer_token_warning(self):
        """Bearer 토큰 접두사 경고 테스트"""
        # ValidationService에 bearer_token 규칙 추가
        self.validation_service.add_custom_validation_rule(
            "bearer_test", "token", {
                "required": True,
                "min_length": 10,
                "max_length": 500
            }
        )
        
        bearer_provider = APIProvider(
            name="bearer_test",
            display_name="Bearer 테스트",
            base_url="https://api.example.com",
            auth_type=AuthType.BEARER_TOKEN,
            required_fields=["token"]
        )
        
        credentials = {
            "token": "Bearer actual_token_value"
        }
        
        result = self.validation_service.validate_api_credentials(
            bearer_provider, credentials
        )
        
        self.assertTrue(result.valid)  # 유효하지만 경고
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("Bearer", result.warnings[0])


class TestSecurityValidation(unittest.TestCase):
    """보안 검증 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.validation_service = ValidationService()
        self.basic_auth_provider = APIProvider(
            name="basic_auth_test",
            display_name="Basic Auth 테스트",
            base_url="https://api.example.com",
            auth_type=AuthType.BASIC_AUTH,
            required_fields=["username", "password"]
        )
    
    def test_validate_weak_password_warning(self):
        """약한 패스워드 경고 테스트"""
        weak_credentials = {
            "username": "testuser",
            "password": "password123"  # 약한 패스워드 패턴
        }
        
        result = self.validation_service.validate_api_credentials(
            self.basic_auth_provider, weak_credentials
        )
        
        self.assertTrue(result.valid)  # 유효하지만 경고
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("약한 패스워드", result.warnings[0])
    
    def test_validate_short_security_field_warning(self):
        """짧은 보안 필드 경고 테스트"""
        short_credentials = {
            "username": "testuser",
            "password": "short"  # 8자 미만
        }
        
        result = self.validation_service.validate_api_credentials(
            self.basic_auth_provider, short_credentials
        )
        
        self.assertTrue(result.valid)  # 유효하지만 경고
        self.assertGreater(len(result.warnings), 0)
        self.assertIn("8자 이상", result.warnings[0])


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)