#!/usr/bin/env python3
"""
영양 관리 CLI 실행 스크립트

이 스크립트는 nutrition-cli 명령어의 진입점입니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# CLI 인터페이스 import 및 실행
if __name__ == "__main__":
    try:
        from cli_interface import main
        main()
    except ImportError as e:
        print(f"❌ 모듈 import 오류: {e}")
        print("필요한 모듈들이 설치되어 있는지 확인해주세요.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        sys.exit(1)