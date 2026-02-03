# Logcat AI 설계 문서 (Refined)

## 1. 개요
Logcat AI는 Android Automotive OS(AAOS) 및 일반 Android 기기에서 발생하는 방대한 Logcat 데이터를 AI(LLM)가 실시간으로 분석하여, 오류의 근본 원인을 파악하고 즉각적인 해결책을 제시하는 개발 보조 도구입니다. 특히 차량용 환경(AAOS)의 복잡한 서비스 간 상호작용과 로그 맥락을 이해하는 데 최적화되어 있습니다.

## 2. 핵심 기능 상세

### 2.1. 로그 수집 및 파싱 (Collector & Parser)
- **수집 모드**: 
    - `Stream Mode`: 실시간 `adb logcat` 수신.
    - `File Mode`: `.txt` 또는 `.log` 파일 로드.
- **지능형 다중 디스플레이 분류 (Auto Display Tagging)**:
    - **자동 분석**: 로그 내의 `displayId`, `ActivityRecord`, `WindowOrientationListener` 등의 패턴을 분석하여 로그별 Display ID(0: Main, 1: Cluster 등)를 자동으로 매핑.
    - **가상 태그 부여**: 원본 로그에 없는 `[Cluster]`, `[IVI]`, `[Passenger]` 등의 가상 태그를 내부적으로 부여하여 필터링 및 시각화 지원.
- **파싱**: 텍스트 로그를 구조화된 데이터(JSON)로 변환 (`Timestamp`, `LogLevel`, `Tag`, `Message`, `DisplayID`).
- **AAOS 특화 필터링**: 
    - `Vehicle HAL (VHAL)`, `CarService` 등 AAOS 주요 서비스 로그 가중치 부여.
- **필터링**: 불필요한 시스템 로그 제외 및 사용자 정의 필터링.

### 2.2. AI 분석 엔진 (AI Analyzer & Agent)
- **핵심 입력 데이터**:
    - **이슈 설명 (Issue Description)**: 사용자가 현재 추적 중인 버그나 증상을 입력 (예: "결제 버튼 클릭 시 앱이 멈춤").
    - **로그 데이터**: 실시간/파일 로그 컨텍스트.
    - **소스 코드**: OpenCode를 통해 접근한 프로젝트 코드.
- **트리거 조건**: 
    - **자동 트리거**: `Error` 또는 `Fatal` 레벨의 로그 감지 시 즉시 분석.
    - **수동 트리거**: 사용자가 특정 로그 범위를 선택하여 "이 이슈 설명에 따라 분석" 요청.
    - **패턴 트리거**: 특정 태그의 빈도 급증, ANR 등 비정상 패턴 감지.
- **컨텍스트 추출 (Context Buffer)**: 
    - 로컬 메모리에 상시 슬라이딩 윈도우 유지.
    - **이슈 설명 기반 필터링**: 사용자의 이슈 설명과 연관된 키워드가 포함된 로그를 우선적으로 추출하여 OpenCode에 전달.

### 2.3. 사용자 인터페이스 (GUI Interface)
- **프로젝트 및 디바이스 설정 바 (Top Bar)**:
    - **Project Loader**: Git URL 입력 및 브랜치 선택 드롭다운 제공.
    - **Load Status Indicator**: 프로젝트 클론 및 인덱싱 상태를 애니메이션과 함께 표시 (Cloning -> Indexing -> Ready).
    - **Current Context**: 현재 로드된 프로젝트명/브랜치명 및 연결된 디바이스 정보 상시 노출.
- **확장형 AAOS 모니터링 대시보드 (Extensible Dashboard)**:
    - **위젯 기반 레이아웃**: 사용자가 필요한 정보(CPU, VHAL, Log 등)를 선택하여 배치할 수 있는 커스터마이징 UI.
    - **커스텀 VHAL 모니터링**: 사용자가 특정 Property ID를 입력하여 실시간으로 값을 추적하고 그래프로 표시.
    - **동적 ADB 스크립트 위젯**: 사용자가 정의한 ADB Shell 명령어(`dumpsys`, `top` 등)의 결과값을 주기적으로 파싱하여 표시하는 범용 위젯 제공.
    - **다중 디스플레이 스위처**: 각 디스플레이별 상태를 독립적으로 모니터링 가능.
- **메인 로그 뷰**: 
    - 실시간 로그 테이블 및 레벨별 색상 강조.
    - 이슈 설명과 관련된 로그 라인에 별도의 하이라이트 표시 가능.
- **OpenCode 분석 패널 (Side Panel)**:
    - 사용자의 이슈 설명을 바탕으로 도출된 분석 결과 및 코드 수정 제안 출력.
- **디바이스 관리**:
    - 연결된 ADB 디바이스 목록 표시 및 선택.
    - 연결 상태 실시간 모니터링 (Connected/Disconnected).
- **대화형 채팅 창**:
    - 분석 결과 하단에 AI와 바로 대화할 수 있는 입력창 제공.

## 3. 기술 스택
- **언어**: Python 3.10+
- **GUI 프레임워크**: PyQt6 (강력한 기능 및 레이아웃 제어)
- **AI/Agent Framework**: **OpenCode** (모든 LLM 추론 및 에이전트 작업의 단일 인터페이스)
- **주요 라이브러리**:
    - `PyQt6`: 메인 GUI 구현.
    - `qdarktheme` / `qt-material`: 현대적이고 세련된 테마 적용.
    - `subprocess`: ADB 명령 실행 및 스트림 수신.
    - `OpenCode SDK/CLI`: LLM 연동 및 코드 분석 에이전트 활용.
    - `pydantic`: 데이터 모델링.
    - `python-dotenv`: 설정 관리.

## 4. 데이터 흐름 (Data Flow)
1. **[User Input]** -> 해결하고자 하는 **이슈 설명** 입력.
2. **[ADB/File Stream]** -> 실시간 로그 수신 및 **UI 즉시 업데이트 (Main Thread)**.
3. **[Parser/Buffer]** -> 로그 구조화 및 최근 1,000줄 메모리 버퍼링.
4. **[Event Detector]** -> 에러/패턴 감지 시 분석 이벤트 발행.
5. **[Async OpenCode Agent]** -> **백그라운드 스레드**에서 분석 수행. 로그 출력에 영향을 주지 않음.
6. **[UI Streaming]** -> AI 답변을 토큰 단위로 분석 패널에 실시간 렌더링.

## 5. 상세 설계 고려 사항
- **비동기 처리 (Concurrency)**: 로그 수집/출력 스레드와 AI 분석 스레드를 완전히 분리하여 UI 프리징 방지.
- **리소스 모니터링 오버헤드**: 디바이스 상태 측정을 위한 ADB 명령(`top`, `dumpsys` 등)이 로그 수집 성능에 영향을 주지 않도록 별도 주기(예: 1~2초)로 실행.
- **분석 효율화 (Throttling)**: 
    - 짧은 시간 내 중복 에러 발생 시 분석 요청 제한(Debounce).
    - 로컬에서 1차 필터링을 거친 후 '의미 있는 컨텍스트'만 선별 전송.
- **API 비용 및 Latency**: 실시간 스트리밍 중에도 사용자가 분석을 중단하거나 새 분석을 요청할 수 있는 인터럽트 구조.

## 6. 향후 확장 계획
- **IDE Plugin**: Android Studio 또는 VS Code 플러그인으로 확장.
- **Local LLM 지원**: Ollama 등을 활용하여 보안이 중요한 프로젝트를 위해 로컬 분석 지원.
- **Custom Knowledge Base**: 프로젝트별 특정 라이브러리 문서를 AI에게 학습/참조시켜 정확도 향상.
