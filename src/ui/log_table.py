import re
import subprocess
import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QGroupBox, QPushButton, QCheckBox, QFileDialog, QMessageBox, QMenu,
    QColorDialog, QRadioButton, QLineEdit, QComboBox, QLabel, QGridLayout, QDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent, QAction

# pylogcatparser 라이브러리 import 시도 (선택적)
PARSER_AVAILABLE = False
LogCatParser = None
try:
    from logcatparser.logCatParser import LogCatParser
    PARSER_AVAILABLE = True
except ImportError:
    print("logcatparser 라이브러리를 찾을 수 없습니다. 로그 파싱 기능을 사용할 수 없습니다.")
    PARSER_AVAILABLE = False
    LogCatParser = None


class LogcatThread(QThread):
    """백그라운드에서 logcat을 수집하는 스레드"""
    log_received = pyqtSignal(str)  # 로그 라인을 전달하는 시그널
    error_occurred = pyqtSignal(str)  # 에러 메시지를 전달하는 시그널
    
    def __init__(self, parent=None, logcat_filter='*:V', buffer='main', format_type='threadtime'):
        super().__init__(parent)
        self.is_running = False
        self.is_paused = False
        self.process = None
        self.logcat_filter = logcat_filter
        self.buffer = buffer
        self.format_type = format_type
    
    def _find_adb_path(self):
        """adb.exe 경로 찾기"""
        # PATH에서 찾기
        adb_path = 'adb'
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=2)
            if result.returncode == 0:
                return adb_path
        except:
            pass
        
        # Windows 환경 변수에서 찾기
        android_home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
        if android_home:
            adb_path = os.path.join(android_home, 'platform-tools', 'adb.exe')
            if os.path.exists(adb_path):
                return adb_path
        
        # 일반적인 Android Studio 경로
        common_paths = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Android', 'Sdk', 'platform-tools', 'adb.exe'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Android', 'Sdk', 'platform-tools', 'adb.exe'),
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return 'adb'  # 기본값
    
    def run(self):
        """logcat 실행"""
        adb_path = self._find_adb_path()
        self.is_running = True
        
        try:
            # logcat 명령어 구성
            logcat_cmd = [adb_path, 'logcat']
            
            # 버퍼 옵션 (-b)
            if self.buffer and self.buffer != 'main':
                logcat_cmd.extend(['-b', self.buffer])
            
            # 출력 형식 옵션 (-v)
            if self.format_type:
                logcat_cmd.extend(['-v', self.format_type])
            else:
                logcat_cmd.extend(['-v', 'time'])
            
            # 필터 표현식 추가
            if self.logcat_filter and self.logcat_filter.strip():
                filter_parts = self.logcat_filter.strip().split()
                logcat_cmd.extend(filter_parts)
            else:
                logcat_cmd.append('*:V')
            
            # encoding='utf-8', errors='ignore'로 한글 및 특수문자 처리
            self.process = subprocess.Popen(
                logcat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1,
                universal_newlines=True
            )
            
            # 로그 라인 읽기
            for line in iter(self.process.stdout.readline, ''):
                if not self.is_running:
                    break
                
                if self.is_paused:
                    continue
                
                line = line.strip()
                if line:
                    self.log_received.emit(line)
            
        except Exception as e:
            self.error_occurred.emit(f"ADB Error: {str(e)}")
        finally:
            if self.process:
                self.process.terminate()
                self.process.wait()
    
    def stop(self):
        """logcat 중지"""
        self.is_running = False
        if self.process:
            self.process.terminate()
    
    def pause(self):
        """일시정지"""
        self.is_paused = True
    
    def resume(self):
        """재개"""
        self.is_paused = False


class FilterDialog(QDialog):
    """필터 설정 다이얼로그"""
    def __init__(self, parent=None, filter_data=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Configuration")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Type (Show/Ignore) - Radio buttons
        type_group = QGroupBox("Type")
        type_layout = QHBoxLayout()
        type_layout.setContentsMargins(5, 5, 5, 5)  # 여백 최소화
        type_layout.setSpacing(10)  # 간격 조정
        self.show_radio = QRadioButton("Show")
        self.ignore_radio = QRadioButton("Ignore")
        self.show_radio.setChecked(True)
        type_layout.addWidget(self.show_radio)
        type_layout.addWidget(self.ignore_radio)
        type_layout.addStretch()  # 오른쪽 여백 제거
        type_group.setLayout(type_layout)
        type_group.setMaximumHeight(60)  # 최대 높이 제한
        layout.addWidget(type_group)
        
        # Color selection
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)  # 여백 최소화
        color_layout.setSpacing(5)  # 간격 조정
        color_layout.addWidget(QLabel("Background Color:"))
        self.color_btn = QPushButton("Choose Color")
        self.color_btn.clicked.connect(self._choose_color)
        self.selected_color = None
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Fields
        fields_group = QGroupBox("Filter Fields")
        fields_layout = QGridLayout()
        fields_layout.setContentsMargins(5, 5, 5, 5)  # 여백 최소화
        fields_layout.setSpacing(5)  # 간격 조정
        
        # Level (ComboBox with predefined options)
        fields_layout.addWidget(QLabel("Level:"), 0, 0)
        self.level_combo = QComboBox()
        self.level_combo.setEditable(True)
        self.level_combo.addItems(["", "V", "D", "I", "W", "E", "F", "A"])
        fields_layout.addWidget(self.level_combo, 0, 1)
        
        # PID
        fields_layout.addWidget(QLabel("PID:"), 1, 0)
        self.pid_edit = QLineEdit()
        fields_layout.addWidget(self.pid_edit, 1, 1)
        
        # TID
        fields_layout.addWidget(QLabel("TID:"), 2, 0)
        self.tid_edit = QLineEdit()
        fields_layout.addWidget(self.tid_edit, 2, 1)
        
        # TAG
        fields_layout.addWidget(QLabel("TAG:"), 3, 0)
        tag_layout = QHBoxLayout()
        self.tag_edit = QLineEdit()
        tag_layout.addWidget(self.tag_edit)
        self.tag_case_cb = QCheckBox("Aa")
        self.tag_case_cb.setToolTip("Case Sensitive")
        tag_layout.addWidget(self.tag_case_cb)
        fields_layout.addLayout(tag_layout, 3, 1)
        
        # Keyword
        fields_layout.addWidget(QLabel("Keyword:"), 4, 0)
        keyword_layout = QHBoxLayout()
        self.keyword_edit = QLineEdit()
        keyword_layout.addWidget(self.keyword_edit)
        self.keyword_regex_cb = QCheckBox("Regex")
        self.keyword_case_cb = QCheckBox("Aa")
        self.keyword_case_cb.setToolTip("Case Sensitive")
        keyword_layout.addWidget(self.keyword_regex_cb)
        keyword_layout.addWidget(self.keyword_case_cb)
        fields_layout.addLayout(keyword_layout, 4, 1)
        
        fields_group.setLayout(fields_layout)
        layout.addWidget(fields_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # 기존 필터 데이터로 채우기
        if filter_data:
            self._load_filter_data(filter_data)
    
    def _choose_color(self):
        """색상 선택"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.selected_color};")
    
    def _load_filter_data(self, filter_data):
        """필터 데이터 로드"""
        if filter_data.get('type') == 'Ignore':
            self.ignore_radio.setChecked(True)
        else:
            self.show_radio.setChecked(True)
        
        if filter_data.get('color'):
            self.selected_color = filter_data['color']
            self.color_btn.setStyleSheet(f"background-color: {self.selected_color};")
        
        fields = filter_data.get('fields', {})
        if fields.get('level'):
            self.level_combo.setCurrentText(fields['level'])
        if fields.get('pid'):
            self.pid_edit.setText(fields['pid'])
        if fields.get('tid'):
            self.tid_edit.setText(fields['tid'])
        if fields.get('tag'):
            self.tag_edit.setText(fields['tag'])
            self.tag_case_cb.setChecked(fields.get('tag_case_sensitive', False))
        if fields.get('keyword'):
            self.keyword_edit.setText(fields['keyword'])
            self.keyword_regex_cb.setChecked(fields.get('keyword_regex', False))
            self.keyword_case_cb.setChecked(fields.get('keyword_case_sensitive', False))
    
    def get_filter_data(self):
        """필터 데이터 반환"""
        return {
            'type': 'Ignore' if self.ignore_radio.isChecked() else 'Show',
            'color': self.selected_color,
            'fields': {
                'level': self.level_combo.currentText().strip(),
                'pid': self.pid_edit.text().strip(),
                'tid': self.tid_edit.text().strip(),
                'tag': self.tag_edit.text().strip(),
                'tag_case_sensitive': self.tag_case_cb.isChecked(),
                'keyword': self.keyword_edit.text().strip(),
                'keyword_regex': self.keyword_regex_cb.isChecked(),
                'keyword_case_sensitive': self.keyword_case_cb.isChecked(),
            }
        }
    
    def accept(self):
        """확인"""
        super().accept()
    
    def reject(self):
        """취소"""
        super().reject()


class LogTable(QWidget):
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
        
        # Log Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Time", "L", "PID", "TID", "Display", "Tag", "Message"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setFont(QFont("Consolas", 10))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setDragDropMode(QTableWidget.DragDropMode.NoDragDrop)
        self.table.setAutoScroll(False)
        
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 40)  # Level 컬럼 너비 줄임
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 150)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        
        # Drag and drop
        self.setAcceptDrops(True)
        
        layout.addWidget(self.table)
    
    def _setup_data(self):
        self.all_logs = []
        self.active_filters = []
        self.logcat_thread = None
        self.pending_logs = []
        self.batch_size = 50
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._process_pending_logs)
        self.update_timer.setInterval(50)
        self.log_collection_start_time = None
    
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
        """로그 라인 파싱"""
        line = line.strip()
        if not line:
            return None
        
        # pylogcatparser 라이브러리 사용 시도 (threadtime 형식)
        if PARSER_AVAILABLE and LogCatParser:
            try:
                parser = LogCatParser("threadtime")
                
                # 라이브러리의 parse 메서드 사용 시도
                try:
                    # LogCatParser는 일반적으로 parse_line 또는 parse 메서드를 제공
                    if hasattr(parser, 'parse_line'):
                        parsed_obj = parser.parse_line(line)
                    elif hasattr(parser, 'parse'):
                        parsed_obj = parser.parse(line)
                    else:
                        # build_log_line을 사용하려면 정규식으로 먼저 매칭 필요
                        # threadtime 형식: mm-dd HH:MM:SS.mmm  PID  TID  Level  Tag: Message
                        threadtime_regex = r'^(\d{2}\-\d{2})\s+(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+(\d+|\-)\s+([VDIWEAF]|\-)\s+([^:]+):\s+(.*)$'
                        match = re.search(threadtime_regex, line)
                        if match:
                            groups = match.groups()
                            parsed_obj = parser.build_log_line(groups)
                        else:
                            raise ValueError("No match")
                    
                    # 파싱된 결과에서 필요한 정보 추출
                    if isinstance(parsed_obj, dict):
                        date = parsed_obj.get('date', '')
                        time_str = parsed_obj.get('time', '')
                        date_time = f"{date} {time_str}".strip() if date and time_str else ''
                        
                        # level 변환
                        level_str = parsed_obj.get('level', '')
                        level_map = {"verbose": "V", "debug": "D", "info": "I", "warn": "W", "error": "E", "fatal": "F", "assert": "A"}
                        if level_str in level_map:
                            level = level_map[level_str]
                        elif level_str and level_str[0].upper() in ["V", "D", "I", "W", "E", "F", "A"]:
                            level = level_str[0].upper()
                        else:
                            level = "-"
                        
                        tag = parsed_obj.get('tag', 'Unknown')
                        message = parsed_obj.get('message', '')
                        display = "Main"
                        
                        if date_time:
                            return (date_time, level, display, tag, message)
                    else:
                        raise ValueError("Unexpected parser result type")
                except (AttributeError, ValueError, TypeError) as e:
                    # 라이브러리 파싱 실패 시 fallback 사용
                    pass
            except Exception as e:
                # 라이브러리 사용 실패 시 fallback 사용
                pass
        
        # Fallback: 직접 파싱
        # 시간 패턴 찾기
        time_pattern = r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'
        time_match = re.match(time_pattern, line)
        
        if not time_match:
            return None
        
        date_time = time_match.group(1)
        remaining = line[len(date_time):].strip()
        
        # 형식 1: mm-dd HH:MM:SS.mmm  PID  -  -  Tag: Message (Level 없음)
        threadtime_simple_pattern = r'^(\d+)\s+-\s+-\s+([^:]+):\s+(.*)$'
        threadtime_simple_match = re.match(threadtime_simple_pattern, remaining)
        if threadtime_simple_match:
            pid = threadtime_simple_match.group(1)
            tid = '-'
            tag = threadtime_simple_match.group(2).strip()
            message = threadtime_simple_match.group(3).strip()
            level = "-"  # Level 정보 없음
            display = "Main"
            return (date_time, level, display, tag, message)
        
        # 형식 2: mm-dd HH:MM:SS.mmm  Level  -  -  PID  TID  Level  Tag: Message
        threadtime_complex_pattern = r'^([VDIWEAF])\s+-\s+-\s+(\d+)\s+(\d+)\s+([VDIWEAF])\s+([^:]+):\s*(.*)$'
        threadtime_complex_match = re.match(threadtime_complex_pattern, remaining)
        if threadtime_complex_match:
            level = threadtime_complex_match.group(4)
            pid = threadtime_complex_match.group(2)
            tid = threadtime_complex_match.group(3)
            tag = threadtime_complex_match.group(5).strip()
            message = threadtime_complex_match.group(6).strip()
            display = "Main"
            return (date_time, level, display, tag, message)
        
        # 형식 3: Level/Tag(  PID  TID  Message
        level_tag_pattern = r'^([DIWEFV])/([^(]+)\(\s*([^)]*?)\s*\)\s+(.*)$'
        level_tag_match = re.match(level_tag_pattern, remaining)
        if level_tag_match:
            level = level_tag_match.group(1)
            tag = level_tag_match.group(2).strip()
            pid_in_paren = level_tag_match.group(3).strip()
            rest = level_tag_match.group(4).strip()
            
            pid_tid_parts = rest.split(None, 2)
            if len(pid_tid_parts) >= 3:
                pid = pid_tid_parts[0] if pid_tid_parts[0] != '-' else (pid_in_paren if pid_in_paren else '-')
                tid = pid_tid_parts[1] if pid_tid_parts[1] != '-' else '-'
                message = pid_tid_parts[2]
            elif len(pid_tid_parts) == 2:
                pid = pid_tid_parts[0] if pid_tid_parts[0] != '-' else (pid_in_paren if pid_in_paren else '-')
                tid = '-'
                message = pid_tid_parts[1]
            else:
                pid = pid_in_paren if pid_in_paren else '-'
                tid = '-'
                message = rest
            
            if pid_in_paren and pid_in_paren != '-':
                pid = pid_in_paren.strip()
            
            display = "Main"
            return (date_time, level, display, tag, message)
        
        # 형식 4: Level PID TID Tag: Message
        # Level은 반드시 V, D, I, W, E, F, A 중 하나여야 함
        parts = remaining.split(None, 4)
        if len(parts) >= 5:
            # Level 검증: V, D, I, W, E, F, A 중 하나인지 확인
            potential_level = parts[0]
            if potential_level in ["V", "D", "I", "W", "E", "F", "A"]:
                level = potential_level
                pid = parts[1]
                tid = parts[2]
                tag_msg = parts[3] + " " + parts[4] if len(parts) > 4 else parts[3]
                
                if ':' in tag_msg:
                    tag, message = tag_msg.split(':', 1)
                    tag = tag.strip()
                    message = message.strip()
                else:
                    tag = "Unknown"
                    message = tag_msg
                
                display = "Main"
                return (date_time, level, display, tag, message)
        
        # 파싱 실패 시 None 반환 (Level이 숫자이거나 형식이 맞지 않음)
        return None
    
    def _on_log_received(self, line):
        """로그 라인 수신"""
        log_data = self._parse_log_line(line)
        if log_data:
            self.all_logs.append(log_data)
            self.pending_logs.append(log_data)
            
            if len(self.pending_logs) >= self.batch_size:
                self._process_pending_logs()
            elif not self.update_timer.isActive():
                self.update_timer.start()
    
    def _process_pending_logs(self):
        """대기 중인 로그 배치 처리"""
        if not self.pending_logs:
            return
        
        # 초기 수집 시 작은 배치
        if self.log_collection_start_time:
            elapsed = time.time() - self.log_collection_start_time
            if elapsed < 3.0:
                current_batch_size = min(20, self.batch_size // 2)
            else:
                current_batch_size = self.batch_size
        else:
            current_batch_size = self.batch_size
        
        logs_to_process = self.pending_logs[:current_batch_size]
        self.pending_logs = self.pending_logs[current_batch_size:]
        
        # 활성화된 필터 가져오기
        enabled_filters = []
        for row in range(self.filter_table.rowCount()):
            checkbox = self.filter_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                filter_index = checkbox.property('filter_index')
                if filter_index is not None and 0 <= filter_index < len(self.active_filters):
                    enabled_filters.append(self.active_filters[filter_index])
        
        show_filters = [f for f in enabled_filters if f.get('type', 'Show') == 'Show']
        ignore_filters = [f for f in enabled_filters if f.get('type', 'Show') == 'Ignore']
        
        rows_to_add = []
        for log_data in logs_to_process:
            if ignore_filters:
                ignore_matches = [self._evaluate_filter(f, log_data) for f in ignore_filters]
                if any(ignore_matches):
                    continue
            
            matched_filter = None
            if show_filters:
                show_matches = [self._evaluate_filter(f, log_data) for f in show_filters]
                if any(show_matches):
                    for f in show_filters:
                        if self._evaluate_filter(f, log_data):
                            matched_filter = f
                            break
                else:
                    continue
            elif not enabled_filters:
                matched_filter = None
            
            rows_to_add.append((log_data, matched_filter))
        
        if rows_to_add:
            self.table.setUpdatesEnabled(False)
            try:
                current_row = self.table.rowCount()
                should_scroll = self.auto_scroll_cb.isChecked() and current_row > 0
                
                self.table.setRowCount(current_row + len(rows_to_add))
                
                for idx, (log_data, matched_filter) in enumerate(rows_to_add):
                    row = current_row + idx
                    self._add_log_row_internal(row, *log_data, matched_filter, set_height=False)
                
                if rows_to_add:
                    for idx in range(len(rows_to_add)):
                        self.table.setRowHeight(current_row + idx, 35)
                
                if should_scroll:
                    self.table.scrollToBottom()
            finally:
                self.table.setUpdatesEnabled(True)
        
        if self.pending_logs:
            if not self.update_timer.isActive():
                self.update_timer.start()
        else:
            self.update_timer.stop()
    
    def _evaluate_filter(self, filter_data, log_data):
        """필터 평가"""
        time_val, level, display, tag, message = log_data
        fields = filter_data.get('fields', {})
        
        # Level
        if fields.get('level'):
            if level.upper() != fields['level'].upper():
                return False
        
        # PID
        if fields.get('pid'):
            pid_match = re.search(r'pid[=:](\d+)', message, re.IGNORECASE)
            pid_value = pid_match.group(1) if pid_match else "-"
            if pid_value != fields['pid']:
                return False
        
        # TID
        if fields.get('tid'):
            tid_match = re.search(r'tid[=:](\d+)', message, re.IGNORECASE)
            tid_value = tid_match.group(1) if tid_match else "-"
            if tid_value != fields['tid']:
                return False
        
        # TAG
        if fields.get('tag'):
            tag_value = fields['tag']
            case_sensitive = fields.get('tag_case_sensitive', False)
            if not case_sensitive:
                if tag_value.lower() not in tag.lower():
                    return False
            else:
                if tag_value not in tag:
                    return False
        
        # Keyword
        if fields.get('keyword'):
            keyword = fields['keyword']
            is_regex = fields.get('keyword_regex', False)
            case_sensitive = fields.get('keyword_case_sensitive', False)
            
            if is_regex:
                try:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    if not re.search(keyword, message, flags):
                        return False
                except:
                    return False
            else:
                if case_sensitive:
                    if keyword not in message:
                        return False
                else:
                    if keyword.lower() not in message.lower():
                        return False
        
        return True
    
    def _add_log_row_internal(self, row, time, level, display, tag, message, matched_filter=None, set_height=True):
        """로그 행 추가 (내부)"""
        bg_color = None
        if matched_filter and matched_filter.get('color'):
            try:
                bg_color = QColor(matched_filter['color'])
                # 투명도 적용 (alpha 값: 0-255, 100 정도면 적당히 투명)
                bg_color.setAlpha(70)  # 배경색이 너무 진하지 않도록 투명도 적용
            except:
                pass
        
        # Time
        time_item = QTableWidgetItem(time)
        time_item.setFont(QFont("Consolas", 9))
        if bg_color:
            time_item.setBackground(bg_color)
        self.table.setItem(row, 0, time_item)
        
        # Level (가운데 정렬)
        level_item = QTableWidgetItem(level)
        level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # 가운데 정렬
        level_item.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self._set_level_color(level_item, level)
        if bg_color:
            current_bg = level_item.background().color()
            if current_bg.alpha() > 0:
                level_item.setBackground(bg_color)
        self.table.setItem(row, 1, level_item)
        
        # PID
        pid_match = re.search(r'pid[=:](\d+)', message, re.IGNORECASE)
        pid_value = pid_match.group(1) if pid_match else "-"
        pid_item = QTableWidgetItem(pid_value)
        pid_item.setFont(QFont("Consolas", 9))
        if bg_color:
            pid_item.setBackground(bg_color)
        self.table.setItem(row, 2, pid_item)
        
        # TID
        tid_match = re.search(r'tid[=:](\d+)', message, re.IGNORECASE)
        tid_value = tid_match.group(1) if tid_match else "-"
        tid_item = QTableWidgetItem(tid_value)
        tid_item.setFont(QFont("Consolas", 9))
        if bg_color:
            tid_item.setBackground(bg_color)
        self.table.setItem(row, 3, tid_item)
        
        # Display
        display_item = QTableWidgetItem(display)
        display_item.setFont(QFont("Consolas", 9))
        if bg_color:
            display_item.setBackground(bg_color)
        self.table.setItem(row, 4, display_item)
        
        # Tag
        tag_item = QTableWidgetItem(tag)
        tag_item.setFont(QFont("Consolas", 9))
        if bg_color:
            tag_item.setBackground(bg_color)
        self.table.setItem(row, 5, tag_item)
        
        # Message
        msg_item = QTableWidgetItem(message)
        msg_item.setFont(QFont("Consolas", 9))
        if bg_color:
            msg_item.setBackground(bg_color)
        self.table.setItem(row, 6, msg_item)
        
        if set_height:
            self.table.setRowHeight(row, 35)
    
    def _set_level_color(self, item, level):
        """레벨 색상 설정"""
        if level == "-" or not level:
            # Level 정보 없음
            item.setForeground(QColor(150, 150, 150))
        elif level == "E" or level == "Error":
            item.setForeground(QColor(255, 100, 100))
            item.setBackground(QColor(50, 20, 20))
        elif level == "W" or level == "Warn":
            item.setForeground(QColor(255, 200, 100))
            item.setBackground(QColor(50, 40, 20))
        elif level == "I" or level == "Info":
            item.setForeground(QColor(150, 200, 255))
        elif level == "D" or level == "Debug":
            item.setForeground(QColor(150, 150, 150))
        else:
            item.setForeground(QColor(200, 200, 200))
    
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
        """로그캣 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    log_data = self._parse_log_line(line)
                    if log_data:
                        self.all_logs.append(log_data)
            
            # 필터 적용하여 표시
            self._apply_filter()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load logcat file: {str(e)}")
    
    def _apply_filter(self):
        """필터 적용"""
        self.table.setRowCount(0)
        
        enabled_filters = []
        for row in range(self.filter_table.rowCount()):
            checkbox = self.filter_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                filter_index = checkbox.property('filter_index')
                if filter_index is not None and 0 <= filter_index < len(self.active_filters):
                    enabled_filters.append(self.active_filters[filter_index])
        
        show_filters = [f for f in enabled_filters if f.get('type', 'Show') == 'Show']
        ignore_filters = [f for f in enabled_filters if f.get('type', 'Show') == 'Ignore']
        
        for log_data in self.all_logs:
            if ignore_filters:
                ignore_matches = [self._evaluate_filter(f, log_data) for f in ignore_filters]
                if any(ignore_matches):
                    continue
            
            matched_filter = None
            if show_filters:
                show_matches = [self._evaluate_filter(f, log_data) for f in show_filters]
                if any(show_matches):
                    for f in show_filters:
                        if self._evaluate_filter(f, log_data):
                            matched_filter = f
                            break
                else:
                    continue
            elif not enabled_filters:
                matched_filter = None
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._add_log_row_internal(row, *log_data, matched_filter)
    
    def save_logs_to_file(self, file_path):
        """로그를 파일로 저장"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for log_data in self.all_logs:
                    time_val, level, display, tag, message = log_data
                    pid_match = re.search(r'pid[=:](\d+)', message, re.IGNORECASE)
                    tid_match = re.search(r'tid[=:](\d+)', message, re.IGNORECASE)
                    pid = pid_match.group(1) if pid_match else "-"
                    tid = tid_match.group(1) if tid_match else "-"
                    log_line = f"{time_val}  {level}  {pid}  {tid}  {tag}: {message}\n"
                    f.write(log_line)
            
            QMessageBox.information(self, "Success", f"Saved {len(self.all_logs)} log entries to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save logs: {str(e)}")
    
    def clear_all_logs(self):
        """모든 로그 초기화"""
        self.all_logs.clear()
        self.pending_logs.clear()
        self.update_timer.stop()
        self.table.setRowCount(0)
        self._apply_filter()
    
    def get_recent_logs(self, max_count: int = 100) -> list:
        """
        최근 로그를 구조화된 딕셔너리 리스트로 반환
        
        Args:
            max_count: 반환할 최대 로그 개수
            
        Returns:
            로그 딕셔너리 리스트 [{'timestamp': ..., 'level': ..., 'tag': ..., 'message': ..., 'display': ...}, ...]
        """
        recent_logs = []
        # 최근 로그부터 가져오기
        logs_to_process = self.all_logs[-max_count:] if len(self.all_logs) > max_count else self.all_logs
        
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
