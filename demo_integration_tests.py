"""
API 연동 통합 테스트 데모 스크립트.
이 스크립트는 통합 테스트의 기능을 시연합니다.
"""

import time
import logging
from unittest.mock import Mock, patch
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def create_mock_food_response():
    """Mock 음식 API 응답을 생성합니다."""
    return {
        "getFoodNtrItdntList1": {
            "header": {
                "resultCode": "00",
                "resultMsg": "NORMAL SERVICE."
            },
            "body": {
                "pageNo": 1,
                "totalCount": 1,
                "numOfRows": 10,
                "items": [
                    {
                        "FOOD_CD": "D000001",
                        "FOOD_NM_KR": "사과",
                        "FOOD_NM_EN": "Apple",
                        "NUTR_CONT1": "52.0",  # 칼로리
                        "NUTR_CONT2": "13.8",  # 탄수화물
                        "NUTR_CONT3": "0.3",   # 단백질
                        "NUTR_CONT4": "0.2",   # 지방
                        "NUTR_CONT5": "2.4",   # 식이섬유
                        "NUTR_CONT6": "1.0",   # 나트륨
                        "SERVING_SIZE": "100",
                        "MAKER_NM": "자연산",
                        "GROUP_NM": "과일류"
                    }
                ]
            }
        }
    }

def create_mock_exercise_response():
    """Mock 운동 API 응답을 생성합니다."""
    return {
        "searchKeyword1": {
            "response": {
                "header": {
                    "resultCode": "0000",
                    "resultMsg": "OK"
                },
                "body": {
                    "items": {
                        "item": [
                            {
                                "contentid": "EX001",
                                "title": "걷기",
                                "overview": "일반적인 걷기 운동",
                                "cat3": "유산소운동",
                                "met": "3.5"
                            }
                        ]
                    },
                    "numOfRows": 10,
                    "pageNo": 1,
                    "totalCount": 1
                }
            }
        }
    }

def test_api_response_time():
    """API 응답 시간 테스트."""
    print("\n=== API 응답 시간 테스트 ===")
    
    # 시뮬레이션된 API 호출
    start_time = time.time()
    
    # Mock API 응답 처리 시뮬레이션
    mock_response = create_mock_food_response()
    time.sleep(0.1)  # 실제 API 호출 시뮬레이션
    
    response_time = time.time() - start_time
    
    print(f"API 응답 시간: {response_time:.3f}초")
    
    # 3초 이하 검증
    if response_time < 3.0:
        print("✅ API 응답 시간이 3초 이하입니다.")
    else:
        print("❌ API 응답 시간이 3초를 초과했습니다.")
    
    return response_time < 3.0

def test_error_handling():
    """오류 처리 테스트."""
    print("\n=== 오류 처리 테스트 ===")
    
    error_scenarios = [
        ("네트워크 오류", "ConnectionError"),
        ("타임아웃 오류", "TimeoutError"),
        ("HTTP 500 오류", "HTTPError"),
        ("잘못된 JSON", "JSONDecodeError")
    ]
    
    for scenario_name, error_type in error_scenarios:
        try:
            print(f"테스트 중: {scenario_name}")
            
            # 오류 시뮬레이션
            if error_type == "ConnectionError":
                raise Exception("네트워크 연결 실패")
            elif error_type == "TimeoutError":
                raise Exception("요청 시간 초과")
            elif error_type == "HTTPError":
                raise Exception("HTTP 500 Internal Server Error")
            elif error_type == "JSONDecodeError":
                raise Exception("JSON 파싱 오류")
            
        except Exception as e:
            print(f"  ✅ {scenario_name} 처리됨: {str(e)}")
    
    return True

def test_data_processing_flow():
    """데이터 처리 플로우 테스트."""
    print("\n=== 데이터 처리 플로우 테스트 ===")
    
    try:
        # 1. Mock API 응답 처리
        food_response = create_mock_food_response()
        food_item = food_response["getFoodNtrItdntList1"]["body"]["items"][0]
        
        print(f"1. 음식 데이터 조회: {food_item['FOOD_NM_KR']}")
        
        # 2. 영양 정보 추출
        calories = float(food_item["NUTR_CONT1"])
        carbs = float(food_item["NUTR_CONT2"])
        protein = float(food_item["NUTR_CONT3"])
        fat = float(food_item["NUTR_CONT4"])
        
        print(f"2. 영양 정보 추출:")
        print(f"   - 칼로리: {calories}kcal")
        print(f"   - 탄수화물: {carbs}g")
        print(f"   - 단백질: {protein}g")
        print(f"   - 지방: {fat}g")
        
        # 3. 칼로리 계산 (150g 기준)
        amount = 150
        calculated_calories = calories * (amount / 100)
        
        print(f"3. 칼로리 계산 ({amount}g): {calculated_calories}kcal")
        
        # 4. 운동 데이터 처리
        exercise_response = create_mock_exercise_response()
        exercise_item = exercise_response["searchKeyword1"]["response"]["body"]["items"]["item"][0]
        
        print(f"4. 운동 데이터 조회: {exercise_item['title']}")
        
        # 5. 운동 칼로리 계산
        met = float(exercise_item["met"])
        weight = 70  # kg
        duration = 30  # 분
        
        exercise_calories = met * weight * (duration / 60) * 1.05
        
        print(f"5. 운동 칼로리 계산:")
        print(f"   - MET: {met}")
        print(f"   - 체중: {weight}kg")
        print(f"   - 시간: {duration}분")
        print(f"   - 소모 칼로리: {exercise_calories:.1f}kcal")
        
        # 6. 칼로리 밸런스
        balance = calculated_calories - exercise_calories
        
        print(f"6. 칼로리 밸런스:")
        print(f"   - 섭취: {calculated_calories}kcal")
        print(f"   - 소모: {exercise_calories:.1f}kcal")
        print(f"   - 밸런스: {balance:.1f}kcal")
        
        print("✅ 데이터 처리 플로우 완료")
        return True
        
    except Exception as e:
        print(f"❌ 데이터 처리 플로우 실패: {str(e)}")
        return False

def test_concurrent_processing():
    """동시 처리 테스트."""
    print("\n=== 동시 처리 테스트 ===")
    
    import threading
    import queue
    
    results = queue.Queue()
    errors = queue.Queue()
    
    def process_request(request_id):
        """개별 요청 처리."""
        try:
            # API 호출 시뮬레이션
            time.sleep(0.1)
            
            # 데이터 처리 시뮬레이션
            mock_data = create_mock_food_response()
            
            results.put(f"요청 {request_id} 완료")
            
        except Exception as e:
            errors.put(f"요청 {request_id} 실패: {str(e)}")
    
    # 10개의 동시 요청 생성
    threads = []
    for i in range(10):
        thread = threading.Thread(target=process_request, args=(i,))
        threads.append(thread)
        thread.start()
    
    # 모든 스레드 완료 대기
    for thread in threads:
        thread.join()
    
    # 결과 확인
    success_count = results.qsize()
    error_count = errors.qsize()
    
    print(f"성공한 요청: {success_count}개")
    print(f"실패한 요청: {error_count}개")
    
    if error_count == 0:
        print("✅ 모든 동시 요청이 성공했습니다.")
        return True
    else:
        print("❌ 일부 동시 요청이 실패했습니다.")
        return False

def test_performance_benchmark():
    """성능 벤치마크 테스트."""
    print("\n=== 성능 벤치마크 테스트 ===")
    
    # 100회 반복 처리
    iterations = 100
    response_times = []
    
    print(f"{iterations}회 API 호출 시뮬레이션 중...")
    
    for i in range(iterations):
        start_time = time.time()
        
        # API 호출 및 데이터 처리 시뮬레이션
        mock_response = create_mock_food_response()
        time.sleep(0.01)  # 실제 처리 시간 시뮬레이션
        
        response_time = time.time() - start_time
        response_times.append(response_time)
        
        if (i + 1) % 20 == 0:
            print(f"  진행률: {i + 1}/{iterations}")
    
    # 통계 계산
    avg_time = sum(response_times) / len(response_times)
    max_time = max(response_times)
    min_time = min(response_times)
    
    print(f"\n성능 통계:")
    print(f"  평균 응답 시간: {avg_time:.3f}초")
    print(f"  최대 응답 시간: {max_time:.3f}초")
    print(f"  최소 응답 시간: {min_time:.3f}초")
    
    # 성능 기준 검증
    performance_ok = avg_time < 1.0 and max_time < 3.0
    
    if performance_ok:
        print("✅ 성능 기준을 만족합니다.")
    else:
        print("❌ 성능 기준을 만족하지 않습니다.")
    
    return performance_ok

def main():
    """메인 함수."""
    print("=== API 연동 통합 테스트 데모 ===")
    
    test_results = []
    
    try:
        # 1. API 응답 시간 테스트
        result1 = test_api_response_time()
        test_results.append(("API 응답 시간", result1))
        
        # 2. 오류 처리 테스트
        result2 = test_error_handling()
        test_results.append(("오류 처리", result2))
        
        # 3. 데이터 처리 플로우 테스트
        result3 = test_data_processing_flow()
        test_results.append(("데이터 처리 플로우", result3))
        
        # 4. 동시 처리 테스트
        result4 = test_concurrent_processing()
        test_results.append(("동시 처리", result4))
        
        # 5. 성능 벤치마크 테스트
        result5 = test_performance_benchmark()
        test_results.append(("성능 벤치마크", result5))
        
        # 결과 요약
        print("\n=== 테스트 결과 요약 ===")
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ 통과" if result else "❌ 실패"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n전체 결과: {passed}/{total} 테스트 통과")
        
        if passed == total:
            print("🎉 모든 통합 테스트가 성공했습니다!")
        else:
            print("⚠️ 일부 테스트가 실패했습니다.")
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()