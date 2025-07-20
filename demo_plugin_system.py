"""
플러그인 시스템 데모 스크립트.
이 스크립트는 플러그인 시스템의 기능을 시연합니다.
"""

import os
import logging
from plugin_system import PluginManager, get_plugin_manager
from test_plugin_system import TestAPIClient, TestDataConverter, TestProcessor

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    """메인 함수."""
    print("=== 플러그인 시스템 데모 ===")
    
    try:
        # 1. 플러그인 매니저 초기화
        print("\n1. 플러그인 매니저 초기화...")
        plugin_manager = PluginManager(
            plugin_dirs=["demo_plugins"],
            config={
                "test_api": {
                    "base_url": "https://api.example.com",
                    "api_key": "demo-key-12345"
                },
                "test_converter": {
                    "encoding": "utf-8"
                },
                "test_processor": {
                    "batch_size": 100
                }
            }
        )
        
        print("✅ 플러그인 매니저 초기화 완료")
        
        # 2. 테스트 플러그인들 수동 등록
        print("\n2. 테스트 플러그인들 등록...")
        
        # API 클라이언트 플러그인 등록
        test_api = TestAPIClient()
        test_api.initialize(plugin_manager.config.get("test_api", {}))
        plugin_manager.registry.register_plugin('api_client', test_api)
        
        # 데이터 변환기 플러그인 등록
        test_converter = TestDataConverter()
        test_converter.initialize(plugin_manager.config.get("test_converter", {}))
        plugin_manager.registry.register_plugin('data_converter', test_converter)
        
        # 데이터 처리기 플러그인 등록
        test_processor = TestProcessor()
        test_processor.initialize(plugin_manager.config.get("test_processor", {}))
        plugin_manager.registry.register_plugin('processor', test_processor)
        
        print("✅ 3개의 테스트 플러그인이 등록되었습니다.")
        
        # 3. 플러그인 정보 조회
        print("\n3. 등록된 플러그인 정보...")
        plugin_info = plugin_manager.get_plugin_info()
        
        print(f"플러그인 디렉토리: {plugin_info['plugin_dirs']}")
        print(f"총 플러그인 수: {plugin_info['total_plugins']}")
        
        for plugin_type, plugins in plugin_info['loaded_plugins'].items():
            if plugins:
                print(f"\n{plugin_type.upper()} 플러그인:")
                for plugin in plugins:
                    print(f"  - {plugin['name']} v{plugin['version']}: {plugin['description']}")
        
        # 4. API 클라이언트 플러그인 사용
        print("\n4. API 클라이언트 플러그인 사용...")
        
        # API 검색 실행
        search_results = plugin_manager.execute_api_search('test_api', 'apple')
        print(f"검색 결과: {search_results}")
        
        # API 상세 정보 조회
        api_client = plugin_manager.get_api_client('test_api')
        detail_result = api_client.get_detail('123')
        print(f"상세 정보: {detail_result}")
        
        # 5. 데이터 변환기 플러그인 사용
        print("\n5. 데이터 변환기 플러그인 사용...")
        
        test_data = {"name": "사과", "calories": 52, "nutrients": ["비타민C", "식이섬유"]}
        
        # 데이터 변환 (변환기 이름 지정)
        converted_data = plugin_manager.convert_data(
            test_data, 'json', 'xml', converter_name='test_converter'
        )
        print(f"변환된 데이터: {converted_data}")
        
        # 자동 변환기 선택
        auto_converted = plugin_manager.convert_data(test_data, 'json', 'xml')
        print(f"자동 변환 결과: {auto_converted}")
        
        # 6. 데이터 처리기 플러그인 사용
        print("\n6. 데이터 처리기 플러그인 사용...")
        
        # 데이터 처리 (처리기 이름 지정)
        processed_data = plugin_manager.process_data(
            test_data, processor_name='test_processor'
        )
        print(f"처리된 데이터: {processed_data}")
        
        # 자동 처리기 선택
        auto_processed = plugin_manager.process_data(test_data)
        print(f"자동 처리 결과: {auto_processed}")
        
        # 7. 플러그인 검색 기능
        print("\n7. 플러그인 검색 기능...")
        
        # 형식별 변환기 찾기
        converter = plugin_manager.find_converter_for_format('json', 'xml')
        if converter:
            print(f"JSON->XML 변환기 발견: {converter.name}")
        else:
            print("JSON->XML 변환기를 찾을 수 없습니다.")
        
        # 데이터별 처리기 찾기
        processor = plugin_manager.find_processor_for_data({"test": "data"})
        if processor:
            print(f"딕셔너리 데이터 처리기 발견: {processor.name}")
        else:
            print("딕셔너리 데이터 처리기를 찾을 수 없습니다.")
        
        # 8. 플러그인 템플릿 생성
        print("\n8. 플러그인 템플릿 생성...")
        
        # API 클라이언트 템플릿 생성
        api_template_path = plugin_manager.create_plugin_template(
            'api_client', 'nutrition_api', 'demo_plugins'
        )
        print(f"✅ API 클라이언트 템플릿 생성: {api_template_path}")
        
        # 데이터 변환기 템플릿 생성
        converter_template_path = plugin_manager.create_plugin_template(
            'data_converter', 'json_to_rdf', 'demo_plugins'
        )
        print(f"✅ 데이터 변환기 템플릿 생성: {converter_template_path}")
        
        # 데이터 처리기 템플릿 생성
        processor_template_path = plugin_manager.create_plugin_template(
            'processor', 'calorie_calculator', 'demo_plugins'
        )
        print(f"✅ 데이터 처리기 템플릿 생성: {processor_template_path}")
        
        # 9. 오류 처리 시연
        print("\n9. 오류 처리 시연...")
        
        try:
            # 존재하지 않는 API 클라이언트 사용
            plugin_manager.execute_api_search('non_existent_api', 'query')
        except ValueError as e:
            print(f"예상된 오류: {e}")
        
        try:
            # 지원하지 않는 형식 변환
            plugin_manager.convert_data(test_data, 'json', 'yaml')
        except ValueError as e:
            print(f"예상된 오류: {e}")
        
        # 10. 전역 플러그인 매니저 사용
        print("\n10. 전역 플러그인 매니저 사용...")
        
        global_manager = get_plugin_manager()
        print(f"전역 플러그인 매니저 디렉토리: {global_manager.plugin_dirs}")
        
        # 11. 플러그인 확장성 시연
        print("\n11. 플러그인 확장성 시연...")
        
        # 새로운 API 클라이언트 플러그인 클래스 정의 (런타임)
        class NewAPIClient(plugin_manager.registry.plugins['api_client']['test_api'].__class__):
            @property
            def name(self):
                return "new_api"
            
            @property
            def description(self):
                return "런타임에 생성된 새로운 API 클라이언트"
            
            def search(self, query, **kwargs):
                return [{"id": "new_1", "name": f"새로운 결과: {query}"}]
        
        # 새 플러그인 등록
        new_api = NewAPIClient()
        new_api.initialize({})
        plugin_manager.registry.register_plugin('api_client', new_api)
        
        # 새 플러그인 사용
        new_results = plugin_manager.execute_api_search('new_api', 'test')
        print(f"새로운 API 클라이언트 결과: {new_results}")
        
        # 12. 최종 플러그인 상태
        print("\n12. 최종 플러그인 상태...")
        final_info = plugin_manager.get_plugin_info()
        print(f"최종 플러그인 수: {final_info['total_plugins']}")
        
        # 플러그인 목록 출력
        plugin_list = plugin_manager.registry.list_plugins()
        for plugin_type, plugin_names in plugin_list.items():
            if plugin_names:
                print(f"{plugin_type}: {', '.join(plugin_names)}")
        
        print("\n=== 플러그인 시스템 데모 완료 ===")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()