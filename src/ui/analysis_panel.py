from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QLineEdit, QPushButton, QScrollArea,
                             QFrame, QSplitter, QSizePolicy, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor

class AnalysisPanel(QWidget):
    """AI 분석 결과 및 채팅 패널"""
    
    # 시그널: 분석 요청, 채팅 전송, OpenCode 설치 요청, 설정 열기
    analysis_requested = pyqtSignal(str)  # issue_description
    chat_message_sent = pyqtSignal(str)  # message
    opencode_install_requested = pyqtSignal()  # OpenCode 설치 요청
    open_settings_requested = pyqtSignal()  # 설정 다이얼로그 열기 요청
    
    def __init__(self):
        super().__init__()
        self.opencode_status = "unknown"  # unknown, installed, not_installed, installing
        self._setup_ui()
        self._setup_styles()
    
    def _setup_ui(self):
        """UI 구성"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # 1. 헤더 영역 (분석 요청 버튼 포함)
        header = self._create_header()
        main_layout.addWidget(header)
        
        # 2. 스플리터로 분석 결과와 채팅 영역 분리
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # 분석 결과 영역
        analysis_section = self._create_analysis_section()
        analysis_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.addWidget(analysis_section)
        
        # 채팅 영역
        chat_section = self._create_chat_section()
        chat_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.addWidget(chat_section)
        
        # 비율 설정 (분석 결과 70%, 채팅 30%)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([400, 200])
        
        main_layout.addWidget(splitter)
    
    def _create_header(self):
        """헤더 영역 생성"""
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)
        
        # 타이틀과 설정 버튼을 포함하는 상단 바
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        
        # 타이틀
        title = QLabel("🤖 AI Analysis")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        title_bar.addWidget(title)
        
        title_bar.addStretch()
        
        # 설정 버튼
        settings_btn = QPushButton("⚙️")
        settings_btn.setToolTip("OpenCode 설정 열기")
        settings_btn.setFixedSize(28, 28)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                font-size: 14pt;
                color: #cccccc;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
                border-color: #569cd6;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """)
        settings_btn.clicked.connect(self._on_settings_clicked)
        title_bar.addWidget(settings_btn)
        
        header_layout.addLayout(title_bar)
        
        # 상태별 패널 스택 (동적 전환)
        self.status_panels = {}
        
        # 1. 확인 중 패널
        checking_panel = self._create_checking_panel()
        self.status_panels["unknown"] = checking_panel
        header_layout.addWidget(checking_panel)
        
        # 2. 미설치 패널
        not_installed_panel = self._create_not_installed_panel()
        self.status_panels["not_installed"] = not_installed_panel
        header_layout.addWidget(not_installed_panel)
        not_installed_panel.setVisible(False)
        
        # 3. 설치 중 패널
        installing_panel = self._create_installing_panel()
        self.status_panels["installing"] = installing_panel
        header_layout.addWidget(installing_panel)
        installing_panel.setVisible(False)
        
        # 4. 설치됨 패널 (정상 작동)
        installed_panel = self._create_installed_panel()
        self.status_panels["installed"] = installed_panel
        header_layout.addWidget(installed_panel)
        installed_panel.setVisible(False)
        
        return header_frame
    
    def _create_checking_panel(self):
        """확인 중 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        status_label = QLabel("🔍 OpenCode 상태 확인 중...")
        status_label.setStyleSheet("color: #888888; font-size: 10pt; padding: 8px;")
        layout.addWidget(status_label)
        
        return panel
    
    def _create_not_installed_panel(self):
        """미설치 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 경고 메시지
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: #3d2b1f;
                border: 1px solid #f48771;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setContentsMargins(8, 8, 8, 8)
        
        warning_title = QLabel("⚠️ OpenCode가 설치되어 있지 않습니다")
        warning_title.setStyleSheet("color: #f48771; font-weight: bold; font-size: 10pt;")
        warning_layout.addWidget(warning_title)
        
        warning_text = QLabel(
            "AI 분석 기능을 사용하려면 OpenCode CLI가 필요합니다.\n"
            "아래 버튼을 클릭하여 자동으로 설치할 수 있습니다."
        )
        warning_text.setStyleSheet("color: #d4d4d4; font-size: 9pt;")
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_frame)
        
        # 설치 버튼
        install_btn = QPushButton("📦 OpenCode 설치하기")
        install_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 4px;
                padding: 10px;
                color: white;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        install_btn.clicked.connect(self._on_install_clicked)
        layout.addWidget(install_btn)
        
        # 설정 열기 링크
        settings_link = QLabel('<a href="#" style="color: #569cd6;">설정에서 더 자세히 보기</a>')
        settings_link.setOpenExternalLinks(False)
        settings_link.linkActivated.connect(self._on_settings_link_clicked)
        settings_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(settings_link)
        
        return panel
    
    def _create_installing_panel(self):
        """설치 중 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 정보 프레임
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #1e3a5f;
                border: 1px solid #569cd6;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        
        info_title = QLabel("📥 OpenCode 설치 중...")
        info_title.setStyleSheet("color: #569cd6; font-weight: bold; font-size: 10pt;")
        info_layout.addWidget(info_title)
        
        self.install_status_label = QLabel("npx를 통해 OpenCode를 다운로드하고 있습니다...")
        self.install_status_label.setStyleSheet("color: #d4d4d4; font-size: 9pt;")
        self.install_status_label.setWordWrap(True)
        info_layout.addWidget(self.install_status_label)
        
        layout.addWidget(info_frame)
        
        # 진행 바
        self.install_progress = QProgressBar()
        self.install_progress.setRange(0, 0)  # 무한 진행 바
        self.install_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                background-color: #1e1e1e;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.install_progress)
        
        return panel
    
    def _create_installed_panel(self):
        """설치됨 패널 생성 (정상 작동)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 성공 메시지
        success_frame = QFrame()
        success_frame.setStyleSheet("""
            QFrame {
                background-color: #1e3a2f;
                border: 1px solid #4ec9b0;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        success_layout = QVBoxLayout(success_frame)
        success_layout.setContentsMargins(8, 8, 8, 8)
        
        success_title = QLabel("✓ OpenCode 준비 완료")
        success_title.setStyleSheet("color: #4ec9b0; font-weight: bold; font-size: 10pt;")
        success_layout.addWidget(success_title)
        
        success_text = QLabel("AI 분석 기능을 사용할 수 있습니다.")
        success_text.setStyleSheet("color: #d4d4d4; font-size: 9pt;")
        success_layout.addWidget(success_text)
        
        layout.addWidget(success_frame)
        
        # 분석 요청 버튼
        self.analyze_btn = QPushButton("📊 분석 요청")
        self.analyze_btn.setToolTip("현재 선택된 로그나 이슈 설명을 기반으로 AI 분석을 요청합니다")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 4px;
                padding: 10px;
                color: white;
                font-weight: bold;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self.analyze_btn)
        
        return panel
    
    def _on_settings_link_clicked(self, link):
        """설정 링크 클릭"""
        self.open_settings_requested.emit()
    
    def _on_settings_clicked(self):
        """설정 버튼 클릭"""
        self.open_settings_requested.emit()
    
    def _create_analysis_section(self):
        """분석 결과 영역 생성"""
        section_frame = QFrame()
        section_frame.setFrameShape(QFrame.Shape.StyledPanel)
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(12, 8, 12, 8)
        section_layout.setSpacing(8)
        
        # 섹션 타이틀
        section_title = QLabel("📋 Analysis Results")
        section_title_font = QFont()
        section_title_font.setBold(True)
        section_title_font.setPointSize(10)
        section_title.setFont(section_title_font)
        section_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(section_title)
        
        # 분석 결과 뷰 (스크롤 가능)
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText("분석 결과가 여기에 표시됩니다.\n위의 '분석 요청' 버튼을 클릭하여 분석을 시작하세요.")
        self.report_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 마크다운 예시 콘텐츠
        self.report_view.setMarkdown(
            "### 분석 결과가 없습니다\n\n"
            "분석을 요청하면 결과가 여기에 표시됩니다.\n\n"
            "**사용 방법:**\n"
            "1. 로그에서 분석하고 싶은 부분을 선택하거나\n"
            "2. 상단의 이슈 설명에 문제를 입력한 후\n"
            "3. '분석 요청' 버튼을 클릭하세요."
        )
        
        section_layout.addWidget(self.report_view)
        
        return section_frame
    
    def _create_chat_section(self):
        """채팅 영역 생성"""
        section_frame = QFrame()
        section_frame.setFrameShape(QFrame.Shape.StyledPanel)
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(12, 8, 12, 8)
        section_layout.setSpacing(8)
        
        # 섹션 타이틀
        section_title = QLabel("💬 Chat with AI")
        section_title_font = QFont()
        section_title_font.setBold(True)
        section_title_font.setPointSize(10)
        section_title.setFont(section_title_font)
        section_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        section_layout.addWidget(section_title)
        
        # 채팅 히스토리 영역
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("AI와의 대화 내용이 여기에 표시됩니다.")
        # size policy 설정으로 확장 가능하도록
        self.chat_history.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        section_layout.addWidget(self.chat_history, stretch=1)  # stretch 추가
        
        # 채팅 입력 영역
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("AI에게 추가 질문을 입력하세요...")
        self.chat_input.returnPressed.connect(self._on_send_message)
        self.chat_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self.chat_input)
        
        self.send_btn = QPushButton("전송")
        self.send_btn.setFixedWidth(60)
        self.send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.send_btn.clicked.connect(self._on_send_message)
        input_layout.addWidget(self.send_btn)
        
        section_layout.addLayout(input_layout)
        
        return section_frame
    
    def _setup_styles(self):
        """스타일 설정"""
        # 버튼 스타일
        button_style = """
            QPushButton {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 12px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1b1b1b;
            }
        """
        self.analyze_btn.setStyleSheet(button_style)
        self.send_btn.setStyleSheet(button_style)
        
        # 텍스트 에디터 스타일
        text_edit_style = """
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10pt;
            }
            QTextEdit:focus {
                border-color: #0078d4;
            }
        """
        self.report_view.setStyleSheet(text_edit_style)
        self.chat_history.setStyleSheet(text_edit_style)
        
        # 입력 필드 스타일
        line_edit_style = """
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px 8px;
                color: #d4d4d4;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """
        self.chat_input.setStyleSheet(line_edit_style)
        
        # 프레임 스타일
        frame_style = """
            QFrame {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """
        self.setStyleSheet(frame_style)
    
    def _on_analyze_clicked(self):
        """분석 요청 버튼 클릭"""
        # OpenCode 설치 상태 확인
        if self.opencode_status != "installed":
            self.report_view.setMarkdown(
                "### ⚠️ OpenCode가 설치되어 있지 않습니다\n\n"
                "AI 분석을 사용하려면 OpenCode가 필요합니다.\n\n"
                "위의 '설치' 버튼을 클릭하여 OpenCode를 설치하세요."
            )
            return
        
        # 메인 윈도우의 이슈 설명을 가져와서 시그널 발생
        # 실제로는 메인 윈도우에서 이슈 설명을 전달받아야 함
        self.analysis_requested.emit("")
    
    def _on_install_clicked(self):
        """OpenCode 설치 버튼 클릭"""
        self.opencode_install_requested.emit()
    
    def set_opencode_status(self, status: str, message: str = ""):
        """
        OpenCode 상태 업데이트 및 패널 전환
        
        Args:
            status: unknown, installed, not_installed, installing
            message: 상태 메시지
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AnalysisPanel] set_opencode_status 호출: status={status}, message={message}")
        logger.info(f"[AnalysisPanel] 현재 상태: {self.opencode_status}")
        logger.info(f"[AnalysisPanel] 사용 가능한 패널: {list(self.status_panels.keys())}")
        
        self.opencode_status = status
        
        # 모든 패널 숨기기
        for panel_name, panel in self.status_panels.items():
            logger.debug(f"[AnalysisPanel] 패널 '{panel_name}' 숨김")
            panel.setVisible(False)
        
        # 해당 상태의 패널만 표시
        if status in self.status_panels:
            logger.info(f"[AnalysisPanel] 패널 '{status}' 표시")
            self.status_panels[status].setVisible(True)
        else:
            logger.warning(f"[AnalysisPanel] 알 수 없는 상태: {status}, 사용 가능한 상태: {list(self.status_panels.keys())}")
        
        # 설치 중 상태 메시지 업데이트
        if status == "installing" and hasattr(self, 'install_status_label'):
            if message:
                self.install_status_label.setText(message)
            else:
                self.install_status_label.setText("npx를 통해 OpenCode를 다운로드하고 있습니다...")
        
        logger.info(f"[AnalysisPanel] 상태 업데이트 완료: {status}")
    
    def _on_send_message(self):
        """채팅 메시지 전송"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        # 채팅 히스토리에 사용자 메시지 추가
        self._add_chat_message("You", message, is_user=True)
        
        # 입력 필드 초기화
        self.chat_input.clear()
        
        # 시그널 발생
        self.chat_message_sent.emit(message)
    
    def _add_chat_message(self, sender, message, is_user=False):
        """채팅 히스토리에 메시지 추가"""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 사용자/AI 구분 색상
        if is_user:
            color = "#4ec9b0"  # 사용자 메시지 색상
            prefix = "👤"
        else:
            color = "#569cd6"  # AI 메시지 색상
            prefix = "🤖"
        
        # 메시지 포맷팅 - 각 메시지를 명확하게 구분되는 블록으로
        # display: block과 margin을 사용하여 줄바꿈 보장
        formatted_text = (
            f'<div style="display: block; margin-bottom: 12px; padding: 4px 0;">'
            f'<span style="color: {color}; font-weight: bold;">{prefix} {sender}:</span> '
            f'<span style="color: #d4d4d4;">{message}</span>'
            f'</div>'
        )
        
        cursor.insertHtml(formatted_text)
        # 줄바꿈을 명확하게 하기 위해 추가
        cursor.insertText("\n")
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()
    
    def set_analysis_result(self, markdown_text):
        """분석 결과 설정 (마크다운 형식)"""
        self.report_view.setMarkdown(markdown_text)
    
    def append_chat_response(self, message):
        """AI 응답을 채팅 히스토리에 추가"""
        self._add_chat_message("AI", message, is_user=False)
    
    def clear_analysis(self):
        """분석 결과 초기화"""
        self.report_view.clear()
        self.report_view.setPlaceholderText("분석 결과가 여기에 표시됩니다.")
    
    def clear_chat(self):
        """채팅 히스토리 초기화"""
        self.chat_history.clear()
