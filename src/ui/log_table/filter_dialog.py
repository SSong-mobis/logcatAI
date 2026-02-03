"""
필터 설정 다이얼로그
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QPushButton, QLabel, QGridLayout, QComboBox, QLineEdit, QCheckBox,
    QColorDialog
)
from PyQt6.QtGui import QColor


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
