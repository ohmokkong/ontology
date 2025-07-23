"""
API 등록 관리 시스템의 암호화 서비스.

AES-256-GCM 암호화와 PBKDF2 키 유도를 사용하여
API 자격증명을 안전하게 암호화/복호화합니다.
"""

import os
import base64
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional, Tuple, Any, List
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import json

from api_registration_models import EncryptedData
from exceptions import (
    EncryptionError, DecryptionError, KeyDerivationError, 
    IntegrityCheckError, MasterPasswordError
)


class EncryptionService:
    """
    AES-256-GCM 기반 암호화 서비스.
    
    API 자격증명을 안전하게 암호화하고 복호화하는 기능을 제공합니다.
    PBKDF2를 사용한 키 유도와 무결성 검증을 지원합니다.
    """
    
    def __init__(self, key_derivation_method: str = "PBKDF2"):
        """
        암호화 서비스 초기화.
        
        Args:
            key_derivation_method: 키 유도 방법 (기본값: PBKDF2)
        """
        self.key_derivation_method = key_derivation_method
        self.algorithm = "AES-256-GCM"
        self.key_length = 32  # 256 bits
        self.salt_length = 32  # 256 bits
        self.nonce_length = 12  # 96 bits (GCM 권장)
        self.iterations = 100000  # PBKDF2 반복 횟수
        
        # 마스터 패스워드 캐시 (메모리에만 저장)
        self._master_password_cache: Optional[str] = None
        self._derived_key_cache: Optional[bytes] = None
        self._current_salt: Optional[bytes] = None
    
    def _generate_salt(self) -> bytes:
        """
        암호화용 솔트 생성.
        
        Returns:
            bytes: 생성된 솔트
        """
        return secrets.token_bytes(self.salt_length)
    
    def _generate_nonce(self) -> bytes:
        """
        GCM 모드용 nonce 생성.
        
        Returns:
            bytes: 생성된 nonce
        """
        return secrets.token_bytes(self.nonce_length)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        PBKDF2를 사용한 키 유도.
        
        Args:
            password: 마스터 패스워드
            salt: 솔트
            
        Returns:
            bytes: 유도된 키
            
        Raises:
            KeyDerivationError: 키 유도 실패 시
        """
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.key_length,
                salt=salt,
                iterations=self.iterations,
                backend=default_backend()
            )
            return kdf.derive(password.encode('utf-8'))
        except Exception as e:
            raise KeyDerivationError(f"키 유도 실패: {str(e)}", "key_derivation_failed")
    
    def _get_master_password(self, master_password: Optional[str] = None) -> str:
        """
        마스터 패스워드 획득.
        
        Args:
            master_password: 제공된 마스터 패스워드
            
        Returns:
            str: 마스터 패스워드
            
        Raises:
            MasterPasswordError: 패스워드 획득 실패 시
        """
        if master_password:
            return master_password
        
        if self._master_password_cache:
            return self._master_password_cache
        
        # 환경변수에서 마스터 패스워드 확인
        env_password = os.getenv('API_MASTER_PASSWORD')
        if env_password:
            return env_password
        
        # 기본 패스워드 (실제 운영에서는 사용하지 않아야 함)
        default_password = "default_master_password_change_me"
        print("⚠️  경고: 기본 마스터 패스워드를 사용하고 있습니다. 보안을 위해 변경해주세요.")
        return default_password
    
    def set_master_password(self, password: str) -> None:
        """
        마스터 패스워드 설정.
        
        Args:
            password: 설정할 마스터 패스워드
        """
        self._master_password_cache = password
        # 캐시된 키 초기화
        self._derived_key_cache = None
        self._current_salt = None
    
    def generate_master_key(self) -> str:
        """
        새로운 마스터 키 생성.
        
        Returns:
            str: 생성된 마스터 키 (base64 인코딩)
        """
        key = secrets.token_bytes(32)  # 256-bit key
        return base64.b64encode(key).decode('utf-8')
    
    def encrypt_credentials(self, credentials: Dict[str, Any], 
                          master_password: Optional[str] = None) -> EncryptedData:
        """
        자격증명 암호화.
        
        Args:
            credentials: 암호화할 자격증명
            master_password: 마스터 패스워드 (선택사항)
            
        Returns:
            EncryptedData: 암호화된 데이터
            
        Raises:
            EncryptionError: 암호화 실패 시
        """
        try:
            # 자격증명을 JSON으로 직렬화
            credentials_json = json.dumps(credentials, ensure_ascii=False)
            credentials_bytes = credentials_json.encode('utf-8')
            
            # 솔트 생성
            salt = self._generate_salt()
            
            # 마스터 패스워드 획득
            password = self._get_master_password(master_password)
            
            # 키 유도
            key = self._derive_key(password, salt)
            
            # nonce 생성
            nonce = self._generate_nonce()
            
            # AES-GCM으로 암호화
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, credentials_bytes, None)
            
            # nonce와 ciphertext 결합
            encrypted_content = nonce + ciphertext
            
            # base64 인코딩
            encrypted_b64 = base64.b64encode(encrypted_content).decode('utf-8')
            salt_b64 = base64.b64encode(salt).decode('utf-8')
            
            return EncryptedData(
                encrypted_content=encrypted_b64,
                salt=salt_b64,
                algorithm=self.algorithm,
                key_derivation=self.key_derivation_method,
                iterations=self.iterations
            )
            
        except Exception as e:
            if isinstance(e, (KeyDerivationError, MasterPasswordError)):
                raise
            raise EncryptionError(f"암호화 실패: {str(e)}", "encryption_failed")
    
    def decrypt_credentials(self, encrypted_data: EncryptedData, 
                          master_password: Optional[str] = None) -> Dict[str, Any]:
        """
        자격증명 복호화.
        
        Args:
            encrypted_data: 암호화된 데이터
            master_password: 마스터 패스워드 (선택사항)
            
        Returns:
            Dict: 복호화된 자격증명
            
        Raises:
            DecryptionError: 복호화 실패 시
            IntegrityCheckError: 무결성 검증 실패 시
        """
        try:
            # 무결성 검증
            if not encrypted_data.verify_integrity():
                raise IntegrityCheckError("암호화된 데이터의 무결성 검증에 실패했습니다")
            
            # base64 디코딩
            encrypted_content = base64.b64decode(encrypted_data.encrypted_content)
            salt = base64.b64decode(encrypted_data.salt)
            
            # nonce와 ciphertext 분리
            nonce = encrypted_content[:self.nonce_length]
            ciphertext = encrypted_content[self.nonce_length:]
            
            # 마스터 패스워드 획득
            password = self._get_master_password(master_password)
            
            # 키 유도
            key = self._derive_key(password, salt)
            
            # AES-GCM으로 복호화
            aesgcm = AESGCM(key)
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            
            # JSON 파싱
            decrypted_json = decrypted_bytes.decode('utf-8')
            credentials = json.loads(decrypted_json)
            
            return credentials
            
        except IntegrityCheckError:
            raise
        except json.JSONDecodeError as e:
            raise DecryptionError(f"복호화된 데이터 파싱 실패: {str(e)}", "json_parsing_failed")
        except Exception as e:
            if isinstance(e, KeyDerivationError):
                raise DecryptionError(f"키 유도 실패: {str(e)}", "key_derivation_failed")
            raise DecryptionError(f"복호화 실패: {str(e)}", "decryption_failed")
    
    def rotate_encryption_key(self, old_password: str, new_password: str, 
                            encrypted_data: EncryptedData) -> EncryptedData:
        """
        암호화 키 교체.
        
        Args:
            old_password: 기존 마스터 패스워드
            new_password: 새로운 마스터 패스워드
            encrypted_data: 재암호화할 데이터
            
        Returns:
            EncryptedData: 새로운 키로 암호화된 데이터
            
        Raises:
            DecryptionError: 기존 데이터 복호화 실패 시
            EncryptionError: 새로운 키로 암호화 실패 시
        """
        try:
            # 기존 패스워드로 복호화
            credentials = self.decrypt_credentials(encrypted_data, old_password)
            
            # 새로운 패스워드로 재암호화
            return self.encrypt_credentials(credentials, new_password)
            
        except Exception as e:
            if isinstance(e, (DecryptionError, EncryptionError)):
                raise
            raise EncryptionError(f"키 교체 실패: {str(e)}", "key_rotation_failed")
    
    def verify_integrity(self, encrypted_data: EncryptedData) -> bool:
        """
        데이터 무결성 검증.
        
        Args:
            encrypted_data: 검증할 암호화된 데이터
            
        Returns:
            bool: 무결성 검증 결과
        """
        try:
            return encrypted_data.verify_integrity()
        except Exception:
            return False
    
    def verify_password(self, password: str, encrypted_data: EncryptedData) -> bool:
        """
        패스워드 검증.
        
        Args:
            password: 검증할 패스워드
            encrypted_data: 테스트용 암호화된 데이터
            
        Returns:
            bool: 패스워드 검증 결과
        """
        try:
            self.decrypt_credentials(encrypted_data, password)
            return True
        except (DecryptionError, KeyDerivationError):
            return False
    
    def create_test_data(self, master_password: Optional[str] = None) -> EncryptedData:
        """
        테스트용 암호화 데이터 생성.
        
        Args:
            master_password: 마스터 패스워드
            
        Returns:
            EncryptedData: 테스트용 암호화된 데이터
        """
        test_credentials = {
            "test_key": "test_value",
            "timestamp": datetime.now().isoformat()
        }
        return self.encrypt_credentials(test_credentials, master_password)
    
    def get_encryption_info(self) -> Dict[str, Any]:
        """
        암호화 설정 정보 반환.
        
        Returns:
            Dict: 암호화 설정 정보
        """
        return {
            "algorithm": self.algorithm,
            "key_derivation": self.key_derivation_method,
            "key_length": self.key_length,
            "salt_length": self.salt_length,
            "iterations": self.iterations,
            "nonce_length": self.nonce_length
        }
    
    def clear_cache(self) -> None:
        """캐시된 패스워드와 키 정보 삭제."""
        self._master_password_cache = None
        self._derived_key_cache = None
        self._current_salt = None
    
    def __del__(self):
        """소멸자에서 캐시 정리."""
        self.clear_cache()


class PasswordManager:
    """
    마스터 패스워드 관리 유틸리티.
    
    마스터 패스워드의 생성, 검증, 변경 등을 관리합니다.
    """
    
    @staticmethod
    def generate_strong_password(length: int = 32) -> str:
        """
        강력한 패스워드 생성.
        
        Args:
            length: 패스워드 길이
            
        Returns:
            str: 생성된 패스워드
        """
        import string
        
        # 문자 집합 정의
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # 각 문자 집합에서 최소 하나씩 포함
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(symbols)
        ]
        
        # 나머지 길이만큼 랜덤 문자 추가
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # 순서 섞기
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
        """
        패스워드 강도 검증.
        
        Args:
            password: 검증할 패스워드
            
        Returns:
            Tuple[bool, List[str]]: (검증 결과, 개선 사항 목록)
        """
        issues = []
        
        if len(password) < 12:
            issues.append("패스워드는 최소 12자 이상이어야 합니다")
        
        if not any(c.islower() for c in password):
            issues.append("소문자를 포함해야 합니다")
        
        if not any(c.isupper() for c in password):
            issues.append("대문자를 포함해야 합니다")
        
        if not any(c.isdigit() for c in password):
            issues.append("숫자를 포함해야 합니다")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            issues.append("특수문자를 포함해야 합니다")
        
        # 연속된 문자 검사 (알파벳과 숫자만)
        for i in range(len(password) - 2):
            if (password[i].isalnum() and password[i+1].isalnum() and password[i+2].isalnum()):
                if (ord(password[i+1]) == ord(password[i]) + 1 and 
                    ord(password[i+2]) == ord(password[i]) + 2):
                    issues.append("연속된 문자는 피해주세요")
                    break
        
        # 반복 문자 검사
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                issues.append("같은 문자의 반복은 피해주세요")
                break
        
        return len(issues) == 0, issues
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
        """
        패스워드 해싱 (저장용).
        
        Args:
            password: 해싱할 패스워드
            salt: 솔트 (선택사항)
            
        Returns:
            Tuple[str, str]: (해시된 패스워드, 솔트) - 모두 base64 인코딩
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        # PBKDF2로 해싱
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        password_hash = kdf.derive(password.encode('utf-8'))
        
        return (
            base64.b64encode(password_hash).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )
    
    @staticmethod
    def verify_password_hash(password: str, password_hash: str, salt: str) -> bool:
        """
        패스워드 해시 검증.
        
        Args:
            password: 검증할 패스워드
            password_hash: 저장된 해시 (base64)
            salt: 솔트 (base64)
            
        Returns:
            bool: 검증 결과
        """
        try:
            salt_bytes = base64.b64decode(salt)
            expected_hash, _ = PasswordManager.hash_password(password, salt_bytes)
            return expected_hash == password_hash
        except Exception:
            return False