"""
암호화 서비스 테스트.

EncryptionService와 PasswordManager의 기능을 테스트합니다.
"""

import unittest
import os
import tempfile
from unittest.mock import patch
from datetime import datetime

from encryption_service import EncryptionService, PasswordManager
from api_registration_models import EncryptedData
from exceptions import (
    EncryptionError, DecryptionError, KeyDerivationError, 
    IntegrityCheckError, MasterPasswordError
)


class TestEncryptionService(unittest.TestCase):
    """EncryptionService 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.encryption_service = EncryptionService()
        self.test_credentials = {
            "api_key": "test_api_key_12345",
            "service_id": "test_service",
            "endpoint": "https://api.test.com"
        }
        self.test_password = "test_master_password_123!"
    
    def test_encrypt_decrypt_success(self):
        """암호화/복호화 성공 테스트"""
        # 암호화
        encrypted_data = self.encryption_service.encrypt_credentials(
            self.test_credentials, self.test_password
        )
        
        # 암호화 데이터 검증
        self.assertIsInstance(encrypted_data, EncryptedData)
        self.assertTrue(len(encrypted_data.encrypted_content) > 0)
        self.assertTrue(len(encrypted_data.salt) > 0)
        self.assertEqual(encrypted_data.algorithm, "AES-256-GCM")
        
        # 복호화
        decrypted_credentials = self.encryption_service.decrypt_credentials(
            encrypted_data, self.test_password
        )
        
        # 복호화 결과 검증
        self.assertEqual(decrypted_credentials, self.test_credentials)
    
    def test_decrypt_with_wrong_password(self):
        """잘못된 패스워드로 복호화 시도 테스트"""
        encrypted_data = self.encryption_service.encrypt_credentials(
            self.test_credentials, self.test_password
        )
        
        with self.assertRaises(DecryptionError):
            self.encryption_service.decrypt_credentials(
                encrypted_data, "wrong_password"
            )
    
    def test_integrity_verification(self):
        """무결성 검증 테스트"""
        encrypted_data = self.encryption_service.encrypt_credentials(
            self.test_credentials, self.test_password
        )
        
        # 정상 무결성 검증
        self.assertTrue(self.encryption_service.verify_integrity(encrypted_data))
        
        # 데이터 변조 후 무결성 검증 실패
        encrypted_data.encrypted_content = "tampered_data"
        self.assertFalse(self.encryption_service.verify_integrity(encrypted_data))
    
    def test_integrity_check_during_decryption(self):
        """복호화 시 무결성 검사 테스트"""
        encrypted_data = self.encryption_service.encrypt_credentials(
            self.test_credentials, self.test_password
        )
        
        # 데이터 변조
        encrypted_data.encrypted_content = "tampered_data"
        
        with self.assertRaises(IntegrityCheckError):
            self.encryption_service.decrypt_credentials(
                encrypted_data, self.test_password
            )
    
    def test_key_rotation(self):
        """키 교체 테스트"""
        old_password = "old_password_123!"
        new_password = "new_password_456!"
        
        # 기존 패스워드로 암호화
        encrypted_data = self.encryption_service.encrypt_credentials(
            self.test_credentials, old_password
        )
        
        # 키 교체
        rotated_data = self.encryption_service.rotate_encryption_key(
            old_password, new_password, encrypted_data
        )
        
        # 새로운 패스워드로 복호화 가능 확인
        decrypted_credentials = self.encryption_service.decrypt_credentials(
            rotated_data, new_password
        )
        self.assertEqual(decrypted_credentials, self.test_credentials)
        
        # 기존 패스워드로는 복호화 불가 확인
        with self.assertRaises(DecryptionError):
            self.encryption_service.decrypt_credentials(
                rotated_data, old_password
            )
    
    def test_password_verification(self):
        """패스워드 검증 테스트"""
        encrypted_data = self.encryption_service.encrypt_credentials(
            self.test_credentials, self.test_password
        )
        
        # 올바른 패스워드 검증
        self.assertTrue(self.encryption_service.verify_password(
            self.test_password, encrypted_data
        ))
        
        # 잘못된 패스워드 검증
        self.assertFalse(self.encryption_service.verify_password(
            "wrong_password", encrypted_data
        ))
    
    def test_master_password_from_environment(self):
        """환경변수에서 마스터 패스워드 로드 테스트"""
        env_password = "env_master_password_789!"
        
        with patch.dict(os.environ, {'API_MASTER_PASSWORD': env_password}):
            # 환경변수 패스워드로 암호화
            encrypted_data = self.encryption_service.encrypt_credentials(
                self.test_credentials
            )
            
            # 환경변수 패스워드로 복호화
            decrypted_credentials = self.encryption_service.decrypt_credentials(
                encrypted_data
            )
            
            self.assertEqual(decrypted_credentials, self.test_credentials)
    
    def test_set_master_password(self):
        """마스터 패스워드 설정 테스트"""
        password = "set_master_password_abc!"
        self.encryption_service.set_master_password(password)
        
        # 설정된 패스워드로 암호화/복호화
        encrypted_data = self.encryption_service.encrypt_credentials(
            self.test_credentials
        )
        
        decrypted_credentials = self.encryption_service.decrypt_credentials(
            encrypted_data
        )
        
        self.assertEqual(decrypted_credentials, self.test_credentials)
    
    def test_generate_master_key(self):
        """마스터 키 생성 테스트"""
        key1 = self.encryption_service.generate_master_key()
        key2 = self.encryption_service.generate_master_key()
        
        # 키가 생성되고 고유함
        self.assertTrue(len(key1) > 0)
        self.assertTrue(len(key2) > 0)
        self.assertNotEqual(key1, key2)
        
        # base64 인코딩 확인
        import base64
        try:
            base64.b64decode(key1)
            base64.b64decode(key2)
        except Exception:
            self.fail("생성된 키가 올바른 base64 형식이 아닙니다")
    
    def test_create_test_data(self):
        """테스트 데이터 생성 테스트"""
        test_data = self.encryption_service.create_test_data(self.test_password)
        
        self.assertIsInstance(test_data, EncryptedData)
        
        # 테스트 데이터 복호화 확인
        decrypted = self.encryption_service.decrypt_credentials(
            test_data, self.test_password
        )
        
        self.assertIn("test_key", decrypted)
        self.assertIn("timestamp", decrypted)
    
    def test_get_encryption_info(self):
        """암호화 정보 조회 테스트"""
        info = self.encryption_service.get_encryption_info()
        
        required_keys = [
            "algorithm", "key_derivation", "key_length", 
            "salt_length", "iterations", "nonce_length"
        ]
        
        for key in required_keys:
            self.assertIn(key, info)
        
        self.assertEqual(info["algorithm"], "AES-256-GCM")
        self.assertEqual(info["key_derivation"], "PBKDF2")
        self.assertEqual(info["key_length"], 32)
    
    def test_clear_cache(self):
        """캐시 정리 테스트"""
        self.encryption_service.set_master_password("test_password")
        self.encryption_service.clear_cache()
        
        # 캐시가 정리되었는지 확인 (내부 상태 확인)
        self.assertIsNone(self.encryption_service._master_password_cache)
        self.assertIsNone(self.encryption_service._derived_key_cache)
    
    def test_empty_credentials(self):
        """빈 자격증명 암호화 테스트"""
        empty_credentials = {}
        
        encrypted_data = self.encryption_service.encrypt_credentials(
            empty_credentials, self.test_password
        )
        
        decrypted_credentials = self.encryption_service.decrypt_credentials(
            encrypted_data, self.test_password
        )
        
        self.assertEqual(decrypted_credentials, empty_credentials)
    
    def test_complex_credentials(self):
        """복잡한 자격증명 암호화 테스트"""
        complex_credentials = {
            "api_key": "complex_api_key_with_special_chars_!@#$%",
            "nested_data": {
                "sub_key": "sub_value",
                "numbers": [1, 2, 3, 4, 5],
                "boolean": True
            },
            "unicode_text": "한글 텍스트 테스트 🔐",
            "timestamp": datetime.now().isoformat()
        }
        
        encrypted_data = self.encryption_service.encrypt_credentials(
            complex_credentials, self.test_password
        )
        
        decrypted_credentials = self.encryption_service.decrypt_credentials(
            encrypted_data, self.test_password
        )
        
        self.assertEqual(decrypted_credentials, complex_credentials)


class TestPasswordManager(unittest.TestCase):
    """PasswordManager 테스트"""
    
    def test_generate_strong_password(self):
        """강력한 패스워드 생성 테스트"""
        password = PasswordManager.generate_strong_password()
        
        # 기본 길이 확인
        self.assertEqual(len(password), 32)
        
        # 다양한 문자 포함 확인
        self.assertTrue(any(c.islower() for c in password))
        self.assertTrue(any(c.isupper() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
        self.assertTrue(any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password))
        
        # 고유성 확인
        password2 = PasswordManager.generate_strong_password()
        self.assertNotEqual(password, password2)
    
    def test_generate_password_custom_length(self):
        """사용자 정의 길이 패스워드 생성 테스트"""
        length = 16
        password = PasswordManager.generate_strong_password(length)
        self.assertEqual(len(password), length)
    
    def test_validate_password_strength_strong(self):
        """강력한 패스워드 검증 테스트"""
        strong_password = "StrongP@ssW9rd135!"
        is_strong, issues = PasswordManager.validate_password_strength(strong_password)
        
        # 디버깅을 위해 문제점 출력
        if not is_strong:
            print(f"패스워드 '{strong_password}'의 문제점: {issues}")
        
        self.assertTrue(is_strong)
        self.assertEqual(len(issues), 0)
    
    def test_validate_password_strength_weak(self):
        """약한 패스워드 검증 테스트"""
        weak_password = "weak"
        is_strong, issues = PasswordManager.validate_password_strength(weak_password)
        
        self.assertFalse(is_strong)
        self.assertGreater(len(issues), 0)
        
        # 예상되는 문제점들 확인
        issues_text = " ".join(issues)
        self.assertIn("12자 이상", issues_text)
        self.assertIn("대문자", issues_text)
        self.assertIn("숫자", issues_text)
        self.assertIn("특수문자", issues_text)
    
    def test_validate_password_consecutive_chars(self):
        """연속 문자 패스워드 검증 테스트"""
        consecutive_password = "Password123abc!"
        is_strong, issues = PasswordManager.validate_password_strength(consecutive_password)
        
        self.assertFalse(is_strong)
        self.assertTrue(any("연속된 문자" in issue for issue in issues))
    
    def test_validate_password_repeated_chars(self):
        """반복 문자 패스워드 검증 테스트"""
        repeated_password = "Passwordaaa123!"
        is_strong, issues = PasswordManager.validate_password_strength(repeated_password)
        
        self.assertFalse(is_strong)
        self.assertTrue(any("반복" in issue for issue in issues))
    
    def test_hash_password(self):
        """패스워드 해싱 테스트"""
        password = "test_password_123!"
        
        # 해싱
        password_hash, salt = PasswordManager.hash_password(password)
        
        # 결과 확인
        self.assertTrue(len(password_hash) > 0)
        self.assertTrue(len(salt) > 0)
        
        # base64 인코딩 확인
        import base64
        try:
            base64.b64decode(password_hash)
            base64.b64decode(salt)
        except Exception:
            self.fail("해시나 솔트가 올바른 base64 형식이 아닙니다")
        
        # 같은 패스워드, 다른 솔트로 다른 해시 생성 확인
        password_hash2, salt2 = PasswordManager.hash_password(password)
        self.assertNotEqual(password_hash, password_hash2)
        self.assertNotEqual(salt, salt2)
    
    def test_verify_password_hash(self):
        """패스워드 해시 검증 테스트"""
        password = "test_password_456!"
        
        # 해싱
        password_hash, salt = PasswordManager.hash_password(password)
        
        # 올바른 패스워드 검증
        self.assertTrue(PasswordManager.verify_password_hash(
            password, password_hash, salt
        ))
        
        # 잘못된 패스워드 검증
        self.assertFalse(PasswordManager.verify_password_hash(
            "wrong_password", password_hash, salt
        ))
    
    def test_hash_with_custom_salt(self):
        """사용자 정의 솔트로 해싱 테스트"""
        password = "test_password_789!"
        custom_salt = b"custom_salt_1234567890123456789012"  # 32 bytes
        
        password_hash, salt = PasswordManager.hash_password(password, custom_salt)
        
        # 솔트가 제공된 것과 일치하는지 확인
        import base64
        self.assertEqual(base64.b64decode(salt), custom_salt)
        
        # 검증 확인
        self.assertTrue(PasswordManager.verify_password_hash(
            password, password_hash, salt
        ))


class TestEncryptionIntegration(unittest.TestCase):
    """암호화 서비스 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.encryption_service = EncryptionService()
        self.password_manager = PasswordManager()
    
    def test_full_encryption_workflow(self):
        """전체 암호화 워크플로우 테스트"""
        # 1. 강력한 패스워드 생성
        master_password = self.password_manager.generate_strong_password()
        
        # 2. 패스워드 강도 검증
        is_strong, issues = self.password_manager.validate_password_strength(master_password)
        self.assertTrue(is_strong, f"생성된 패스워드가 약함: {issues}")
        
        # 3. 패스워드 해싱 (저장용)
        password_hash, salt = self.password_manager.hash_password(master_password)
        
        # 4. 자격증명 암호화
        credentials = {
            "api_key": "production_api_key_12345",
            "secret": "super_secret_value",
            "config": {"timeout": 30, "retries": 3}
        }
        
        encrypted_data = self.encryption_service.encrypt_credentials(
            credentials, master_password
        )
        
        # 5. 무결성 검증
        self.assertTrue(self.encryption_service.verify_integrity(encrypted_data))
        
        # 6. 패스워드 검증 (저장된 해시 사용)
        self.assertTrue(self.password_manager.verify_password_hash(
            master_password, password_hash, salt
        ))
        
        # 7. 복호화
        decrypted_credentials = self.encryption_service.decrypt_credentials(
            encrypted_data, master_password
        )
        
        # 8. 결과 검증
        self.assertEqual(decrypted_credentials, credentials)
    
    def test_multiple_credentials_encryption(self):
        """여러 자격증명 암호화 테스트"""
        master_password = "multi_test_password_123!"
        
        credentials_list = [
            {"api_key": "food_api_key", "service": "food_service"},
            {"api_key": "exercise_api_key", "service": "exercise_service"},
            {"oauth_token": "oauth_token_123", "refresh_token": "refresh_123"}
        ]
        
        encrypted_list = []
        
        # 모든 자격증명 암호화
        for credentials in credentials_list:
            encrypted_data = self.encryption_service.encrypt_credentials(
                credentials, master_password
            )
            encrypted_list.append(encrypted_data)
        
        # 모든 자격증명 복호화 및 검증
        for i, encrypted_data in enumerate(encrypted_list):
            decrypted = self.encryption_service.decrypt_credentials(
                encrypted_data, master_password
            )
            self.assertEqual(decrypted, credentials_list[i])
    
    def test_password_change_scenario(self):
        """패스워드 변경 시나리오 테스트"""
        old_password = "old_master_password_123!"
        new_password = "new_master_password_456!"
        
        credentials = {"api_key": "test_key", "secret": "test_secret"}
        
        # 기존 패스워드로 암호화
        encrypted_data = self.encryption_service.encrypt_credentials(
            credentials, old_password
        )
        
        # 패스워드 변경 (키 교체)
        rotated_data = self.encryption_service.rotate_encryption_key(
            old_password, new_password, encrypted_data
        )
        
        # 새 패스워드로 복호화 확인
        decrypted = self.encryption_service.decrypt_credentials(
            rotated_data, new_password
        )
        self.assertEqual(decrypted, credentials)
        
        # 기존 패스워드로는 복호화 불가 확인
        with self.assertRaises(DecryptionError):
            self.encryption_service.decrypt_credentials(
                rotated_data, old_password
            )


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)