"""로그 수집기 - ADB logcat 및 파일 로그 수집"""
import subprocess
import os
import logging
from typing import Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class LogCollector:
    """로그 수집기 기본 클래스"""
    
    def __init__(self):
        self.is_running = False
        self.is_paused = False
    
    def start(self):
        """수집 시작"""
        self.is_running = True
    
    def stop(self):
        """수집 중지"""
        self.is_running = False
    
    def pause(self):
        """일시정지"""
        self.is_paused = True
    
    def resume(self):
        """재개"""
        self.is_paused = False


class ADBLogCollector(LogCollector):
    """ADB logcat을 통한 실시간 로그 수집"""
    
    def __init__(self, logcat_filter='*:V', buffer='main', format_type='threadtime'):
        super().__init__()
        self.logcat_filter = logcat_filter
        self.buffer = buffer
        self.format_type = format_type
        self.process = None
        self.on_log_received: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    def _find_adb_path(self) -> str:
        """adb.exe 경로 찾기"""
        # PATH에서 찾기
        adb_path = 'adb'
        try:
            result = subprocess.run(
                ['adb', 'version'], 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='replace', 
                timeout=2
            )
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
    
    def collect(self):
        """logcat 실행 및 수집"""
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
            
            logger.info(f"[Collector] Starting logcat: {' '.join(logcat_cmd)}")
            
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
                if line and self.on_log_received:
                    self.on_log_received(line)
            
        except Exception as e:
            error_msg = f"ADB Error: {str(e)}"
            logger.error(f"[Collector] {error_msg}")
            if self.on_error:
                self.on_error(error_msg)
        finally:
            if self.process:
                self.process.terminate()
                self.process.wait()
    
    def stop(self):
        """수집 중지"""
        super().stop()
        if self.process:
            self.process.terminate()


class FileLogCollector(LogCollector):
    """파일에서 로그 읽기"""
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = Path(file_path)
        self.on_log_received: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    def collect(self):
        """파일에서 로그 읽기"""
        if not self.file_path.exists():
            error_msg = f"File not found: {self.file_path}"
            logger.error(f"[Collector] {error_msg}")
            if self.on_error:
                self.on_error(error_msg)
            return
        
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if not self.is_running:
                        break
                    
                    if self.is_paused:
                        continue
                    
                    line = line.strip()
                    if line and self.on_log_received:
                        self.on_log_received(line)
        except Exception as e:
            error_msg = f"File read error: {str(e)}"
            logger.error(f"[Collector] {error_msg}")
            if self.on_error:
                self.on_error(error_msg)
