"""설정 다이얼로그"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTabWidget, QWidget, QGroupBox,
                             QLineEdit, QMessageBox, QTextEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils.opencode_installer import OpenCodeInstaller


class PreferencesDialog(QDialog):
    """설정 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.installer = OpenCodeInstaller()
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 탭 위젯
        tabs = QTabWidget()
        
        # OpenCode 설정 탭
        opencode_tab = self._create_opencode_tab()
        tabs.addTab(opencode_tab, "OpenCode")
        
        # 일반 설정 탭 (향후 확장)
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.addWidget(QLabel("일반 설정 (향후 추가 예정)"))
        general_layout.addStretch()
        tabs.addTab(general_tab, "일반")
        
        layout.addWidget(tabs)
        
        # 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("확인")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_opencode_tab(self):
        """OpenCode 설정 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 상태 정보 그룹
        status_group = QGroupBox("OpenCode 상태")
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(8)
        
        # Node.js 상태
        node_layout = QHBoxLayout()
        node_layout.addWidget(QLabel("Node.js:"))
        self.node_status_label = QLabel("확인 중...")
        node_layout.addWidget(self.node_status_label)
        node_layout.addStretch()
        status_layout.addLayout(node_layout)
        
        # npm 상태
        npm_layout = QHBoxLayout()
        npm_layout.addWidget(QLabel("npm:"))
        self.npm_status_label = QLabel("확인 중...")
        npm_layout.addWidget(self.npm_status_label)
        npm_layout.addStretch()
        status_layout.addLayout(npm_layout)
        
        # OpenCode 상태
        opencode_layout = QHBoxLayout()
        opencode_layout.addWidget(QLabel("OpenCode:"))
        self.opencode_status_label = QLabel("확인 중...")
        opencode_layout.addWidget(self.opencode_status_label)
        opencode_layout.addStretch()
        status_layout.addLayout(opencode_layout)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 상태 새로고침")
        refresh_btn.clicked.connect(self._refresh_status)
        status_layout.addWidget(refresh_btn)
        
        layout.addWidget(status_group)
        
        # 설치 그룹
        install_group = QGroupBox("OpenCode 설치")
        install_layout = QVBoxLayout(install_group)
        install_layout.setSpacing(8)
        
        install_info = QLabel(
            "OpenCode CLI를 설치하면 AI 분석 기능을 사용할 수 있습니다.\n"
            "npx를 통해 자동으로 다운로드됩니다."
        )
        install_info.setWordWrap(True)
        install_info.setStyleSheet("color: #888888;")
        install_layout.addWidget(install_info)
        
        self.install_btn = QPushButton("📦 OpenCode 설치")
        self.install_btn.clicked.connect(self._install_opencode)
        install_layout.addWidget(self.install_btn)
        
        layout.addWidget(install_group)
        
        # API 키 설정 그룹
        api_group = QGroupBox("API 키 설정 (선택사항)")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(8)
        
        api_info = QLabel(
            "클라우드 모델(OpenAI, Anthropic)을 사용하는 경우 API 키를 설정하세요.\n"
            "환경 변수로 설정하거나 아래에 입력할 수 있습니다."
        )
        api_info.setWordWrap(True)
        api_info.setStyleSheet("color: #888888;")
        api_layout.addWidget(api_info)
        
        # Anthropic API Key
        anthropic_layout = QHBoxLayout()
        anthropic_layout.addWidget(QLabel("Anthropic API Key:"))
        self.anthropic_key_input = QLineEdit()
        self.anthropic_key_input.setPlaceholderText("sk-ant-...")
        self.anthropic_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        anthropic_layout.addWidget(self.anthropic_key_input)
        api_layout.addLayout(anthropic_layout)
        
        # OpenAI API Key
        openai_layout = QHBoxLayout()
        openai_layout.addWidget(QLabel("OpenAI API Key:"))
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setPlaceholderText("sk-...")
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        openai_layout.addWidget(self.openai_key_input)
        api_layout.addLayout(openai_layout)
        
        save_keys_btn = QPushButton("💾 API 키 저장")
        save_keys_btn.clicked.connect(self._save_api_keys)
        api_layout.addWidget(save_keys_btn)
        
        layout.addWidget(api_group)
        
        layout.addStretch()
        
        return tab
    
    def _load_settings(self):
        """설정 로드"""
        import os
        # 환경 변수에서 API 키 로드
        self.anthropic_key_input.setText(os.environ.get('ANTHROPIC_API_KEY', ''))
        self.openai_key_input.setText(os.environ.get('OPENAI_API_KEY', ''))
        
        # 상태 확인
        self._refresh_status()
    
    def _refresh_status(self):
        """상태 새로고침"""
        # Node.js 확인
        node_installed, node_version = self.installer.check_nodejs()
        if node_installed:
            self.node_status_label.setText(f"✓ 설치됨 (v{node_version})")
            self.node_status_label.setStyleSheet("color: #4ec9b0;")
        else:
            self.node_status_label.setText("✗ 미설치")
            self.node_status_label.setStyleSheet("color: #f48771;")
        
        # npm 확인
        npm_installed, npm_version = self.installer.check_npm()
        if npm_installed:
            self.npm_status_label.setText(f"✓ 설치됨 (v{npm_version})")
            self.npm_status_label.setStyleSheet("color: #4ec9b0;")
        else:
            self.npm_status_label.setText("✗ 미설치")
            self.npm_status_label.setStyleSheet("color: #f48771;")
        
        # OpenCode 확인
        opencode_available = self.installer.check_opencode()
        if opencode_available:
            self.opencode_status_label.setText("✓ 사용 가능 (npx)")
            self.opencode_status_label.setStyleSheet("color: #4ec9b0;")
            self.install_btn.setEnabled(False)
            self.install_btn.setText("✓ 이미 설치됨")
        else:
            self.opencode_status_label.setText("✗ 미설치")
            self.opencode_status_label.setStyleSheet("color: #f48771;")
            self.install_btn.setEnabled(True)
            self.install_btn.setText("📦 OpenCode 설치")
    
    def _install_opencode(self):
        """OpenCode 설치"""
        if not self.installer.check_nodejs()[0]:
            QMessageBox.warning(
                self,
                "Node.js 미설치",
                self.installer.install_nodejs_instructions()
            )
            return
        
        reply = QMessageBox.question(
            self,
            "OpenCode 설치",
            "OpenCode CLI를 설치하시겠습니까?\n\n"
            "npx를 통해 자동으로 다운로드됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.install_btn.setEnabled(False)
            self.install_btn.setText("설치 중...")
            
            success, message = self.installer.ensure_opencode_available()
            
            if success:
                QMessageBox.information(self, "설치 완료", "OpenCode가 성공적으로 설치되었습니다.")
            else:
                QMessageBox.warning(self, "설치 실패", f"OpenCode 설치에 실패했습니다:\n\n{message}")
            
            self._refresh_status()
    
    def _save_api_keys(self):
        """API 키 저장"""
        import os
        
        anthropic_key = self.anthropic_key_input.text().strip()
        openai_key = self.openai_key_input.text().strip()
        
        # 환경 변수 설정 (현재 세션에만 적용)
        if anthropic_key:
            os.environ['ANTHROPIC_API_KEY'] = anthropic_key
        if openai_key:
            os.environ['OPENAI_API_KEY'] = openai_key
        
        # TODO: .env 파일에 저장하는 기능 추가 가능
        
        QMessageBox.information(
            self,
            "저장 완료",
            "API 키가 현재 세션에 저장되었습니다.\n\n"
            "영구적으로 저장하려면 환경 변수에 설정하거나 .env 파일을 사용하세요."
        )
