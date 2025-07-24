"""
API 등록 관리 시스템의 보안 저장소.

암호화된 API 자격증명을 안전하게 저장하고 관리하는 기능을 제공합니다.
파일 권한 관리, 백업, 무결성 검증 등의 보안 기능을 포함합니다.
"""

import os
import json
import stat
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from api_registration_models import (
    APIRegistration, EncryptedData, APIProvider, 
    ExportResult, ImportResult
)
from encryption_service import EncryptionService
from exceptions import (
    SecurityError, PermissionError, FileSystemError,
    BackupError, IntegrityCheckError, APINotFoundError,
    ConfigurationExportError, ConfigurationImportError,
    BackupCorruptedError, DuplicateAPIRegistrationError
)


class SecureStorage:
    """
    보안 저장소 클래스.
    
    암호화된 API 자격증명을 안전하게 저장하고 관리합니다.
    파일 권한, 백업, 무결성 검증 등의 보안 기능을 제공합니다.
    """
    
    def __init__(self, storage_dir: str = None, encryption_service: EncryptionService = None):
        """
        보안 저장소 초기화.
        
        Args:
            storage_dir: 저장소 디렉토리 경로
            encryption_service: 암호화 서비스 인스턴스
        """
        # 기본 저장소 디렉토리 설정
        if storage_dir is None:
            home_dir = Path.home()
            storage_dir = home_dir / ".api_registration" / "secure_storage"
        
        self.storage_dir = Path(storage_dir)
        self.registrations_file = self.storage_dir / "registrations.json"
        self.providers_file = self.storage_dir / "providers.json"
        self.backup_dir = self.storage_dir / "backups"
        self.temp_dir = self.storage_dir / "temp"
        
        # 암호화 서비스 설정
        self.encryption_service = encryption_service or EncryptionService()
        
        # 저장소 초기화
        self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """저장소 디렉토리 및 파일 초기화."""
        try:
            # 디렉토리 생성
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(exist_ok=True)
            self.temp_dir.mkdir(exist_ok=True)
            
            # 디렉토리 권한 설정 (소유자만 읽기/쓰기/실행)
            self._set_secure_permissions(self.storage_dir, 0o700)
            self._set_secure_permissions(self.backup_dir, 0o700)
            self._set_secure_permissions(self.temp_dir, 0o700)
            
            # 기본 파일 생성
            if not self.registrations_file.exists():
                self._create_empty_registrations_file()
            
            if not self.providers_file.exists():
                self._create_default_providers_file()
            
            # 파일 권한 설정 (소유자만 읽기/쓰기)
            self._set_secure_permissions(self.registrations_file, 0o600)
            self._set_secure_permissions(self.providers_file, 0o600)
            
        except Exception as e:
            raise SecurityError(f"저장소 초기화 실패: {str(e)}")
    
    def _set_secure_permissions(self, path: Path, permissions: int) -> None:
        """
        파일/디렉토리에 보안 권한 설정.
        
        Args:
            path: 대상 경로
            permissions: 설정할 권한 (8진수)
            
        Raises:
            PermissionError: 권한 설정 실패 시
        """
        try:
            if path.exists():
                os.chmod(path, permissions)
        except OSError as e:
            raise PermissionError(f"권한 설정 실패 ({path}): {str(e)}")
    
    def _create_empty_registrations_file(self) -> None:
        """빈 등록 파일 생성."""
        empty_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "registrations": {},
            "metadata": {
                "total_count": 0,
                "last_updated": datetime.now().isoformat()
            }
        }
        
        with open(self.registrations_file, 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, indent=2, ensure_ascii=False)
    
    def _create_default_providers_file(self) -> None:
        """기본 제공업체 파일 생성."""
        default_providers = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "providers": {},
            "metadata": {
                "total_count": 0,
                "last_updated": datetime.now().isoformat()
            }
        }
        
        with open(self.providers_file, 'w', encoding='utf-8') as f:
            json.dump(default_providers, f, indent=2, ensure_ascii=False)
    
    def _load_registrations_data(self) -> Dict[str, Any]:
        """
        등록 데이터 로드.
        
        Returns:
            Dict: 등록 데이터
            
        Raises:
            FileSystemError: 파일 로드 실패 시
        """
        try:
            if not self.registrations_file.exists():
                self._create_empty_registrations_file()
            
            with open(self.registrations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise FileSystemError(f"등록 데이터 로드 실패: {str(e)}")
    
    def _save_registrations_data(self, data: Dict[str, Any]) -> None:
        """
        등록 데이터 저장.
        
        Args:
            data: 저장할 데이터
            
        Raises:
            FileSystemError: 파일 저장 실패 시
        """
        try:
            # 메타데이터 업데이트
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            data["metadata"]["total_count"] = len(data.get("registrations", {}))
            
            # 임시 파일에 먼저 저장
            temp_file = self.temp_dir / f"registrations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 권한 설정
            self._set_secure_permissions(temp_file, 0o600)
            
            # 원본 파일로 이동 (원자적 연산)
            shutil.move(str(temp_file), str(self.registrations_file))
            
        except Exception as e:
            # 임시 파일 정리
            if temp_file.exists():
                temp_file.unlink()
            raise FileSystemError(f"등록 데이터 저장 실패: {str(e)}")
    
    def _load_providers_data(self) -> Dict[str, Any]:
        """
        제공업체 데이터 로드.
        
        Returns:
            Dict: 제공업체 데이터
        """
        try:
            if not self.providers_file.exists():
                self._create_default_providers_file()
            
            with open(self.providers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise FileSystemError(f"제공업체 데이터 로드 실패: {str(e)}")
    
    def _save_providers_data(self, data: Dict[str, Any]) -> None:
        """
        제공업체 데이터 저장.
        
        Args:
            data: 저장할 데이터
        """
        try:
            # 메타데이터 업데이트
            data["metadata"]["last_updated"] = datetime.now().isoformat()
            data["metadata"]["total_count"] = len(data.get("providers", {}))
            
            # 임시 파일에 먼저 저장
            temp_file = self.temp_dir / f"providers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 권한 설정
            self._set_secure_permissions(temp_file, 0o600)
            
            # 원본 파일로 이동
            shutil.move(str(temp_file), str(self.providers_file))
            
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise FileSystemError(f"제공업체 데이터 저장 실패: {str(e)}")
    
    def _create_backup(self, backup_name: str = None) -> str:
        """
        백업 생성.
        
        Args:
            backup_name: 백업 이름 (선택사항)
            
        Returns:
            str: 생성된 백업 파일 경로
            
        Raises:
            BackupError: 백업 생성 실패 시
        """
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_file = self.backup_dir / f"{backup_name}.json"
            
            # 현재 데이터 수집
            registrations_data = self._load_registrations_data()
            providers_data = self._load_providers_data()
            
            backup_data = {
                "backup_info": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "backup_name": backup_name
                },
                "registrations": registrations_data,
                "providers": providers_data
            }
            
            # 백업 파일 저장
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # 권한 설정
            self._set_secure_permissions(backup_file, 0o600)
            
            return str(backup_file)
            
        except Exception as e:
            raise BackupError(f"백업 생성 실패: {str(e)}")
    
    def _verify_data_integrity(self, data: Dict[str, Any]) -> bool:
        """
        데이터 무결성 검증.
        
        Args:
            data: 검증할 데이터
            
        Returns:
            bool: 무결성 검증 결과
        """
        try:
            # 기본 구조 확인
            required_keys = ["version", "registrations", "metadata"]
            if not all(key in data for key in required_keys):
                return False
            
            # 등록 데이터 검증
            registrations = data.get("registrations", {})
            for api_id, reg_data in registrations.items():
                if not isinstance(reg_data, dict):
                    return False
                
                # 암호화된 자격증명 무결성 검증
                if "encrypted_credentials" in reg_data:
                    encrypted_data = EncryptedData.from_dict(reg_data["encrypted_credentials"])
                    if not encrypted_data.verify_integrity():
                        return False
            
            return True
            
        except Exception:
            return False
    
    # ==================== 공개 메서드 ====================
    
    def store_registration(self, registration: APIRegistration) -> None:
        """
        API 등록 정보 저장.
        
        Args:
            registration: 저장할 API 등록 정보
            
        Raises:
            DuplicateAPIRegistrationError: 중복 등록 시
            FileSystemError: 저장 실패 시
        """
        try:
            data = self._load_registrations_data()
            
            # 중복 확인
            if registration.api_id in data["registrations"]:
                raise DuplicateAPIRegistrationError(
                    f"API ID '{registration.api_id}'가 이미 등록되어 있습니다"
                )
            
            # 백업 생성
            self._create_backup(f"before_add_{registration.api_id}")
            
            # 등록 데이터 추가
            data["registrations"][registration.api_id] = registration.to_dict(include_sensitive=True)
            
            # 저장
            self._save_registrations_data(data)
            
        except DuplicateAPIRegistrationError:
            raise
        except Exception as e:
            raise FileSystemError(f"API 등록 저장 실패: {str(e)}")
    
    def get_registration(self, api_id: str) -> APIRegistration:
        """
        API 등록 정보 조회.
        
        Args:
            api_id: 조회할 API ID
            
        Returns:
            APIRegistration: API 등록 정보
            
        Raises:
            APINotFoundError: API를 찾을 수 없는 경우
        """
        try:
            data = self._load_registrations_data()
            
            if api_id not in data["registrations"]:
                raise APINotFoundError(f"API ID '{api_id}'를 찾을 수 없습니다")
            
            reg_data = data["registrations"][api_id]
            
            # APIRegistration 객체 재구성
            provider_data = reg_data["provider"]
            provider = APIProvider(**provider_data)
            
            encrypted_credentials = EncryptedData.from_dict(reg_data["encrypted_credentials"])
            
            registration = APIRegistration(
                api_id=reg_data["api_id"],
                provider=provider,
                encrypted_credentials=encrypted_credentials,
                configuration=reg_data.get("configuration", {}),
                created_at=datetime.fromisoformat(reg_data["created_at"]),
                updated_at=datetime.fromisoformat(reg_data["updated_at"]),
                last_tested=datetime.fromisoformat(reg_data["last_tested"]) if reg_data.get("last_tested") else None,
                status=reg_data.get("status", "active"),
                metadata=reg_data.get("metadata", {})
            )
            
            return registration
            
        except APINotFoundError:
            raise
        except Exception as e:
            raise FileSystemError(f"API 등록 조회 실패: {str(e)}")
    
    def update_registration(self, registration: APIRegistration) -> None:
        """
        API 등록 정보 업데이트.
        
        Args:
            registration: 업데이트할 API 등록 정보
            
        Raises:
            APINotFoundError: API를 찾을 수 없는 경우
        """
        try:
            data = self._load_registrations_data()
            
            if registration.api_id not in data["registrations"]:
                raise APINotFoundError(f"API ID '{registration.api_id}'를 찾을 수 없습니다")
            
            # 백업 생성
            self._create_backup(f"before_update_{registration.api_id}")
            
            # 업데이트 시간 설정
            registration.updated_at = datetime.now()
            
            # 등록 데이터 업데이트
            data["registrations"][registration.api_id] = registration.to_dict(include_sensitive=True)
            
            # 저장
            self._save_registrations_data(data)
            
        except APINotFoundError:
            raise
        except Exception as e:
            raise FileSystemError(f"API 등록 업데이트 실패: {str(e)}")
    
    def delete_registration(self, api_id: str) -> None:
        """
        API 등록 정보 삭제.
        
        Args:
            api_id: 삭제할 API ID
            
        Raises:
            APINotFoundError: API를 찾을 수 없는 경우
        """
        try:
            data = self._load_registrations_data()
            
            if api_id not in data["registrations"]:
                raise APINotFoundError(f"API ID '{api_id}'를 찾을 수 없습니다")
            
            # 백업 생성
            self._create_backup(f"before_delete_{api_id}")
            
            # 등록 데이터 삭제
            del data["registrations"][api_id]
            
            # 저장
            self._save_registrations_data(data)
            
        except APINotFoundError:
            raise
        except Exception as e:
            raise FileSystemError(f"API 등록 삭제 실패: {str(e)}")
    
    def list_registrations(self, include_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        모든 API 등록 목록 조회.
        
        Args:
            include_sensitive: 민감한 정보 포함 여부
            
        Returns:
            List[Dict]: API 등록 목록
        """
        try:
            data = self._load_registrations_data()
            registrations = []
            
            for api_id, reg_data in data["registrations"].items():
                if include_sensitive:
                    registrations.append(reg_data)
                else:
                    # 민감한 정보 제외
                    safe_data = {k: v for k, v in reg_data.items() 
                               if k != "encrypted_credentials"}
                    registrations.append(safe_data)
            
            return registrations
            
        except Exception as e:
            raise FileSystemError(f"API 등록 목록 조회 실패: {str(e)}")
    
    def get_decrypted_credentials(self, api_id: str, master_password: str = None) -> Dict[str, Any]:
        """
        복호화된 자격증명 조회.
        
        Args:
            api_id: API ID
            master_password: 마스터 패스워드
            
        Returns:
            Dict: 복호화된 자격증명
        """
        registration = self.get_registration(api_id)
        return self.encryption_service.decrypt_credentials(
            registration.encrypted_credentials, 
            master_password
        )
    
    def export_configuration(self, export_path: str, include_sensitive: bool = False,
                           api_ids: List[str] = None, master_password: str = None) -> ExportResult:
        """
        설정 내보내기.
        
        Args:
            export_path: 내보낼 파일 경로
            include_sensitive: 민감한 정보 포함 여부
            api_ids: 내보낼 API ID 목록 (None이면 전체)
            master_password: 마스터 패스워드 (민감한 정보 포함 시 필요)
            
        Returns:
            ExportResult: 내보내기 결과
        """
        try:
            data = self._load_registrations_data()
            providers_data = self._load_providers_data()
            
            # 내보낼 등록 필터링
            registrations_to_export = {}
            if api_ids:
                for api_id in api_ids:
                    if api_id in data["registrations"]:
                        registrations_to_export[api_id] = data["registrations"][api_id]
            else:
                registrations_to_export = data["registrations"]
            
            # 민감한 정보 처리
            if include_sensitive and not master_password:
                return ExportResult(
                    success=False,
                    message="민감한 정보를 포함하려면 마스터 패스워드가 필요합니다",
                    errors=["마스터 패스워드 누락"]
                )
            
            export_data = {
                "export_info": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "include_sensitive": include_sensitive,
                    "exported_count": len(registrations_to_export)
                },
                "registrations": {},
                "providers": providers_data["providers"]
            }
            
            # 등록 데이터 처리
            for api_id, reg_data in registrations_to_export.items():
                if include_sensitive:
                    # 민감한 정보 포함 - 재암호화
                    try:
                        encrypted_data = EncryptedData.from_dict(reg_data["encrypted_credentials"])
                        credentials = self.encryption_service.decrypt_credentials(
                            encrypted_data, master_password
                        )
                        # 새로운 키로 재암호화
                        new_encrypted = self.encryption_service.encrypt_credentials(
                            credentials, master_password
                        )
                        reg_data_copy = reg_data.copy()
                        reg_data_copy["encrypted_credentials"] = new_encrypted.to_dict()
                        export_data["registrations"][api_id] = reg_data_copy
                    except Exception as e:
                        return ExportResult(
                            success=False,
                            message=f"자격증명 처리 실패: {str(e)}",
                            errors=[f"API {api_id}: {str(e)}"]
                        )
                else:
                    # 민감한 정보 제외
                    safe_data = {k: v for k, v in reg_data.items() 
                               if k != "encrypted_credentials"}
                    export_data["registrations"][api_id] = safe_data
            
            # 파일 저장
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            # 파일 권한 설정
            self._set_secure_permissions(export_path, 0o600)
            
            return ExportResult(
                success=True,
                file_path=str(export_path),
                exported_count=len(registrations_to_export),
                message=f"{len(registrations_to_export)}개 API 설정을 성공적으로 내보냈습니다"
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                message=f"설정 내보내기 실패: {str(e)}",
                errors=[str(e)]
            )
    
    def import_configuration(self, import_path: str, master_password: str = None,
                           overwrite: bool = False) -> ImportResult:
        """
        설정 가져오기.
        
        Args:
            import_path: 가져올 파일 경로
            master_password: 마스터 패스워드
            overwrite: 기존 설정 덮어쓰기 여부
            
        Returns:
            ImportResult: 가져오기 결과
        """
        try:
            import_path = Path(import_path)
            if not import_path.exists():
                return ImportResult(
                    success=False,
                    message="가져올 파일을 찾을 수 없습니다",
                    errors=["파일 없음"]
                )
            
            # 파일 로드
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 데이터 검증
            if not self._verify_import_data(import_data):
                return ImportResult(
                    success=False,
                    message="가져올 데이터 형식이 올바르지 않습니다",
                    errors=["데이터 형식 오류"]
                )
            
            # 백업 생성
            backup_file = self._create_backup("before_import")
            
            current_data = self._load_registrations_data()
            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            warnings = []
            
            # 등록 데이터 가져오기
            for api_id, reg_data in import_data.get("registrations", {}).items():
                try:
                    # 중복 확인
                    if api_id in current_data["registrations"] and not overwrite:
                        skipped_count += 1
                        warnings.append(f"API {api_id}: 이미 존재함 (건너뜀)")
                        continue
                    
                    # 민감한 정보 처리
                    if "encrypted_credentials" in reg_data:
                        if not master_password:
                            error_count += 1
                            errors.append(f"API {api_id}: 마스터 패스워드 필요")
                            continue
                        
                        # 자격증명 검증
                        encrypted_data = EncryptedData.from_dict(reg_data["encrypted_credentials"])
                        try:
                            credentials = self.encryption_service.decrypt_credentials(
                                encrypted_data, master_password
                            )
                            # 현재 시스템으로 재암호화
                            new_encrypted = self.encryption_service.encrypt_credentials(
                                credentials, master_password
                            )
                            reg_data["encrypted_credentials"] = new_encrypted.to_dict()
                        except Exception as e:
                            error_count += 1
                            errors.append(f"API {api_id}: 자격증명 처리 실패 - {str(e)}")
                            continue
                    
                    # 등록 데이터 추가/업데이트
                    current_data["registrations"][api_id] = reg_data
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"API {api_id}: {str(e)}")
            
            # 제공업체 데이터 가져오기
            if "providers" in import_data:
                try:
                    providers_data = self._load_providers_data()
                    for provider_name, provider_info in import_data["providers"].items():
                        providers_data["providers"][provider_name] = provider_info
                    self._save_providers_data(providers_data)
                except Exception as e:
                    warnings.append(f"제공업체 데이터 가져오기 실패: {str(e)}")
            
            # 데이터 저장
            if imported_count > 0:
                self._save_registrations_data(current_data)
            
            success = imported_count > 0 or (imported_count == 0 and error_count == 0)
            
            return ImportResult(
                success=success,
                imported_count=imported_count,
                skipped_count=skipped_count,
                error_count=error_count,
                message=f"가져오기 완료: {imported_count}개 성공, {skipped_count}개 건너뜀, {error_count}개 실패",
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            return ImportResult(
                success=False,
                message=f"설정 가져오기 실패: {str(e)}",
                errors=[str(e)]
            )
    
    def _verify_import_data(self, data: Dict[str, Any]) -> bool:
        """
        가져올 데이터 검증.
        
        Args:
            data: 검증할 데이터
            
        Returns:
            bool: 검증 결과
        """
        try:
            # 기본 구조 확인
            if not isinstance(data, dict):
                return False
            
            # 내보내기 정보 확인
            if "export_info" not in data:
                return False
            
            export_info = data["export_info"]
            if not isinstance(export_info, dict):
                return False
            
            # 등록 데이터 확인
            if "registrations" in data:
                registrations = data["registrations"]
                if not isinstance(registrations, dict):
                    return False
                
                for api_id, reg_data in registrations.items():
                    if not isinstance(reg_data, dict):
                        return False
                    
                    # 필수 필드 확인
                    required_fields = ["api_id", "provider", "created_at"]
                    if not all(field in reg_data for field in required_fields):
                        return False
            
            return True
            
        except Exception:
            return False
    
    def restore_from_backup(self, backup_path: str, master_password: str = None) -> ImportResult:
        """
        백업에서 복원.
        
        Args:
            backup_path: 백업 파일 경로
            master_password: 마스터 패스워드
            
        Returns:
            ImportResult: 복원 결과
        """
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                return ImportResult(
                    success=False,
                    message="백업 파일을 찾을 수 없습니다",
                    errors=["백업 파일 없음"]
                )
            
            # 백업 파일 로드
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # 백업 데이터 검증
            if not self._verify_backup_data(backup_data):
                raise BackupCorruptedError("백업 파일이 손상되었습니다")
            
            # 현재 상태 백업
            current_backup = self._create_backup("before_restore")
            
            try:
                # 등록 데이터 복원
                if "registrations" in backup_data:
                    registrations_data = backup_data["registrations"]
                    if self._verify_data_integrity(registrations_data):
                        self._save_registrations_data(registrations_data)
                    else:
                        raise IntegrityCheckError("등록 데이터 무결성 검증 실패")
                
                # 제공업체 데이터 복원
                if "providers" in backup_data:
                    providers_data = backup_data["providers"]
                    self._save_providers_data(providers_data)
                
                return ImportResult(
                    success=True,
                    imported_count=len(backup_data.get("registrations", {}).get("registrations", {})),
                    message="백업에서 성공적으로 복원했습니다"
                )
                
            except Exception as e:
                # 복원 실패 시 이전 상태로 되돌리기
                try:
                    with open(current_backup, 'r', encoding='utf-8') as f:
                        rollback_data = json.load(f)
                    if "registrations" in rollback_data:
                        self._save_registrations_data(rollback_data["registrations"])
                    if "providers" in rollback_data:
                        self._save_providers_data(rollback_data["providers"])
                except Exception:
                    pass  # 롤백 실패는 무시
                
                raise e
                
        except Exception as e:
            return ImportResult(
                success=False,
                message=f"백업 복원 실패: {str(e)}",
                errors=[str(e)]
            )
    
    def _verify_backup_data(self, data: Dict[str, Any]) -> bool:
        """
        백업 데이터 검증.
        
        Args:
            data: 검증할 백업 데이터
            
        Returns:
            bool: 검증 결과
        """
        try:
            # 백업 정보 확인
            if "backup_info" not in data:
                return False
            
            backup_info = data["backup_info"]
            required_fields = ["created_at", "version", "backup_name"]
            if not all(field in backup_info for field in required_fields):
                return False
            
            # 등록 데이터 확인
            if "registrations" in data:
                if not self._verify_data_integrity(data["registrations"]):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        백업 목록 조회.
        
        Returns:
            List[Dict]: 백업 목록
        """
        try:
            backups = []
            
            for backup_file in self.backup_dir.glob("*.json"):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                    
                    backup_info = backup_data.get("backup_info", {})
                    file_stat = backup_file.stat()
                    
                    backups.append({
                        "file_name": backup_file.name,
                        "file_path": str(backup_file),
                        "backup_name": backup_info.get("backup_name", "Unknown"),
                        "created_at": backup_info.get("created_at", "Unknown"),
                        "version": backup_info.get("version", "Unknown"),
                        "file_size": file_stat.st_size,
                        "registrations_count": len(backup_data.get("registrations", {}).get("registrations", {}))
                    })
                    
                except Exception:
                    # 손상된 백업 파일은 건너뜀
                    continue
            
            # 생성 시간 순으로 정렬 (최신 순)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backups
            
        except Exception as e:
            raise FileSystemError(f"백업 목록 조회 실패: {str(e)}")
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        오래된 백업 정리.
        
        Args:
            keep_count: 유지할 백업 개수
            
        Returns:
            int: 삭제된 백업 개수
        """
        try:
            backups = self.list_backups()
            
            if len(backups) <= keep_count:
                return 0
            
            # 삭제할 백업 선정 (오래된 순)
            backups_to_delete = backups[keep_count:]
            deleted_count = 0
            
            for backup in backups_to_delete:
                try:
                    backup_path = Path(backup["file_path"])
                    if backup_path.exists():
                        backup_path.unlink()
                        deleted_count += 1
                except Exception:
                    continue  # 개별 삭제 실패는 무시
            
            return deleted_count
            
        except Exception as e:
            raise FileSystemError(f"백업 정리 실패: {str(e)}")
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        저장소 정보 조회.
        
        Returns:
            Dict: 저장소 정보
        """
        try:
            data = self._load_registrations_data()
            providers_data = self._load_providers_data()
            backups = self.list_backups()
            
            # 디스크 사용량 계산
            total_size = 0
            for file_path in [self.registrations_file, self.providers_file]:
                if file_path.exists():
                    total_size += file_path.stat().st_size
            
            for backup in backups:
                total_size += backup["file_size"]
            
            return {
                "storage_directory": str(self.storage_dir),
                "registrations_count": len(data.get("registrations", {})),
                "providers_count": len(providers_data.get("providers", {})),
                "backups_count": len(backups),
                "total_disk_usage": total_size,
                "last_updated": data.get("metadata", {}).get("last_updated"),
                "version": data.get("version", "Unknown"),
                "encryption_info": self.encryption_service.get_encryption_info()
            }
            
        except Exception as e:
            raise FileSystemError(f"저장소 정보 조회 실패: {str(e)}")
    
    def verify_storage_integrity(self) -> Dict[str, Any]:
        """
        저장소 무결성 검증.
        
        Returns:
            Dict: 검증 결과
        """
        try:
            results = {
                "overall_status": "healthy",
                "issues": [],
                "warnings": [],
                "checks_performed": []
            }
            
            # 파일 존재 확인
            results["checks_performed"].append("파일 존재 확인")
            if not self.registrations_file.exists():
                results["issues"].append("등록 파일이 존재하지 않습니다")
                results["overall_status"] = "error"
            
            if not self.providers_file.exists():
                results["warnings"].append("제공업체 파일이 존재하지 않습니다")
            
            # 파일 권한 확인
            results["checks_performed"].append("파일 권한 확인")
            try:
                for file_path in [self.registrations_file, self.providers_file]:
                    if file_path.exists():
                        file_mode = oct(file_path.stat().st_mode)[-3:]
                        if file_mode != "600":
                            results["warnings"].append(f"{file_path.name} 파일 권한이 안전하지 않습니다 ({file_mode})")
            except Exception as e:
                results["warnings"].append(f"권한 확인 실패: {str(e)}")
            
            # 데이터 무결성 확인
            results["checks_performed"].append("데이터 무결성 확인")
            try:
                data = self._load_registrations_data()
                if not self._verify_data_integrity(data):
                    results["issues"].append("등록 데이터 무결성 검증 실패")
                    results["overall_status"] = "error"
            except Exception as e:
                results["issues"].append(f"데이터 로드 실패: {str(e)}")
                results["overall_status"] = "error"
            
            # 암호화 데이터 검증
            results["checks_performed"].append("암호화 데이터 검증")
            try:
                data = self._load_registrations_data()
                corrupted_registrations = []
                
                for api_id, reg_data in data.get("registrations", {}).items():
                    if "encrypted_credentials" in reg_data:
                        try:
                            encrypted_data = EncryptedData.from_dict(reg_data["encrypted_credentials"])
                            if not encrypted_data.verify_integrity():
                                corrupted_registrations.append(api_id)
                        except Exception:
                            corrupted_registrations.append(api_id)
                
                if corrupted_registrations:
                    results["issues"].append(f"손상된 암호화 데이터: {', '.join(corrupted_registrations)}")
                    results["overall_status"] = "error"
                    
            except Exception as e:
                results["warnings"].append(f"암호화 데이터 검증 실패: {str(e)}")
            
            # 백업 상태 확인
            results["checks_performed"].append("백업 상태 확인")
            try:
                backups = self.list_backups()
                if len(backups) == 0:
                    results["warnings"].append("백업 파일이 없습니다")
                elif len(backups) > 20:
                    results["warnings"].append(f"백업 파일이 너무 많습니다 ({len(backups)}개)")
            except Exception as e:
                results["warnings"].append(f"백업 상태 확인 실패: {str(e)}")
            
            # 전체 상태 결정
            if results["issues"]:
                results["overall_status"] = "error"
            elif results["warnings"]:
                results["overall_status"] = "warning"
            
            return results
            
        except Exception as e:
            return {
                "overall_status": "error",
                "issues": [f"무결성 검증 실패: {str(e)}"],
                "warnings": [],
                "checks_performed": ["무결성 검증 시작"]
            }