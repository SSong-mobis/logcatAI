"""OpenCode 자동 설치 유틸리티"""
import subprocess
import os
import sys
import logging
import platform
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class OpenCodeInstaller:
    """OpenCode CLI 자동 설치 클래스"""
    
    def __init__(self):
        self.system = platform.system()
        self.node_required_version = (18, 0, 0)
    
    def check_nodejs(self) -> Tuple[bool, Optional[str]]:
        """
        Node.js 설치 확인
        
        Returns:
            (is_installed, version_string)
        """
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=2,
                shell=True if self.system == 'Windows' else False
            )
            if result.returncode == 0:
                version_str = result.stdout.strip()
                # v18.0.0 형식에서 숫자 추출
                version_str = version_str.lstrip('v')
                return True, version_str
            return False, None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, None
    
    def check_npm(self) -> Tuple[bool, Optional[str]]:
        """
        npm 설치 확인
        
        Returns:
            (is_installed, version_string)
        """
        try:
            result = subprocess.run(
                ['npm', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=2,
                shell=True if self.system == 'Windows' else False
            )
            if result.returncode == 0:
                version_str = result.stdout.strip()
                return True, version_str
            return False, None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, None
    
    def check_opencode(self) -> bool:
        """
        OpenCode CLI 설치 확인
        
        Returns:
            설치 여부
        """
        # npx를 통해 확인 (npx는 자동 다운로드 가능)
        try:
            result = subprocess.run(
                ['npx', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=2,
                shell=True if self.system == 'Windows' else False
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def install_opencode_via_npx(self) -> Tuple[bool, str]:
        """
        npx를 통해 OpenCode 설치 (전역 설치)
        
        Returns:
            (success, message)
        """
        try:
            # npx를 통해 한 번 실행하여 캐시에 저장
            logger.info("Installing OpenCode via npx...")
            result = subprocess.run(
                ['npx', '-y', '@opencode-ai/cli', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
                shell=True if self.system == 'Windows' else False
            )
            
            if result.returncode == 0:
                return True, "OpenCode is now available via npx"
            else:
                return False, f"Failed to install OpenCode: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
        except Exception as e:
            return False, f"Error installing OpenCode: {str(e)}"
    
    def install_opencode_global(self) -> Tuple[bool, str]:
        """
        npm을 통해 OpenCode 전역 설치
        
        Returns:
            (success, message)
        """
        try:
            logger.info("Installing OpenCode globally via npm...")
            result = subprocess.run(
                ['npm', 'install', '-g', '@opencode-ai/cli'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,  # 5분 타임아웃
                shell=True if self.system == 'Windows' else False
            )
            
            if result.returncode == 0:
                return True, "OpenCode installed successfully"
            else:
                return False, f"Failed to install OpenCode: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "Installation timed out"
        except Exception as e:
            return False, f"Error installing OpenCode: {str(e)}"
    
    def install_nodejs_instructions(self) -> str:
        """Node.js 설치 안내 메시지 반환"""
        if self.system == 'Windows':
            return (
                "Node.js가 설치되어 있지 않습니다.\n\n"
                "설치 방법:\n"
                "1. https://nodejs.org 에서 LTS 버전 다운로드 및 설치\n"
                "2. 또는 Chocolatey 사용: choco install nodejs-lts\n"
                "3. 설치 후 터미널을 재시작하세요."
            )
        elif self.system == 'Darwin':  # macOS
            return (
                "Node.js가 설치되어 있지 않습니다.\n\n"
                "설치 방법:\n"
                "1. Homebrew 사용: brew install node\n"
                "2. 또는 https://nodejs.org 에서 다운로드\n"
                "3. 설치 후 터미널을 재시작하세요."
            )
        else:  # Linux
            return (
                "Node.js가 설치되어 있지 않습니다.\n\n"
                "설치 방법:\n"
                "1. Ubuntu/Debian: sudo apt-get install nodejs npm\n"
                "2. 또는 nvm 사용: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash\n"
                "3. 설치 후 터미널을 재시작하세요."
            )
    
    def ensure_opencode_available(self) -> Tuple[bool, str]:
        """
        OpenCode가 사용 가능한지 확인하고, 없으면 설치 시도
        
        Returns:
            (is_available, message)
        """
        # Node.js 확인
        node_installed, node_version = self.check_nodejs()
        if not node_installed:
            return False, self.install_nodejs_instructions()
        
        logger.info(f"Node.js version: {node_version}")
        
        # npm 확인
        npm_installed, npm_version = self.check_npm()
        if not npm_installed:
            return False, "npm이 설치되어 있지 않습니다. Node.js를 재설치하세요."
        
        logger.info(f"npm version: {npm_version}")
        
        # OpenCode 확인 (npx 사용 가능하면 OK)
        if self.check_opencode():
            return True, "OpenCode is available via npx"
        
        # npx를 통해 한 번 실행하여 캐시에 저장
        success, message = self.install_opencode_via_npx()
        if success:
            return True, message
        
        # 실패 시 전역 설치 시도
        logger.info("Trying global installation...")
        success, message = self.install_opencode_global()
        return success, message


def check_and_install_opencode() -> Tuple[bool, str]:
    """
    OpenCode 설치 확인 및 자동 설치 (편의 함수)
    
    Returns:
        (is_available, message)
    """
    installer = OpenCodeInstaller()
    return installer.ensure_opencode_available()


if __name__ == "__main__":
    # 테스트용
    logging.basicConfig(level=logging.INFO)
    installer = OpenCodeInstaller()
    
    print("Checking Node.js...")
    node_installed, node_version = installer.check_nodejs()
    print(f"Node.js: {'✓' if node_installed else '✗'} {node_version or 'Not installed'}")
    
    print("\nChecking npm...")
    npm_installed, npm_version = installer.check_npm()
    print(f"npm: {'✓' if npm_installed else '✗'} {npm_version or 'Not installed'}")
    
    print("\nChecking OpenCode...")
    opencode_available = installer.check_opencode()
    print(f"OpenCode: {'✓' if opencode_available else '✗'}")
    
    if not opencode_available and node_installed:
        print("\nInstalling OpenCode...")
        success, message = installer.ensure_opencode_available()
        print(f"Result: {message}")
