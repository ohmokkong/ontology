"""
백업 및 파일 관리 매니저.

온톨로지 파일 자동 백업 생성, TTL 문법 검증 및 오류 처리,
파일 저장 실패 시 대체 경로 사용 기능을 제공합니다.
"""

import os
import shutil
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from rdflib import Graph
from rdflib.exceptions import ParserError
from rdflib.plugins.parsers.notation3 import BadSyntax

from ontology_manager import OntologyManager, ValidationResult
from exceptions import DataValidationError, CalorieCalculationError


class BackupStrategy(Enum):
    """백업 전략."""
    TIMESTAMP = "timestamp"      # 타임스탬프 기반
    INCREMENTAL = "incremental"  # 증분 백업
    VERSIONED = "versioned"      # 버전 기반
    ROLLING = "rolling"          # 롤링 백업


class BackupStatus(Enum):
    """백업 상태."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class BackupConfig:
    """백업 설정."""
    strategy: BackupStrategy = BackupStrategy.TIMESTAMP
    max_backups: int = 10
    backup_interval_hours: int = 24
    compression_enabled: bool = False
    checksum_validation: bool = True
    alternative_paths: List[str] = field(default_factory=list)
    auto_cleanup: bool = True


@dataclass
class BackupRecord:
    """백업 기록."""
    backup_id: str
    original_file: str
    backup_file: str
    timestamp: datetime
    file_size: int
    checksum: str
    status: BackupStatus
    strategy: BackupStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileOperationResult:
    """파일 작업 결과."""
    success: bool
    file_path: str
    operation: str
    timestamp: datetime
    error_message: Optional[str] = None
    alternative_path_used: bool = False
    backup_created: bool = False
    validation_result: Optional[ValidationResult] = None
cl
ass BackupManager:
    """
    백업 및 파일 관리 매니저.
    
    온톨로지 파일의 자동 백업, 검증, 복구 및 대체 경로 관리 기능을 제공합니다.
    """
    
    def __init__(self, config: Optional[BackupConfig] = None, ontology_manager: Optional[OntologyManager] = None):
        """
        BackupManager 초기화.
        
        Args:
            config: 백업 설정
            ontology_manager: 온톨로지 매니저 인스턴스
        """
        self.config = config or BackupConfig()
        self.ontology_manager = ontology_manager or OntologyManager()
        
        # 백업 기록 저장소
        self.backup_records: List[BackupRecord] = []
        self.backup_history_file = "backup_history.json"
        
        # 기본 백업 디렉토리
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # 대체 경로 설정
        self.alternative_paths = [
            Path("backups/alternative"),
            Path("temp/backups"),
            Path.home() / "Documents" / "ontology_backups"
        ]
        
        # 백업 기록 로드
        self._load_backup_history()
        
        print("✓ 백업 매니저 초기화 완료")
        print(f"  - 백업 전략: {self.config.strategy.value}")
        print(f"  - 최대 백업 수: {self.config.max_backups}")
        print(f"  - 백업 디렉토리: {self.backup_dir}")
    
    def create_backup(self, file_path: str, strategy: Optional[BackupStrategy] = None) -> BackupRecord:
        """
        파일 백업을 생성합니다.
        
        Args:
            file_path: 백업할 파일 경로
            strategy: 백업 전략 (기본값: 설정된 전략)
            
        Returns:
            BackupRecord: 백업 기록
            
        Raises:
            DataValidationError: 백업 생성 실패 시
        """
        if not os.path.exists(file_path):
            raise DataValidationError(f"백업할 파일을 찾을 수 없습니다: {file_path}")
        
        strategy = strategy or self.config.strategy
        
        try:
            # 백업 파일명 생성
            backup_filename = self._generate_backup_filename(file_path, strategy)
            backup_path = self.backup_dir / backup_filename
            
            # 백업 디렉토리 확인 및 생성
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 복사
            shutil.copy2(file_path, backup_path)
            
            # 체크섬 계산
            checksum = self._calculate_checksum(backup_path)
            
            # 백업 기록 생성
            backup_record = BackupRecord(
                backup_id=self._generate_backup_id(),
                original_file=file_path,
                backup_file=str(backup_path),
                timestamp=datetime.now(),
                file_size=os.path.getsize(backup_path),
                checksum=checksum,
                status=BackupStatus.SUCCESS,
                strategy=strategy,
                metadata={
                    "original_size": os.path.getsize(file_path),
                    "compression": self.config.compression_enabled
                }
            )
            
            # 백업 기록 저장
            self.backup_records.append(backup_record)
            self._save_backup_history()
            
            # 자동 정리
            if self.config.auto_cleanup:
                self._cleanup_old_backups(file_path)
            
            print(f"✓ 백업 생성 완료:")
            print(f"  - 원본: {file_path}")
            print(f"  - 백업: {backup_path}")
            print(f"  - 전략: {strategy.value}")
            print(f"  - 크기: {backup_record.file_size} bytes")
            
            return backup_record
            
        except Exception as e:
            # 실패한 백업 기록
            failed_record = BackupRecord(
                backup_id=self._generate_backup_id(),
                original_file=file_path,
                backup_file="",
                timestamp=datetime.now(),
                file_size=0,
                checksum="",
                status=BackupStatus.FAILED,
                strategy=strategy,
                metadata={"error": str(e)}
            )
            
            self.backup_records.append(failed_record)
            self._save_backup_history()
            
            raise DataValidationError(f"백업 생성 실패: {str(e)}")    

    def save_with_backup(self, graph: Graph, file_path: str, validate: bool = True) -> FileOperationResult:
        """
        백업을 생성한 후 파일을 저장합니다.
        
        Args:
            graph: 저장할 RDF 그래프
            file_path: 저장할 파일 경로
            validate: 저장 후 검증 여부
            
        Returns:
            FileOperationResult: 파일 작업 결과
        """
        print(f"📁 백업과 함께 파일 저장: {file_path}")
        
        result = FileOperationResult(
            success=False,
            file_path=file_path,
            operation="save_with_backup",
            timestamp=datetime.now()
        )
        
        try:
            # 기존 파일이 있으면 백업 생성
            if os.path.exists(file_path):
                backup_record = self.create_backup(file_path)
                result.backup_created = True
                print(f"✓ 기존 파일 백업 완료: {backup_record.backup_file}")
            
            # 파일 저장 시도
            success = self._save_to_path(graph, file_path)
            
            if not success:
                # 대체 경로 시도
                alternative_path = self._try_alternative_paths(graph, file_path)
                if alternative_path:
                    result.file_path = alternative_path
                    result.alternative_path_used = True
                    success = True
                    print(f"✓ 대체 경로 사용: {alternative_path}")
            
            if success:
                # 검증 수행
                if validate:
                    validation_result = self.ontology_manager.validate_ttl_syntax(result.file_path)
                    result.validation_result = validation_result
                    
                    if not validation_result.is_valid:
                        result.error_message = f"검증 실패: {len(validation_result.errors)}개 오류"
                        print(f"⚠️ 파일 검증 실패: {len(validation_result.errors)}개 오류")
                    else:
                        print(f"✓ 파일 검증 성공: {validation_result.triples_count}개 트리플")
                
                result.success = True
                print(f"✓ 파일 저장 완료: {result.file_path}")
            else:
                result.error_message = "모든 경로에서 저장 실패"
                print(f"❌ 파일 저장 실패: {file_path}")
            
            return result
            
        except Exception as e:
            result.error_message = str(e)
            print(f"❌ 파일 저장 중 오류: {str(e)}")
            return result
    
    def restore_from_backup(self, backup_id: str, target_path: Optional[str] = None) -> bool:
        """
        백업에서 파일을 복원합니다.
        
        Args:
            backup_id: 백업 ID
            target_path: 복원할 경로 (기본값: 원본 경로)
            
        Returns:
            bool: 복원 성공 여부
        """
        # 백업 기록 찾기
        backup_record = None
        for record in self.backup_records:
            if record.backup_id == backup_id:
                backup_record = record
                break
        
        if not backup_record:
            print(f"❌ 백업 기록을 찾을 수 없습니다: {backup_id}")
            return False
        
        if not os.path.exists(backup_record.backup_file):
            print(f"❌ 백업 파일을 찾을 수 없습니다: {backup_record.backup_file}")
            return False
        
        try:
            target = target_path or backup_record.original_file
            
            # 체크섬 검증
            if self.config.checksum_validation:
                current_checksum = self._calculate_checksum(backup_record.backup_file)
                if current_checksum != backup_record.checksum:
                    print(f"⚠️ 백업 파일 체크섬 불일치")
                    return False
            
            # 파일 복원
            shutil.copy2(backup_record.backup_file, target)
            
            print(f"✓ 백업 복원 완료:")
            print(f"  - 백업: {backup_record.backup_file}")
            print(f"  - 복원: {target}")
            print(f"  - 날짜: {backup_record.timestamp}")
            
            return True
            
        except Exception as e:
            print(f"❌ 백업 복원 실패: {str(e)}")
            return False
    
    def validate_and_repair(self, file_path: str) -> FileOperationResult:
        """
        파일을 검증하고 필요시 복구합니다.
        
        Args:
            file_path: 검증할 파일 경로
            
        Returns:
            FileOperationResult: 검증 및 복구 결과
        """
        print(f"🔍 파일 검증 및 복구: {file_path}")
        
        result = FileOperationResult(
            success=False,
            file_path=file_path,
            operation="validate_and_repair",
            timestamp=datetime.now()
        )
        
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                result.error_message = "파일이 존재하지 않음"
                return result
            
            # TTL 문법 검증
            validation_result = self.ontology_manager.validate_ttl_syntax(file_path)
            result.validation_result = validation_result
            
            if validation_result.is_valid:
                result.success = True
                print(f"✓ 파일 검증 성공: {validation_result.triples_count}개 트리플")
                return result
            
            # 검증 실패 시 복구 시도
            print(f"⚠️ 파일 검증 실패: {len(validation_result.errors)}개 오류")
            
            # 최근 백업에서 복구 시도
            recent_backup = self._find_recent_backup(file_path)
            if recent_backup:
                print(f"🔧 최근 백업에서 복구 시도: {recent_backup.backup_file}")
                
                if self.restore_from_backup(recent_backup.backup_id, file_path):
                    # 복구 후 재검증
                    validation_result = self.ontology_manager.validate_ttl_syntax(file_path)
                    result.validation_result = validation_result
                    
                    if validation_result.is_valid:
                        result.success = True
                        print(f"✓ 백업에서 복구 성공")
                    else:
                        result.error_message = "복구 후에도 검증 실패"
                else:
                    result.error_message = "백업에서 복구 실패"
            else:
                result.error_message = "복구할 백업이 없음"
            
            return result
            
        except Exception as e:
            result.error_message = str(e)
            print(f"❌ 검증 및 복구 중 오류: {str(e)}")
            return result    
   
 def _generate_backup_filename(self, file_path: str, strategy: BackupStrategy) -> str:
        """백업 파일명 생성."""
        file_path_obj = Path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if strategy == BackupStrategy.TIMESTAMP:
            return f"{file_path_obj.stem}_backup_{timestamp}{file_path_obj.suffix}"
        elif strategy == BackupStrategy.VERSIONED:
            version = len([r for r in self.backup_records if r.original_file == file_path]) + 1
            return f"{file_path_obj.stem}_v{version:03d}_{timestamp}{file_path_obj.suffix}"
        elif strategy == BackupStrategy.INCREMENTAL:
            return f"{file_path_obj.stem}_inc_{timestamp}{file_path_obj.suffix}"
        else:  # ROLLING
            return f"{file_path_obj.stem}_rolling_{timestamp}{file_path_obj.suffix}"
    
    def _generate_backup_id(self) -> str:
        """백업 ID 생성."""
        return f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.backup_records):04d}"
    
    def _calculate_checksum(self, file_path: str) -> str:
        """파일 체크섬 계산."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _save_to_path(self, graph: Graph, file_path: str) -> bool:
        """지정된 경로에 그래프 저장."""
        try:
            # 디렉토리 생성
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 그래프 저장
            graph.serialize(destination=file_path, format="turtle")
            return True
        except Exception as e:
            print(f"⚠️ 저장 실패 ({file_path}): {str(e)}")
            return False
    
    def _try_alternative_paths(self, graph: Graph, original_path: str) -> Optional[str]:
        """대체 경로에 저장 시도."""
        file_name = os.path.basename(original_path)
        
        for alt_path in self.alternative_paths:
            try:
                alt_path.mkdir(parents=True, exist_ok=True)
                full_path = alt_path / file_name
                
                if self._save_to_path(graph, str(full_path)):
                    return str(full_path)
            except Exception as e:
                print(f"⚠️ 대체 경로 저장 실패 ({alt_path}): {str(e)}")
                continue
        
        return None
    
    def _find_recent_backup(self, file_path: str) -> Optional[BackupRecord]:
        """최근 백업 찾기."""
        recent_backups = [
            record for record in self.backup_records
            if record.original_file == file_path and record.status == BackupStatus.SUCCESS
        ]
        
        if not recent_backups:
            return None
        
        return max(recent_backups, key=lambda x: x.timestamp)
    
    def _cleanup_old_backups(self, file_path: str) -> None:
        """오래된 백업 정리."""
        file_backups = [
            record for record in self.backup_records
            if record.original_file == file_path and record.status == BackupStatus.SUCCESS
        ]
        
        if len(file_backups) <= self.config.max_backups:
            return
        
        # 오래된 백업 정렬
        sorted_backups = sorted(file_backups, key=lambda x: x.timestamp, reverse=True)
        backups_to_remove = sorted_backups[self.config.max_backups:]
        
        for backup in backups_to_remove:
            try:
                if os.path.exists(backup.backup_file):
                    os.remove(backup.backup_file)
                    print(f"🗑️ 오래된 백업 삭제: {backup.backup_file}")
                
                self.backup_records.remove(backup)
            except Exception as e:
                print(f"⚠️ 백업 삭제 실패: {str(e)}")
        
        self._save_backup_history()
    
    def _load_backup_history(self) -> None:
        """백업 기록 로드."""
        if not os.path.exists(self.backup_history_file):
            return
        
        try:
            with open(self.backup_history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for record_data in data:
                record = BackupRecord(
                    backup_id=record_data['backup_id'],
                    original_file=record_data['original_file'],
                    backup_file=record_data['backup_file'],
                    timestamp=datetime.fromisoformat(record_data['timestamp']),
                    file_size=record_data['file_size'],
                    checksum=record_data['checksum'],
                    status=BackupStatus(record_data['status']),
                    strategy=BackupStrategy(record_data['strategy']),
                    metadata=record_data.get('metadata', {})
                )
                self.backup_records.append(record)
            
            print(f"✓ 백업 기록 로드: {len(self.backup_records)}개")
            
        except Exception as e:
            print(f"⚠️ 백업 기록 로드 실패: {str(e)}")
    
    def _save_backup_history(self) -> None:
        """백업 기록 저장."""
        try:
            data = []
            for record in self.backup_records:
                data.append({
                    'backup_id': record.backup_id,
                    'original_file': record.original_file,
                    'backup_file': record.backup_file,
                    'timestamp': record.timestamp.isoformat(),
                    'file_size': record.file_size,
                    'checksum': record.checksum,
                    'status': record.status.value,
                    'strategy': record.strategy.value,
                    'metadata': record.metadata
                })
            
            with open(self.backup_history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 백업 기록 저장 실패: {str(e)}")