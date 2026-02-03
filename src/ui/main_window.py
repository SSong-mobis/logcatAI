import sys
import subprocess
import os
import re
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QComboBox, QLabel, 
                             QStatusBar, QTabWidget, QMenuBar, QMessageBox,
                             QFileDialog, QDockWidget, QToolBar)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

from ui.log_table import LogTable
from ui.dashboard.container import DashboardContainer
from ui.analysis_panel import AnalysisPanel
from agent.analyzer import LogAnalyzer
from utils.opencode_installer import OpenCodeInstaller
from PyQt6.QtCore import QThread, pyqtSignal

# OpenCodeInstallThread는 opencode_page.py에서 import

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Logcat AI - AAOS Analysis Tool")
        self.resize(1400, 900)
        
        # Current workspace info
        self.current_project = None
        self.current_branch = None
        
        # AI Analyzer 초기화
        self.analyzer = LogAnalyzer()
        
        # OpenCode 설치 확인 (백그라운드에서)
        self._check_opencode_setup()
        
        # Create menu bar
        self._create_menu_bar()
        
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 1. Top Bar (Device Settings only)
        top_bar = self._create_top_bar()
        main_layout.addLayout(top_bar)
        
        # 2. Issue Description Input
        issue_layout = QHBoxLayout()
        issue_label = QLabel("이슈 설명:")
        issue_label.setFixedWidth(70)
        issue_layout.addWidget(issue_label)
        
        self.issue_input = QLineEdit()
        self.issue_input.setPlaceholderText("어떤 문제를 해결하고 싶나요? (예: 결제 버튼 클릭 시 앱 멈춤 현상 분석 요청...)")
        self.issue_input.setFixedHeight(40)
        issue_layout.addWidget(self.issue_input)
        main_layout.addLayout(issue_layout)
        
        # 3. Tab Widget (Log View, Dashboard, OpenCode)
        self.tabs = QTabWidget()
        
        self.log_table = LogTable()
        self.dashboard = DashboardContainer()
        self.analysis_panel = AnalysisPanel()
        
        # OpenCode 전용 페이지 생성
        from ui.opencode_page import OpenCodePage
        self.opencode_page = OpenCodePage()
        
        # 분석 패널 시그널 연결
        self.analysis_panel.analysis_requested.connect(self._on_analysis_requested)
        self.analysis_panel.chat_message_sent.connect(self._on_chat_message_sent)
        self.analysis_panel.opencode_install_requested.connect(self._on_opencode_install_requested)
        self.analysis_panel.open_settings_requested.connect(lambda: self.tabs.setCurrentWidget(self.opencode_page))
        
        # LogTable 상태 메시지를 메인 윈도우 상태바에 연결
        self.log_table.status_message.connect(self._on_log_table_status)
        
        # OpenCode 상태 확인 및 UI 업데이트
        self._check_opencode_status()
        
        self.tabs.addTab(self.log_table, "📋 Log View")
        self.tabs.addTab(self.dashboard, "📊 Dashboard")
        self.tabs.addTab(self.opencode_page, "🤖 OpenCode")
        
        # 디바이스 변경 시 대시보드에 알림
        self.device_combo.currentTextChanged.connect(self._on_device_changed)
        
        main_layout.addWidget(self.tabs)
        
        # 4. AI Analysis를 사이드 패널(Dock Widget)로 추가
        self._create_ai_analysis_dock()
        
        # 4. Status Bar
        self.setStatusBar(QStatusBar())
        self._update_status_bar()
        
        # 초기 LogTable 상태 표시
        self.log_table.status_message.emit("준비")

    def _create_menu_bar(self):
        menubar = self.menuBar()
        
        # File 메뉴
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Load Logcat File...", self._load_logcat_file)
        file_menu.addAction("Save Logs As...", self._save_logs_as)
        file_menu.addSeparator()
        file_menu.addAction("Clear Logs", self._clear_logs)
        
        # Workspace 메뉴
        workspace_menu = menubar.addMenu("Workspace")
        workspace_menu.addAction("Manage Workspaces...", self._open_workspace_manager)
        workspace_menu.addSeparator()
        workspace_menu.addAction("Load Project", self._load_project)
        workspace_menu.addAction("Close Project", self._close_project)
        
        # Settings 메뉴
        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction("Preferences...", self._open_preferences)
    
    def _load_logcat_file(self):
        """로그캣 파일 로드"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Logcat File",
            "",
            "Text Files (*.txt);;Log Files (*.log);;All Files (*)"
        )
        
        if file_path:
            self.log_table.load_logcat_file(file_path)
    
    def _save_logs_as(self):
        """로그를 파일로 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Logs As",
            "",
            "Text Files (*.txt);;Log Files (*.log);;All Files (*)"
        )
        
        if file_path:
            self.log_table.save_logs_to_file(file_path)
    
    def _clear_logs(self):
        """로그 초기화"""
        self.log_table.clear_all_logs()
    
    def _open_workspace_manager(self):
        from ui.components.workspace_dialog import WorkspaceDialog
        dialog = WorkspaceDialog(self)
        if dialog.exec():
            # Workspace 설정 완료
            self.current_project = dialog.get_selected_project()
            self.current_branch = dialog.get_selected_branch()
            self._update_status_bar()
    
    def _load_project(self):
        if not self.current_project:
            self._open_workspace_manager()
            return
        # TODO: 실제 프로젝트 로드 로직 (Git clone 등)
        QMessageBox.information(self, "Project Loading", f"Loading {self.current_project} ({self.current_branch})...\nThis will clone the repository and index it for OpenCode.")
    
    def _close_project(self):
        self.current_project = None
        self.current_branch = None
        self._update_status_bar()
        QMessageBox.information(self, "Project Closed", "Current project has been closed.")
    
    def _open_preferences(self):
        """설정 다이얼로그 열기"""
        from ui.components.preferences_dialog import PreferencesDialog
        dialog = PreferencesDialog(self)
        if dialog.exec():
            # 설정이 변경되었으면 OpenCode 상태 다시 확인
            self._check_opencode_status()
    
    def _create_ai_analysis_dock(self):
        """AI Analysis를 사이드 패널(Dock Widget)로 생성"""
        # Dock Widget 생성
        self.ai_analysis_dock = QDockWidget("🤖 AI Analysis", self)
        self.ai_analysis_dock.setWidget(self.analysis_panel)
        
        # 오른쪽에 배치
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ai_analysis_dock)
        
        # 기본 너비 설정 (사이드 패널일 때만 적용)
        self.ai_analysis_dock.setMinimumWidth(300)  # 최소 너비
        self.ai_analysis_dock.setMaximumWidth(800)  # 최대 너비
        
        # 기본적으로 숨김 상태로 시작 (필요시 주석 해제하여 기본 표시)
        # self.ai_analysis_dock.setVisible(True)
        
        # 토글 가능하도록 설정
        self.ai_analysis_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        
        # 도킹 위치 변경 시 크기 조정
        self.ai_analysis_dock.dockLocationChanged.connect(self._on_dock_location_changed)
        
        # 툴바에 토글 버튼 추가
        toolbar = QToolBar("AI Analysis", self)
        toggle_action = toolbar.addAction("🤖")
        toggle_action.setCheckable(True)
        toggle_action.setChecked(False)
        toggle_action.triggered.connect(self._toggle_ai_analysis)
        self.addToolBar(Qt.ToolBarArea.RightToolBarArea, toolbar)
    
    def _on_dock_location_changed(self, area):
        """도킹 위치가 변경될 때 크기 조정"""
        if area == Qt.DockWidgetArea.TopDockWidgetArea or area == Qt.DockWidgetArea.BottomDockWidgetArea:
            # 상단/하단 도킹 시 가로 너비를 창 너비에 맞춤
            self.ai_analysis_dock.setMinimumWidth(0)  # 최소 너비 제한 해제
            self.ai_analysis_dock.setMaximumWidth(16777215)  # 최대 너비 제한 해제 (Qt의 최대값)
            # 높이 제한 설정
            self.ai_analysis_dock.setMinimumHeight(200)
            self.ai_analysis_dock.setMaximumHeight(400)
        else:
            # 좌우 사이드 패널일 때는 가로 너비 제한 적용
            self.ai_analysis_dock.setMinimumWidth(300)
            self.ai_analysis_dock.setMaximumWidth(800)
            # 높이 제한 해제
            self.ai_analysis_dock.setMinimumHeight(0)
            self.ai_analysis_dock.setMaximumHeight(16777215)
    
    def _toggle_ai_analysis(self, checked):
        """AI Analysis 사이드 패널 토글"""
        self.ai_analysis_dock.setVisible(checked)
    
    def _check_opencode_setup(self):
        """OpenCode 설치 확인 및 안내 (백그라운드)"""
        # 백그라운드에서 확인 (UI 블로킹 방지)
        def check_in_background():
            installer = OpenCodeInstaller()
            node_installed, _ = installer.check_nodejs()
            opencode_available = installer.check_opencode()
            
            if not node_installed:
                # Node.js가 없으면 나중에 분석 요청 시 안내
                return
            elif not opencode_available:
                # OpenCode가 없으면 자동 설치 시도
                success, message = installer.ensure_opencode_available()
                if not success:
                    # 설치 실패 시 사용자에게 안내 (나중에 분석 요청 시)
                    logger.warning(f"OpenCode setup failed: {message}")
        
        # 별도 스레드에서 실행
        import threading
        thread = threading.Thread(target=check_in_background, daemon=True)
        thread.start()
    
    def _check_opencode_status(self):
        """OpenCode 상태 확인 및 UI 업데이트"""
        logger.info("[OpenCode] 상태 확인 시작")
        # QThread를 사용하여 상태 확인
        self.status_check_thread = OpenCodeStatusCheckThread(self.analyzer)
        self.status_check_thread.status_checked.connect(self._on_status_checked)
        logger.info("[OpenCode] 스레드 시작")
        self.status_check_thread.start()
    
    def _on_status_checked(self, status: str, message: str):
        """상태 확인 완료 처리 (메인 스레드에서 호출)"""
        logger.info(f"[OpenCode] 상태 확인 완료: status={status}, message={message}")
        self.analysis_panel.set_opencode_status(status, message)
        logger.info(f"[OpenCode] UI 업데이트 완료")
    
    def _on_opencode_install_requested(self):
        """OpenCode 설치 요청 처리"""
        installer = OpenCodeInstaller()
        node_installed, _ = installer.check_nodejs()
        
        if not node_installed:
            QMessageBox.warning(
                self,
                "Node.js 미설치",
                installer.install_nodejs_instructions()
            )
            return
        
        # 설치 확인 다이얼로그
        reply = QMessageBox.question(
            self,
            "OpenCode 설치",
            "OpenCode CLI를 설치하시겠습니까?\n\n"
            "npx를 통해 자동으로 다운로드됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 설치 스레드 시작
            self.install_thread = OpenCodeInstallThread(installer)
            self.install_thread.install_progress.connect(self._on_install_progress)
            self.install_thread.install_complete.connect(self._on_install_complete)
            self.install_thread.install_error.connect(self._on_install_error)
            self.install_thread.start()
            
            self.analysis_panel.set_opencode_status("installing", "OpenCode 설치 중...")
    
    def _on_install_progress(self, message: str):
        """설치 진행 상황 업데이트"""
        logger.info(f"[OpenCode] 설치 진행: {message}")
        self.analysis_panel.set_opencode_status("installing", message)
    
    def _on_install_complete(self, success: bool, message: str):
        """설치 완료 처리"""
        logger.info(f"[OpenCode] 설치 완료: success={success}, message={message}")
        if success:
            self.analysis_panel.set_opencode_status("installed", message)
            QMessageBox.information(self, "설치 완료", "OpenCode가 성공적으로 설치되었습니다.")
        else:
            self.analysis_panel.set_opencode_status("not_installed", message)
            QMessageBox.warning(self, "설치 실패", f"OpenCode 설치에 실패했습니다:\n\n{message}")
    
    def _on_install_error(self, error: str):
        """설치 오류 처리"""
        logger.error(f"[OpenCode] 설치 오류: {error}")
        self.analysis_panel.set_opencode_status("not_installed", error)
        QMessageBox.critical(self, "설치 오류", f"오류가 발생했습니다:\n\n{error}")
    
    def _on_analysis_requested(self, _):
        """분석 요청 처리"""
        issue_description = self.issue_input.text().strip()
        if not issue_description:
            QMessageBox.information(self, "알림", "이슈 설명을 입력해주세요.")
            return
        
        # OpenCode 설치 확인 및 자동 설치 시도
        installer = OpenCodeInstaller()
        node_installed, node_version = installer.check_nodejs()
        
        if not node_installed:
            QMessageBox.warning(
                self,
                "Node.js 미설치",
                installer.install_nodejs_instructions()
            )
            return
        
        if not self.analyzer.check_installation():
            # OpenCode 자동 설치 시도
            reply = QMessageBox.question(
                self,
                "OpenCode 설치",
                "OpenCode CLI가 설치되어 있지 않습니다.\n\n"
                "지금 자동으로 설치하시겠습니까?\n"
                "(npx를 통해 자동 다운로드됩니다)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 설치 진행 다이얼로그 표시
                QMessageBox.information(
                    self,
                    "OpenCode 설치 중",
                    "OpenCode를 설치하고 있습니다.\n"
                    "잠시만 기다려주세요..."
                )
                
                success, message = installer.ensure_opencode_available()
                if not success:
                    QMessageBox.warning(
                        self,
                        "설치 실패",
                        f"OpenCode 설치에 실패했습니다:\n\n{message}\n\n"
                        "수동으로 설치해주세요:\n"
                        "npm install -g @opencode-ai/cli"
                    )
                    return
            else:
                return
        
        # 작업 공간 설정 (프로젝트가 로드된 경우)
        if self.current_project:
            # workspace 폴더 경로 구성 (실제 구현 시 경로 조정 필요)
            workspace_path = f"workspace/{self.current_project.split('/')[-1]}"
            self.analyzer.set_workspace(workspace_path)
        
        # 분석 시작 (비동기)
        self.analysis_thread = AnalysisThread(self.analyzer, issue_description, self.log_table.get_recent_logs())
        self.analysis_thread.analysis_complete.connect(self._on_analysis_complete)
        self.analysis_thread.analysis_error.connect(self._on_analysis_error)
        self.analysis_thread.start()
    
    def _on_analysis_complete(self, result: dict):
        """분석 완료 처리"""
        logger.info(f"[Analysis] 완료: success={result.get('success')}")
        if result.get('success'):
            analysis_text = result.get('analysis', '분석 결과가 없습니다.')
            self.analysis_panel.set_analysis_result(analysis_text)
            self.analysis_panel.append_chat_response("분석이 완료되었습니다.")
        else:
            error = result.get('error', '알 수 없는 오류')
            self.analysis_panel.set_analysis_result(
                f"### 분석 실패\n\n**오류**: {error}\n\n"
                f"OpenCode CLI 설치 및 설정을 확인해주세요."
            )
    
    def _on_analysis_error(self, error_message: str):
        """분석 오류 처리"""
        logger.error(f"[Analysis] 오류: {error_message}")
        self.analysis_panel.set_analysis_result(
            f"### 분석 오류\n\n**오류 메시지**: {error_message}\n\n"
            f"OpenCode CLI 실행 중 문제가 발생했습니다."
        )
        self.analysis_panel.append_chat_response(f"오류: {error_message}")
    
    def _on_chat_message_sent(self, message):
        """채팅 메시지 전송 처리"""
        # OpenCode 설치 확인
        if not self.analyzer.check_installation():
            self.analysis_panel.append_chat_response(
                "OpenCode CLI가 설치되어 있지 않습니다. "
                "npm install -g @opencode-ai/cli 명령으로 설치해주세요."
            )
            return
        
        # 비동기 채팅 스레드 시작
        self.chat_thread = ChatThread(self.analyzer, message)
        self.chat_thread.chat_complete.connect(self._on_chat_complete)
        self.chat_thread.chat_error.connect(self._on_chat_error)
        self.chat_thread.start()
    
    def _on_chat_complete(self, result: dict):
        """채팅 응답 완료 처리"""
        if result.get('success'):
            response = result.get('response', '응답이 없습니다.')
            self.analysis_panel.append_chat_response(response)
        else:
            error = result.get('error', '알 수 없는 오류')
            self.analysis_panel.append_chat_response(f"오류: {error}")
    
    def _on_chat_error(self, error_message: str):
        """채팅 오류 처리"""
        self.analysis_panel.append_chat_response(f"오류: {error_message}")
    
    def _on_device_changed(self, device_text):
        """디바이스 변경 시 대시보드에 디바이스 ID 전달"""
        if device_text and device_text != "No devices found":
            # 디바이스 ID 추출
            device_id = device_text
            if '(' in device_text and ')' in device_text:
                match = re.search(r'\(([^)]+)\)', device_text)
                if match:
                    device_id = match.group(1)
            self.dashboard.set_device_id(device_id)
        else:
            self.dashboard.set_device_id(None)
    
    def _update_status_bar(self):
        # 현재 선택된 디바이스 정보 가져오기
        device_text = self.device_combo.currentText()
        device_info = device_text if device_text and device_text != "No devices found" else "No device"
        
        if self.current_project:
            project_display = f"{self.current_project.split('/')[-1]} ({self.current_branch})"
            self.project_label.setText(project_display)
            self.project_label.setStyleSheet("color: green; font-weight: bold;")
            self.statusBar().showMessage(f"Project: {self.current_project} | Branch: {self.current_branch} | Device: {device_info}")
        else:
            self.project_label.setText("No project loaded")
            self.project_label.setStyleSheet("color: gray; font-style: italic;")
            self.statusBar().showMessage(f"No project loaded | Device: {device_info}")
    
    def _on_log_table_status(self, message: str):
        print(f"[MainWindow] LogTable 상태 메시지 수신: {message}")
        """LogTable에서 상태 메시지 수신하여 상태바에 표시"""
        # 기존 상태바 메시지에 LogTable 상태 추가
        device_text = self.device_combo.currentText()
        device_info = device_text if device_text and device_text != "No devices found" else "No device"
        
        if self.current_project:
            project_info = f"Project: {self.current_project.split('/')[-1]} ({self.current_branch})"
            self.statusBar().showMessage(f"{project_info} | Device: {device_info} | {message}")
        else:
            self.statusBar().showMessage(f"No project loaded | Device: {device_info} | {message}")
    
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
    
    def _refresh_devices(self):
        """adb devices로 연결된 디바이스 목록 새로고침"""
        adb_path = self._find_adb_path()
        current_selection = self.device_combo.currentText()
        
        try:
            result = subprocess.run(
                [adb_path, 'devices'],
                capture_output=True,
                text=True,
                timeout=5,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode != 0:
                QMessageBox.warning(self, "ADB Error", f"Failed to run 'adb devices':\n{result.stderr}")
                return
            
            # 디바이스 목록 파싱
            devices = []
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # 첫 번째 줄은 "List of devices attached" 스킵
                line = line.strip()
                if not line or 'offline' in line.lower():
                    continue
                
                # 형식: "device_id    device" 또는 "device_id    unauthorized"
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    device_id = parts[0]
                    # 디바이스 이름 추출 시도 (adb -s device_id shell getprop ro.product.model)
                    try:
                        name_result = subprocess.run(
                            [adb_path, '-s', device_id, 'shell', 'getprop', 'ro.product.model'],
                            capture_output=True,
                            text=True,
                            timeout=2,
                            encoding='utf-8',
                            errors='ignore'
                        )
                        if name_result.returncode == 0 and name_result.stdout.strip():
                            device_name = name_result.stdout.strip()
                            devices.append(f"{device_name} ({device_id})")
                        else:
                            devices.append(device_id)
                    except:
                        devices.append(device_id)
            
            # ComboBox 업데이트
            self.device_combo.clear()
            if devices:
                self.device_combo.addItems(devices)
                # 이전 선택 유지
                if current_selection in devices:
                    self.device_combo.setCurrentText(current_selection)
                elif current_selection:
                    # 이전 선택이 목록에 없으면 첫 번째 항목 선택
                    self.device_combo.setCurrentIndex(0)
            else:
                self.device_combo.addItem("No devices found")
                self.device_combo.setEnabled(False)
                self.conn_btn.setEnabled(False)
            
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Timeout", "ADB command timed out. Please check your ADB connection.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to refresh devices: {str(e)}")
    
    def _connect_device(self):
        """선택된 디바이스에 연결"""
        device_text = self.device_combo.currentText()
        if not device_text or device_text == "No devices found":
            QMessageBox.warning(self, "No Device", "Please select a device first.")
            return
        
        # 디바이스 ID 추출 (예: "Pixel 6 Pro (emulator-5554)" -> "emulator-5554")
        device_id = device_text
        if '(' in device_text and ')' in device_text:
            match = re.search(r'\(([^)]+)\)', device_text)
            if match:
                device_id = match.group(1)
        
        # 연결 상태 확인
        adb_path = self._find_adb_path()
        try:
            result = subprocess.run(
                [adb_path, '-s', device_id, 'shell', 'echo', 'connected'],
                capture_output=True,
                text=True,
                timeout=3,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                # 대시보드에 디바이스 ID 전달
                self.dashboard.set_device_id(device_id)
                QMessageBox.information(self, "Connected", f"Successfully connected to:\n{device_text}")
                self._update_status_bar()
            else:
                QMessageBox.warning(self, "Connection Failed", f"Failed to connect to:\n{device_text}")
                # 연결 실패 시 대시보드에서 디바이스 ID 제거
                self.dashboard.set_device_id(None)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Connection error: {str(e)}")
    
    def _create_top_bar(self):
        layout = QHBoxLayout()
        
        # Current Project Info (Read-only display)
        self.project_label = QLabel("No project loaded")
        self.project_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(QLabel("Current Project:"))
        layout.addWidget(self.project_label)
        
        layout.addSpacing(20)
        
        # Device Selector
        layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        layout.addWidget(self.device_combo)
        
        self.refresh_devices_btn = QPushButton("🔄 Refresh")
        self.refresh_devices_btn.clicked.connect(self._refresh_devices)
        layout.addWidget(self.refresh_devices_btn)
        
        self.conn_btn = QPushButton("Connect")
        self.conn_btn.clicked.connect(self._connect_device)
        layout.addWidget(self.conn_btn)
        
        # 초기 디바이스 목록 로드
        self._refresh_devices()
        
        layout.addStretch()
        
        return layout


class OpenCodeStatusCheckThread(QThread):
    """OpenCode 상태 확인을 수행하는 백그라운드 스레드"""
    status_checked = pyqtSignal(str, str)  # status, message
    
    def __init__(self, analyzer: LogAnalyzer):
        super().__init__()
        self.analyzer = analyzer
        import logging
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """상태 확인 실행"""
        self.logger.info("[OpenCodeStatusCheckThread] run() 시작")
        try:
            from utils.opencode_installer import OpenCodeInstaller
            installer = OpenCodeInstaller()
            self.logger.info("[OpenCodeStatusCheckThread] Node.js 확인 중...")
            node_installed, node_version = installer.check_nodejs()
            self.logger.info(f"[OpenCodeStatusCheckThread] Node.js 확인 결과: installed={node_installed}, version={node_version}")
            
            if not node_installed:
                self.logger.info("[OpenCodeStatusCheckThread] Node.js 미설치 - not_installed 시그널 발생")
                self.status_checked.emit("not_installed", "Node.js가 설치되어 있지 않습니다.")
                return
            
            # OpenCode 확인
            self.logger.info("[OpenCodeStatusCheckThread] OpenCode 설치 확인 중...")
            opencode_installed = self.analyzer.check_installation()
            self.logger.info(f"[OpenCodeStatusCheckThread] OpenCode 확인 결과: installed={opencode_installed}")
            
            if opencode_installed:
                self.logger.info("[OpenCodeStatusCheckThread] OpenCode 설치됨 - installed 시그널 발생")
                self.status_checked.emit("installed", f"Node.js {node_version}")
            else:
                self.logger.info("[OpenCodeStatusCheckThread] OpenCode 미설치 - not_installed 시그널 발생")
                self.status_checked.emit("not_installed", "OpenCode가 설치되어 있지 않습니다.")
        except Exception as e:
            self.logger.error(f"[OpenCodeStatusCheckThread] 오류 발생: {str(e)}", exc_info=True)
            self.status_checked.emit("not_installed", f"상태 확인 중 오류 발생: {str(e)}")


class OpenCodeInstallThread(QThread):
    """OpenCode 설치를 수행하는 백그라운드 스레드"""
    install_progress = pyqtSignal(str)
    install_complete = pyqtSignal(bool, str)
    install_error = pyqtSignal(str)
    
    def __init__(self, installer: OpenCodeInstaller):
        super().__init__()
        self.installer = installer
        import logging
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """OpenCode 설치 실행"""
        try:
            self.install_progress.emit("Node.js 확인 중...")
            self.logger.info("[OpenCodeInstallThread] Node.js 확인 중...")
            node_installed, node_version = self.installer.check_nodejs()
            if not node_installed:
                self.install_complete.emit(False, "Node.js가 설치되어 있지 않습니다.")
                return
            
            self.install_progress.emit("npm 확인 중...")
            self.logger.info("[OpenCodeInstallThread] npm 확인 중...")
            npm_installed, _ = self.installer.check_npm()
            if not npm_installed:
                self.install_complete.emit(False, "npm이 설치되어 있지 않습니다.")
                return
            
            self.install_progress.emit("OpenCode 설치 중...")
            self.logger.info("[OpenCodeInstallThread] OpenCode 설치 중...")
            success, message = self.installer.ensure_opencode_available()
            self.logger.info(f"[OpenCodeInstallThread] 설치 완료: success={success}, message={message}")
            self.install_complete.emit(success, message)
        except Exception as e:
            self.logger.error(f"[OpenCodeInstallThread] 오류 발생: {str(e)}", exc_info=True)
            self.install_error.emit(str(e))


class AnalysisThread(QThread):
    """분석 작업을 수행하는 백그라운드 스레드"""
    analysis_complete = pyqtSignal(dict)
    analysis_error = pyqtSignal(str)
    
    def __init__(self, analyzer: LogAnalyzer, issue_description: str, log_context: list):
        super().__init__()
        self.analyzer = analyzer
        self.issue_description = issue_description
        self.log_context = log_context
    
    def run(self):
        """분석 실행"""
        try:
            result = self.analyzer.analyze(
                issue_description=self.issue_description,
                selected_logs=self.log_context
            )
            self.analysis_complete.emit(result)
        except Exception as e:
            self.analysis_error.emit(str(e))


class ChatThread(QThread):
    """채팅 작업을 수행하는 백그라운드 스레드"""
    chat_complete = pyqtSignal(dict)
    chat_error = pyqtSignal(str)
    
    def __init__(self, analyzer: LogAnalyzer, message: str):
        super().__init__()
        self.analyzer = analyzer
        self.message = message
    
    def run(self):
        """채팅 실행"""
        try:
            result = self.analyzer.chat(self.message)
            self.chat_complete.emit(result)
        except Exception as e:
            self.chat_error.emit(str(e))


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # TODO: Setup dark theme (pyqtdarktheme.apply() when available)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
