# logcat-parser-rs

Rust로 작성된 Android/AAOS logcat 고성능 파서 Python 확장 모듈입니다.  
PyO3로 Python 바인딩을 제공하며, 대용량 로그 파일(수백만 줄)을 효율적으로 파싱합니다.

---

## 개요

| 항목 | 설명 |
|------|------|
| **역할** | logcat 로그 라인 파싱 → Python dict 반환 |
| **지원 형식** | threadtime, Level/Tag(PID TID) 형식 |
| **특징** | 정규식 한 번 컴파일, 스트리밍 I/O, AAOS Display 분류 |

---

## 지원 로그 형식

다음 형식을 인식합니다.

1. **threadtime (단순)**  
   `mm-dd HH:MM:SS.mmm  PID  -  -  Tag: Message`

2. **threadtime (상세)**  
   `mm-dd HH:MM:SS.mmm  L  -  -  PID  TID  L  Tag: Message`

3. **Level/Tag**  
   `mm-dd HH:MM:SS.mmm  L/Tag(  PID  TID  ) Message`

반환 dict 키: `timestamp`, `level`, `pid`, `tid`, `tag`, `message`, `display`  
(파싱 실패 시 `None`)

---

## API 레퍼런스

### `parse_log_line(line: str) -> dict | None`

한 줄을 파싱해 dict 또는 `None` 반환.

```python
from logcat_parser_rs import parse_log_line

d = parse_log_line("01-25 12:34:56.789  1234  -  -  E  MyTag: Hello")
# {'timestamp': '01-25 12:34:56.789', 'level': 'E', 'pid': '1234', 'tid': '-', 'tag': 'MyTag', 'message': 'Hello', 'display': 'Main'}
```

---

### `parse_log_batch(lines: list[str]) -> list[dict]`

여러 줄을 한 번에 파싱. 단일 라인 파싱보다 효율적.

```python
from logcat_parser_rs import parse_log_batch

results = parse_log_batch(["line1", "line2", ...])
# 파싱 성공한 항목만 리스트로 반환
```

---

### `parse_log_file_chunk(file_path: str, batch_size: int) -> list[dict]`

파일 전체를 읽어 메모리에서 배치 단위로 파싱 후 **한 번에** 반환.  
(파일을 한 번만 읽음, O(n))

- `file_path`: 로그 파일 경로
- `batch_size`: 내부 배치 크기 (예: 10000)
- 반환: 파싱된 dict 리스트

```python
from logcat_parser_rs import parse_log_file_chunk

all_parsed = parse_log_file_chunk("/path/to/log.txt", 10000)
```

---

### `parse_file_streaming(file_path: str, chunk_size: int, callback: Callable) -> int`

파일을 **한 번만** 읽으면서 청크마다 콜백 호출. 대용량 파일에서 진행률 표시·취소에 적합 (O(n)).

- `file_path`: 로그 파일 경로
- `chunk_size`: 한 번에 넘겨줄 (파싱된) 로그 개수 단위
- `callback(parsed_logs, current_line, total_lines) -> bool`  
  - `parsed_logs`: 이번 청크의 dict 리스트  
  - `current_line`: 현재까지 읽은 줄 번호  
  - `total_lines`: 파일 전체 줄 수  
  - `True` 계속, `False` 중단
- 반환: 총 파싱된 로그 개수

```python
from logcat_parser_rs import parse_file_streaming

def on_chunk(parsed_logs, current_line, total_lines):
    print(f"{current_line}/{total_lines}")
    # UI 업데이트 등
    return True  # False 시 중단

total = parse_file_streaming("/path/to/log.txt", 50000, on_chunk)
```

---

### `count_file_lines(file_path: str) -> int`

파일의 총 줄 수만 빠르게 셉니다.

```python
from logcat_parser_rs import count_file_lines

n = count_file_lines("/path/to/log.txt")
```

---

## AAOS Display 분류

`display` 필드는 메시지/태그 패턴으로 자동 분류됩니다.

| 값 | 조건 예 |
|----|----------|
| `Main` | displayId 0, 또는 기본 |
| `Cluster` | displayId 1, 태그에 "cluster" |
| `IVI` | displayId 2, "ivi" / "infotainment" |
| `Passenger` | "passenger" |
| `Display` | 그 외 displayId |

---

## 빌드 및 설치

### 요구 사항

- Rust (rustup)
- Python 3.8+
- Windows: Visual Studio Build Tools (C++)

### Windows

```powershell
# Rust 미설치 시: https://rustup.rs/
# Maturin (Python 모듈로 실행 권장)
pip install maturin

cd rust-parser
python -m maturin build --release
pip install --force-reinstall "target/wheels/logcat_parser_rs-0.1.0-cp38-abi3-win_amd64.whl"
```

캐시 없이 다시 빌드하려면:

```powershell
cargo clean
python -m maturin build --release
pip install --force-reinstall "target/wheels/logcat_parser_rs-0.1.0-cp38-abi3-win_amd64.whl"
```

### Linux / macOS

```bash
pip install maturin
cd rust-parser
python -m maturin build --release
pip install target/wheels/logcat_parser_rs-*.whl
```

---

## 성능

- Python 단일 정규식 파서 대비 **10~50배** 빠른 편.
- 1.4GB / 약 186만 줄 기준 **parse_file_streaming** 사용 시 약 30~40초 수준 (환경에 따라 변동).
- `chunk_size`를 크게(예: 50_000) 하면 콜백 횟수가 줄어 더 유리.

---

## 프로젝트 내 사용

이 모듈은 `src/core/parser_rust.py`에서 래핑되어 사용됩니다.

- `RustLogParser.parse()` → `parse_log_line`
- `RustLogParser.parse_batch()` → `parse_log_batch`
- `RustLogParser.parse_file_chunk()` → `parse_log_file_chunk`
- `RustLogParser.parse_file_streaming()` → `parse_file_streaming`
- `RustLogParser.count_file_lines()` → `count_file_lines`

`parse_file_streaming`이 있으면 스트리밍 모드로 파일 로드하며, 없으면 `parse_file_chunk` fallback을 사용합니다.
