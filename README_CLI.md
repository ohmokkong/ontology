# 영양 관리 CLI 사용 가이드

## 🎯 개요

영양 관리 CLI는 음식/운동 검색, 칼로리 계산, 온톨로지 관리를 위한 명령줄 도구입니다.

## 🚀 빠른 시작

### 설치 및 실행

```bash
# CLI 실행 (도움말)
python cli_interface.py --help

# 대화형 모드 시작
python cli_interface.py interactive

# 또는 전용 스크립트 사용
python nutrition-cli.py
```

### 기본 사용법

```bash
# 음식 검색
python cli_interface.py search food "닭가슴살"

# 운동 검색
python cli_interface.py search exercise "달리기"

# 음식 추가
python cli_interface.py calorie add-food "밥" 150

# 운동 추가
python cli_interface.py calorie add-exercise "달리기" 30

# 칼로리 계산
python cli_interface.py calorie calculate
```

## 📋 주요 명령어

### 🔍 검색 명령어

#### 음식 검색

```bash
# 기본 검색
python cli_interface.py search food "닭가슴살"

# 상세 정보 포함
python cli_interface.py search food "닭가슴살" --detailed

# 결과 개수 제한
python cli_interface.py search food "닭가슴살" --limit 5

# JSON 형태 출력
python cli_interface.py search food "닭가슴살" --json
```

#### 운동 검색

```bash
# 기본 검색
python cli_interface.py search exercise "달리기"

# 상세 정보 포함
python cli_interface.py search exercise "달리기" --detailed
```

#### 통합 검색

```bash
# 음식과 운동 모두 검색
python cli_interface.py search all "운동"
```

### 📊 칼로리 관리

#### 음식 추가

```bash
# 기본 추가
python cli_interface.py calorie add-food "닭가슴살" 150

# 시간 지정
python cli_interface.py calorie add-food "아침식사" 200 --time "08:00"
```

#### 운동 추가

```bash
# 기본 추가
python cli_interface.py calorie add-exercise "달리기" 30

# 체중 지정
python cli_interface.py calorie add-exercise "달리기" 30 --weight 65

# 시간 지정
python cli_interface.py calorie add-exercise "저녁운동" 45 --time "19:00"
```

#### 칼로리 계산 및 분석

```bash
# 일일 칼로리 계산
python cli_interface.py calorie calculate

# 현재 세션 표시
python cli_interface.py calorie show

# 세션 초기화
python cli_interface.py calorie clear

# 목표 칼로리 설정
python cli_interface.py calorie set-goal 2000
```

### 🔧 온톨로지 관리

```bash
# 온톨로지 상태 확인
python cli_interface.py ontology status

# 온톨로지 통계
python cli_interface.py ontology stats

# 온톨로지 백업
python cli_interface.py ontology backup --output-dir backups

# 온톨로지 검증
python cli_interface.py ontology validate diet-ontology.ttl
```

### ⚙️ 설정 관리

```bash
# 현재 설정 표시
python cli_interface.py config show

# 설정 값 변경
python cli_interface.py config set cache_ttl 7200

# API 키 설정
python cli_interface.py config set-api-key food "your-api-key"
python cli_interface.py config set-api-key exercise "your-api-key"

# 설정 초기화
python cli_interface.py config reset
```

### 🗄️ 캐시 관리

```bash
# 캐시 통계
python cli_interface.py cache stats

# 캐시 초기화
python cli_interface.py cache clear
```

## 💬 대화형 모드

대화형 모드는 CLI를 더 편리하게 사용할 수 있는 방법입니다.

### 시작하기

```bash
python cli_interface.py interactive
```

### 대화형 명령어

```
🎯 대화형 모드 명령어:

🔍 검색:
  search food <음식명>     - 음식 검색
  search exercise <운동명> - 운동 검색

📊 칼로리 관리:
  add food <음식명> <양(g)>        - 음식 추가
  add exercise <운동명> <시간(분)> - 운동 추가
  calculate                        - 칼로리 계산
  show                            - 현재 세션 표시
  clear                           - 세션 초기화

🔧 온톨로지:
  ontology status    - 온톨로지 상태
  ontology stats     - 온톨로지 통계

⚙️ 유틸리티:
  cache stats        - 캐시 통계
  config show        - 설정 표시
  help              - 도움말
  exit              - 종료
```

### 사용 예시

```
> add food 닭가슴살 150
✅ 음식 추가됨: 닭가슴살 150.0g (12:30)

> add exercise 달리기 30
✅ 운동 추가됨: 달리기 30.0분 (12:45)

> calculate
📊 일일 칼로리 계산 결과
========================================
섭취 칼로리: 300 kcal
소모 칼로리: 210 kcal
순 칼로리: 90 kcal
💡 90 kcal 초과 섭취

> show
📅 현재 세션 (2025-07-22)
========================================
🍽️ 섭취 음식:
  1. 닭가슴살 - 150.0g (12:30) - 300 kcal

🏃 운동:
  1. 달리기 - 30.0분 (12:45) - 210 kcal 소모
```

## 🎨 출력 형태

### 기본 출력

- 이모지를 활용한 시각적 표시
- 색상 구분 (성공: 녹색, 오류: 빨간색, 경고: 노란색)
- 구조화된 정보 표시

### JSON 출력

```bash
python cli_interface.py search food "닭가슴살" --json
```

```json
[
  {
    "name": "닭가슴살",
    "calories": 165,
    "protein": 31,
    "carbohydrate": 0,
    "fat": 3.6
  }
]
```

## ⚠️ 오류 처리

CLI는 다양한 오류 상황을 감지하고 도움말을 제공합니다:

### 일반적인 오류들

1. **잘못된 명령어**

   ```
   ❌ 알 수 없는 명령어: invalid command
   'help'를 입력하여 사용법을 확인하세요.
   ```

2. **잘못된 숫자 형식**

   ```
   ❌ 양은 숫자로 입력해주세요.
   ```

3. **잘못된 시간 형식**
   ```
   ⚠️ 잘못된 시간 형식: 25:70 (HH:MM 형식으로 입력하세요)
   ```

## 🔧 고급 사용법

### 배치 처리

여러 명령어를 스크립트로 실행:

```bash
#!/bin/bash
python cli_interface.py calorie add-food "아침식사" 300 --time "08:00"
python cli_interface.py calorie add-food "점심식사" 500 --time "12:00"
python cli_interface.py calorie add-exercise "달리기" 30 --time "07:00"
python cli_interface.py calorie calculate
```

### 설정 파일 사용

```bash
python cli_interface.py --config-file my-config.json search food "닭가슴살"
```

### 상세 로그 출력

```bash
python cli_interface.py --verbose search food "닭가슴살"
```

## 🐛 문제 해결

### 자주 발생하는 문제들

1. **모듈 import 오류**

   - 필요한 Python 패키지가 설치되어 있는지 확인
   - `pip install -r requirements.txt`

2. **API 연결 오류**

   - API 키가 올바르게 설정되어 있는지 확인
   - `python cli_interface.py config show`

3. **파일 권한 오류**
   - 온톨로지 파일에 대한 읽기/쓰기 권한 확인

### 도움말 얻기

```bash
# 전체 도움말
python cli_interface.py --help

# 특정 명령어 도움말
python cli_interface.py search --help
python cli_interface.py calorie --help

# 대화형 모드에서 도움말
> help
```

## 📞 지원

문제가 발생하거나 기능 요청이 있으시면:

1. CLI 내장 도움말 시스템 활용
2. 오류 메시지의 제안사항 확인
3. 상세 로그 옵션(`--verbose`) 사용

---

**영양 관리 CLI**로 건강한 식단과 운동을 체계적으로 관리하세요! 🎯
