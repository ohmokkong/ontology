"""
백업 매니저 테스트 모듈.
이 모듈은 백업 매니저의 기능을 테스트합니다.
"""

import unittest
import os
import tempfile
import shutil
import time
from unittest.mock import MagicMock, patch, mock_open

from backup_manager import BackupManager, FileManager
from exceptions import BackupError, FileSystemError, TTLSyntaxError


class TestBackupManager(unittest.TestCase):
    """백업 매니저 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.test_dir, "backups")
        
        # 백업 매니저 초기화
        self.backup_manager = BackupManager(
            backup_dir=self.backup_dir,
            max_backups=3,
            backup_interval=1,  # 1초 (테스트용)
            validate_ttl=False  # TTL 검증 비활성화 (테스트용)
        )
        
        # 테스트 파일 생성
        self.test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(self.test_file, 'w') as f:
            f.write("테스트 파일 내용")
    
    def tearDown(self):
        """테스트 정리."""
        # 임시 디렉토리 삭제
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_backup_directory_creation(self):
        """백업 디렉토리 생성 테스트."""
        self.assertTrue(os.path.exists(self.backup_dir))
        self.assertTrue(os.path.isdir(self.backup_dir))
    
    def test_create_backup_success(self):
        """백업 생성 성공 테스트."""
        backup_path = self.backup_manager.create_backup(self.test_file, force=True)
        
        # 백업 파일이 생성되었는지 확인
        self.assertTrue(os.path.exists(backup_path))
        
        # 백업 파일 내용 확인
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "테스트 파일 내용")
        
        # 백업 파일명 패턴 확인
        backup_filename = os.path.basename(backup_path)
        self.assertTrue(backup_filename.startswith("test_file_backup_"))
        self.assertTrue(backup_filename.endswith(".txt"))
    
    def test_create_backup_file_not_exists(self):
        """존재하지 않는 파일 백업 시도 테스트."""
        non_existent_file = os.path.join(self.test_dir, "non_existent.txt")
        
        with self.assertRaises(FileSystemError):
            self.backup_manager.create_backup(non_existent_file)
    
    def test_backup_interval_check(self):
        """백업 간격 확인 테스트."""
        # 첫 번째 백업 생성
        backup_path1 = self.backup_manager.create_backup(self.test_file, force=True)
        
        # 간격이 충분하지 않은 상태에서 백업 시도
        backup_path2 = self.backup_manager.create_backup(self.test_file, force=False)
        
        # 같은 백업 파일이 반환되어야 함
        self.assertEqual(backup_path1, backup_path2)
        
        # 시간 경과 후 백업 시도
        time.sleep(2)  # backup_interval(1초)보다 길게 대기
        backup_path3 = self.backup_manager.create_backup(self.test_file, force=False)
        
        # 새로운 백업 파일이 생성되어야 함
        self.assertNotEqual(backup_path1, backup_path3)
    
    def test_cleanup_old_backups(self):
        """오래된 백업 정리 테스트."""
        # max_backups(3)보다 많은 백업 생성
        backup_paths = []
        for i in range(5):
            backup_path = self.backup_manager.create_backup(self.test_file, force=True)
            backup_paths.append(backup_path)
            time.sleep(0.1)  # 파일 생성 시간 차이를 위해
        
        # 최대 3개의 백업만 남아있어야 함
        existing_backups = self.backup_manager.list_backups(self.test_file)
        self.assertEqual(len(existing_backups), 3)
        
        # 가장 최근 3개의 백업이 남아있는지 확인
        for backup_info in existing_backups:
            self.assertIn(backup_info['path'], backup_paths[-3:])
    
    def test_get_latest_backup(self):
        """최신 백업 조회 테스트."""
        # 백업이 없는 경우
        latest = self.backup_manager._get_latest_backup(self.test_file)
        self.assertIsNone(latest)
        
        # 백업 생성 후 조회
        backup_path1 = self.backup_manager.create_backup(self.test_file, force=True)
        time.sleep(0.1)
        backup_path2 = self.backup_manager.create_backup(self.test_file, force=True)
        
        latest = self.backup_manager._get_latest_backup(self.test_file)
        self.assertEqual(latest, backup_path2)
    
    def test_restore_backup(self):
        """백업 복원 테스트."""
        # 백업 생성
        backup_path = self.backup_manager.create_backup(self.test_file, force=True)
        
        # 원본 파일 수정
        with open(self.test_file, 'w') as f:
            f.write("수정된 내용")
        
        # 백업 복원
        restored_path = self.backup_manager.restore_backup(backup_path, self.test_file)
        
        # 복원된 내용 확인
        with open(restored_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "테스트 파일 내용")
    
    def test_restore_backup_file_not_exists(self):
        """존재하지 않는 백업 파일 복원 시도 테스트."""
        non_existent_backup = os.path.join(self.backup_dir, "non_existent_backup.txt")
        
        with self.assertRaises(FileSystemError):
            self.backup_manager.restore_backup(non_existent_backup)
    
    def test_infer_original_path(self):
        """원본 파일 경로 추정 테스트."""
        backup_filename = "test_file_backup_20231201_120000.txt"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        original_path = self.backup_manager._infer_original_path(backup_path)
        self.assertEqual(original_path, "test_file.txt")
    
    def test_list_backups(self):
        """백업 목록 조회 테스트."""
        # 백업 생성
        backup_path1 = self.backup_manager.create_backup(self.test_file, force=True)
        time.sleep(0.1)
        backup_path2 = self.backup_manager.create_backup(self.test_file, force=True)
        
        # 특정 파일의 백업 목록 조회
        backups = self.backup_manager.list_backups(self.test_file)
        self.assertEqual(len(backups), 2)
        
        # 최신 백업이 첫 번째에 있는지 확인
        self.assertEqual(backups[0]['path'], backup_path2)
        self.assertEqual(backups[1]['path'], backup_path1)
        
        # 백업 정보 확인
        for backup_info in backups:
            self.assertIn('path', backup_info)
            self.assertIn('original_file', backup_info)
            self.assertIn('created_time', backup_info)
            self.assertIn('size', backup_info)
    
    def test_verify_backup_integrity(self):
        """백업 무결성 검증 테스트."""
        # 정상 백업 파일
        backup_path = self.backup_manager.create_backup(self.test_file, force=True)
        self.assertTrue(self.backup_manager.verify_backup_integrity(backup_path))
        
        # 존재하지 않는 파일
        non_existent_backup = os.path.join(self.backup_dir, "non_existent.txt")
        self.assertFalse(self.backup_manager.verify_backup_integrity(non_existent_backup))
        
        # 빈 파일
        empty_backup = os.path.join(self.backup_dir, "empty_backup.txt")
        with open(empty_backup, 'w') as f:
            pass  # 빈 파일 생성
        self.assertFalse(self.backup_manager.verify_backup_integrity(empty_backup))
    
    @patch('backup_manager.Graph')
    def test_validate_ttl_file_success(self, mock_graph):
        """TTL 파일 검증 성공 테스트."""
        # TTL 검증 활성화
        self.backup_manager.validate_ttl = True
        
        # Mock 설정
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        
        # TTL 파일 생성
        ttl_file = os.path.join(self.test_dir, "test.ttl")
        with open(ttl_file, 'w') as f:
            f.write("@prefix ex: <http://example.org/> .")
        
        # 검증 실행 (예외가 발생하지 않아야 함)
        self.backup_manager._validate_ttl_file(ttl_file)
        
        # Graph.parse가 호출되었는지 확인
        mock_graph_instance.parse.assert_called_once_with(ttl_file, format="turtle")
    
    @patch('backup_manager.Graph')
    def test_validate_ttl_file_failure(self, mock_graph):
        """TTL 파일 검증 실패 테스트."""
        # TTL 검증 활성화
        self.backup_manager.validate_ttl = True
        
        # Mock 설정 (파싱 오류 발생)
        mock_graph_instance = MagicMock()
        mock_graph_instance.parse.side_effect = Exception("TTL 파싱 오류")
        mock_graph.return_value = mock_graph_instance
        
        # TTL 파일 생성
        ttl_file = os.path.join(self.test_dir, "invalid.ttl")
        with open(ttl_file, 'w') as f:
            f.write("잘못된 TTL 내용")
        
        # 검증 실행 (TTLSyntaxError 발생해야 함)
        with self.assertRaises(TTLSyntaxError):
            self.backup_manager._validate_ttl_file(ttl_file)
    
    @patch('shutil.copy2')
    def test_fallback_paths(self, mock_copy2):
        """대체 경로 사용 테스트."""
        # 기본 경로에서 실패하도록 설정
        mock_copy2.side_effect = [PermissionError("권한 없음"), None]
        
        # 백업 생성 시도
        backup_path = self.backup_manager.create_backup(self.test_file, force=True)
        
        # 대체 경로에 백업이 생성되었는지 확인
        self.assertIsNotNone(backup_path)
        self.assertIn("fallback_backups", backup_path)


class TestFileManager(unittest.TestCase):
    """파일 매니저 테스트 클래스."""
    
    def setUp(self):
        """테스트 설정."""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.primary_dir = os.path.join(self.test_dir, "primary")
        self.fallback_dir = os.path.join(self.test_dir, "fallback")
        
        # 파일 매니저 초기화
        self.file_manager = FileManager(
            primary_dir=self.primary_dir,
            fallback_dirs=[self.fallback_dir]
        )
    
    def tearDown(self):
        """테스트 정리."""
        # 임시 디렉토리 삭제
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_primary_directory_creation(self):
        """기본 디렉토리 생성 테스트."""
        self.assertTrue(os.path.exists(self.primary_dir))
        self.assertTrue(os.path.isdir(self.primary_dir))
    
    def test_safe_write_file_success(self):
        """파일 안전 저장 성공 테스트."""
        filename = "test_file.txt"
        content = "테스트 내용"
        
        saved_path = self.file_manager.safe_write_file(filename, content)
        
        # 기본 경로에 저장되었는지 확인
        expected_path = os.path.join(self.primary_dir, filename)
        self.assertEqual(saved_path, expected_path)
        
        # 파일 내용 확인
        with open(saved_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)
    
    @patch('builtins.open')
    def test_safe_write_file_fallback(self, mock_open_func):
        """파일 저장 대체 경로 사용 테스트."""
        filename = "test_file.txt"
        content = "테스트 내용"
        
        # 기본 경로에서 실패하도록 설정
        def side_effect(path, mode, encoding=None):
            if self.primary_dir in path:
                raise PermissionError("권한 없음")
            else:
                return mock_open(read_data=content).return_value
        
        mock_open_func.side_effect = side_effect
        
        # 실제 대체 디렉토리 생성
        os.makedirs(self.fallback_dir, exist_ok=True)
        
        # 파일 저장 시도
        with patch('builtins.open', mock_open()) as mock_file:
            # 실제 파일 저장을 위해 대체 경로에 파일 생성
            fallback_path = os.path.join(self.fallback_dir, filename)
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            saved_path = self.file_manager.safe_write_file(filename, content)
            
            # 대체 경로에 저장되었는지 확인
            self.assertEqual(saved_path, fallback_path)
    
    def test_safe_read_file_success(self):
        """파일 안전 읽기 성공 테스트."""
        # 테스트 파일 생성
        test_file = os.path.join(self.primary_dir, "test_read.txt")
        test_content = "읽기 테스트 내용"
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # 파일 읽기
        content = self.file_manager.safe_read_file(test_file)
        self.assertEqual(content, test_content)
    
    def test_safe_read_file_not_exists(self):
        """존재하지 않는 파일 읽기 테스트."""
        non_existent_file = os.path.join(self.primary_dir, "non_existent.txt")
        
        with self.assertRaises(FileSystemError):
            self.file_manager.safe_read_file(non_existent_file)


if __name__ == '__main__':
    unittest.main()