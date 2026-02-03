"""
로그 테이블 모델 (QAbstractTableModel 기반 가상화)

QTableWidget 대신 QTableView + QAbstractTableModel을 사용하여:
- 화면에 보이는 행만 렌더링 (가상화)
- QTableWidgetItem 객체 생성 없이 데이터 직접 반환
- 메모리 사용량 대폭 감소
- UI 블로킹 없음
"""
import re
from typing import Any, List, Dict, Optional, Tuple
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor, QFont


def compute_filtered_indices_and_matches(
    logs: List[Tuple[str, str, str, str, str]],
    filters: List[Dict],
) -> Tuple[List[int], List[Optional[Dict]]]:
    """
    워커 스레드에서 호출 가능. 필터 적용 결과 (filtered_indices, matched_filters) 반환.
    메인 스레드 블로킹 없이 대량 로그 필터링용.
    """
    if not logs:
        return [], []
    pid_pattern = re.compile(r'pid[=:](\d+)', re.IGNORECASE)
    tid_pattern = re.compile(r'tid[=:](\d+)', re.IGNORECASE)
    regex_cache: Dict[Tuple[str, int], re.Pattern] = {}

    def get_regex(pattern: str, flags: int = 0) -> Optional[re.Pattern]:
        key = (pattern, flags)
        if key not in regex_cache:
            try:
                regex_cache[key] = re.compile(pattern, flags)
            except Exception:
                return None
        return regex_cache[key]

    def match_filter(f: Dict, log_data: Tuple[str, str, str, str, str]) -> bool:
        _, level, _, tag, message = log_data
        fields = f.get('fields', {})
        if fields.get('level') and level.upper() != fields['level'].upper():
            return False
        if fields.get('pid'):
            m = pid_pattern.search(message)
            if (m.group(1) if m else '-') != fields['pid']:
                return False
        if fields.get('tid'):
            m = tid_pattern.search(message)
            if (m.group(1) if m else '-') != fields['tid']:
                return False
        if fields.get('tag'):
            tag_val = fields['tag']
            if fields.get('tag_case_sensitive', False):
                if tag_val not in tag:
                    return False
            elif tag_val.lower() not in tag.lower():
                return False
        if fields.get('keyword'):
            kw = fields['keyword']
            if fields.get('keyword_regex', False):
                rx = get_regex(kw, 0 if fields.get('keyword_case_sensitive', False) else re.IGNORECASE)
                if not rx or not rx.search(message):
                    return False
            else:
                if fields.get('keyword_case_sensitive', False):
                    if kw not in message:
                        return False
                elif kw.lower() not in message.lower():
                    return False
        return True

    def evaluate_log(log_data: Tuple[str, str, str, str, str]) -> Optional[Dict]:
        if not filters:
            return None
        show_filters = [f for f in filters if f.get('enabled', True) and f.get('type', 'Show') == 'Show']
        ignore_filters = [f for f in filters if f.get('enabled', True) and f.get('type', 'Show') == 'Ignore']
        for f in ignore_filters:
            if match_filter(f, log_data):
                return False
        if show_filters:
            for f in show_filters:
                if match_filter(f, log_data):
                    return f
            return False
        return None

    filtered_indices: List[int] = []
    matched_filters: List[Optional[Dict]] = []
    for i, log_data in enumerate(logs):
        matched = evaluate_log(log_data)
        if matched is not False:
            filtered_indices.append(i)
            matched_filters.append(matched)
    return filtered_indices, matched_filters


class LogTableModel(QAbstractTableModel):
    """
    로그 데이터를 위한 가상화 테이블 모델
    
    데이터는 내부 리스트로 관리하고, 뷰가 요청할 때만 해당 셀 데이터를 반환.
    100만 개 로그여도 화면에 보이는 50~100개 행만 실제로 렌더링됨.
    """
    
    # 컬럼 정의
    COLUMNS = ["Time", "L", "PID", "TID", "Display", "Tag", "Message"]
    COLUMN_COUNT = len(COLUMNS)
    
    # 컬럼 인덱스
    COL_TIME = 0
    COL_LEVEL = 1
    COL_PID = 2
    COL_TID = 3
    COL_DISPLAY = 4
    COL_TAG = 5
    COL_MESSAGE = 6
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 모든 로그 데이터 (튜플: timestamp, level, display, tag, message)
        self._all_logs: List[Tuple[str, str, str, str, str]] = []
        
        # 필터링된 로그 인덱스 (all_logs의 인덱스를 저장)
        self._filtered_indices: List[int] = []
        
        # 필터링된 로그에 매칭된 필터 정보 (색상용)
        self._matched_filters: List[Optional[Dict]] = []
        
        # 필터 목록
        self._filters: List[Dict] = []
        
        # 정규식 캐시
        self._regex_cache: Dict[Tuple[str, int], re.Pattern] = {}
        
        # PID/TID 추출용 정규식 (미리 컴파일)
        self._pid_pattern = re.compile(r'pid[=:](\d+)', re.IGNORECASE)
        self._tid_pattern = re.compile(r'tid[=:](\d+)', re.IGNORECASE)
        
        # 폰트 캐시
        self._default_font = QFont("Consolas", 9)
        self._bold_font = QFont("Consolas", 9, QFont.Weight.Bold)
        
        # 레벨별 색상
        self._level_colors = {
            'E': (QColor(255, 100, 100), QColor(50, 20, 20)),  # Error
            'W': (QColor(255, 200, 100), QColor(50, 40, 20)),  # Warning
            'I': (QColor(150, 200, 255), None),  # Info
            'D': (QColor(150, 150, 150), None),  # Debug
            'V': (QColor(200, 200, 200), None),  # Verbose
            '-': (QColor(150, 150, 150), None),  # Unknown
        }
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """필터링된 로그 개수 반환"""
        if parent.isValid():
            return 0
        return len(self._filtered_indices)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """컬럼 개수 반환"""
        if parent.isValid():
            return 0
        return self.COLUMN_COUNT
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """
        셀 데이터 반환 (가상화의 핵심)
        
        뷰가 화면에 표시할 셀을 요청할 때만 호출됨.
        100만 개 로그여도 화면에 보이는 셀만 이 메서드가 호출됨.
        """
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row < 0 or row >= len(self._filtered_indices):
            return None
        
        # 원본 데이터 인덱스
        original_idx = self._filtered_indices[row]
        log_data = self._all_logs[original_idx]
        timestamp, level, display, tag, message = log_data
        
        # 매칭된 필터 (색상용)
        matched_filter = self._matched_filters[row] if row < len(self._matched_filters) else None
        
        if role == Qt.ItemDataRole.DisplayRole:
            # 실제 표시 데이터
            if col == self.COL_TIME:
                return timestamp
            elif col == self.COL_LEVEL:
                return level
            elif col == self.COL_PID:
                match = self._pid_pattern.search(message)
                return match.group(1) if match else "-"
            elif col == self.COL_TID:
                match = self._tid_pattern.search(message)
                return match.group(1) if match else "-"
            elif col == self.COL_DISPLAY:
                return display
            elif col == self.COL_TAG:
                return tag
            elif col == self.COL_MESSAGE:
                return message
        
        elif role == Qt.ItemDataRole.FontRole:
            # 폰트 설정
            if col == self.COL_LEVEL:
                return self._bold_font
            return self._default_font
        
        elif role == Qt.ItemDataRole.ForegroundRole:
            # 전경색 (텍스트 색상)
            if col == self.COL_LEVEL:
                level_upper = level.upper() if level else '-'
                level_key = level_upper[0] if level_upper else '-'
                colors = self._level_colors.get(level_key, self._level_colors['-'])
                return colors[0]
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            # 배경색
            # 필터 매칭된 경우 필터 색상 적용
            if matched_filter and matched_filter.get('color'):
                try:
                    bg_color = QColor(matched_filter['color'])
                    bg_color.setAlpha(70)
                    return bg_color
                except:
                    pass
            
            # 레벨 배경색 (Error, Warning)
            if col == self.COL_LEVEL:
                level_upper = level.upper() if level else '-'
                level_key = level_upper[0] if level_upper else '-'
                colors = self._level_colors.get(level_key, self._level_colors['-'])
                return colors[1]
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # 텍스트 정렬
            if col == self.COL_LEVEL:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """헤더 데이터 반환"""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self.COLUMNS):
                    return self.COLUMNS[section]
        return None
    
    # ========== 데이터 관리 메서드 ==========
    
    def add_logs(self, logs: List[Tuple[str, str, str, str, str]]) -> None:
        """
        로그 배치 추가 (고성능)
        
        Args:
            logs: 로그 튜플 리스트 [(timestamp, level, display, tag, message), ...]
        """
        if not logs:
            return
        
        start_idx = len(self._all_logs)
        self._all_logs.extend(logs)
        
        # 새 로그에 대해 필터링 적용
        new_filtered = []
        new_matched = []
        
        for i, log_data in enumerate(logs):
            original_idx = start_idx + i
            matched_filter = self._evaluate_log(log_data)
            
            if matched_filter is not False:
                new_filtered.append(original_idx)
                new_matched.append(matched_filter)
        
        if new_filtered:
            # 모델 업데이트 알림
            first_new_row = len(self._filtered_indices)
            last_new_row = first_new_row + len(new_filtered) - 1
            
            self.beginInsertRows(QModelIndex(), first_new_row, last_new_row)
            self._filtered_indices.extend(new_filtered)
            self._matched_filters.extend(new_matched)
            self.endInsertRows()
    
    def add_log(self, log_data: Tuple[str, str, str, str, str]) -> None:
        """단일 로그 추가"""
        self.add_logs([log_data])
    
    def set_filters(self, filters: List[Dict]) -> None:
        """
        필터 설정 및 재적용
        
        Args:
            filters: 필터 딕셔너리 리스트
        """
        self._filters = filters
        self._reapply_filters()
    
    def _reapply_filters(self) -> None:
        """모든 로그에 필터 재적용"""
        self.beginResetModel()
        
        self._filtered_indices.clear()
        self._matched_filters.clear()
        
        for idx, log_data in enumerate(self._all_logs):
            matched_filter = self._evaluate_log(log_data)
            if matched_filter is not False:
                self._filtered_indices.append(idx)
                self._matched_filters.append(matched_filter)
        
        self.endResetModel()
    
    def _evaluate_log(self, log_data: Tuple[str, str, str, str, str]) -> Optional[Dict]:
        """
        로그가 필터를 통과하는지 평가
        
        Returns:
            - False: 필터에 의해 제외됨
            - None: 필터 없이 통과
            - Dict: 매칭된 Show 필터 (색상 적용용)
        """
        if not self._filters:
            return None
        
        # 활성화된 필터 분류
        show_filters = [f for f in self._filters if f.get('enabled', True) and f.get('type', 'Show') == 'Show']
        ignore_filters = [f for f in self._filters if f.get('enabled', True) and f.get('type', 'Show') == 'Ignore']
        
        # Ignore 필터 체크 (하나라도 매치하면 제외)
        for f in ignore_filters:
            if self._match_filter(f, log_data):
                return False
        
        # Show 필터 체크
        if show_filters:
            for f in show_filters:
                if self._match_filter(f, log_data):
                    return f
            return False  # Show 필터가 있는데 매치 안 됨
        
        return None  # 필터 없이 통과
    
    def _match_filter(self, filter_data: Dict, log_data: Tuple[str, str, str, str, str]) -> bool:
        """단일 필터 매칭 평가"""
        timestamp, level, display, tag, message = log_data
        fields = filter_data.get('fields', {})
        
        # Level
        if fields.get('level'):
            if level.upper() != fields['level'].upper():
                return False
        
        # PID
        if fields.get('pid'):
            match = self._pid_pattern.search(message)
            pid_value = match.group(1) if match else "-"
            if pid_value != fields['pid']:
                return False
        
        # TID
        if fields.get('tid'):
            match = self._tid_pattern.search(message)
            tid_value = match.group(1) if match else "-"
            if tid_value != fields['tid']:
                return False
        
        # TAG
        if fields.get('tag'):
            tag_value = fields['tag']
            case_sensitive = fields.get('tag_case_sensitive', False)
            if case_sensitive:
                if tag_value not in tag:
                    return False
            else:
                if tag_value.lower() not in tag.lower():
                    return False
        
        # Keyword (Message)
        if fields.get('keyword'):
            keyword = fields['keyword']
            is_regex = fields.get('keyword_regex', False)
            case_sensitive = fields.get('keyword_case_sensitive', False)
            
            if is_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                regex = self._get_compiled_regex(keyword, flags)
                if regex:
                    if not regex.search(message):
                        return False
                else:
                    return False
            else:
                if case_sensitive:
                    if keyword not in message:
                        return False
                else:
                    if keyword.lower() not in message.lower():
                        return False
        
        return True
    
    def _get_compiled_regex(self, pattern: str, flags: int = 0) -> Optional[re.Pattern]:
        """컴파일된 정규식 가져오기 (캐싱)"""
        cache_key = (pattern, flags)
        if cache_key not in self._regex_cache:
            try:
                self._regex_cache[cache_key] = re.compile(pattern, flags)
            except:
                return None
        return self._regex_cache[cache_key]
    
    def clear(self) -> None:
        """모든 데이터 초기화"""
        self.beginResetModel()
        self._all_logs.clear()
        self._filtered_indices.clear()
        self._matched_filters.clear()
        self._regex_cache.clear()
        self.endResetModel()
    
    def get_all_logs(self) -> List[Tuple[str, str, str, str, str]]:
        """모든 로그 데이터 반환"""
        return self._all_logs

    def get_filters(self) -> List[Dict]:
        """현재 필터 목록 (워커에서 필터 계산 시 사용)"""
        return self._filters

    def set_prepared_data(
        self,
        all_logs: List[Tuple[str, str, str, str, str]],
        filtered_indices: List[int],
        matched_filters: List[Optional[Dict]],
    ) -> None:
        """
        워커에서 미리 계산한 데이터로 한 번에 설정. 메인 스레드에서만 호출.
        """
        self.beginResetModel()
        self._all_logs = all_logs
        self._filtered_indices = filtered_indices
        self._matched_filters = matched_filters
        self.endResetModel()

    def get_filtered_count(self) -> int:
        """필터링된 로그 개수"""
        return len(self._filtered_indices)
    
    def get_total_count(self) -> int:
        """전체 로그 개수"""
        return len(self._all_logs)
    
    def get_log_at(self, row: int) -> Optional[Tuple[str, str, str, str, str]]:
        """특정 행의 로그 데이터 반환"""
        if 0 <= row < len(self._filtered_indices):
            idx = self._filtered_indices[row]
            return self._all_logs[idx]
        return None
