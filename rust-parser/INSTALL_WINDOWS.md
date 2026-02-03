# Windows에서 Rust 파서 설치 가이드

## 1단계: Rust 설치

### 방법 1: rustup-init.exe 사용 (가장 간단)

1. 브라우저에서 https://rustup.rs/ 접속
2. "RUSTUP-INIT.EXE (64-BIT)" 다운로드
3. 다운로드한 `rustup-init.exe` 실행
4. 기본 설정으로 설치 진행 (Enter 키 누르기)
5. PowerShell 재시작

### 방법 2: PowerShell에서 직접 다운로드

```powershell
# rustup-init.exe 다운로드
Invoke-WebRequest -Uri https://win.rustup.rs/x86_64 -OutFile rustup-init.exe

# 실행
.\rustup-init.exe

# 기본 설정으로 설치 (Enter 키)
```

### 설치 확인

PowerShell을 재시작한 후:

```powershell
rustc --version
cargo --version
```

## 2단계: Visual Studio Build Tools 설치

Rust는 C++ 컴파일러가 필요합니다.

### 방법 1: Visual Studio Build Tools 설치

1. https://visualstudio.microsoft.com/downloads/ 접속
2. "Build Tools for Visual Studio" 다운로드
3. 설치 시 "Desktop development with C++" 워크로드 선택

### 방법 2: Visual Studio Community 설치

1. https://visualstudio.microsoft.com/vs/community/ 다운로드
2. 설치 시 "Desktop development with C++" 워크로드 선택

## 3단계: Maturin 설치

```powershell
pip install maturin
```

## 4단계: Rust 파서 빌드

```powershell
# 프로젝트 루트에서
cd rust-parser

# 개발 모드로 빌드 및 설치 (권장)
maturin develop --release

# 또는 wheel 파일로 빌드
maturin build --release
pip install target/wheels/logcat_parser_rs-*.whl
```

## 문제 해결

### "link.exe not found" 오류

Visual Studio Build Tools가 설치되지 않았거나 PATH에 없습니다.
- Visual Studio Installer에서 "Desktop development with C++" 확인
- PowerShell 재시작

### "maturin not found" 오류

```powershell
pip install --upgrade maturin
```

### Rust 버전 확인

```powershell
rustc --version  # 1.70 이상 권장
```

## 설치 완료 확인

Python에서 테스트:

```python
from logcat_parser_rs import parse_log_line
result = parse_log_line("01-25 12:34:56.789  1234  5678  E  Tag: Message")
print(result)  # {'timestamp': '01-25 12:34:56.789', ...}
```

성공하면 Rust 파서가 자동으로 사용됩니다!
