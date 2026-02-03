"""Rust 기반 고성능 로그 파서 (선택적 사용)"""
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Rust 확장 모듈 사용 시도
RUST_PARSER_AVAILABLE = False
try:
    from logcat_parser_rs import (
        parse_log_line as rust_parse_log_line,
        parse_log_batch as rust_parse_log_batch,
    )
    RUST_PARSER_AVAILABLE = True
    logger.info("[Parser] Rust 파서 사용 가능 - 고성능 모드 활성화")
    
    # 파일 I/O 함수는 선택적 (새 버전에만 있음)
    try:
        from logcat_parser_rs import (
            parse_log_file_chunk as rust_parse_log_file_chunk,
            count_file_lines as rust_count_file_lines
        )
        logger.info("[Parser] Rust 파일 I/O 함수 사용 가능")
    except ImportError:
        logger.warning("[Parser] Rust 파일 I/O 함수를 사용할 수 없음 - 파서를 다시 빌드하세요")
        rust_parse_log_file_chunk = None
        rust_count_file_lines = None
    
    # 스트리밍 파서 (O(n) - 가장 효율적)
    try:
        from logcat_parser_rs import parse_file_streaming as rust_parse_file_streaming
        logger.info("[Parser] Rust 스트리밍 파서 사용 가능")
    except ImportError:
        logger.warning("[Parser] Rust 스트리밍 파서를 사용할 수 없음 - 파서를 다시 빌드하세요")
        rust_parse_file_streaming = None
except ImportError:
    logger.debug("[Parser] Rust 파서를 사용할 수 없음 - Python 파서 사용")
    rust_parse_log_line = None
    rust_parse_log_batch = None
    rust_parse_log_file_chunk = None
    rust_count_file_lines = None
    rust_parse_file_streaming = None


class RustLogParser:
    """Rust 기반 고성능 로그 파서"""
    
    def __init__(self, format_type: str = 'threadtime'):
        """
        Args:
            format_type: 로그 형식 (현재는 threadtime만 지원)
        """
        self.format_type = format_type
        if not RUST_PARSER_AVAILABLE:
            raise ImportError("Rust 파서가 설치되지 않았습니다. 'maturin develop' 또는 'pip install .'을 실행하세요.")
    
    def parse(self, line: str) -> Optional[Dict[str, Any]]:
        """
        로그 라인을 파싱 (Rust 구현)
        
        Args:
            line: 로그 라인 문자열
            
        Returns:
            파싱된 로그 딕셔너리 또는 None
        """
        if not line or not line.strip():
            return None
        
        try:
            result = rust_parse_log_line(line)
            if result:
                # PyDict를 Python dict로 변환
                return dict(result)
        except Exception as e:
            logger.debug(f"[RustParser] 파싱 실패: {str(e)}")
        
        return None
    
    def parse_batch(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        배치 파싱 (더 빠름)
        
        Args:
            lines: 로그 라인 리스트
            
        Returns:
            파싱된 로그 딕셔너리 리스트
        """
        if not lines:
            return []
        
        try:
            # Rust 배치 파싱 직접 호출
            results = rust_parse_log_batch(lines)
            # PyObject 리스트를 Python dict 리스트로 변환
            parsed = []
            for r in results:
                if r is not None:
                    try:
                        parsed.append(dict(r))
                    except Exception as e:
                        logger.debug(f"[RustParser] dict 변환 실패: {str(e)}")
            return parsed
        except Exception as e:
            logger.error(f"[RustParser] 배치 파싱 실패: {str(e)}", exc_info=True)
            return []
    
    def parse_file_chunk(self, file_path: str, batch_size: int = 10000) -> List[Dict[str, Any]]:
        """
        파일에서 직접 읽고 파싱 (Rust I/O + 파싱, 매우 빠름)
        
        Args:
            file_path: 로그 파일 경로
            batch_size: 한 번에 처리할 배치 크기
            
        Returns:
            파싱된 로그 딕셔너리 리스트
        """
        if not RUST_PARSER_AVAILABLE:
            raise ImportError("Rust 파서가 설치되지 않았습니다")
        
        if rust_parse_log_file_chunk is None:
            raise ImportError(
                "Rust 파일 I/O 함수를 사용할 수 없습니다. "
                "Rust 파서를 다시 빌드하고 설치하세요: "
                "cd rust-parser && python -m maturin build --release"
            )
        
        try:
            results = rust_parse_log_file_chunk(file_path, batch_size)
            # PyObject 리스트를 Python dict 리스트로 변환
            parsed = []
            for r in results:
                if r is not None:
                    try:
                        parsed.append(dict(r))
                    except Exception as e:
                        logger.debug(f"[RustParser] dict 변환 실패: {str(e)}")
            return parsed
        except Exception as e:
            logger.error(f"[RustParser] 파일 파싱 실패: {str(e)}", exc_info=True)
            return []
    
    def parse_file_streaming(self, file_path: str, chunk_size: int, callback) -> int:
        """
        파일을 스트리밍으로 읽고 청크마다 콜백 호출 (O(n) - 가장 효율적)
        
        Args:
            file_path: 로그 파일 경로
            chunk_size: 청크 크기
            callback: 콜백 함수 (parsed_logs, current_line, total_lines) -> bool
                     False 반환 시 중단
            
        Returns:
            총 파싱된 로그 수
        """
        if not RUST_PARSER_AVAILABLE:
            raise ImportError("Rust 파서가 설치되지 않았습니다")
        
        if rust_parse_file_streaming is None:
            raise ImportError(
                "Rust 스트리밍 파서를 사용할 수 없습니다. "
                "Rust 파서를 다시 빌드하고 설치하세요: "
                "cd rust-parser && python -m maturin build --release"
            )
        
        def wrapper_callback(parsed_dicts, current_line, total_lines):
            """Rust에서 호출되는 콜백 - PyObject를 dict로 변환"""
            converted = []
            for r in parsed_dicts:
                if r is not None:
                    try:
                        converted.append(dict(r))
                    except Exception as e:
                        logger.debug(f"[RustParser] dict 변환 실패: {str(e)}")
            return callback(converted, current_line, total_lines)
        
        try:
            return rust_parse_file_streaming(file_path, chunk_size, wrapper_callback)
        except Exception as e:
            logger.error(f"[RustParser] 스트리밍 파싱 실패: {str(e)}", exc_info=True)
            return 0
    
    @staticmethod
    def count_file_lines(file_path: str) -> int:
        """
        파일의 총 줄 수를 빠르게 계산 (Rust)
        
        Args:
            file_path: 로그 파일 경로
            
        Returns:
            총 줄 수
        """
        if not RUST_PARSER_AVAILABLE or rust_count_file_lines is None:
            # Fallback: Python으로 계산
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return sum(1 for _ in f)
            except Exception:
                return 0
        
        try:
            return rust_count_file_lines(file_path)
        except Exception as e:
            logger.warning(f"[RustParser] 줄 수 계산 실패: {str(e)}, Python fallback 사용")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return sum(1 for _ in f)
            except Exception:
                return 0
