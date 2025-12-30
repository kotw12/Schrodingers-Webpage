# 🕵️ 슈뢰딩거의 웹페이지: LLM 기반 동적 웹 허니팟

> *"공격자가 공격할 때만 취약점이 드러나는 웹사이트"*

**슈뢰딩거의 웹페이지**는 대규모 언어 모델(LLM)을 활용하여 실시간으로 가짜 취약점을 생성하는 기만 기반(Deception-based) 웹 허니팟입니다. 정적인 응답만 제공하는 기존 허니팟과 달리, 본 시스템은 공격자의 행동에 동적으로 적응하며, 정상 사용자에게는 일반적인 로그인 실패 페이지를 보여주고, 공격자에게는 데이터베이스가 노출된 듯한 에러메시지, 가짜 데이터베이스를 제공합니다.

---

## 🎯 프로젝트 개요

### 취지
llm 모델을 보안의 영역에서 기만 전술에 사용해보자는 취지입니다.

### 기능
본 프로젝트는 **OpenAI GPT-4o**를 활용하여:
- **문맥에 맞는 가짜 응답 생성** (MySQL 에러, 데이터베이스 덤프)
- **사전 정의된 가짜 스키마**를 통한 여러 탐색 시도 간 **일관성 유지**
- **패턴 기반 입력 분석**을 통한 공격자와 정상 사용자 구분
- IP, 타임스탬프, 페이로드, 응답 유형을 포함한 **공격 시도 로깅**

### 주목 포인트
LLM을 전통적인 방어나 공격 특화가 아닌 기만으로 사용했습니다. 
본 프로젝트는 AI를 **능동적 기만(Active Deception)**에 활용해 보았습니다. 공격자가 취약점 공격에 성공했다고 믿게 만들면서 시간을 낭비시키고 공격 전술을 드러내게 합니다.

---

## 🏗️ 시스템 아키텍처
![workflow](/Schrödinger's%20Webpage/img/flow.png)

전체 워크플로우는 입력값에서 공격 패턴을 먼저 탐지하고, 공격이 감지되면 `UNION SELECT` 여부에 따라 분기하여 **가짜 데이터베이스 덤프** 또는 **가짜 MySQL 에러**를 AI로 생성한 뒤, 모든 이벤트를 로깅하여 관제실에 표시합니다. [chart:167]

**메인 흐름**  
사용자 입력
  
입력 패턴 분석기 (', --, UNION, SELECT 등 탐지)
  
[정상 입력] → 표준 로그인 실패 페이지  
[공격 감지] → LLM 결정 계층 (GPT-4o)  
  
[UNION SELECT] → 가짜 DB 덤프 (관리자 계정 포함)  
[기타 SQLi] → 가짜 MySQL 에러 메시지  
  
공격 로거 (메모리 내 저장)
  
대시보드 (/dashboard)에 실시간 표시 

---

## 🚀 기능구현

### 1. 적응형 SQL 인젝션 응답
- **UNION SELECT 공격** → 관리자 계정이 포함된 가짜 사용자 테이블 반환 (MD5 해시)
- **구문 오류** → 가짜 파일 경로를 포함한 실제와 유사한 MySQL 5.7 에러 메시지 생성
- **정상 입력** → 표준 "로그인 실패" 페이지 (허니팟 노출 없음)

### 2. 일관성 엔진
시스템은 LLM 프롬프트에 주입된 **고정된 가짜 데이터베이스 스키마**를 사용합니다:  
테이블: users  
컬럼: id, username, password_hash (MD5), email, last_login  
고정 데이터:  
1 | admin | 5f4dcc3b5aa765d61d8327deb882cf99 | admin@stone-security.com  
2 | guest | 084e0343a0486ff05530df6c705c8bb4 | guest@stone-security.com  
3 | tester | 098f6bcd4621d373cade4e832627b4f6 | test@dev-team.net  

이를 통해 공격자는 **세션 간 동일한 데이터**를 보게 되어 허니팟 탐지가 힘들어집니다.

### 3. 실시간 공격 대시보드
- **위치**: `/dashboard?key=1q2w3e4r!`
- **기능**:
  - 5초마다 자동 새로고침되는 공격 실시간 피드
  - 공격자 IP, 타임스탬프, 공격 유형, 페이로드 일부 표시
  - 현재 데모이기 때문에 허술함

### 4. 패턴 기반 탐지
간단하지만 효과적인 룰 기반 필터:
danger_chars = ["'", '"', "--", "#", ";", "/*", "union", "select", "sleep(", "benchmark("]

향후 버전에서는 ML 기반 이상 탐지나, 다른 탐지기술 적용도 생각해 볼 수 있습니다.
현재는 분기를 위해 필터링 사용

---

## 📦 설치 및 실행

### 사전 요구사항
- Python 3.8 이상
- OpenAI API 키

### 빠른 시작
저장소 클론
git clone https://github.com/YOUR_USERNAME/schrodingers-webpage-honeypot.git  
cd schrodingers-webpage-honeypot

라이브러리 설치
pip install fastapi uvicorn openai python-multipart

main.py에서 OpenAI API 키 설정  
12번째 줄: client = openai.OpenAI(api_key="YOUR_API_KEY_HERE")

서버 실행
python main.py


접속 주소:
- **허니팟**: `http://localhost:8000`
- **관제실**: `http://localhost:8000/dashboard?key=1q2w3e4r!`

---

## 🔮 향후 로드맵

### Phase 1: 다중 공격 벡터 지원
- 다양한 웹서버를 대상으로 한 공격 범위 강화

### Phase 2: 인텔리전스 강화
- 룰 기반 탐지를 ML 기반 탐지로 강화
- 세션 추적: 동일 공격자의 여러 요청 상관관계 분석

---

## 데모 스크린샷
![공격1](/Schrödinger's%20Webpage/img/attack1.png)
![공격2](/Schrödinger's%20Webpage/img/attack2.png)
![에러1](/Schrödinger's%20Webpage/img/error1.png)
![에러2](/Schrödinger's%20Webpage/img/error2.png)
![로그](/Schrödinger's%20Webpage/img/log.png)