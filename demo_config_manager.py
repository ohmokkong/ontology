"""
설정 관리 시스템 데모 스크립트.
이 스크립트는 설정 관리 시스템의 기능을 시연합니다.
"""

import os
import logging
from config_manager import ConfigManager, get_config_manager, get_config, set_config

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    """메인 함수."""
    print("=== 설정 관리 시스템 데모 ===")
    
    try:
        # 1. 설정 매니저 초기화
        print("\n1. 설정 매니저 초기화...")
        config_manager = ConfigManager(
            config_dir="demo_config",
            environment="development",
            auto_reload=False
        )
        
        # 2. 기본 설정 파일 생성
        print("\n2. 기본 설정 파일 생성...")
        config_manager.create_default_config()
        print("✅ 기본 설정 파일들이 생성되었습니다.")
        
        # 3. 설정 로드 및 조회
        print("\n3. 설정 로드 및 조회...")
        config_manager.load_config()
        
        # API 설정 조회
        food_api_config = config_manager.get_api_config("food")
        print(f"음식 API 설정:")
        print(f"  - Base URL: {food_api_config.get('base_url')}")
        print(f"  - Timeout: {food_api_config.get('timeout')}")
        print(f"  - Retry Count: {food_api_config.get('retry_count')}")
        
        # 캐시 설정 조회
        cache_config = config_manager.get_cache_config()
        print(f"캐시 설정:")
        print(f"  - Enabled: {cache_config.get('enabled')}")
        print(f"  - TTL: {cache_config.get('ttl')}")
        print(f"  - Max Size: {cache_config.get('max_size')}")
        
        # 4. 동적 설정 변경
        print("\n4. 동적 설정 변경...")
        config_manager.set("api.food.key", "demo-api-key-12345")
        config_manager.set("cache.ttl", 7200)
        config_manager.set("features.demo_mode", True)
        
        print("✅ 설정 값들이 동적으로 변경되었습니다.")
        print(f"  - 음식 API 키: {config_manager.get('api.food.key')}")
        print(f"  - 캐시 TTL: {config_manager.get('cache.ttl')}")
        print(f"  - 데모 모드: {config_manager.get('features.demo_mode')}")
        
        # 5. 환경 변수 오버라이드 시연
        print("\n5. 환경 변수 오버라이드 시연...")
        os.environ['FOOD_API_KEY'] = 'env-override-key'
        os.environ['API_TIMEOUT'] = '60'
        
        config_manager.reload_config()
        
        print("✅ 환경 변수로 설정이 오버라이드되었습니다.")
        print(f"  - 음식 API 키: {config_manager.get('api.food.key')}")
        print(f"  - API 타임아웃: {config_manager.get('api.timeout', 'N/A')}")
        
        # 6. 설정 검증
        print("\n6. 설정 검증...")
        validation_result = config_manager.validate_config()
        
        if validation_result['is_valid']:
            print("✅ 설정 검증 성공!")
        else:
            print("❌ 설정 검증 실패:")
            for error in validation_result['errors']:
                print(f"  - 오류: {error}")
        
        if validation_result['warnings']:
            print("⚠️ 경고사항:")
            for warning in validation_result['warnings']:
                print(f"  - 경고: {warning}")
        
        # 7. 설정 요약 정보
        print("\n7. 설정 요약 정보...")
        summary = config_manager.get_config_summary()
        print(f"환경: {summary['environment']}")
        print(f"설정 디렉토리: {summary['config_dir']}")
        print(f"자동 재로드: {summary['auto_reload']}")
        print(f"감시 중인 파일 수: {len(summary['watched_files'])}")
        print(f"설정 키 수: {len(summary['config_keys'])}")
        print(f"총 설정 항목 수: {summary['total_settings']}")
        
        # 8. 전역 설정 함수 사용
        print("\n8. 전역 설정 함수 사용...")
        
        # 전역 설정 매니저 사용
        global_manager = get_config_manager()
        print(f"전역 설정 매니저 환경: {global_manager.environment}")
        
        # 전역 설정 함수 사용
        set_config("demo.global_setting", "global_value")
        global_value = get_config("demo.global_setting")
        print(f"전역 설정 값: {global_value}")
        
        # 기본값 사용
        default_value = get_config("non.existent.key", "default_value")
        print(f"기본값 사용: {default_value}")
        
        # 9. 설정 저장
        print("\n9. 현재 설정 저장...")
        config_manager.save_config("demo_saved_config.json")
        print("✅ 현재 설정이 파일로 저장되었습니다.")
        
        # 10. 다양한 설정 조회 예제
        print("\n10. 다양한 설정 조회 예제...")
        
        # 중첩된 설정 조회
        nested_value = config_manager.get("api.food.endpoints.search", "기본 엔드포인트")
        print(f"중첩된 설정: {nested_value}")
        
        # 존재하지 않는 설정 조회 (기본값 사용)
        missing_value = config_manager.get("missing.config.key", "기본값")
        print(f"존재하지 않는 설정: {missing_value}")
        
        # 특정 API 설정 전체 조회
        exercise_config = config_manager.get_api_config("exercise")
        print(f"운동 API 설정 키 수: {len(exercise_config)}")
        
        print("\n=== 설정 관리 시스템 데모 완료 ===")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()