"""
로그 테이블 메인 위젯

QTableView + QAbstractTableModel 기반 가상화 테이블
- 화면에 보이는 행만 렌더링
- 100만 개 로그도 빠르게 표시
- UI 블로킹 없음
"""
import re
import time
import os
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QTableView, QHeaderView, QAbstractItemView,
    QGroupBox, QPushButton, QCheckBox, QFileDialog, QMessageBox, QMenu,
    QRadioButton, QLineEdit, QComboBox, QLabel, QGridLayout, QDialog
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent, QAction

# Core 모듈 import
from core.parser import LogParser
from core.buffer import LogBuffer
from core.detector import ErrorDetector

# 로컬 모듈 import
from .threads import LogcatThread, FileLoadThread, PrepareModelThread
from .filter_dialog import FilterDialog
from .log_model import LogTableModel


class LogTable(QWidget):
    # 상태바 업데이트 시그널
    status_message = pyqtSignal(str)  # 상태 메시지 전달
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._setup_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Logcat Control & Filter Panel
        control_layout = QHBoxLayout()
        
        # Logcat Control Group
        control_group = QGroupBox("Logcat Control")
        control_group.setMaximumWidth(200)
        control_group.setMaximumHeight(140)
        control_layout_group = QGridLayout()
        
        self.start_btn = QPushButton("▶ Start")
        self.stop_btn = QPushButton("⏹ Stop")
        self.pause_btn = QPushButton("⏸ Pause")
        self.clear_btn = QPushButton("Clear")
        self.auto_scroll_cb = QCheckBox("Auto Scroll")
        self.auto_scroll_cb.setChecked(True)
        
        self.start_btn.clicked.connect(self._start_logcat)
        self.stop_btn.clicked.connect(self._stop_logcat)
        self.pause_btn.clicked.connect(self._pause_logcat)
        self.clear_btn.clicked.connect(self.clear_all_logs)
        
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        
        control_layout_group.addWidget(self.start_btn, 0, 0)
        control_layout_group.addWidget(self.stop_btn, 0, 1)
        control_layout_group.addWidget(self.pause_btn, 1, 0)
        control_layout_group.addWidget(self.clear_btn, 1, 1)
        control_layout_group.addWidget(self.auto_scroll_cb, 2, 0, 1, 2)
        
        control_group.setLayout(control_layout_group)
        control_layout.addWidget(control_group)
        
        # Filter Panel
        filter_group = QGroupBox("Filters")
        filter_group.setMaximumHeight(140)
        filter_layout = QVBoxLayout()
        
        self.filter_table = QTableWidget(0, 7)
        self.filter_table.setHorizontalHeaderLabels(["Enable", "Level", "PID", "TID", "Display", "Tag", "Message"])
        self.filter_table.setMaximumHeight(100)
        self.filter_table.setColumnWidth(0, 50)
        self.filter_table.setColumnWidth(1, 50)
        self.filter_table.setColumnWidth(2, 50)
        self.filter_table.setColumnWidth(3, 50)
        self.filter_table.setColumnWidth(4, 70)
        self.filter_table.setColumnWidth(5, 100)
        self.filter_table.horizontalHeader().setStretchLastSection(True)
        
        self.filter_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.filter_table.customContextMenuRequested.connect(self._show_filter_context_menu)
        self.filter_table.itemDoubleClicked.connect(self._on_filter_double_clicked)
        
        filter_layout.addWidget(self.filter_table)
        filter_group.setLayout(filter_layout)
        control_layout.addWidget(filter_group)
        
        layout.addLayout(control_layout)
        
        # Log Table (QTableView + 가상화 모델)
        self.log_model = LogTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.log_model)
        
        # 테이블 설정
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setFont(QFont("Consolas", 10))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(True)
        
        # 컬럼 너비 설정
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(30)
        self.table.setColumnWidth(0, 130)   # Time
        self.table.setColumnWidth(1, 40)    # Level
        self.table.setColumnWidth(2, 60)    # PID
        self.table.setColumnWidth(3, 60)    # TID
        self.table.setColumnWidth(4, 80)    # Display
        self.table.setColumnWidth(5, 150)   # Tag
        header.setStretchLastSection(True)   # Message 컬럼 자동 확장
        
        # 행 높이 설정 (전역)
        self.table.verticalHeader().setDefaultSectionSize(28)
        
        # 스크롤 성능 최적화
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # Drag and drop
        self.setAcceptDrops(True)
        
        layout.addWidget(self.table)
    
    def _setup_data(self):
        # 필터 관련
        self.active_filters = []
        
        # 스레드 관련
        self.logcat_thread = None
        self.file_load_thread = None
        
        # 배치 처리 (실시간 logcat용)
        self.pending_logs = []
        self.batch_size = 100  # 배치 크기 증가 (모델 사용으로 더 효율적)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._process_pending_logs)
        self.update_timer.setInterval(50)
        self.log_collection_start_time = None
        
        # 파일 로드 중 임시 저장 (로드 완료 후 한 번에 추가)
        self.pending_file_logs = []
        
        # Core 모듈 초기화
        self.log_parser = LogParser(format_type='threadtime')
        self.log_buffer = LogBuffer(max_size=1000)
        self.error_detector = ErrorDetector()
        self.error_detector.on_error_detected = self._on_error_detected
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            if file_path.endswith(('.txt', '.log')):
                self.load_logcat_file(file_path)
                break
    
    def _parse_log_line(self, line):
        """
        로그 라인 파싱 (core.parser 사용)
        기존 튜플 형식 유지: (timestamp, level, display, tag, message)
        """
        # Core parser 사용
        parsed_dict = self.log_parser.parse(line)
        if not parsed_dict:
            return None
        
        # 딕셔너리를 튜플로 변환 (기존 코드 호환성)
        timestamp = parsed_dict.get('timestamp', '')
        level = parsed_dict.get('level', '-')
        display = parsed_dict.get('display', 'Main')
        tag = parsed_dict.get('tag', 'Unknown')
        message = parsed_dict.get('message', '')
        
        # 버퍼에 추가 (딕셔너리 형식)
        self.log_buffer.add(parsed_dict)
        
        # 에러 감지
        self.error_detector.detect(parsed_dict)
        
        # 튜플 반환 (기존 UI 코드 호환성)
        return (timestamp, level, display, tag, message)
    
    def _on_error_detected(self, error_info):
        """에러 감지 콜백 (core.detector에서 호출)"""
        # 필요시 에러 알림 또는 자동 분석 트리거
        pass
    
    def _on_log_received(self, line):
        """로그 라인 수신 (실시간 logcat)"""
        log_data = self._parse_log_line(line)
        if log_data:
            self.pending_logs.append(log_data)
            
            if len(self.pending_logs) >= self.batch_size:
                self._process_pending_logs()
            elif not self.update_timer.isActive():
                self.update_timer.start()
    
    def _process_pending_logs(self):
        """대기 중인 로그 배치 처리 (모델에 추가)"""
        if not self.pending_logs:
            return
        
        # 초기 수집 시 작은 배치
        if self.log_collection_start_time:
            elapsed = time.time() - self.log_collection_start_time
            if elapsed < 3.0:
                current_batch_size = min(50, self.batch_size // 2)
            else:
                current_batch_size = self.batch_size
        else:
            current_batch_size = self.batch_size
        
        logs_to_process = self.pending_logs[:current_batch_size]
        self.pending_logs = self.pending_logs[current_batch_size:]
        
        # 모델에 로그 추가 (필터링은 모델 내부에서 처리)
        should_scroll = self.auto_scroll_cb.isChecked()
        
        self.log_model.add_logs(logs_to_process)
        
        # 자동 스크롤
        if should_scroll and self.log_model.rowCount() > 0:
            self.table.scrollToBottom()
        
        # 남은 로그 처리
        if self.pending_logs:
            if not self.update_timer.isActive():
                self.update_timer.start()
        else:
            self.update_timer.stop()
    
    def _sync_filters_to_model(self):
        """필터 설정을 모델에 동기화"""
        enabled_filters = []
        for row in range(self.filter_table.rowCount()):
            checkbox = self.filter_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                filter_index = checkbox.property('filter_index')
                if filter_index is not None and 0 <= filter_index < len(self.active_filters):
                    filter_data = self.active_filters[filter_index].copy()
                    filter_data['enabled'] = True
                    enabled_filters.append(filter_data)
        
        self.log_model.set_filters(enabled_filters)
    
    def _show_filter_context_menu(self, position):
        """필터 컨텍스트 메뉴"""
        menu = QMenu(self)
        
        add_action = QAction("Add Filter...", self)
        add_action.triggered.connect(self._add_filter_rule)
        menu.addAction(add_action)
        
        current_row = self.filter_table.currentRow()
        if current_row >= 0:
            edit_action = QAction("Edit Filter...", self)
            edit_action.triggered.connect(self._edit_selected_filter)
            menu.addAction(edit_action)
            
            delete_action = QAction("Delete Filter", self)
            delete_action.triggered.connect(self._delete_selected_filter)
            menu.addAction(delete_action)
            
            menu.addSeparator()
        
        save_action = QAction("Save Filter...", self)
        save_action.triggered.connect(self._save_filters)
        menu.addAction(save_action)
        
        load_action = QAction("Load Filter...", self)
        load_action.triggered.connect(self._load_filters)
        menu.addAction(load_action)
        
        menu.addSeparator()
        
        clear_action = QAction("Clear All", self)
        clear_action.triggered.connect(self._clear_all_filters)
        menu.addAction(clear_action)
        
        menu.exec(self.filter_table.mapToGlobal(position))
    
    def _on_filter_double_clicked(self, item):
        """필터 더블클릭"""
        row = item.row()
        if row >= 0 and row < len(self.active_filters):
            self._edit_filter(row)
    
    def _add_filter_rule(self):
        """필터 추가"""
        dialog = FilterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            filter_data = dialog.get_filter_data()
            self._add_filter_to_table(filter_data)
    
    def _edit_selected_filter(self):
        """선택된 필터 편집"""
        row = self.filter_table.currentRow()
        if row >= 0:
            self._edit_filter(row)
    
    def _edit_filter(self, row):
        """필터 편집"""
        if row < 0 or row >= len(self.active_filters):
            return
        
        filter_data = self.active_filters[row]
        dialog = FilterDialog(self, filter_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_filter_data = dialog.get_filter_data()
            self.active_filters[row] = new_filter_data
            self._update_filter_table_row(row, new_filter_data)
    
    def _delete_selected_filter(self):
        """선택된 필터 삭제"""
        row = self.filter_table.currentRow()
        if row >= 0:
            del self.active_filters[row]
            self.filter_table.removeRow(row)
            # 인덱스 재설정
            for r in range(self.filter_table.rowCount()):
                checkbox = self.filter_table.cellWidget(r, 0)
                if checkbox:
                    checkbox.setProperty('filter_index', r)
    
    def _add_filter_to_table(self, filter_data):
        """필터를 테이블에 추가"""
        self.active_filters.append(filter_data)
        row = self.filter_table.rowCount()
        self.filter_table.insertRow(row)
        self._update_filter_table_row(row, filter_data)
    
    def _update_filter_table_row(self, row, filter_data):
        """필터 테이블 행 업데이트"""
        # Enable checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.setProperty('filter_index', row)
        self.filter_table.setCellWidget(row, 0, checkbox)
        
        # Fields
        fields = filter_data.get('fields', {})
        self.filter_table.setItem(row, 1, QTableWidgetItem(fields.get('level', '') or ''))
        self.filter_table.setItem(row, 2, QTableWidgetItem(fields.get('pid', '') or ''))
        self.filter_table.setItem(row, 3, QTableWidgetItem(fields.get('tid', '') or ''))
        self.filter_table.setItem(row, 4, QTableWidgetItem("Main"))  # Display
        self.filter_table.setItem(row, 5, QTableWidgetItem(fields.get('tag', '') or ''))
        self.filter_table.setItem(row, 6, QTableWidgetItem(fields.get('keyword', '') or ''))
        
        # Background color (투명도 적용)
        if filter_data.get('color'):
            filter_bg_color = QColor(filter_data['color'])
            filter_bg_color.setAlpha(70)  # 투명도 적용
            for col in range(7):
                item = self.filter_table.item(row, col)
                if item:
                    item.setBackground(filter_bg_color)
    
    def _save_filters(self):
        """필터 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Filters", "", "Filter Files (*.dlf);;All Files (*)"
        )
        if file_path:
            import json
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.active_filters, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Success", "Filters saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save filters: {str(e)}")
    
    def _load_filters(self):
        """필터 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Filters", "", "Filter Files (*.dlf);;All Files (*)"
        )
        if file_path:
            import json
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    filters = json.load(f)
                self.active_filters = filters
                self.filter_table.setRowCount(0)
                for filter_data in filters:
                    self._add_filter_to_table(filter_data)
                QMessageBox.information(self, "Success", "Filters loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load filters: {str(e)}")
    
    def _clear_all_filters(self):
        """모든 필터 삭제"""
        self.active_filters.clear()
        self.filter_table.setRowCount(0)
    
    def _start_logcat(self):
        """로그캣 시작"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        
        if self.logcat_thread and self.logcat_thread.isRunning():
            return
        
        self.log_collection_start_time = time.time()
        self.status_message.emit("Logcat 수집 중...")
        
        self.logcat_thread = LogcatThread(
            self,
            logcat_filter='*:V',
            buffer='main',
            format_type='threadtime'
        )
        self.logcat_thread.log_received.connect(self._on_log_received)
        self.logcat_thread.error_occurred.connect(self._on_logcat_error)
        self.logcat_thread.finished.connect(lambda: self.start_btn.setEnabled(True))
        self.logcat_thread.start()
        
        self.update_timer.start()
    
    def _stop_logcat(self):
        """로그캣 중지"""
        self.update_timer.stop()
        self.log_collection_start_time = None
        
        if self.pending_logs:
            self._process_pending_logs()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        
        if self.logcat_thread and self.logcat_thread.isRunning():
            self.logcat_thread.stop()
            self.logcat_thread.wait()
        
        self.pause_btn.setText("⏸ Pause")
        
        # 상태바 업데이트
        total_count = self.log_model.get_total_count()
        filtered_count = self.log_model.get_filtered_count()
        if total_count > 0:
            self.status_message.emit(f"준비 (로그: {total_count:,}개, 표시: {filtered_count:,}개)")
        else:
            self.status_message.emit("준비")
    
    def _pause_logcat(self):
        """로그캣 일시정지/재개"""
        if not self.logcat_thread or not self.logcat_thread.isRunning():
            return
        
        if self.pause_btn.text() == "⏸ Pause":
            self.logcat_thread.pause()
            self.pause_btn.setText("▶ Resume")
        else:
            self.logcat_thread.resume()
            self.pause_btn.setText("⏸ Pause")
    
    def _on_logcat_error(self, error_msg):
        """로그캣 에러 처리"""
        QMessageBox.warning(self, "Logcat Error", error_msg)
        self._stop_logcat()
    
    def load_logcat_file(self, file_path):
        """로그캣 파일 로드 (백그라운드 스레드)"""
        if self.file_load_thread and self.file_load_thread.isRunning():
            QMessageBox.warning(self, "Warning", "파일 로드가 이미 진행 중입니다.")
            return
        
        # 임시 저장 리스트 초기화
        self.pending_file_logs.clear()
        
        # 상태바에 로드 시작 메시지 표시
        self.status_message.emit("파일 로드 중...")
        
        # 파일 로드 스레드 시작
        self.file_load_thread = FileLoadThread(file_path, self.log_parser)
        self.file_load_thread.log_batch_parsed.connect(self._on_file_log_batch_parsed)
        self.file_load_thread.progress_updated.connect(self._on_file_load_progress)
        self.file_load_thread.load_complete.connect(self._on_file_load_complete)
        self.file_load_thread.load_error.connect(self._on_file_load_error)
        self.file_load_thread.start()
    
    def _on_file_log_batch_parsed(self, log_batch):
        """파일에서 파싱된 로그 배치 수신 (임시 저장 + 버퍼/에러감지만, 모델 추가는 준비 스레드 완료 후)"""
        if not log_batch:
            return
        
        self.pending_file_logs.extend(log_batch)
        # 배치 단위로 버퍼/에러 감지 (완료 시 185만 루프 제거)
        for log_tuple in log_batch:
            timestamp, level, display, tag, message = log_tuple
            parsed_dict = {
                'timestamp': timestamp, 'level': level, 'pid': '-', 'tid': '-',
                'tag': tag, 'message': message, 'display': display,
            }
            self.log_buffer.add(parsed_dict)
            self.error_detector.detect(parsed_dict)
    
    def _on_file_load_progress(self, progress, current_line, total_lines):
        """파일 로드 진행 상황 업데이트 (상태바에 표시)"""
        print(f"[LogTable] 파일 로드 진행 상황 업데이트 - 진행률: {progress}%, 현재 줄: {current_line:,} / 전체 줄: {total_lines:,}")
        self.status_message.emit(f"파일 로드 중... {progress}% ({current_line:,} / {total_lines:,} 줄)")
    
    def _on_file_load_complete(self, total_lines):
        """파일 로드 완료 - 워커에서 필터 계산 후 메인에서 set_prepared_data만 호출 (UI 블로킹 방지)"""
        if not self.pending_file_logs:
            self.status_message.emit("로드 완료: 0개 로그")
            return
        
        self.status_message.emit(f"필터 적용 중... ({len(self.pending_file_logs):,}개)")
        logs_copy = list(self.pending_file_logs)
        filters = self.log_model.get_filters()
        self._prepare_model_thread = PrepareModelThread(logs_copy, filters)
        self._prepare_model_thread.prepared_data.connect(self._on_prepared_data)
        self._prepare_model_thread.start()

    def _on_prepared_data(self, all_logs, filtered_indices, matched_filters):
        """워커에서 필터 계산 완료 → 메인에서 모델만 갱신 (짧은 블로킹)"""
        self.log_model.set_prepared_data(all_logs, filtered_indices, matched_filters)
        self.pending_file_logs.clear()
        self._sync_filters_to_model()
        total_count = self.log_model.get_total_count()
        filtered_count = self.log_model.get_filtered_count()
        self.status_message.emit(f"로드 완료: {total_count:,}개 로그 (표시: {filtered_count:,}개)")
    
    def _on_file_load_error(self, error_msg):
        """파일 로드 에러"""
        # 임시 리스트 초기화
        self.pending_file_logs.clear()
        self.status_message.emit(f"로드 실패: {error_msg}")
        QMessageBox.critical(self, "Error", f"파일 로드 실패: {error_msg}")
    
    def _apply_filter(self):
        """필터 적용 (모델에 위임)"""
        self._sync_filters_to_model()
    
    def save_logs_to_file(self, file_path):
        """로그를 파일로 저장"""
        try:
            all_logs = self.log_model.get_all_logs()
            pid_pattern = re.compile(r'pid[=:](\d+)', re.IGNORECASE)
            tid_pattern = re.compile(r'tid[=:](\d+)', re.IGNORECASE)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for log_data in all_logs:
                    time_val, level, display, tag, message = log_data
                    pid_match = pid_pattern.search(message)
                    tid_match = tid_pattern.search(message)
                    pid = pid_match.group(1) if pid_match else "-"
                    tid = tid_match.group(1) if tid_match else "-"
                    log_line = f"{time_val}  {level}  {pid}  {tid}  {tag}: {message}\n"
                    f.write(log_line)
            
            QMessageBox.information(self, "Success", f"Saved {len(all_logs)} log entries to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save logs: {str(e)}")
    
    def clear_all_logs(self):
        """모든 로그 초기화"""
        self.pending_logs.clear()
        self.log_buffer.clear()
        self.update_timer.stop()
        self.log_model.clear()
        self.status_message.emit("준비")
    
    def get_recent_logs(self, max_count: int = 100) -> list:
        """
        최근 로그를 구조화된 딕셔너리 리스트로 반환
        
        Args:
            max_count: 반환할 최대 로그 개수
            
        Returns:
            로그 딕셔너리 리스트 [{'timestamp': ..., 'level': ..., 'tag': ..., 'message': ..., 'display': ...}, ...]
        """
        recent_logs = []
        all_logs = self.log_model.get_all_logs()
        
        # 최근 로그부터 가져오기
        logs_to_process = all_logs[-max_count:] if len(all_logs) > max_count else all_logs
        
        for log_data in logs_to_process:
            if log_data and len(log_data) >= 5:
                timestamp, level, display, tag, message = log_data
                recent_logs.append({
                    'timestamp': timestamp,
                    'level': level,
                    'display': display,
                    'tag': tag,
                    'message': message
                })
        
        return recent_logs
    
    @property
    def all_logs(self):
        """하위 호환성을 위한 all_logs 프로퍼티"""
        return self.log_model.get_all_logs()
