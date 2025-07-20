"""
백업 매니저 모듈.

이 모듈은 온톨로지 파일의 자동 백업 생성 및 관리 기능을 제공합니다.
TTL 파일의 문법 검증과 파일 저장 실패 시 대체 경로 사용 기능도 포함합니다.
"""

import os
import shutil
import time
import datetime
import logging
import tempfile
import re
import glob
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union

from rdflib import Graph
from exceptions import BackupError, FileSystemError, TTLSyntaxError, FilePermissionError, DiskSpaceError


class BackupManager:
    """
    백업 매니저 클래스.
    
    온톨로지 파일의 자동 백업 생성, 관리 및 복원 기능을 제공합니다.
    TTL 파일의 문법 검증 및 파일 저장 실패 시 대체 경로 사용 기능도 포함합니다.
    """
    
    def __init__(self, 
                 backup_dir: str = "backups", 
                 max_backups: int = 10,
                 backup_interval: int = 24 * 60 * 60,  # 24시간(초 단위)
                 validate_ttl: bool = True):
        """
        BackupManager 초기화.
        
        Args:
            backup_dir: 백업 파일이 저장될 디렉토리 경로
            max_backups: 유지할 최대 백업 파일 수
            backup_interval: 백업 간 최소 시간 간격(초)
            validate_ttl: TTL 파일 검증 여부
        """
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.backup_interval = backup_interval
        self.validate_ttl = validate_ttl
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # 백업 디렉토리 생성
        self._ensure_backup_dir()
        
        # 대체 경로 설정
        self.fallback_dirs = [
            "fallback_backups",
            tempfile.gettempdir(),
            os.path.expanduser("~")
        ]
        
        self.logger.info(f"백업 매니저 초기화 완료: 백업 디렉토리={self.backup_dir}, 최대 백업 수={self.max_backups}")
    
    def _ensure_backup_dir(self) -> None:
        """
        백업 디렉토리가 존재하는지 확인하고, 없으면 생성합니다.
        
        Raises:
            FileSystemError: 디렉토리 생성 실패 시
        """
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            self.logger.debug(f"백업 디렉토리 확인/생성 완료: {self.backup_dir}")
        except Exception as e:
            error_msg = f"백업 디렉토리 생성 실패: {str(e)}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg)
    
    def create_backup(self, file_path: str, force: bool = False) -> str:
        """
        지정된 파일의 백업을 생성합니다.
        
        Args:
            file_path: 백업할 파일 경로
            force: 시간 간격 무시하고 강제 백업 여부
            
        Returns:
            str: 생성된 백업 파일 경로
            
        Raises:
            FileSystemError: 파일이 존재하지 않거나 백업 생성 실패 시
            BackupError: 백업 관련 오류 발생 시
        """
        # 파일 존재 확인
        if not os.path.exists(file_path):
            error_msg = f"백업할 파일이 존재하지 않습니다: {file_path}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg)
        
        # TTL 파일 검증 (확장자가 .ttl인 경우)
        if self.validate_ttl and file_path.lower().endswith(".ttl"):
            self._validate_ttl_file(file_path)
        
        # 마지막 백업 이후 충분한 시간이 지났는지 확인 (force가 아닌 경우)
        if not force and not self._should_create_backup(file_path):
            self.logger.info(f"최근에 백업이 생성되어 백업을 건너뜁니다: {file_path}")
            # 가장 최근 백업 파일 경로 반환
            return self._get_latest_backup(file_path)
        
        # 백업 파일 경로 생성
        backup_path = self._generate_backup_path(file_path)
        
        # 백업 생성
        try:
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"백업 생성 완료: {file_path} -> {backup_path}")
        except Exception as e:
            # 기본 경로에 백업 실패 시 대체 경로 시도
            backup_path = self._try_fallback_paths(file_path)
            if not backup_path:
                error_msg = f"백업 생성 실패: {str(e)}"
                self.logger.error(error_msg)
                raise BackupError(error_msg)
        
        # 오래된 백업 정리
        self._cleanup_old_backups(file_path)
        
        return backup_path
    
    def _validate_ttl_file(self, file_path: str) -> None:
        """
        TTL 파일의 문법을 검증합니다.
        
        Args:
            file_path: 검증할 TTL 파일 경로
            
        Raises:
            TTLSyntaxError: TTL 파일 검증 실패 시
        """
        try:
            graph = Graph()
            graph.parse(file_path, format="turtle")
            self.logger.debug(f"TTL 파일 검증 성공: {file_path}")
        except Exception as e:
            error_msg = f"TTL 파일 검증 실패: {file_path}, 오류: {str(e)}"
            self.logger.error(error_msg)
            raise TTLSyntaxError(error_msg)
    
    def _should_create_backup(self, file_path: str) -> bool:
        """
        마지막 백업 이후 충분한 시간이 지났는지 확인합니다.
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            bool: 백업 생성 필요 여부
        """
        latest_backup = self._get_latest_backup(file_path)
        if not latest_backup or not os.path.exists(latest_backup):
            return True
        
        # 마지막 백업 시간 확인
        backup_time = os.path.getmtime(latest_backup)
        current_time = time.time()
        
        return (current_time - backup_time) >= self.backup_interval
    
    def _generate_backup_path(self, file_path: str) -> str:
        """
        백업 파일 경로를 생성합니다.
        
        Args:
            file_path: 원본 파일 경로
            
        Returns:
            str: 생성된 백업 파일 경로
        """
        # 파일명과 확장자 분리
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        
        # 타임스탬프 생성
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 백업 파일명 생성
        backup_filename = f"{name}_backup_{timestamp}{ext}"
        
        return os.path.join(self.backup_dir, backup_filename)
    
    def _get_latest_backup(self, file_path: str) -> Optional[str]:
        """
        지정된 파일의 가장 최근 백업 파일 경로를 반환합니다.
        
        Args:
            file_path: 원본 파일 경로
            
        Returns:
            Optional[str]: 가장 최근 백업 파일 경로 (없으면 None)
        """
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        
        # 백업 파일 패턴
        pattern = os.path.join(self.backup_dir, f"{name}_backup_*{ext}")
        backup_files = glob.glob(pattern)
        
        if not backup_files:
            return None
        
        # 수정 시간 기준으로 정렬하여 가장 최근 파일 반환
        backup_files.sort(key=os.path.getmtime, reverse=True)
        return backup_files[0]
    
    def _try_fallback_paths(self, file_path: str) -> Optional[str]:
        """
        대체 경로에 백업 파일을 생성합니다.
        
        Args:
            file_path: 원본 파일 경로
            
        Returns:
            Optional[str]: 성공한 백업 파일 경로 (실패 시 None)
        """
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{name}_backup_{timestamp}{ext}"
        
        for fallback_dir in self.fallback_dirs:
            try:
                # 대체 디렉토리 생성
                os.makedirs(fallback_dir, exist_ok=True)
                
                # 백업 파일 경로
                backup_path = os.path.join(fallback_dir, backup_filename)
                
                # 백업 생성
                shutil.copy2(file_path, backup_path)
                
                self.logger.warning(f"대체 경로에 백업 생성: {backup_path}")
                return backup_path
                
            except Exception as e:
                self.logger.debug(f"대체 경로 {fallback_dir} 백업 실패: {str(e)}")
                continue
        
        return None
    
    def _cleanup_old_backups(self, file_path: str) -> None:
        """
        오래된 백업 파일들을 정리합니다.
        
        Args:
            file_path: 원본 파일 경로
        """
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name)
        
        # 백업 파일 패턴
        pattern = os.path.join(self.backup_dir, f"{name}_backup_*{ext}")
        backup_files = glob.glob(pattern)
        
        if len(backup_files) <= self.max_backups:
            return
        
        # 수정 시간 기준으로 정렬 (오래된 것부터)
        backup_files.sort(key=os.path.getmtime)
        
        # 최대 개수를 초과하는 오래된 백업 파일들 삭제
        files_to_delete = backup_files[:-self.max_backups]
        
        for file_to_delete in files_to_delete:
            try:
                os.remove(file_to_delete)
                self.logger.debug(f"오래된 백업 파일 삭제: {file_to_delete}")
            except Exception as e:
                self.logger.warning(f"백업 파일 삭제 실패: {file_to_delete}, 오류: {str(e)}")
    
    def restore_backup(self, backup_path: str, target_path: str = None) -> str:
        """
        백업 파일을 복원합니다.
        
        Args:
            backup_path: 복원할 백업 파일 경로
            target_path: 복원할 대상 경로 (None이면 원본 경로로 추정)
            
        Returns:
            str: 복원된 파일 경로
            
        Raises:
            FileSystemError: 백업 파일이 존재하지 않거나 복원 실패 시
            TTLSyntaxError: TTL 파일 검증 실패 시
        """
        # 백업 파일 존재 확인
        if not os.path.exists(backup_path):
            error_msg = f"백업 파일이 존재하지 않습니다: {backup_path}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg)
        
        # 대상 경로 결정
        if target_path is None:
            target_path = self._infer_original_path(backup_path)
        
        # TTL 파일 검증 (백업 파일이 TTL인 경우)
        if self.validate_ttl and backup_path.lower().endswith(".ttl"):
            self._validate_ttl_file(backup_path)
        
        try:
            # 기존 파일이 있으면 임시 백업 생성
            temp_backup = None
            if os.path.exists(target_path):
                temp_backup = f"{target_path}.temp_backup"
                shutil.copy2(target_path, temp_backup)
            
            # 백업 파일 복원
            shutil.copy2(backup_path, target_path)
            
            # 임시 백업 삭제
            if temp_backup and os.path.exists(temp_backup):
                os.remove(temp_backup)
            
            self.logger.info(f"백업 복원 완료: {backup_path} -> {target_path}")
            return target_path
            
        except Exception as e:
            # 복원 실패 시 임시 백업으로 롤백
            if temp_backup and os.path.exists(temp_backup):
                try:
                    shutil.copy2(temp_backup, target_path)
                    os.remove(temp_backup)
                    self.logger.info(f"복원 실패로 인한 롤백 완료: {target_path}")
                except Exception as rollback_error:
                    self.logger.error(f"롤백 실패: {str(rollback_error)}")
            
            error_msg = f"백업 복원 실패: {str(e)}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg)
    
    def _infer_original_path(self, backup_path: str) -> str:
        """
        백업 파일 경로로부터 원본 파일 경로를 추정합니다.
        
        Args:
            backup_path: 백업 파일 경로
            
        Returns:
            str: 추정된 원본 파일 경로
        """
        backup_filename = os.path.basename(backup_path)
        
        # 백업 파일명 패턴: {name}_backup_{timestamp}{ext}
        pattern = r"(.+)_backup_\d{8}_\d{6}(\..+)?"
        match = re.match(pattern, backup_filename)
        
        if match:
            name = match.group(1)
            ext = match.group(2) or ""
            original_filename = f"{name}{ext}"
        else:
            # 패턴이 맞지 않으면 _backup_ 부분만 제거
            original_filename = backup_filename.replace("_backup_", "_")
        
        return original_filename
    
    def list_backups(self, file_path: str = None) -> List[Dict[str, Union[str, float, int]]]:
        """
        백업 파일 목록을 반환합니다.
        
        Args:
            file_path: 특정 파일의 백업만 조회 (None이면 모든 백업)
            
        Returns:
            List[Dict]: 백업 파일 정보 목록
        """
        backups = []
        
        if file_path:
            # 특정 파일의 백업만 조회
            file_name = os.path.basename(file_path)
            name, ext = os.path.splitext(file_name)
            pattern = os.path.join(self.backup_dir, f"{name}_backup_*{ext}")
        else:
            # 모든 백업 파일 조회
            pattern = os.path.join(self.backup_dir, "*_backup_*")
        
        backup_files = glob.glob(pattern)
        
        for backup_file in backup_files:
            try:
                stat = os.stat(backup_file)
                original_file = self._infer_original_path(backup_file)
                
                backups.append({
                    'path': backup_file,
                    'original_file': original_file,
                    'created_time': stat.st_mtime,
                    'size': stat.st_size
                })
            except Exception as e:
                self.logger.warning(f"백업 파일 정보 조회 실패: {backup_file}, 오류: {str(e)}")
        
        # 생성 시간 기준으로 정렬 (최신순)
        backups.sort(key=lambda x: x['created_time'], reverse=True)
        
        return backups
    
    def verify_backup_integrity(self, backup_path: str) -> bool:
        """
        백업 파일의 무결성을 검증합니다.
        
        Args:
            backup_path: 검증할 백업 파일 경로
            
        Returns:
            bool: 무결성 검증 결과
        """
        try:
            # 파일 존재 확인
            if not os.path.exists(backup_path):
                self.logger.error(f"백업 파일이 존재하지 않습니다: {backup_path}")
                return False
            
            # 파일 크기 확인 (0바이트 파일 체크)
            if os.path.getsize(backup_path) == 0:
                self.logger.error(f"백업 파일이 비어있습니다: {backup_path}")
                return False
            
            # TTL 파일인 경우 문법 검증
            if self.validate_ttl and backup_path.lower().endswith(".ttl"):
                self._validate_ttl_file(backup_path)
            
            self.logger.debug(f"백업 파일 무결성 검증 성공: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"백업 파일 무결성 검증 실패: {backup_path}, 오류: {str(e)}")
            return False


class FileManager:
    """
    파일 관리 유틸리티 클래스.
    
    파일 저장 실패 시 대체 경로 사용 및 안전한 파일 작업을 위한 기능을 제공합니다.
    """
    
    def __init__(self, primary_dir: str = "data", fallback_dirs: List[str] = None):
        """
        FileManager 초기화.
        
        Args:
            primary_dir: 기본 저장 디렉토리
            fallback_dirs: 대체 저장 디렉토리 목록
        """
        self.primary_dir = primary_dir
        self.fallback_dirs = fallback_dirs or [
            "fallback_data",
            tempfile.gettempdir(),
            os.path.expanduser("~")
        ]
        
        self.logger = logging.getLogger(__name__)
        
        # 기본 디렉토리 생성
        self._ensure_directory(self.primary_dir)
    
    def _ensure_directory(self, directory: str) -> None:
        """
        디렉토리가 존재하는지 확인하고, 없으면 생성합니다.
        
        Args:
            directory: 확인/생성할 디렉토리 경로
            
        Raises:
            FileSystemError: 디렉토리 생성 실패 시
        """
        try:
            os.makedirs(directory, exist_ok=True)
            self.logger.debug(f"디렉토리 확인/생성 완료: {directory}")
        except Exception as e:
            error_msg = f"디렉토리 생성 실패: {directory}, 오류: {str(e)}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg)
    
    def safe_write_file(self, filename: str, content: str, encoding: str = 'utf-8') -> str:
        """
        파일을 안전하게 저장합니다. 실패 시 대체 경로를 시도합니다.
        
        Args:
            filename: 저장할 파일명
            content: 파일 내용
            encoding: 파일 인코딩
            
        Returns:
            str: 실제 저장된 파일 경로
            
        Raises:
            FileSystemError: 모든 경로에서 저장 실패 시
        """
        # 기본 경로 시도
        primary_path = os.path.join(self.primary_dir, filename)
        
        try:
            with open(primary_path, 'w', encoding=encoding) as f:
                f.write(content)
            self.logger.info(f"파일 저장 성공: {primary_path}")
            return primary_path
        except Exception as e:
            self.logger.warning(f"기본 경로 저장 실패: {primary_path}, 오류: {str(e)}")
        
        # 대체 경로들 시도
        for fallback_dir in self.fallback_dirs:
            try:
                self._ensure_directory(fallback_dir)
                fallback_path = os.path.join(fallback_dir, filename)
                
                with open(fallback_path, 'w', encoding=encoding) as f:
                    f.write(content)
                
                self.logger.warning(f"대체 경로에 파일 저장: {fallback_path}")
                return fallback_path
                
            except Exception as e:
                self.logger.debug(f"대체 경로 저장 실패: {fallback_dir}, 오류: {str(e)}")
                continue
        
        # 모든 경로에서 실패
        error_msg = f"모든 경로에서 파일 저장 실패: {filename}"
        self.logger.error(error_msg)
        raise FileSystemError(error_msg)
    
    def safe_read_file(self, file_path: str, encoding: str = 'utf-8') -> str:
        """
        파일을 안전하게 읽습니다.
        
        Args:
            file_path: 읽을 파일 경로
            encoding: 파일 인코딩
            
        Returns:
            str: 파일 내용
            
        Raises:
            FileSystemError: 파일 읽기 실패 시
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            self.logger.debug(f"파일 읽기 성공: {file_path}")
            return content
        except Exception as e:
            error_msg = f"파일 읽기 실패: {file_path}, 오류: {str(e)}"
            self.logger.error(error_msg)
            raise FileSystemError(error_msg)