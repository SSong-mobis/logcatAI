"""Agent 설정 다이얼로그"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QLineEdit, QTextEdit,
                             QCheckBox, QSpinBox, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import json
import os
from pathlib import Path


class AgentSettingsDialog(QDialog):
    """Agent (팀원) 설정 다이얼로그"""
    
    def __init__(self, parent=None, agent_name: str = ""):
        super().__init__(parent)
        self.agent_name = agent_name
        self.setWindowTitle(f"Agent 설정: {agent_name}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.config_path = self._get_config_path()
        self.settings = self._load_settings()
        
        self._setup_ui()
    
    def _get_config_path(self):
        """설정 파일 경로 가져오기"""
        # ~/.config/opencode/agents/{agent_name}.json 또는 .opencode/agents/{agent_name}.json
        home = Path.home()
        config_dir = home / ".config" / "opencode" / "agents"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Agent 이름에서 파일명 생성 (특수문자 제거)
        safe_name = "".join(c for c in self.agent_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        # 이모지 제거
        safe_name = ''.join(c for c in safe_name if ord(c) < 128)
        
        return config_dir / f"{safe_name}.json"
    
    def _load_settings(self):
        """설정 파일 로드"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_settings(self):
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}")
            return False
    
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Agent 정보
        info_group = QGroupBox("Agent 정보")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)
        
        name_label = QLabel(f"팀원 이름: {self.agent_name}")
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        info_layout.addWidget(name_label)
        
        role_label = QLabel("역할: Agent Team의 멤버로 특정 작업을 담당합니다.")
        role_label.setStyleSheet("color: #888888; font-size: 9pt;")
        info_layout.addWidget(role_label)
        
        path_label = QLabel(f"설정 파일: {self.config_path}")
        path_label.setStyleSheet("color: #888888; font-size: 9pt;")
        info_layout.addWidget(path_label)
        
        layout.addWidget(info_group)
        
        # 일반 설정
        general_group = QGroupBox("일반 설정")
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(8)
        
        # 활성화 여부
        self.enabled_cb = QCheckBox("Agent 활성화")
        self.enabled_cb.setChecked(self.settings.get('enabled', True))
        self.enabled_cb.setToolTip("이 Agent가 작업에 참여할지 여부를 설정합니다.")
        general_layout.addWidget(self.enabled_cb)
        
        # 우선순위
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("작업 우선순위:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 100)
        self.priority_spin.setValue(self.settings.get('priority', 50))
        self.priority_spin.setToolTip("숫자가 클수록 높은 우선순위 (0-100)\n여러 Agent가 동시에 작업할 때 우선순위가 높은 Agent가 먼저 실행됩니다.")
        priority_layout.addWidget(self.priority_spin)
        priority_layout.addStretch()
        general_layout.addLayout(priority_layout)
        
        layout.addWidget(general_group)
        
        # 고급 설정
        advanced_group = QGroupBox("고급 설정")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setSpacing(8)
        
        # 설정 JSON 편집
        json_label = QLabel("설정 JSON (고급 사용자용):")
        advanced_layout.addWidget(json_label)
        
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{\n  "key": "value"\n}')
        self.json_edit.setFont(QFont("Consolas", 9))
        
        # 현재 설정을 JSON으로 표시
        try:
            json_text = json.dumps(self.settings, indent=2, ensure_ascii=False)
            self.json_edit.setPlainText(json_text)
        except Exception:
            self.json_edit.setPlainText("{}")
        
        advanced_layout.addWidget(self.json_edit)
        
        layout.addWidget(advanced_group)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 저장")
        save_btn.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _on_save_clicked(self):
        """저장 버튼 클릭"""
        # 일반 설정 저장
        self.settings['enabled'] = self.enabled_cb.isChecked()
        self.settings['priority'] = self.priority_spin.value()
        
        # JSON 편집기에서 설정 가져오기
        try:
            json_text = self.json_edit.toPlainText().strip()
            if json_text:
                json_settings = json.loads(json_text)
                # JSON 설정을 병합 (일반 설정 우선)
                self.settings.update(json_settings)
                # 일반 설정이 덮어씌워지지 않도록 다시 설정
                self.settings['enabled'] = self.enabled_cb.isChecked()
                self.settings['priority'] = self.priority_spin.value()
        except json.JSONDecodeError as e:
            QMessageBox.warning(
                self, 
                "JSON 오류", 
                f"JSON 형식이 올바르지 않습니다:\n{str(e)}\n\n일반 설정만 저장됩니다."
            )
        
        # 설정 저장
        if self._save_settings():
            QMessageBox.information(self, "저장 완료", "Agent 설정이 저장되었습니다.")
            self.accept()
