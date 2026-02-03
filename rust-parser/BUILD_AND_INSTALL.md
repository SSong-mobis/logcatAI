# Rust 파서 빌드 및 설치 가이드

## 빠른 설치 (권장)

### Windows (PowerShell)

```powershell
# 1. rust-parser 디렉토리로 이동
cd rust-parser

# 2. 빌드 (release 모드)
python -m maturin build --release

# 3. 빌드된 wheel 파일 찾기
# target/wheels/logcat_parser_rs-*.whl 파일이 생성됩니다

# 4. 설치 (PowerShell에서는 와일드카드 대신 전체 파일명 사용)
python -m pip install target\wheels\logcat_parser_rs-0.1.0-cp38-abi3-win_amd64.whl --force-reinstall

# 또는 Get-ChildItem으로 파일 찾기
python -m pip install (Get-ChildItem target\wheels\logcat_parser_rs-*.whl).FullName --force-reinstall
```

### 가상환경이 있는 경우

```powershell
# 가상환경 활성화 후
python -m maturin develop --release
```

## 문제 해결

### 한글 경로 문제
한글 경로 때문에 `pip install`이 실패하는 경우:
1. wheel 파일을 영문 경로로 복사
2. 또는 `maturin develop` 사용 (가상환경 필요)

### 설치 확인

```python
python -c "from logcat_parser_rs import parse_log_file_chunk, count_file_lines; print('✅ 설치 완료')"
```

성공하면 "✅ 설치 완료"가 출력됩니다.

## 새 기능 확인

설치 후 다음 함수들이 사용 가능합니다:
- `parse_log_line`: 단일 라인 파싱
- `parse_log_batch`: 배치 파싱
- `parse_log_file_chunk`: **파일 I/O + 파싱 (새 기능)**
- `count_file_lines`: **파일 줄 수 계산 (새 기능)**
