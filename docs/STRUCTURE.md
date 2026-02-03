# Logcat AI 프로젝트 폴더 구조

```text
logcatAI/
├── src/                        # 소스 코드 메인 디렉토리
│   ├── main.py                 # 애플리케이션 진입점 (PyQt6 실행)
│   ├── core/                   # 핵심 로직 (로그 처리)
│   │   ├── collector.py        # ADB/파일 로그 수집기
│   │   ├── parser.py           # 로그 파싱 및 구조화 (Regex 기반)
│   │   ├── detector.py         # 에러 및 비정상 패턴 감지기
│   │   ├── monitor/            # 확장형 모니터링 프레임워크
│   │   │   ├── base.py         # 모니터 플러그인 추상 클래스
│   │   │   ├── cpu_mem.py      # 기본 리소스 모니터
│   │   │   ├── vhal.py         # VHAL 속성 추적 모니터
│   │   │   └── custom_shell.py # 사용자 정의 ADB 명령 모니터
│   │   └── buffer.py           # 슬라이딩 윈도우 컨텍스트 버퍼 관리
│   ├── agent/                  # AI 및 OpenCode 연동
│   │   ├── opencode_client.py  # OpenCode SDK/CLI 래퍼
│   │   └── analyzer.py         # 이슈 설명 기반 분석 및 프롬프트 관리
│   ├── ui/                     # GUI 컴포넌트 (PyQt6)
│   │   ├── main_window.py      # 메인 윈도우 레이아웃 및 컨트롤러
│   │   ├── log_table/           # 로그 테이블 모듈
│   │   │   ├── __init__.py     # 모듈 초기화 (LogTable, FilterDialog export)
│   │   │   ├── log_table.py    # 메인 로그 테이블 위젯
│   │   │   ├── threads.py      # 백그라운드 스레드 (LogcatThread, FileLoadThread, FilterApplyThread)
│   │   │   └── filter_dialog.py # 필터 설정 다이얼로그
│   │   ├── dashboard/          # 확장형 대시보드 UI
│   │   │   ├── container.py    # 위젯들을 담는 그리드 컨테이너
│   │   │   ├── widgets.py      # 다양한 차트 및 텍스트 위젯 템플릿
│   │   │   └── config_dialog.py# 모니터링 항목 설정 다이얼로그
│   │   ├── analysis_panel.py   # AI 분석 및 Diff 결과 사이드 패널
│   │   ├── chat_widget.py      # 대화형 채팅 위젯
│   │   └── components/         # 기타 재사용 가능한 UI 요소 (버튼, 입력창 등)
│   └── utils/                  # 유틸리티 및 공통 기능
│       ├── config.py           # .env 및 설정 값 관리
│       ├── adb_helper.py       # ADB 명령 실행 보조 도구
│       ├── git_helper.py       # Git Clone 및 Branch 관리 도구
│       └── logger.py           # 내부 디버깅용 로거
├── workspace/                  # 클론된 프로젝트들이 저장되는 로컬 작업 공간 (Gitignore 대상)
├── assets/                     # 이미지, 아이콘, QSS 스타일시트
│   └── styles/                 # 테마 및 스타일 관련 파일
├── docs/                       # 설계 문서 및 매뉴얼
│   ├── DESIGN.md               # 전반적인 설계 및 시나리오
│   ├── STRUCTURE.md            # 폴더 구조 및 모듈 설명
│   └── UI_DESIGN.md            # GUI 레이아웃 및 UX 설계
├── tests/                      # 단위 테스트 및 통합 테스트
├── .env                        # 환경 변수 (OpenCode API 키 등)
├── .gitignore                  # Git 관리 제외 목록
├── requirements.txt            # 의존성 패키지 목록
└── README.md                   # 프로젝트 개요 및 빠른 시작 가이드
```

## 모듈별 상세 설명

### 1. `src/core/`
*   **Collector**: `subprocess`를 통해 `adb logcat` 스트림을 실시간으로 읽어옵니다.
*   **Buffer**: AI 분석 시 맥락을 파악할 수 있도록 최신 로그 1,000줄을 메모리에 상시 보관합니다.

### 2. `src/agent/`
*   **OpenCode Client**: 사용자의 이슈 설명과 수집된 로그를 OpenCode 에이전트에 전달하고 분석 결과를 받아옵니다.
*   **Analyzer**: AI에게 보낼 최적의 데이터(로그 요약, 이슈 맥락 등)를 구성합니다.

### 3. `src/ui/`
*   **Main Thread**: 로그를 실시간으로 테이블에 뿌려주는 역할을 하며, UI가 멈추지 않도록 무거운 작업(ADB 수집, AI 분석)은 별도의 Worker Thread로 분리합니다.

### 4. `src/utils/`
*   **Config**: API 키 관리나 로컬 저장소 경로 등을 처리합니다.
