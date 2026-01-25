"""OpenCode 전용 페이지"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTabWidget, QGroupBox, QLineEdit,
                             QTextEdit, QComboBox, QCheckBox, QMessageBox,
                             QProgressBar, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from utils.opencode_installer import OpenCodeInstaller
from agent.analyzer import LogAnalyzer


class OpenCodePage(QWidget):
    """OpenCode 전용 관리 페이지"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.installer = OpenCodeInstaller()
        self.analyzer = LogAnalyzer()
        self._setup_ui()
        # 상태 확인을 백그라운드 스레드에서 실행 (UI 블로킹 방지)
        self._check_status_async()
    
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 헤더
        header = QLabel("🤖 OpenCode 관리")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(16)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # 탭 위젯
        tabs = QTabWidget()
        
        # 1. 상태 및 설치 탭
        status_tab = self._create_status_tab()
        tabs.addTab(status_tab, "상태 및 설치")
        
        # 2. Oh My OpenCode 탭
        ohmy_tab = self._create_ohmy_opencode_tab()
        tabs.addTab(ohmy_tab, "Oh My OpenCode")
        
        # 3. 프로젝트 관리 탭
        project_tab = self._create_project_tab()
        tabs.addTab(project_tab, "프로젝트 관리")
        
        # 4. 설정 탭
        settings_tab = self._create_settings_tab()
        tabs.addTab(settings_tab, "설정")
        
        layout.addWidget(tabs)
    
    def _create_status_tab(self):
        """상태 및 설치 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 상태 정보 그룹
        status_group = QGroupBox("시스템 상태")
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(12)
        
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
        opencode_layout.addWidget(QLabel("OpenCode CLI:"))
        self.opencode_status_label = QLabel("확인 중...")
        opencode_layout.addWidget(self.opencode_status_label)
        opencode_layout.addStretch()
        status_layout.addLayout(opencode_layout)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("🔄 상태 새로고침")
        refresh_btn.clicked.connect(self._check_status_async)
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
        install_info.setStyleSheet("color: #888888; padding: 8px;")
        install_layout.addWidget(install_info)
        
        self.install_btn = QPushButton("📦 OpenCode 설치")
        self.install_btn.clicked.connect(self._install_opencode)
        install_layout.addWidget(self.install_btn)
        
        # 설치 진행 바
        self.install_progress = QProgressBar()
        self.install_progress.setVisible(False)
        self.install_progress.setRange(0, 0)
        install_layout.addWidget(self.install_progress)
        
        layout.addWidget(install_group)
        
        layout.addStretch()
        return tab
    
    def _create_ohmy_opencode_tab(self):
        """Oh My OpenCode 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 소개
        intro_group = QGroupBox("Oh My OpenCode 소개")
        intro_layout = QVBoxLayout(intro_group)
        intro_text = QLabel(
            "Oh My OpenCode는 OpenCode의 오케스트레이션 레이어로, "
            "멀티 에이전트를 사용하여 복잡한 개발 작업을 처리합니다.\n\n"
            "주요 기능:\n"
            "• 멀티 에이전트 오케스트레이션 (Planner-Sisyphus, Librarian, Explore, Oracle)\n"
            "• 20+ 내장 훅 (컨텍스트 관리, 세션 복구, 코드 품질 검사 등)\n"
            "• MCP 통합 (Context7, grep.app)\n"
            "• LSP 지원 (코드 분석, 타입 체크, 리팩토링)\n"
            "• 빌드 파이프라인 인식"
        )
        intro_text.setWordWrap(True)
        intro_text.setStyleSheet("padding: 8px;")
        intro_layout.addWidget(intro_text)
        layout.addWidget(intro_group)
        
        # 상태 및 설치
        ohmy_status_group = QGroupBox("Oh My OpenCode 상태")
        ohmy_layout = QVBoxLayout(ohmy_status_group)
        ohmy_layout.setSpacing(12)
        
        # 상태 표시
        ohmy_status_layout = QHBoxLayout()
        ohmy_status_layout.addWidget(QLabel("설치 상태:"))
        self.ohmy_status_label = QLabel("확인 중...")
        ohmy_status_layout.addWidget(self.ohmy_status_label)
        ohmy_status_layout.addStretch()
        ohmy_layout.addLayout(ohmy_status_layout)
        
        # 설치 버튼
        self.ohmy_install_btn = QPushButton("📦 Oh My OpenCode 설치")
        self.ohmy_install_btn.clicked.connect(self._install_ohmy_opencode)
        ohmy_layout.addWidget(self.ohmy_install_btn)
        
        # 설치 진행 바
        self.ohmy_install_progress = QProgressBar()
        self.ohmy_install_progress.setVisible(False)
        self.ohmy_install_progress.setRange(0, 0)
        ohmy_layout.addWidget(self.ohmy_install_progress)
        
        layout.addWidget(ohmy_status_group)
        
        # Agent Team 목록
        agents_group = QGroupBox("Agent Team (에이전트 팀)")
        agents_layout = QVBoxLayout(agents_group)
        
        agents_info = QLabel(
            "Oh My OpenCode는 멀티 에이전트 오케스트레이션 시스템입니다.\n"
            "각 팀원(Agent)은 특정 역할을 담당합니다."
        )
        agents_info.setWordWrap(True)
        agents_info.setStyleSheet("color: #888888; padding: 8px;")
        agents_layout.addWidget(agents_info)
        
        self.agents_list = QListWidget()
        self.agents_list.addItem("Agent Team 목록을 불러오는 중...")
        self.agents_list.itemDoubleClicked.connect(self._on_agent_double_clicked)
        agents_layout.addWidget(self.agents_list)
        
        agents_buttons = QHBoxLayout()
        settings_btn = QPushButton("⚙️ 팀원 설정")
        settings_btn.clicked.connect(self._on_agent_settings_clicked)
        agents_buttons.addWidget(settings_btn)
        
        refresh_agents_btn = QPushButton("🔄 새로고침")
        refresh_agents_btn.clicked.connect(self._refresh_agents)
        agents_buttons.addWidget(refresh_agents_btn)
        
        agents_buttons.addStretch()
        agents_layout.addLayout(agents_buttons)
        
        layout.addWidget(agents_group)
        
        layout.addStretch()
        return tab
    
    def _create_project_tab(self):
        """프로젝트 관리 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 프로젝트 목록
        projects_group = QGroupBox("로드된 프로젝트")
        projects_layout = QVBoxLayout(projects_group)
        
        self.projects_list = QListWidget()
        projects_layout.addWidget(self.projects_list)
        
        project_buttons = QHBoxLayout()
        add_project_btn = QPushButton("➕ 프로젝트 추가")
        add_project_btn.clicked.connect(self._add_project)
        project_buttons.addWidget(add_project_btn)
        
        remove_project_btn = QPushButton("➖ 프로젝트 제거")
        remove_project_btn.clicked.connect(self._remove_project)
        project_buttons.addWidget(remove_project_btn)
        
        project_buttons.addStretch()
        projects_layout.addLayout(project_buttons)
        
        layout.addWidget(projects_group)
        
        # 프로젝트 인덱싱 상태
        indexing_group = QGroupBox("인덱싱 상태")
        indexing_layout = QVBoxLayout(indexing_group)
        
        self.indexing_status_label = QLabel("인덱싱된 프로젝트가 없습니다.")
        indexing_layout.addWidget(self.indexing_status_label)
        
        index_btn = QPushButton("🔍 프로젝트 인덱싱")
        index_btn.clicked.connect(self._index_project)
        indexing_layout.addWidget(index_btn)
        
        layout.addWidget(indexing_group)
        
        layout.addStretch()
        return tab
    
    def _create_settings_tab(self):
        """설정 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 모델 설정
        model_group = QGroupBox("모델 설정")
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(8)
        
        model_info = QLabel("기본 AI 모델을 선택하세요.")
        model_info.setStyleSheet("color: #888888;")
        model_layout.addWidget(model_info)
        
        model_select_layout = QHBoxLayout()
        model_select_layout.addWidget(QLabel("모델 제공자:"))
        self.model_provider_combo = QComboBox()
        self.model_provider_combo.addItems(["Ollama (로컬)", "OpenAI", "Anthropic"])
        model_select_layout.addWidget(self.model_provider_combo)
        model_select_layout.addStretch()
        model_layout.addLayout(model_select_layout)
        
        layout.addWidget(model_group)
        
        # API 키 설정
        api_group = QGroupBox("API 키 설정")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(8)
        
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
        
        # 고급 설정
        advanced_group = QGroupBox("고급 설정")
        advanced_layout = QVBoxLayout(advanced_group)
        advanced_layout.setSpacing(8)
        
        self.sandbox_cb = QCheckBox("샌드박스 모드 활성화")
        advanced_layout.addWidget(self.sandbox_cb)
        
        self.auto_index_cb = QCheckBox("프로젝트 자동 인덱싱")
        advanced_layout.addWidget(self.auto_index_cb)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        return tab
    
    def _check_status_async(self):
        """상태 확인을 백그라운드 스레드에서 실행"""
        self.status_check_thread = OpenCodePageStatusCheckThread(self.installer, self.analyzer)
        self.status_check_thread.status_checked.connect(self._on_status_checked)
        self.status_check_thread.start()
    
    def _on_status_checked(self, node_status, npm_status, opencode_status, ohmy_status):
        """상태 확인 완료 처리 (메인 스레드에서 호출)"""
        # Node.js 상태 업데이트
        if node_status['installed']:
            self.node_status_label.setText(f"✓ 설치됨 (v{node_status['version']})")
            self.node_status_label.setStyleSheet("color: #4ec9b0;")
        else:
            self.node_status_label.setText("✗ 미설치")
            self.node_status_label.setStyleSheet("color: #f48771;")
        
        # npm 상태 업데이트
        if npm_status['installed']:
            self.npm_status_label.setText(f"✓ 설치됨 (v{npm_status['version']})")
            self.npm_status_label.setStyleSheet("color: #4ec9b0;")
        else:
            self.npm_status_label.setText("✗ 미설치")
            self.npm_status_label.setStyleSheet("color: #f48771;")
        
        # OpenCode 상태 업데이트
        if opencode_status['installed']:
            self.opencode_status_label.setText("✓ 사용 가능 (npx)")
            self.opencode_status_label.setStyleSheet("color: #4ec9b0;")
            self.install_btn.setEnabled(False)
            self.install_btn.setText("✓ 이미 설치됨")
        else:
            self.opencode_status_label.setText("✗ 미설치")
            self.opencode_status_label.setStyleSheet("color: #f48771;")
            self.install_btn.setEnabled(True)
            self.install_btn.setText("📦 OpenCode 설치")
        
        # Oh My OpenCode 상태 업데이트
        if ohmy_status['installed']:
            self.ohmy_status_label.setText(f"✓ 설치됨 ({ohmy_status.get('method', '')})")
            self.ohmy_status_label.setStyleSheet("color: #4ec9b0;")
            self.ohmy_install_btn.setEnabled(False)
            self.ohmy_install_btn.setText("✓ 이미 설치됨")
        else:
            self.ohmy_status_label.setText("✗ 미설치")
            self.ohmy_status_label.setStyleSheet("color: #f48771;")
            self.ohmy_install_btn.setEnabled(True)
            self.ohmy_install_btn.setText("📦 Oh My OpenCode 설치")
    
    def _check_status(self):
        """상태 확인 (동기 버전 - 수동 새로고침용)"""
        self._check_status_async()
    
    def _check_ohmy_opencode_status(self):
        """Oh My OpenCode 상태 확인"""
        import subprocess
        import logging
        logger = logging.getLogger(__name__)
        
        # bunx가 있는지 먼저 확인 (여러 방법 시도)
        bunx_available = False
        try:
            result = subprocess.run(
                ['bunx', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=3,
                shell=True
            )
            bunx_available = result.returncode == 0
            if bunx_available:
                logger.info(f"[bunx] 확인됨: {result.stdout.strip()}")
        except Exception as e:
            logger.debug(f"[bunx] PATH 확인 실패: {str(e)}")
        
        # npm 전역 패키지에서도 확인
        if not bunx_available:
            try:
                result = subprocess.run(
                    ['npm', 'list', '-g', 'bunx', '--depth=0'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=3,
                    shell=True
                )
                if result.returncode == 0 and 'bunx' in result.stdout:
                    bunx_available = True
                    logger.info("[bunx] npm 전역 패키지에서 확인됨")
            except Exception as e:
                logger.debug(f"[bunx] npm 확인 실패: {str(e)}")
        
        # bunx가 있으면 bunx로 확인, 없으면 npx로 확인
        if bunx_available:
            try:
                result = subprocess.run(
                    ['bunx', 'oh-my-opencode', '--version'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    self.ohmy_status_label.setText(f"✓ 설치됨 (bunx)")
                    self.ohmy_status_label.setStyleSheet("color: #4ec9b0;")
                    self.ohmy_install_btn.setEnabled(False)
                    self.ohmy_install_btn.setText("✓ 이미 설치됨")
                    return
            except:
                pass
        else:
            # npx로 확인
            try:
                result = subprocess.run(
                    ['npx', 'oh-my-opencode', '--version'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    self.ohmy_status_label.setText(f"✓ 설치됨 (npx)")
                    self.ohmy_status_label.setStyleSheet("color: #4ec9b0;")
                    self.ohmy_install_btn.setEnabled(False)
                    self.ohmy_install_btn.setText("✓ 이미 설치됨")
                    return
            except:
                pass
        
        # npm 전역 설치 확인
        try:
            result = subprocess.run(
                ['npm', 'list', '-g', 'oh-my-opencode'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5,
                shell=True
            )
            
            if result.returncode == 0:
                self.ohmy_status_label.setText("✓ 설치됨 (전역)")
                self.ohmy_status_label.setStyleSheet("color: #4ec9b0;")
                self.ohmy_install_btn.setEnabled(False)
                self.ohmy_install_btn.setText("✓ 이미 설치됨")
                return
        except:
            pass
        
        self.ohmy_status_label.setText("✗ 미설치")
        self.ohmy_status_label.setStyleSheet("color: #f48771;")
        self.ohmy_install_btn.setEnabled(True)
        self.ohmy_install_btn.setText("📦 Oh My OpenCode 설치")
    
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
            "OpenCode CLI를 설치하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.install_btn.setEnabled(False)
            self.install_progress.setVisible(True)
            
            # 설치 스레드 시작
            self.install_thread = OpenCodeInstallThread(self.installer)
            self.install_thread.install_complete.connect(self._on_install_complete)
            self.install_thread.start()
    
    def _install_ohmy_opencode(self):
        """Oh My OpenCode 설치"""
        if not self.installer.check_nodejs()[0]:
            QMessageBox.warning(
                self,
                "Node.js 미설치",
                self.installer.install_nodejs_instructions()
            )
            return
        
        # bunx가 있는지 확인 (여러 방법 시도)
        import subprocess
        import os
        bunx_available = False
        
        # 방법 1: PATH에서 직접 확인
        try:
            result = subprocess.run(
                ['bunx', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=3,
                shell=True
            )
            bunx_available = result.returncode == 0
            if bunx_available:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[bunx] 확인됨: {result.stdout.strip()}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"[bunx] PATH 확인 실패: {str(e)}")
        
        # 방법 2: npm 전역 패키지에서 확인
        if not bunx_available:
            try:
                result = subprocess.run(
                    ['npm', 'list', '-g', 'bunx', '--depth=0'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=3,
                    shell=True
                )
                if result.returncode == 0 and 'bunx' in result.stdout:
                    bunx_available = True
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info("[bunx] npm 전역 패키지에서 확인됨")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"[bunx] npm 확인 실패: {str(e)}")
        
        if not bunx_available:
            # bunx가 없으면 bunx 설치 먼저 진행
            reply = QMessageBox.question(
                self,
                "bunx 설치 필요",
                "Oh My OpenCode를 설치하려면 bunx가 필요합니다.\n\n"
                "bunx를 설치하시겠습니까?\n"
                "(npm install -g bunx)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.ohmy_install_btn.setEnabled(False)
                self.ohmy_install_progress.setVisible(True)
                
                # bunx 설치 스레드 시작 (npm을 통해)
                self.bunx_install_thread = BunxInstallThread()
                self.bunx_install_thread.install_complete.connect(self._on_bunx_install_complete)
                self.bunx_install_thread.start()
            return
        
        # bunx가 있으면 바로 Oh My OpenCode 설치
        reply = QMessageBox.question(
            self,
            "Oh My OpenCode 설치",
            "Oh My OpenCode를 설치하시겠습니까?\n\n"
            "bunx를 통해 자동으로 설치됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.ohmy_install_btn.setEnabled(False)
            self.ohmy_install_progress.setVisible(True)
            
            # 설치 스레드 시작
            self.ohmy_install_thread = OhMyOpenCodeInstallThread()
            self.ohmy_install_thread.install_complete.connect(self._on_ohmy_install_complete)
            self.ohmy_install_thread.start()
    
    def _on_install_complete(self, success: bool, message: str):
        """OpenCode 설치 완료"""
        self.install_progress.setVisible(False)
        if success:
            QMessageBox.information(self, "설치 완료", "OpenCode가 성공적으로 설치되었습니다.")
        else:
            QMessageBox.warning(self, "설치 실패", f"OpenCode 설치에 실패했습니다:\n\n{message}")
        self._check_status()
    
    def _on_bunx_install_complete(self, success: bool, message: str):
        """bunx 설치 완료"""
        self.ohmy_install_progress.setVisible(False)
        if success:
            QMessageBox.information(
                self, 
                "bunx 설치 완료", 
                "bunx가 성공적으로 설치되었습니다.\n\n"
                "이제 Oh My OpenCode를 설치할 수 있습니다."
            )
            # bunx 설치 후 자동으로 Oh My OpenCode 설치 진행
            self._install_ohmy_opencode()
        else:
            QMessageBox.warning(self, "bunx 설치 실패", f"bunx 설치에 실패했습니다:\n\n{message}")
            self.ohmy_install_btn.setEnabled(True)
    
    def _on_ohmy_install_complete(self, success: bool, message: str):
        """Oh My OpenCode 설치 완료"""
        self.ohmy_install_progress.setVisible(False)
        if success:
            QMessageBox.information(self, "설치 완료", "Oh My OpenCode가 성공적으로 설치되었습니다.")
        else:
            QMessageBox.warning(self, "설치 실패", f"Oh My OpenCode 설치에 실패했습니다:\n\n{message}")
        self._check_ohmy_opencode_status()
    
    def _refresh_agents(self):
        """Agent Team 목록 새로고침"""
        self.agents_list.clear()
        self.agents_list.addItem("Agent Team 목록을 불러오는 중...")
        
        # 백그라운드 스레드에서 Agent 목록 가져오기
        self.agents_thread = AgentsListThread()
        self.agents_thread.agents_loaded.connect(self._on_agents_loaded)
        self.agents_thread.start()
    
    def _on_agents_loaded(self, agents):
        """Agent Team 목록 로드 완료"""
        self.agents_list.clear()
        
        if not agents:
            self.agents_list.addItem("Agent Team을 찾을 수 없습니다.")
            return
        
        for agent in agents:
            self.agents_list.addItem(agent)
    
    def _on_agent_double_clicked(self, item):
        """Agent 더블클릭 시 설정 다이얼로그 열기"""
        agent_name = item.text()
        self._open_agent_settings(agent_name)
    
    def _on_agent_settings_clicked(self):
        """Agent 설정 버튼 클릭"""
        current_item = self.agents_list.currentItem()
        if current_item:
            agent_name = current_item.text()
            self._open_agent_settings(agent_name)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Agent 선택", "설정할 팀원(Agent)을 선택해주세요.")
    
    def _open_agent_settings(self, agent_name):
        """Agent 설정 다이얼로그 열기"""
        from ui.components.agent_settings_dialog import AgentSettingsDialog
        dialog = AgentSettingsDialog(self, agent_name)
        dialog.exec()
    
    def _add_project(self):
        """프로젝트 추가"""
        # TODO: 프로젝트 추가 다이얼로그
        QMessageBox.information(self, "프로젝트 추가", "프로젝트 추가 기능은 구현 중입니다.")
    
    def _remove_project(self):
        """프로젝트 제거"""
        # TODO: 선택된 프로젝트 제거
        QMessageBox.information(self, "프로젝트 제거", "프로젝트 제거 기능은 구현 중입니다.")
    
    def _index_project(self):
        """프로젝트 인덱싱"""
        # TODO: OpenCode 프로젝트 인덱싱
        QMessageBox.information(self, "프로젝트 인덱싱", "프로젝트 인덱싱 기능은 구현 중입니다.")
    
    def _save_api_keys(self):
        """API 키 저장"""
        import os
        
        anthropic_key = self.anthropic_key_input.text().strip()
        openai_key = self.openai_key_input.text().strip()
        
        if anthropic_key:
            os.environ['ANTHROPIC_API_KEY'] = anthropic_key
        if openai_key:
            os.environ['OPENAI_API_KEY'] = openai_key
        
        QMessageBox.information(self, "저장 완료", "API 키가 저장되었습니다.")


class OpenCodePageStatusCheckThread(QThread):
    """OpenCode 페이지 상태 확인을 수행하는 백그라운드 스레드"""
    status_checked = pyqtSignal(dict, dict, dict, dict)  # node_status, npm_status, opencode_status, ohmy_status
    
    def __init__(self, installer: OpenCodeInstaller, analyzer: LogAnalyzer):
        super().__init__()
        self.installer = installer
        self.analyzer = analyzer
        import logging
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """상태 확인 실행"""
        try:
            self.logger.info("[OpenCodePageStatusCheckThread] 상태 확인 시작")
            
            # Node.js 확인
            try:
                node_installed, node_version = self.installer.check_nodejs()
                node_status = {
                    'installed': node_installed,
                    'version': node_version or ''
                }
            except Exception as e:
                self.logger.error(f"[OpenCodePageStatusCheckThread] Node.js 확인 오류: {str(e)}")
                node_status = {'installed': False, 'version': ''}
            
            # npm 확인
            try:
                npm_installed, npm_version = self.installer.check_npm()
                npm_status = {
                    'installed': npm_installed,
                    'version': npm_version or ''
                }
            except Exception as e:
                self.logger.error(f"[OpenCodePageStatusCheckThread] npm 확인 오류: {str(e)}")
                npm_status = {'installed': False, 'version': ''}
            
            # OpenCode 확인
            try:
                opencode_available = self.analyzer.check_installation()
                opencode_status = {
                    'installed': opencode_available
                }
            except Exception as e:
                self.logger.error(f"[OpenCodePageStatusCheckThread] OpenCode 확인 오류: {str(e)}")
                opencode_status = {'installed': False}
            
            # Oh My OpenCode 확인
            try:
                ohmy_status = self._check_ohmy_opencode()
            except Exception as e:
                self.logger.error(f"[OpenCodePageStatusCheckThread] Oh My OpenCode 확인 오류: {str(e)}")
                ohmy_status = {'installed': False}
            
            # 시그널 발생 (메인 스레드에서 UI 업데이트)
            self.status_checked.emit(node_status, npm_status, opencode_status, ohmy_status)
            self.logger.info("[OpenCodePageStatusCheckThread] 상태 확인 완료")
        except Exception as e:
            self.logger.error(f"[OpenCodePageStatusCheckThread] 전체 오류: {str(e)}", exc_info=True)
            # 오류 발생 시에도 기본값으로 시그널 발생
            self.status_checked.emit(
                {'installed': False, 'version': ''},
                {'installed': False, 'version': ''},
                {'installed': False},
                {'installed': False}
            )
    
    def _check_ohmy_opencode(self):
        """Oh My OpenCode 상태 확인"""
        import subprocess
        import logging
        logger = logging.getLogger(__name__)
        
        # bunx가 있는지 먼저 확인 (여러 방법 시도)
        bunx_available = False
        try:
            result = subprocess.run(
                ['bunx', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=3,
                shell=True
            )
            bunx_available = result.returncode == 0
            if bunx_available:
                logger.info(f"[bunx] 확인됨: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"[bunx] PATH 확인 실패: {str(e)}")
        
        # npm 전역 패키지에서도 확인
        if not bunx_available:
            try:
                result = subprocess.run(
                    ['npm', 'list', '-g', 'bunx', '--depth=0'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=3,
                    shell=True
                )
                if result.returncode == 0 and 'bunx' in result.stdout:
                    bunx_available = True
                    logger.info("[bunx] npm 전역 패키지에서 확인됨")
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                logger.debug(f"[bunx] npm 확인 실패: {str(e)}")
        
        # bunx가 있으면 bunx로 확인
        if bunx_available:
            try:
                result = subprocess.run(
                    ['bunx', 'oh-my-opencode', '--version'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=3,  # 타임아웃 단축
                    shell=True
                )
                
                if result.returncode == 0:
                    return {'installed': True, 'method': 'bunx'}
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
        
        # npm 전역 설치 확인 (빠른 확인)
        try:
            result = subprocess.run(
                ['npm', 'list', '-g', 'oh-my-opencode', '--depth=0'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=2,  # 타임아웃 단축
                shell=True
            )
            
            if result.returncode == 0 and 'oh-my-opencode' in result.stdout:
                return {'installed': True, 'method': '전역'}
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        
        # npx는 너무 오래 걸릴 수 있으므로 스킵
        return {'installed': False}


class OpenCodeInstallThread(QThread):
    """OpenCode 설치 스레드"""
    install_complete = pyqtSignal(bool, str)
    
    def __init__(self, installer: OpenCodeInstaller):
        super().__init__()
        self.installer = installer
    
    def run(self):
        """설치 실행"""
        success, message = self.installer.ensure_opencode_available()
        self.install_complete.emit(success, message)


class BunInstallThread(QThread):
    """Bun 설치 스레드"""
    install_complete = pyqtSignal(bool, str)
    
    def run(self):
        """Bun 설치 실행"""
        import subprocess
        import logging
        import platform
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("[Bun] 설치 시작")
            system = platform.system()
            
            if system == 'Windows':
                # Windows: PowerShell을 통해 설치
                # 실행 정책 우회 및 전체 URL 사용
                install_script = '''
                $ErrorActionPreference = "Stop"
                try {
                    $response = Invoke-WebRequest -Uri "https://bun.sh/install.ps1" -UseBasicParsing
                    Invoke-Expression $response.Content
                } catch {
                    Write-Host "Error: $_"
                    exit 1
                }
                '''
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', install_script],
                    shell=False,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=300
                )
            else:
                # Linux/Mac: curl을 통해 설치
                result = subprocess.run(
                    ['curl', '-fsSL', 'https://bun.sh/install'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30
                )
                
                if result.returncode == 0:
                    # 스크립트를 bash로 실행
                    install_script = result.stdout
                    bash_result = subprocess.run(
                        ['bash'],
                        input=install_script,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=300
                    )
                    result = bash_result
                else:
                    # curl 실패 시 직접 bash로 실행
                    result = subprocess.run(
                        ['bash', '-c', 'curl -fsSL https://bun.sh/install | bash'],
                        shell=False,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=300
                    )
            
            if result.returncode == 0:
                logger.info("[Bun] 설치 완료")
                # 설치 후 bunx가 사용 가능한지 확인
                try:
                    check_result = subprocess.run(
                        ['bunx', '--version'],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=5,
                        shell=True
                    )
                    if check_result.returncode == 0:
                        self.install_complete.emit(True, "Bun이 성공적으로 설치되었습니다.")
                    else:
                        self.install_complete.emit(False, "Bun 설치 후 bunx 확인에 실패했습니다. 터미널을 재시작해보세요.")
                except Exception as e:
                    logger.warning(f"[Bun] bunx 확인 실패: {str(e)}")
                    self.install_complete.emit(True, "Bun이 설치되었습니다. 터미널을 재시작하면 bunx를 사용할 수 있습니다.")
            else:
                logger.error(f"[Bun] 설치 실패: returncode={result.returncode}")
                logger.error(f"[Bun] stdout: {result.stdout[:500]}")
                logger.error(f"[Bun] stderr: {result.stderr[:500]}")
                
                # 에러 메시지 구성
                error_parts = []
                if result.stderr:
                    error_parts.append(f"오류: {result.stderr[:200]}")
                if result.stdout:
                    # stdout에 에러 정보가 있을 수 있음
                    if 'error' in result.stdout.lower() or 'failed' in result.stdout.lower():
                        error_parts.append(f"출력: {result.stdout[:200]}")
                
                error_msg = "\n".join(error_parts) if error_parts else f"설치 실패 (코드: {result.returncode})"
                
                # 대안 제시
                error_msg += "\n\n대안: npm을 통해 설치할 수 있습니다:\nnpm install -g bun"
                
                self.install_complete.emit(False, error_msg)
        except subprocess.TimeoutExpired:
            logger.error("[Bun] 설치 타임아웃")
            self.install_complete.emit(False, "Bun 설치가 타임아웃되었습니다.")
        except Exception as e:
            logger.error(f"[Bun] 설치 오류: {str(e)}")
            self.install_complete.emit(False, f"오류 발생: {str(e)}")


class BunxInstallThread(QThread):
    """npm을 통한 bunx 설치 스레드"""
    install_complete = pyqtSignal(bool, str)
    
    def run(self):
        """npm을 통해 bunx 설치 실행"""
        import subprocess
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("[bunx] npm을 통한 설치 시작")
            result = subprocess.run(
                ['npm', 'install', '-g', 'bunx'],
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("[bunx] npm을 통한 설치 완료")
                # 설치 후 bunx가 사용 가능한지 확인
                try:
                    check_result = subprocess.run(
                        ['bunx', '--version'],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=5,
                        shell=True
                    )
                    if check_result.returncode == 0:
                        self.install_complete.emit(True, "bunx가 성공적으로 설치되었습니다.")
                    else:
                        self.install_complete.emit(True, "bunx가 설치되었습니다. 터미널을 재시작하면 사용할 수 있습니다.")
                except Exception as e:
                    logger.warning(f"[bunx] 확인 실패: {str(e)}")
                    self.install_complete.emit(True, "bunx가 설치되었습니다. 터미널을 재시작하면 사용할 수 있습니다.")
            else:
                logger.error(f"[bunx] npm 설치 실패: {result.stderr}")
                error_msg = result.stderr if result.stderr else result.stdout
                self.install_complete.emit(False, f"npm을 통한 bunx 설치 실패: {error_msg[:200]}")
        except subprocess.TimeoutExpired:
            logger.error("[bunx] npm 설치 타임아웃")
            self.install_complete.emit(False, "npm을 통한 bunx 설치가 타임아웃되었습니다.")
        except Exception as e:
            logger.error(f"[bunx] npm 설치 오류: {str(e)}")
            self.install_complete.emit(False, f"오류 발생: {str(e)}")


class OhMyOpenCodeInstallThread(QThread):
    """Oh My OpenCode 설치 스레드"""
    install_complete = pyqtSignal(bool, str)
    
    def run(self):
        """Oh My OpenCode 설치 실행"""
        import subprocess
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("[OhMyOpenCode] 설치 시작")
            
            # Oh My OpenCode 설치 방법 시도 (여러 방법)
            install_methods = [
                # 방법 1: npx로 직접 oh-my-opencode 설치 (bunx 없이)
                (['npx', '-y', 'oh-my-opencode', 'install'], 'npx -y oh-my-opencode'),
                # 방법 2: npm을 통해 전역 설치
                (['npm', 'install', '-g', 'oh-my-opencode'], 'npm install -g'),
                # 방법 3: bunx를 통한 설치 시도
                (['npx', '-y', 'bunx', 'oh-my-opencode', 'install'], 'npx -y bunx'),
                # 방법 4: 직접 bunx 실행
                (['bunx', 'oh-my-opencode', 'install'], 'bunx'),
            ]
            
            last_error = None
            for cmd, method_name in install_methods:
                try:
                    logger.info(f"[OhMyOpenCode] {method_name} 방법으로 설치 시도")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=300,
                        shell=True
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"[OhMyOpenCode] {method_name} 방법으로 설치 완료")
                        self.install_complete.emit(True, f"Oh My OpenCode가 성공적으로 설치되었습니다. ({method_name})")
                        return
                    else:
                        logger.warning(f"[OhMyOpenCode] {method_name} 방법 실패: {result.stderr[:200]}")
                        last_error = result.stderr if result.stderr else result.stdout
                except FileNotFoundError:
                    logger.debug(f"[OhMyOpenCode] {method_name} 명령어를 찾을 수 없음")
                    continue
                except subprocess.TimeoutExpired:
                    logger.error(f"[OhMyOpenCode] {method_name} 설치 타임아웃")
                    last_error = "설치가 타임아웃되었습니다."
                    continue
                except Exception as e:
                    logger.debug(f"[OhMyOpenCode] {method_name} 오류: {str(e)}")
                    last_error = str(e)
                    continue
            
            # 모든 방법 실패
            logger.error(f"[OhMyOpenCode] 모든 설치 방법 실패")
            error_msg = last_error if last_error else "모든 설치 방법이 실패했습니다."
            self.install_complete.emit(False, f"설치 실패: {error_msg[:200]}")
            
        except Exception as e:
            logger.error(f"[OhMyOpenCode] 설치 오류: {str(e)}", exc_info=True)
            self.install_complete.emit(False, f"오류 발생: {str(e)}")


class AgentsListThread(QThread):
    """Oh My OpenCode Agent Team 목록을 가져오는 스레드"""
    agents_loaded = pyqtSignal(list)  # Agent 목록
    
    def run(self):
        """Agent Team 목록 가져오기"""
        import subprocess
        import logging
        import json
        from pathlib import Path
        logger = logging.getLogger(__name__)
        
        agents = []
        
        try:
            # 방법 1: 설정 파일에서 직접 읽기 (가장 확실한 방법)
            config_paths = [
                # 사용자 전역 설정
                Path.home() / ".config" / "opencode" / "oh-my-opencode.json",
                # 프로젝트별 설정 (현재 작업 디렉토리 기준)
                Path.cwd() / ".opencode" / "oh-my-opencode.json",
            ]
            
            config_found = False
            for config_path in config_paths:
                logger.info(f"[AgentsList] 설정 파일 확인: {config_path}")
                if config_path.exists():
                    try:
                        logger.info(f"[AgentsList] 설정 파일에서 읽기: {config_path}")
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        
                        logger.debug(f"[AgentsList] 설정 파일 내용: {json.dumps(config, indent=2, ensure_ascii=False)}")
                        
                        # agents 섹션에서 Agent 목록 추출
                        if 'agents' in config and isinstance(config['agents'], dict):
                            for agent_name, agent_config in config['agents'].items():
                                enabled = agent_config.get('enabled', True)
                                status = "✓ 활성화" if enabled else "✗ 비활성화"
                                
                                # Agent 이름을 읽기 쉽게 변환
                                display_name = agent_name.replace('-', ' ').replace('_', ' ').title()
                                if 'planner' in agent_name.lower() or 'sisyphus' in agent_name.lower():
                                    display_name = f"🤖 {display_name} (계획 수립 Agent)"
                                elif 'librarian' in agent_name.lower():
                                    display_name = f"📚 {display_name} (문서 관리 Agent)"
                                elif 'explore' in agent_name.lower():
                                    display_name = f"🔍 {display_name} (코드 탐색 Agent)"
                                elif 'oracle' in agent_name.lower():
                                    display_name = f"🔮 {display_name} (분석 및 예측 Agent)"
                                else:
                                    display_name = f"🤖 {display_name}"
                                
                                agents.append(f"{display_name} - {status}")
                            
                            if agents:
                                logger.info(f"[AgentsList] 설정 파일에서 {len(agents)}개 Agent 발견")
                                config_found = True
                                break
                        else:
                            logger.warning(f"[AgentsList] 설정 파일에 'agents' 섹션이 없음: {config_path}")
                    except json.JSONDecodeError as e:
                        logger.error(f"[AgentsList] 설정 파일 JSON 파싱 오류 ({config_path}): {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"[AgentsList] 설정 파일 읽기 실패 ({config_path}): {str(e)}", exc_info=True)
                        continue
                else:
                    logger.debug(f"[AgentsList] 설정 파일 없음: {config_path}")
            
            # 설정 파일이 없으면 기본 설정 파일 생성 제안
            if not config_found and not agents:
                logger.info("[AgentsList] 설정 파일이 없음 - 기본 Agent 목록 사용")
            
            # 방법 2: CLI 명령어로 가져오기 시도 (설정 파일이 없는 경우)
            if not agents:
                methods = [
                    # 방법 1: npx로 직접 실행
                    (['npx', '-y', 'oh-my-opencode', 'list'], 'npx -y oh-my-opencode'),
                    # 방법 2: npm 전역 설치된 경우
                    (['oh-my-opencode', 'list'], 'oh-my-opencode'),
                    # 방법 3: bunx를 통해 실행
                    (['npx', '-y', 'bunx', 'oh-my-opencode', 'list'], 'npx -y bunx'),
                ]
                
                for cmd, method_name in methods:
                    try:
                        logger.info(f"[AgentsList] {method_name} 방법으로 Agent Team 목록 가져오기 시도")
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            timeout=30,
                            shell=True
                        )
                        
                        if result.returncode == 0:
                            # 출력 파싱
                            output = result.stdout.strip()
                            if output:
                                # JSON 형식인지 확인
                                try:
                                    data = json.loads(output)
                                    if isinstance(data, list):
                                        agents = [str(a) for a in data]
                                    elif isinstance(data, dict) and 'plugins' in data:
                                        agents = [str(a) for a in data['plugins']]
                                    elif isinstance(data, dict) and 'agents' in data:
                                        agents = [str(a) for a in data['agents']]
                                except json.JSONDecodeError:
                                    # JSON이 아니면 줄 단위로 파싱
                                    lines = [line.strip() for line in output.split('\n') if line.strip()]
                                    agents = [line for line in lines if line and not line.startswith('#')]
                                
                                if agents:
                                    logger.info(f"[AgentsList] {method_name} 방법으로 {len(agents)}개 Agent 발견")
                                    break
                    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                        logger.debug(f"[AgentsList] {method_name} 방법 실패: {str(e)}")
                        continue
                    except Exception as e:
                        logger.debug(f"[AgentsList] {method_name} 오류: {str(e)}")
                        continue
            
            # Agent를 찾지 못한 경우 기본 Agent 목록 표시
            if not agents:
                logger.warning("[AgentsList] Agent Team 목록을 가져올 수 없음 - 기본 목록 사용")
                # Oh My OpenCode의 기본 Agent Team 목록
                agents = [
                    "🤖 Planner-Sisyphus (계획 수립 Agent) - ✓ 활성화",
                    "📚 Librarian (문서 관리 Agent) - ✗ 비활성화",
                    "🔍 Explore (코드 탐색 Agent) - ✗ 비활성화",
                    "🔮 Oracle (분석 및 예측 Agent) - ✗ 비활성화",
                ]
            
        except Exception as e:
            logger.error(f"[AgentsList] 오류: {str(e)}", exc_info=True)
            agents = ["Agent Team 목록을 불러오는 중 오류가 발생했습니다."]
        
        # 시그널 발생 (메인 스레드에서 UI 업데이트)
        self.agents_loaded.emit(agents)
