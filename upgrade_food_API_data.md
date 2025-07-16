# 식품영양성분DB 연동 및 온톨로지 확장 가이드

이 문서는 식약처의 "식품영양성분 데이터베이스" Open API를 활용하여 실시간으로 데이터를 가져오고, 이를 RDF/Turtle 형식의 온톨로지로 변환하는 `upgrade_ontology.py` 스크립트의 사용법과 결과물 활용 방법을 안내합니다.

---

## 1. 개요

- **목표**: 사용자가 입력한 음식 이름에 대해 식약처 Open API를 호출하여 영양 정보를 가져오고, 이를 `TTL` 형식으로 변환
- **적용 대상**: 기존 `diet-ontology.ttl` 온톨로지에 통합 가능한 식품 영양 정보

---

## 2. 사전 준비

### 2.1 공공데이터포털 회원가입 및 API 키 발급

1. [공공데이터포털](https://www.data.go.kr) 접속 및 로그인
2. "식품의약품안전처\_식품영양성분 데이터베이스" 검색
3. 활용 신청 후 **일반 인증키 (Decoding Key)** 발급
4. 발급된 API 키를 복사해둡니다

---

## 3. 관련 파일 및 기능

### 3.1 관련 파일 목록

- `upgrade_ontology.py`: 식약처 API 연동 및 TTL 파일 자동 생성 스크립트
- `diet-ontology.ttl`: 기존 온톨로지 스키마 파일

### 3.2 새롭게 정의해야 할 데이터 속성

```turtle
:hasCarbohydrate a owl:DatatypeProperty ;
    rdfs:domain :Food ;
    rdfs:range xsd:decimal ;
    rdfs:label "탄수화물(g)"@ko .

:hasProtein a owl:DatatypeProperty ;
    rdfs:domain :Food ;
    rdfs:range xsd:decimal ;
    rdfs:label "단백질(g)"@ko .

:hasFat a owl:DatatypeProperty ;
    rdfs:domain :Food ;
    rdfs:range xsd:decimal ;
    rdfs:label "지방(g)"@ko .
```

---

## 4. 실행 방법

### 4.1 필수 라이브러리 설치

```bash
pip install requests rdflib
```

### 4.2 API 키 환경 변수 설정 (권장)

```bash
# Windows
set MFDS_API_KEY=여러분의_인증키

# macOS / Linux
export MFDS_API_KEY=여러분의_인증키
```

> 또는 `upgrade_ontology.py` 상단의 `API_KEY = "YOUR_API_KEY_HERE"`를 직접 수정할 수 있음

---

## 5. 스크립트 실행

```bash
python upgrade_ontology.py
```

실행하면 음식명을 물어보는 프롬프트가 표시됩니다.

예시 입력:

```
영양 정보를 검색할 음식 이름을 입력하세요 (예: 바나나): 바나나
```

### 결과:

- `new_바나나_data.ttl` 형태의 파일이 생성됨
- 여러 식품 항목(예: 바나나, 생것 / 바나나, 찐 것 등)의 영양 정보 포함

---

## 6. TTL 결과 예시

```turtle
@prefix : <http://example.org/diet#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:A00300400100101 a :Food ;
    rdfs:label "바나나,생것"@ko ;
    :hasCalorie "93.0"^^xsd:decimal ;
    :hasCarbohydrate "24.1"^^xsd:decimal ;
    :hasFat "0.2"^^xsd:decimal ;
    :hasProtein "1.2"^^xsd:decimal .
```

---

## 7. 온톨로지 통합 방법

### 7.1 수동 통합

- `new_*.ttl` 파일을 열고 기존 `diet-ontology.ttl` 파일에 복사 및 병합

### 7.2 owl\:imports 사용

- 기존 온톨로지 파일에 다음과 같이 참조 추가

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .

<http://example.org/diet#> a owl:Ontology ;
    owl:imports <file://./new_바나나_data.ttl> .
```

> 이 방법은 RDF 툴 또는 triple store에서 import 기능을 지원할 경우 활용

---

## 8. 향후 확장 방향

- 검색 결과 자동 병합 및 온톨로지 업데이트 기능 추가
- 음식-식사시간, 음식-식단 관계 확장
- SPARQL 기반 질의 기능 탑재
- GUI 또는 웹 서비스 연동

---

문의: 시스템 관리자 또는 기술 문서 담당자에게 연락 바랍니다.
