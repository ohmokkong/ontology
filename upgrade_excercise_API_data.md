# 운동(MET) API 연동 및 온톨로지 확장 가이드

본 문서는 ‘보건소 모바일 헬스케어’ OpenAPI의 **운동 목록 및 MET 계수** 정보를 가져와, RDF/Turtle 형식으로 변환 후 음식 섭취 데이터와 통합하는 온톨로지 확장 과정을 안내합니다.

---

## 1. 데이터 출처

- **한국건강증진개발원_보건소 모바일 헬스케어 운동 데이터**  
  - 제공 내용: 운동명, 운동 설명, 단위체중당 에너지 소비량(METs) :contentReference[oaicite:1]{index=1}  
  - 제공 방식: JSON/XML OpenAPI 및 CSV 파일  

---

## 2. 온톨로지 모델 설계

```turtle
:Exercise a owl:Class ;
    rdfs:label "운동 항목"@ko .

:hasMET a owl:DatatypeProperty ;
    rdfs:domain :Exercise ;
    rdfs:range xsd:decimal ;
    rdfs:label "MET 계수"@ko .

:ExerciseSession a owl:Class ;
    rdfs:label "운동 세션"@ko .

:performedExercise a owl:ObjectProperty ;
    rdfs:domain :ExerciseSession ;
    rdfs:range :Exercise ;
    rdfs:label "실행된 운동"@ko .

:hasWeight a owl:DatatypeProperty ;
    rdfs:domain :ExerciseSession ;
    rdfs:range xsd:decimal ;
    rdfs:label "체중(kg)"@ko .

:hasDuration a owl:DatatypeProperty ;
    rdfs:domain :ExerciseSession ;
    rdfs:range xsd:decimal ;
    rdfs:label "운동 시간(분)"@ko .

:caloriesBurned a owl:DatatypeProperty ;
    rdfs:domain :ExerciseSession ;
    rdfs:range xsd:decimal ;
    rdfs:label "소모 칼로리(kcal)"@ko .
※ caloriesBurned = MET × 체중(kg) × (시간(h)) 계산 공식 적용

3. 연동 및 변환 절차
API 신청 및 키 확보: 공공데이터포털에서 ‘보건소 모바일 헬스케어 운동’ OpenAPI 신청 후 키 발급

JSON 형식 데이터 호출: 운동 목록, MET 정보 요청

rdflib 기반 처리: Exercise 개체 생성 및 MET 지정

운동 세션 계산 기능 추가: 활동 시나리오 입력 시 ExerciseSession·caloriesBurned 계산

음식 섭취 온톨로지와 통합: Food, ExerciseSession 연결하여 netCalories 등 값 연산