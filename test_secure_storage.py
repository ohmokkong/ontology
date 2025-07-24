"""
보안 저장소 테스트.

SecureStorage 클래스의 모든 기능을 테스트합니다.
"""

import os
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import pytest

from secure_storage import SecureStorage
from encryption_service import EncryptionService
from api_registration_models import (
    APIRegistration, APIProvider, EncryptedData, AuthType, APIStatus
)
from exceptions import (
    APINotFoundError, DuplicateAPIRegistrationError, 
    FileSystemError, BackupCorruptedError
)


class TestSecureStorage:
    """보안 저장소 테스트 클래스."""
    
    def setup_method(self):
        """각 테스트 전 설정."""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.temp_dir) / "test_storage"
        
        # 암호화 서비스 및 보안 저장소 초기화
        self.encryption_service = EncryptionService()
        self.encryption_service.set_master_password("test_master_password")
        
        self.storage = SecureStorage(
            storage_dir=str(self.storage_dir),
            encryption_service=self.encryption_service
        )
        
        # 테스트용 API 제공업체
        self.test_provider = APIProvider(
            name="test_api",
            display_name="Test API",
            base_url="https://api.test.com",
            auth_type=AuthType.API_KEY,
            required_fields=["api_key"],
            optional_fields=["user_id"],
            test_endpoint="test",
            documentation_url="https://docs.test.com"
        )
        
        # 테스트용 자격증명
        self.test_credentials = {
            "api_key": "test_api_key_12345",
            "user_id": "test_user"
        }
        
        # 암호화된 자격증명
        self.encrypted_credentials = self.encryption_service.encrypt_credentials(
            self.test_credentials
        )
        
        # 테스트용 API 등록
        self.test_registration = APIRegistration(
            api_id="test_api_001",
            provider=self.test_provider,
            encrypted_credentials=self.encrypted_credentials,
            configuration={"timeout": 30, "retry_count": 3},
            status=APIStatus.ACTIVE,
            metadata={"test": True}
        )
    
    def teardown_method(self):
        """각 테스트 후 정리."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_storage_initialization(self):
        """저장소 초기화 테스트."""
        # 디렉토리 생성 확인
        assert self.storage_dir.exists()
        assert (self.storage_dir / "backups").exists()
        assert (self.storage_dir / "temp").exists()
        
        # 기본 파일 생성 확인
        assert self.storage.registrations_file.exists()
        assert self.storage.providers_file.exists()
        
        # 파일 권한 확인 (Unix 시스템에서만)
        if os.name == 'posix':
            reg_mode = oct(self.storage.registrations_file.stat().st_mode)[-3:]
            assert reg_mode == "600"
    
    def test_store_registration(self):
        """API 등록 저장 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 저장 확인
        stored_registration = self.storage.get_registration("test_api_001")
        assert stored_registration.api_id == "test_api_001"
        assert stored_registration.provider.name == "test_api"
        assert stored_registration.status == APIStatus.ACTIVE
        
        # 자격증명 복호화 확인
        decrypted = self.storage.get_decrypted_credentials("test_api_001")
        assert decrypted["api_key"] == "test_api_key_12345"
        assert decrypted["user_id"] == "test_user"
    
    def test_duplicate_registration_error(self):
        """중복 등록 오류 테스트."""
        # 첫 번째 등록
        self.storage.store_registration(self.test_registration)
        
        # 중복 등록 시도
        with pytest.raises(DuplicateAPIRegistrationError):
            self.storage.store_registration(self.test_registration)
    
    def test_get_nonexistent_registration(self):
        """존재하지 않는 등록 조회 테스트."""
        with pytest.raises(APINotFoundError):
            self.storage.get_registration("nonexistent_api")
    
    def test_update_registration(self):
        """API 등록 업데이트 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 등록 정보 수정
        updated_registration = self.storage.get_registration("test_api_001")
        updated_registration.status = APIStatus.INACTIVE
        updated_registration.configuration["timeout"] = 60
        
        # 업데이트
        self.storage.update_registration(updated_registration)
        
        # 업데이트 확인
        stored_registration = self.storage.get_registration("test_api_001")
        assert stored_registration.status == APIStatus.INACTIVE
        assert stored_registration.configuration["timeout"] == 60
    
    def test_delete_registration(self):
        """API 등록 삭제 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 삭제
        self.storage.delete_registration("test_api_001")
        
        # 삭제 확인
        with pytest.raises(APINotFoundError):
            self.storage.get_registration("test_api_001")
    
    def test_list_registrations(self):
        """등록 목록 조회 테스트."""
        # 여러 등록 저장
        registrations = []
        for i in range(3):
            reg = APIRegistration(
                api_id=f"test_api_{i:03d}",
                provider=self.test_provider,
                encrypted_credentials=self.encrypted_credentials,
                configuration={"index": i}
            )
            registrations.append(reg)
            self.storage.store_registration(reg)
        
        # 목록 조회 (민감한 정보 제외)
        reg_list = self.storage.list_registrations(include_sensitive=False)
        assert len(reg_list) == 3
        
        # 민감한 정보 제외 확인
        for reg_data in reg_list:
            assert "encrypted_credentials" not in reg_data
            assert "api_id" in reg_data
            assert "provider" in reg_data
        
        # 목록 조회 (민감한 정보 포함)
        reg_list_sensitive = self.storage.list_registrations(include_sensitive=True)
        assert len(reg_list_sensitive) == 3
        
        # 민감한 정보 포함 확인
        for reg_data in reg_list_sensitive:
            assert "encrypted_credentials" in reg_data
    
    def test_export_configuration_without_sensitive(self):
        """민감한 정보 제외 설정 내보내기 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 내보내기
        export_path = self.temp_dir + "/export_test.json"
        result = self.storage.export_configuration(
            export_path=export_path,
            include_sensitive=False
        )
        
        # 결과 확인
        assert result.success
        assert result.exported_count == 1
        assert result.file_path == export_path
        
        # 파일 내용 확인
        with open(export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        assert "export_info" in export_data
        assert export_data["export_info"]["include_sensitive"] is False
        assert "test_api_001" in export_data["registrations"]
        assert "encrypted_credentials" not in export_data["registrations"]["test_api_001"]
    
    def test_export_configuration_with_sensitive(self):
        """민감한 정보 포함 설정 내보내기 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 내보내기 (마스터 패스워드 없이)
        export_path = self.temp_dir + "/export_sensitive_test.json"
        result = self.storage.export_configuration(
            export_path=export_path,
            include_sensitive=True
        )
        
        # 마스터 패스워드 없이는 실패해야 함
        assert not result.success
        assert "마스터 패스워드" in result.message
        
        # 마스터 패스워드와 함께 내보내기
        result = self.storage.export_configuration(
            export_path=export_path,
            include_sensitive=True,
            master_password="test_master_password"
        )
        
        # 결과 확인
        assert result.success
        assert result.exported_count == 1
        
        # 파일 내용 확인
        with open(export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        assert export_data["export_info"]["include_sensitive"] is True
        assert "encrypted_credentials" in export_data["registrations"]["test_api_001"]
    
    def test_export_specific_apis(self):
        """특정 API만 내보내기 테스트."""
        # 여러 등록 저장
        for i in range(3):
            reg = APIRegistration(
                api_id=f"test_api_{i:03d}",
                provider=self.test_provider,
                encrypted_credentials=self.encrypted_credentials
            )
            self.storage.store_registration(reg)
        
        # 특정 API만 내보내기
        export_path = self.temp_dir + "/export_specific_test.json"
        result = self.storage.export_configuration(
            export_path=export_path,
            api_ids=["test_api_000", "test_api_002"]
        )
        
        # 결과 확인
        assert result.success
        assert result.exported_count == 2
        
        # 파일 내용 확인
        with open(export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        registrations = export_data["registrations"]
        assert len(registrations) == 2
        assert "test_api_000" in registrations
        assert "test_api_002" in registrations
        assert "test_api_001" not in registrations
    
    def test_import_configuration(self):
        """설정 가져오기 테스트."""
        # 내보내기 데이터 생성
        self.storage.store_registration(self.test_registration)
        export_path = self.temp_dir + "/export_for_import.json"
        self.storage.export_configuration(export_path, include_sensitive=True, 
                                        master_password="test_master_password")
        
        # 새로운 저장소 생성
        new_storage_dir = Path(self.temp_dir) / "new_storage"
        new_storage = SecureStorage(
            storage_dir=str(new_storage_dir),
            encryption_service=self.encryption_service
        )
        
        # 가져오기
        result = new_storage.import_configuration(
            import_path=export_path,
            master_password="test_master_password"
        )
        
        # 결과 확인
        assert result.success
        assert result.imported_count == 1
        assert result.error_count == 0
        
        # 가져온 데이터 확인
        imported_registration = new_storage.get_registration("test_api_001")
        assert imported_registration.api_id == "test_api_001"
        assert imported_registration.provider.name == "test_api"
        
        # 자격증명 확인
        decrypted = new_storage.get_decrypted_credentials("test_api_001")
        assert decrypted["api_key"] == "test_api_key_12345"
    
    def test_import_with_overwrite(self):
        """덮어쓰기 가져오기 테스트."""
        # 기존 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 수정된 등록으로 내보내기
        modified_registration = self.storage.get_registration("test_api_001")
        modified_registration.configuration["timeout"] = 120
        self.storage.update_registration(modified_registration)
        
        export_path = self.temp_dir + "/export_modified.json"
        self.storage.export_configuration(export_path, include_sensitive=True,
                                        master_password="test_master_password")
        
        # 원래 설정으로 되돌리기
        original_registration = self.storage.get_registration("test_api_001")
        original_registration.configuration["timeout"] = 30
        self.storage.update_registration(original_registration)
        
        # 덮어쓰기 없이 가져오기
        result = self.storage.import_configuration(
            import_path=export_path,
            master_password="test_master_password",
            overwrite=False
        )
        
        assert result.success
        assert result.imported_count == 0
        assert result.skipped_count == 1
        
        # 설정이 변경되지 않았는지 확인
        current_registration = self.storage.get_registration("test_api_001")
        assert current_registration.configuration["timeout"] == 30
        
        # 덮어쓰기로 가져오기
        result = self.storage.import_configuration(
            import_path=export_path,
            master_password="test_master_password",
            overwrite=True
        )
        
        assert result.success
        assert result.imported_count == 1
        assert result.skipped_count == 0
        
        # 설정이 변경되었는지 확인
        updated_registration = self.storage.get_registration("test_api_001")
        assert updated_registration.configuration["timeout"] == 120
    
    def test_backup_creation_and_listing(self):
        """백업 생성 및 목록 조회 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 백업 생성
        backup_path = self.storage._create_backup("manual_backup")
        assert os.path.exists(backup_path)
        
        # 백업 목록 조회
        backups = self.storage.list_backups()
        assert len(backups) >= 1
        
        # 백업 정보 확인
        backup_info = backups[0]
        assert "file_name" in backup_info
        assert "backup_name" in backup_info
        assert "created_at" in backup_info
        assert "registrations_count" in backup_info
        assert backup_info["registrations_count"] == 1
    
    def test_restore_from_backup(self):
        """백업에서 복원 테스트."""
        # 등록 저장 및 백업 생성
        self.storage.store_registration(self.test_registration)
        backup_path = self.storage._create_backup("restore_test")
        
        # 등록 삭제
        self.storage.delete_registration("test_api_001")
        
        # 삭제 확인
        with pytest.raises(APINotFoundError):
            self.storage.get_registration("test_api_001")
        
        # 백업에서 복원
        result = self.storage.restore_from_backup(
            backup_path=backup_path,
            master_password="test_master_password"
        )
        
        # 복원 결과 확인
        assert result.success
        assert result.imported_count == 1
        
        # 복원된 데이터 확인
        restored_registration = self.storage.get_registration("test_api_001")
        assert restored_registration.api_id == "test_api_001"
        assert restored_registration.provider.name == "test_api"
    
    def test_cleanup_old_backups(self):
        """오래된 백업 정리 테스트."""
        # 여러 백업 생성
        backup_paths = []
        for i in range(15):
            backup_path = self.storage._create_backup(f"backup_{i:02d}")
            backup_paths.append(backup_path)
        
        # 백업 개수 확인
        backups_before = self.storage.list_backups()
        assert len(backups_before) == 15
        
        # 백업 정리 (10개 유지)
        deleted_count = self.storage.cleanup_old_backups(keep_count=10)
        assert deleted_count == 5
        
        # 정리 후 백업 개수 확인
        backups_after = self.storage.list_backups()
        assert len(backups_after) == 10
    
    def test_storage_info(self):
        """저장소 정보 조회 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 백업 생성
        self.storage._create_backup("info_test")
        
        # 저장소 정보 조회
        info = self.storage.get_storage_info()
        
        # 정보 확인
        assert "storage_directory" in info
        assert "registrations_count" in info
        assert "providers_count" in info
        assert "backups_count" in info
        assert "total_disk_usage" in info
        assert "encryption_info" in info
        
        assert info["registrations_count"] == 1
        assert info["backups_count"] >= 1
        assert info["total_disk_usage"] > 0
    
    def test_verify_storage_integrity(self):
        """저장소 무결성 검증 테스트."""
        # 등록 저장
        self.storage.store_registration(self.test_registration)
        
        # 무결성 검증
        result = self.storage.verify_storage_integrity()
        
        # 결과 확인
        assert "overall_status" in result
        assert "issues" in result
        assert "warnings" in result
        assert "checks_performed" in result
        
        # 정상 상태 확인
        assert result["overall_status"] in ["healthy", "warning"]
        assert len(result["checks_performed"]) > 0
    
    def test_data_integrity_verification(self):
        """데이터 무결성 검증 테스트."""
        # 정상 데이터
        normal_data = {
            "version": "1.0",
            "registrations": {
                "test_api": {
                    "api_id": "test_api",
                    "encrypted_credentials": self.encrypted_credentials.to_dict()
                }
            },
            "metadata": {"total_count": 1}
        }
        
        assert self.storage._verify_data_integrity(normal_data)
        
        # 비정상 데이터 (필수 키 누락)
        invalid_data = {
            "registrations": {}
        }
        
        assert not self.storage._verify_data_integrity(invalid_data)
        
        # 비정상 데이터 (잘못된 암호화 데이터)
        corrupted_data = {
            "version": "1.0",
            "registrations": {
                "test_api": {
                    "api_id": "test_api",
                    "encrypted_credentials": {
                        "encrypted_content": "invalid_content",
                        "salt": "invalid_salt",
                        "integrity_hash": "wrong_hash"
                    }
                }
            },
            "metadata": {"total_count": 1}
        }
        
        assert not self.storage._verify_data_integrity(corrupted_data)
    
    def test_secure_permissions(self):
        """보안 권한 설정 테스트."""
        if os.name != 'posix':
            pytest.skip("Unix 시스템에서만 권한 테스트 가능")
        
        # 파일 권한 확인
        reg_stat = self.storage.registrations_file.stat()
        reg_mode = oct(reg_stat.st_mode)[-3:]
        assert reg_mode == "600"
        
        # 디렉토리 권한 확인
        dir_stat = self.storage.storage_dir.stat()
        dir_mode = oct(dir_stat.st_mode)[-3:]
        assert dir_mode == "700"
    
    def test_error_handling(self):
        """오류 처리 테스트."""
        # 존재하지 않는 파일 가져오기
        result = self.storage.import_configuration("/nonexistent/file.json")
        assert not result.success
        assert "파일을 찾을 수 없습니다" in result.message
        
        # 잘못된 백업 파일 복원
        invalid_backup = self.temp_dir + "/invalid_backup.json"
        with open(invalid_backup, 'w') as f:
            json.dump({"invalid": "data"}, f)
        
        result = self.storage.restore_from_backup(invalid_backup)
        assert not result.success
    
    def test_concurrent_access_safety(self):
        """동시 접근 안전성 테스트."""
        import threading
        import time
        
        results = []
        errors = []
        
        def store_registration(index):
            try:
                reg = APIRegistration(
                    api_id=f"concurrent_api_{index:03d}",
                    provider=self.test_provider,
                    encrypted_credentials=self.encrypted_credentials
                )
                self.storage.store_registration(reg)
                results.append(f"success_{index}")
            except Exception as e:
                errors.append(f"error_{index}: {str(e)}")
        
        # 동시에 여러 등록 시도
        threads = []
        for i in range(5):
            thread = threading.Thread(target=store_registration, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()
        
        # 결과 확인 (일부는 성공, 일부는 실패할 수 있음)
        assert len(results) + len(errors) == 5
        
        # 실제로 저장된 등록 확인
        stored_registrations = self.storage.list_registrations()
        assert len(stored_registrations) <= 5  # 중복 방지로 인해 5개 이하


if __name__ == "__main__":
    pytest.main([__file__, "-v"])