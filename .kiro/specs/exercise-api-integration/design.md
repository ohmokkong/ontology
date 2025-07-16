# Design Document

## Overview

이 설계는 한국건강증진개발원의 보건소 모바일 헬스케어 API를 통해 운동 데이터를 가져와서 기존 다이어트 온톨로지 시스템에 통합하는 시스템을 구현합니다. 시스템은 API 연동, 데이터 변환, 온톨로지 확장, 칼로리 계산의 네 가지 주요 컴포넌트로 구성됩니다.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Public API    │    │   API Client     │    │  Data Processor │
│ (Health Korea)  │◄───┤   Component      │◄───┤   Component     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Configuration  │    │  Error Handler   │    │ Ontology Builder│
│   Component     │    │   Component      │    │   Component     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ RDF/Turtle File │
                                               │ (diet-ontology) │
                                               └─────────────────┘
```

## Components and Interfaces

### 1. API Client Component

**책임**: 공공 API와의 통신 및 데이터 가져오기

**주요 메서드**:

- `fetch_met_data()`: API에서 운동 데이터 가져오기
- `validate_api_response(response)`: API 응답 유효성 검사
- `handle_api_errors(error)`: API 오류 처리

**인터페이스**:

```python
class ExerciseAPIClient:
    def __init__(self, api_key: str, base_url: str)
    def fetch_exercise_data(self, page: int = 1, per_page: int = 100) -> List[Dict]
    def validate_response(self, response: requests.Response) -> bool
    def get_total_pages(self) -> int
```

### 2. Data Processor Component

**책임**: API 응답 데이터의 파싱 및 검증

**주요 메서드**:

- `parse_exercise_data(raw_data)`: 원시 데이터 파싱
- `validate_exercise_item(item)`: 개별 운동 데이터 검증
- `normalize_exercise_name(name)`: 운동명 정규화

**인터페이스**:

```python
class ExerciseDataProcessor:
    def parse_api_response(self, response_data: Dict) -> List[ExerciseItem]
    def validate_exercise_item(self, item: Dict) -> bool
    def normalize_data(self, items: List[Dict]) -> List[ExerciseItem]
```

### 3. Ontology Builder Component

**책임**: RDF 그래프 생성 및 온톨로지 확장

**주요 메서드**:

- `build_exercise_graph(exercise_list)`: Exercise 개체들로 RDF 그래프 구성
- `create_exercise_session(exercise, weight, duration)`: ExerciseSession 개체 생성
- `calculate_calories_burned(met, weight, duration)`: 칼로리 소모량 계산
- `integrate_with_existing_ontology()`: 기존 온톨로지와 통합

**인터페이스**:

```python
class OntologyBuilder:
    def __init__(self, namespace: Namespace)
    def build_exercise_graph(self, exercises: List[ExerciseItem]) -> Graph
    def create_exercise_session(self, exercise_uri: URIRef, weight: float, duration: float) -> URIRef
    def calculate_calories(self, met: float, weight: float, duration_minutes: float) -> float
    def merge_with_existing_ontology(self, existing_graph: Graph) -> Graph
```

### 4. Configuration Component

**책임**: 시스템 설정 관리 및 환경 변수 처리

**인터페이스**:

```python
class ConfigurationManager:
    def get_api_key(self) -> str
    def get_api_url(self) -> str
    def validate_configuration(self) -> bool
    def get_output_path(self) -> str
```

## Data Models

### Exercise Data Model

```python
@dataclass
class ExerciseItem:
    name: str           # 운동명
    description: str    # 운동 설명
    met_value: float    # MET 계수
    category: str       # 운동 카테고리 (선택적)

    def to_uri(self, namespace: Namespace) -> URIRef:
        return namespace[self.name.replace(" ", "_").replace("/", "_")]
```

### Exercise Session Model

```python
@dataclass
class ExerciseSession:
    exercise_uri: URIRef    # 수행된 운동
    weight: float          # 체중 (kg)
    duration: float        # 운동 시간 (분)
    calories_burned: float # 소모 칼로리
    timestamp: datetime    # 운동 시간

    def calculate_calories(self, met: float) -> float:
        return met * self.weight * (self.duration / 60.0)
```

### Ontology Schema Extensions

기존 온톨로지에 추가될 클래스와 속성:

```turtle
# 새로운 클래스
:ExerciseSession a owl:Class ;
    rdfs:label "운동 세션"@ko ;
    rdfs:comment "특정 시점에 수행된 운동 활동"@ko .

# 새로운 데이터 속성
:hasMET a owl:DatatypeProperty ;
    rdfs:domain :Exercise ;
    rdfs:range xsd:decimal ;
    rdfs:label "MET 계수"@ko .

:hasWeight a owl:DatatypeProperty ;
    rdfs:domain :ExerciseSession ;
    rdfs:range xsd:decimal ;
    rdfs:label "체중(kg)"@ko .

:caloriesBurned a owl:DatatypeProperty ;
    rdfs:domain :ExerciseSession ;
    rdfs:range xsd:decimal ;
    rdfs:label "소모 칼로리(kcal)"@ko .

# 새로운 객체 속성
:performedExercise a owl:ObjectProperty ;
    rdfs:domain :ExerciseSession ;
    rdfs:range :Exercise ;
    rdfs:label "실행된 운동"@ko .

:hasExerciseSession a owl:ObjectProperty ;
    rdfs:domain :User ;
    rdfs:range :ExerciseSession ;
    rdfs:label "운동 세션 보유"@ko .
```

## Error Handling

### API 연동 오류 처리

- **연결 오류**: 재시도 로직 (최대 3회, 지수 백오프)
- **인증 오류**: 명확한 API 키 설정 안내
- **응답 파싱 오류**: 개별 항목 스킵 후 계속 진행
- **타임아웃**: 설정 가능한 타임아웃 값 (기본 10초)

### 데이터 검증 오류 처리

- **필수 필드 누락**: 해당 항목 스킵 및 로깅
- **잘못된 MET 값**: 기본값 적용 또는 스킵
- **중복 데이터**: 최신 데이터로 업데이트

### 파일 시스템 오류 처리

- **권한 오류**: 명확한 권한 설정 안내
- **디스크 공간 부족**: 사전 공간 확인
- **파일 잠금**: 임시 파일 사용 후 원자적 이동

## Testing Strategy

### Unit Tests

- API 클라이언트 모킹을 통한 데이터 가져오기 테스트
- 데이터 프로세서의 파싱 및 검증 로직 테스트
- 온톨로지 빌더의 RDF 그래프 생성 테스트
- 칼로리 계산 공식 정확성 테스트

### Integration Tests

- 실제 API와의 연동 테스트 (테스트 키 사용)
- 기존 온톨로지와의 통합 테스트
- 전체 파이프라인 테스트 (API → 처리 → 저장)

### Performance Tests

- 대량 데이터 처리 성능 테스트
- 메모리 사용량 모니터링
- API 호출 최적화 테스트

### Error Scenario Tests

- 네트워크 오류 시나리오
- 잘못된 API 응답 처리
- 파일 시스템 오류 처리
- 부분적 데이터 손실 시나리오

## Security Considerations

- API 키는 환경 변수로만 관리
- API 응답 데이터 검증 및 새니타이징
- 파일 경로 검증 (디렉토리 트래버설 방지)
- 로깅 시 민감 정보 마스킹

## Performance Optimization

- API 호출 배치 처리 (페이지네이션 활용)
- RDF 그래프 메모리 효율적 구성
- 중복 데이터 제거 최적화
- 파일 I/O 최소화 (메모리 버퍼링)
