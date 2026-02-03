use pyo3::prelude::*;
use pyo3::types::PyDict;
use regex::Regex;
use once_cell::sync::Lazy;
use std::fs::File;
use std::io::{BufRead, BufReader};

// 정규식 패턴들을 한 번만 컴파일 (성능 최적화)
static TIME_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})").unwrap()
});

static THREADTIME_SIMPLE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^(\d+)\s+-\s+-\s+([^:]+):\s+(.*)$").unwrap()
});

static THREADTIME_COMPLEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^([VDIWEAF])\s+-\s+-\s+(\d+)\s+(\d+)\s+([VDIWEAF])\s+([^:]+):\s*(.*)$").unwrap()
});

static LEVEL_TAG_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^([DIWEFV])/([^(]+)\(\s*([^)]*?)\s*\)\s+(.*)$").unwrap()
});

static DISPLAY_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        Regex::new(r"(?i)displayId[:\s]+(\d+)").unwrap(),
        Regex::new(r"(?i)display[:\s]+(\d+)").unwrap(),
        Regex::new(r"(?i)Display\s+(\d+)").unwrap(),
    ]
});

/// 로그 라인을 파싱하여 딕셔너리로 반환
#[pyfunction]
fn parse_log_line(line: &str) -> Option<PyObject> {
    Python::with_gil(|py| {
        let line = line.trim();
        if line.is_empty() {
            return None;
        }

        // 시간 패턴 찾기
        let time_match = TIME_PATTERN.find(line)?;
        let timestamp = time_match.as_str();
        let remaining = &line[time_match.end()..].trim();

        // 형식 1: mm-dd HH:MM:SS.mmm  PID  -  -  Tag: Message (Level 없음)
        if let Some(caps) = THREADTIME_SIMPLE.captures(remaining) {
            let pid = caps.get(1)?.as_str();
            let tag = caps.get(2)?.as_str().trim();
            let message = caps.get(3)?.as_str().trim();
            let display = classify_display(tag, message);

            let dict = PyDict::new_bound(py);
            dict.set_item("timestamp", timestamp).ok()?;
            dict.set_item("level", "-").ok()?;
            dict.set_item("pid", pid).ok()?;
            dict.set_item("tid", "-").ok()?;
            dict.set_item("tag", tag).ok()?;
            dict.set_item("message", message).ok()?;
            dict.set_item("display", display).ok()?;
            return Some(dict.into());
        }

        // 형식 2: mm-dd HH:MM:SS.mmm  Level  -  -  PID  TID  Level  Tag: Message
        if let Some(caps) = THREADTIME_COMPLEX.captures(remaining) {
            let level = caps.get(4)?.as_str();
            let pid = caps.get(2)?.as_str();
            let tid = caps.get(3)?.as_str();
            let tag = caps.get(5)?.as_str().trim();
            let message = caps.get(6)?.as_str().trim();
            let display = classify_display(tag, message);

            let dict = PyDict::new_bound(py);
            dict.set_item("timestamp", timestamp).ok()?;
            dict.set_item("level", level).ok()?;
            dict.set_item("pid", pid).ok()?;
            dict.set_item("tid", tid).ok()?;
            dict.set_item("tag", tag).ok()?;
            dict.set_item("message", message).ok()?;
            dict.set_item("display", display).ok()?;
            return Some(dict.into());
        }

        // 형식 3: Level/Tag(  PID  TID  Message
        if let Some(caps) = LEVEL_TAG_PATTERN.captures(remaining) {
            let level = caps.get(1)?.as_str();
            let tag = caps.get(2)?.as_str().trim();
            let pid_tid = caps.get(3)?.as_str().trim();
            let message = caps.get(4)?.as_str().trim();

            let pid_tid_parts: Vec<&str> = pid_tid.split_whitespace().collect();
            let pid = pid_tid_parts.get(0).unwrap_or(&"-");
            let tid = pid_tid_parts.get(1).unwrap_or(&"-");
            let display = classify_display(tag, message);

            let dict = PyDict::new_bound(py);
            dict.set_item("timestamp", timestamp).ok()?;
            dict.set_item("level", level).ok()?;
            dict.set_item("pid", *pid).ok()?;
            dict.set_item("tid", *tid).ok()?;
            dict.set_item("tag", tag).ok()?;
            dict.set_item("message", message).ok()?;
            dict.set_item("display", display).ok()?;
            return Some(dict.into());
        }

        None
    })
}

/// 배치 파싱 (벡터화된 처리로 더 빠름)
#[pyfunction]
fn parse_log_batch(lines: Vec<String>) -> Vec<PyObject> {
    lines
        .into_iter()
        .filter_map(|line| parse_log_line(&line))
        .collect()
}

/// 파일에서 로그를 읽고 파싱 (고성능 파일 I/O + 파싱)
/// 배치 단위로 결과를 반환하여 메모리 효율적 처리
#[pyfunction]
fn parse_log_file_chunk(file_path: &str, batch_size: usize) -> PyResult<Vec<PyObject>> {
    // 파일 읽기 (GIL 밖에서 수행)
    let file = File::open(file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to open file: {}", e)))?;
    
    let reader = BufReader::new(file);
    let mut lines = Vec::new();
    
    for line in reader.lines() {
        match line {
            Ok(line) => {
                let trimmed = line.trim();
                if !trimmed.is_empty() {
                    lines.push(trimmed.to_string());  // 소유권 확보
                }
            }
            Err(e) => {
                // 읽기 오류는 로그하고 계속 진행
                eprintln!("Line read error: {}", e);
            }
        }
    }
    
    // 파싱 (GIL 필요)
    Python::with_gil(|_py| {
        let mut results = Vec::new();
        
        // 배치 단위로 파싱
        for chunk in lines.chunks(batch_size) {
            let parsed: Vec<PyObject> = chunk
                .iter()
                .filter_map(|l| parse_log_line(l))
                .collect();
            results.extend(parsed);
        }
        
        Ok(results)
    })
}

/// 파일의 총 줄 수를 빠르게 계산
#[pyfunction]
fn count_file_lines(file_path: &str) -> PyResult<usize> {
    let file = File::open(file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to open file: {}", e)))?;
    
    let reader = BufReader::new(file);
    let count = reader.lines().count();
    Ok(count)
}

/// 파일을 한 번만 읽고 청크마다 콜백 호출 (O(n) - 가장 효율적)
/// callback(parsed_logs: List[Dict], progress: int, total: int) -> bool
/// 콜백이 False 반환하면 중단
#[pyfunction]
fn parse_file_streaming(
    file_path: &str, 
    chunk_size: usize, 
    callback: PyObject
) -> PyResult<usize> {
    let file = File::open(file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to open file: {}", e)))?;
    
    // 먼저 총 줄 수 계산 (진행률용)
    let total_lines = {
        let file = File::open(file_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to open file: {}", e)))?;
        BufReader::new(file).lines().count()
    };
    
    let reader = BufReader::new(file);
    let mut lines_buffer: Vec<String> = Vec::with_capacity(chunk_size);
    let mut total_parsed = 0usize;
    let mut current_line = 0usize;
    
    for line in reader.lines() {
        match line {
            Ok(line) => {
                let trimmed = line.trim();
                if !trimmed.is_empty() {
                    lines_buffer.push(trimmed.to_string());
                }
                current_line += 1;
                
                // chunk_size마다 콜백 호출
                if lines_buffer.len() >= chunk_size {
                    let should_continue = Python::with_gil(|py| {
                        // 파싱
                        let parsed: Vec<PyObject> = lines_buffer
                            .drain(..)
                            .filter_map(|l| parse_log_line(&l))
                            .collect();
                        
                        let count = parsed.len();
                        total_parsed += count;
                        
                        // 콜백 호출: callback(parsed_logs, progress, total)
                        let result = callback.call1(py, (parsed, current_line, total_lines));
                        
                        match result {
                            Ok(obj) => obj.extract::<bool>(py).unwrap_or(true),
                            Err(_) => false, // 에러 시 중단
                        }
                    });
                    
                    if !should_continue {
                        return Ok(total_parsed);
                    }
                }
            }
            Err(e) => {
                eprintln!("Line read error: {}", e);
                current_line += 1;
            }
        }
    }
    
    // 남은 라인 처리
    if !lines_buffer.is_empty() {
        Python::with_gil(|py| {
            let parsed: Vec<PyObject> = lines_buffer
                .into_iter()
                .filter_map(|l| parse_log_line(&l))
                .collect();
            
            total_parsed += parsed.len();
            let _ = callback.call1(py, (parsed, current_line, total_lines));
        });
    }
    
    Ok(total_parsed)
}

/// AAOS 다중 디스플레이 자동 분류
fn classify_display(tag: &str, message: &str) -> &'static str {
    // Display ID 패턴 찾기
    for pattern in DISPLAY_PATTERNS.iter() {
        if let Some(caps) = pattern.captures(message) {
            if let Some(display_id) = caps.get(1) {
                match display_id.as_str() {
                    "0" => return "Main",
                    "1" => return "Cluster",
                    "2" => return "IVI",
                    _ => return "Display",
                }
            }
        }
    }

    // 태그 기반 분류
    let tag_lower = tag.to_lowercase();
    if tag_lower.contains("cluster") {
        return "Cluster";
    } else if tag_lower.contains("ivi") || tag_lower.contains("infotainment") {
        return "IVI";
    } else if tag_lower.contains("passenger") {
        return "Passenger";
    }

    "Main"
}

/// Python 모듈 정의
#[pymodule]
fn logcat_parser_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_log_line, m)?)?;
    m.add_function(wrap_pyfunction!(parse_log_batch, m)?)?;
    m.add_function(wrap_pyfunction!(parse_log_file_chunk, m)?)?;
    m.add_function(wrap_pyfunction!(count_file_lines, m)?)?;
    m.add_function(wrap_pyfunction!(parse_file_streaming, m)?)?;
    Ok(())
}
