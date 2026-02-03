"""
로그 테이블 관련 백그라운드 스레드 클래스들
"""
import os
import random
import threading
import time
from PyQt6.QtCore import QThread, pyqtSignal
from core.collector import ADBLogCollector
from core.parser import LogParser
from .log_model import compute_filtered_indices_and_matches


class LogcatThread(QThread):
    """백그라운드에서 logcat을 수집하는 스레드 (core.collector 래퍼)"""
    log_received = pyqtSignal(str)  # 로그 라인을 전달하는 시그널
    error_occurred = pyqtSignal(str)  # 에러 메시지를 전달하는 시그널
    
    def __init__(self, parent=None, logcat_filter='*:V', buffer='main', format_type='threadtime'):
        super().__init__(parent)
        self.collector = ADBLogCollector(logcat_filter=logcat_filter, buffer=buffer, format_type=format_type)
        self.collector.on_log_received = self._on_log_received
        self.collector.on_error = self._on_error
    
    def _on_log_received(self, line: str):
        """콜백: 로그 수신"""
        self.log_received.emit(line)
    
    def _on_error(self, error: str):
        """콜백: 에러 발생"""
        self.error_occurred.emit(error)
    
    def run(self):
        """logcat 실행"""
        self.collector.collect()
    
    def stop(self):
        """logcat 중지"""
        self.collector.stop()
    
    def pause(self):
        """일시정지"""
        self.collector.pause()
    
    def resume(self):
        """재개"""
        self.collector.resume()
    
    @property
    def is_running(self):
        """실행 중 여부"""
        return self.collector.is_running
    
    @property
    def is_paused(self):
        """일시정지 여부"""
        return self.collector.is_paused


class FilterApplyThread(QThread):
    """백그라운드에서 필터 적용 및 UI 업데이트 준비"""
    batch_ready = pyqtSignal(list, int, int)  # 배치 데이터, 시작 인덱스, 총 개수
    filter_complete = pyqtSignal(int)  # 필터 완료 (총 개수)
    
    def __init__(self, all_logs, active_filters, filter_table, evaluate_filter_func):
        super().__init__()
        self.all_logs = all_logs
        self.active_filters = active_filters
        self.filter_table = filter_table
        self.evaluate_filter = evaluate_filter_func
        self.should_cancel = False
        self.batch_size = 10000  # 배치 크기
    
    def run(self):
        """필터 적용 및 배치 준비"""
        try:
            # 활성화된 필터 수집
            enabled_filters = []
            for row in range(self.filter_table.rowCount()):
                checkbox = self.filter_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    filter_index = checkbox.property('filter_index')
                    if filter_index is not None and 0 <= filter_index < len(self.active_filters):
                        enabled_filters.append(self.active_filters[filter_index])
            
            show_filters = [f for f in enabled_filters if f.get('type', 'Show') == 'Show']
            ignore_filters = [f for f in enabled_filters if f.get('type', 'Show') == 'Ignore']
            
            # 필터 비활성화 모드
            FILTER_DISABLED = True
            
            # 필터링된 로그 수집
            filtered_logs = []
            for log_data in self.all_logs:
                if self.should_cancel:
                    return
                
                if FILTER_DISABLED:
                    filtered_logs.append((log_data, None))
                else:
                    # Ignore 필터 체크
                    if ignore_filters:
                        should_ignore = False
                        for f in ignore_filters:
                            if self.evaluate_filter(f, log_data):
                                should_ignore = True
                                break
                        if should_ignore:
                            continue
                    
                    # Show 필터 체크
                    matched_filter = None
                    if show_filters:
                        for f in show_filters:
                            if self.evaluate_filter(f, log_data):
                                matched_filter = f
                                break
                        if matched_filter is None:
                            continue
                    elif not enabled_filters:
                        matched_filter = None
                    
                    filtered_logs.append((log_data, matched_filter))
                
                # 배치 단위로 시그널 전송
                if len(filtered_logs) >= self.batch_size:
                    self.batch_ready.emit(filtered_logs.copy(), len(filtered_logs) - self.batch_size, len(self.all_logs))
                    filtered_logs.clear()
            
            # 마지막 배치 전송
            if filtered_logs:
                self.batch_ready.emit(filtered_logs, len(self.all_logs) - len(filtered_logs), len(self.all_logs))
            
            # 완료 시그널
            total_filtered = len(self.all_logs) if FILTER_DISABLED else len([l for l in self.all_logs if True])  # 실제로는 필터링된 개수
            self.filter_complete.emit(total_filtered)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[FilterThread] 오류: {str(e)}", exc_info=True)
    
    def cancel(self):
        """취소"""
        self.should_cancel = True


class PrepareModelThread(QThread):
    """워커에서 필터 적용 계산 후, 메인에서 set_prepared_data만 호출하도록 결과 전달"""
    prepared_data = pyqtSignal(list, list, list)  # all_logs, filtered_indices, matched_filters

    def __init__(self, logs: list, filters: list):
        super().__init__()
        self.logs = logs
        self.filters = filters

    def run(self):
        filtered_indices, matched_filters = compute_filtered_indices_and_matches(self.logs, self.filters)
        self.prepared_data.emit(self.logs, filtered_indices, matched_filters)


class FileLoadThread(QThread):
    """백그라운드에서 로그 파일을 로드하는 스레드"""
    log_batch_parsed = pyqtSignal(list)  # 배치 단위로 파싱된 로그 리스트 전달
    progress_updated = pyqtSignal(int, int, int)  # 진행률, 현재 줄, 전체 줄
    load_complete = pyqtSignal(int)  # 로드 완료 (전체 줄 수)
    load_error = pyqtSignal(str)  # 에러 메시지
    
    def __init__(self, file_path: str, parser: LogParser):
        super().__init__()
        self.file_path = file_path
        self.parser = parser
        self.batch_size = 50000  # 배치 단위로 처리 (큰 파일 성능 최적화)
        self.should_cancel = False
    
    def run(self):
        """파일 로드 실행 - Rust 파일 I/O + 파싱 사용 (최고 성능)"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Rust 파일 파서 사용 가능 여부 확인
            has_use_rust = hasattr(self.parser, 'use_rust')
            use_rust_value = getattr(self.parser, 'use_rust', False) if has_use_rust else False
            has_rust_parser = hasattr(self.parser, 'rust_parser')
            rust_parser_value = getattr(self.parser, 'rust_parser', None) if has_rust_parser else None
            has_parse_file_chunk = hasattr(rust_parser_value, 'parse_file_chunk') if rust_parser_value is not None else False
            
            use_rust_file_parsing = (
                has_use_rust
                and use_rust_value
                and has_rust_parser
                and rust_parser_value is not None
                and has_parse_file_chunk
            )
            
            # 디버깅: 각 조건 확인
            logger.debug(f"[FileLoad] Rust 파서 감지:")
            logger.debug(f"  - hasattr(parser, 'use_rust'): {has_use_rust}")
            logger.debug(f"  - parser.use_rust: {use_rust_value}")
            logger.debug(f"  - hasattr(parser, 'rust_parser'): {has_rust_parser}")
            logger.debug(f"  - parser.rust_parser is not None: {rust_parser_value is not None}")
            logger.debug(f"  - hasattr(rust_parser, 'parse_file_chunk'): {has_parse_file_chunk}")
            logger.debug(f"  - 최종 결과: use_rust_file_parsing = {use_rust_file_parsing}")
            
            if use_rust_file_parsing:
                # Rust 스트리밍 파서 사용 가능 여부 확인
                has_streaming = hasattr(rust_parser_value, 'parse_file_streaming')
                logger.info(f"[FileLoad] has_streaming = {has_streaming}")
                logger.info(f"[FileLoad] rust_parser 함수 목록: {dir(rust_parser_value)}")
                
                if has_streaming:
                    # Rust 스트리밍 파서 사용 (O(n) - 가장 효율적, 파일 한 번만 읽음)
                    logger.info(f"[FileLoad] 🚀 Rust 스트리밍 파서 사용 - 배치 크기: {self.batch_size}")
                    
                    parsed_count = [0]  # 클로저에서 수정하기 위해 리스트로
                    
                    def on_chunk_parsed(parsed_dicts, current_line, total_lines):
                        """Rust에서 청크마다 호출되는 콜백"""
                        print(f"[PID {os.getpid()}] [Thread {threading.get_ident()}] [FileLoad] Rust 스트리밍 파서 청크 파싱 - 현재 줄: {current_line}, 전체 줄: {total_lines}")
                        if self.should_cancel:
                            return False  # 중단
                        
                        batch = []
                        for parsed_dict in parsed_dicts:
                            if parsed_dict:
                                timestamp = parsed_dict.get('timestamp', '')
                                level = parsed_dict.get('level', '-')
                                display = parsed_dict.get('display', 'Main')
                                tag = parsed_dict.get('tag', 'Unknown')
                                message = parsed_dict.get('message', '')
                                log_tuple = (timestamp, level, display, tag, message)
                                batch.append(log_tuple)
                        
                        if batch:
                            self.log_batch_parsed.emit(batch)
                            parsed_count[0] += len(batch)
                        
                        # 진행 상황 업데이트
                        progress = int((current_line / total_lines) * 100) if total_lines > 0 else 0
                        self.progress_updated.emit(progress, current_line, total_lines)

                        time.sleep(0.02)
                        return True  # 계속 진행
                    
                    # Rust 스트리밍 파서 호출 (파일을 한 번만 읽음)
                    self.parser.rust_parser.parse_file_streaming(
                        self.file_path, self.batch_size, on_chunk_parsed
                    )
                    
                    # 완료
                    if not self.should_cancel:
                        self.load_complete.emit(parsed_count[0])
   
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[FileLoad] 파일 로드 오류: {str(e)}", exc_info=True)
            self.load_error.emit(str(e))
    
    def cancel(self):
        """로드 취소"""
        self.should_cancel = True
