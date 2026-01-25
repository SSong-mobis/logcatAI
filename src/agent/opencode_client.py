"""OpenCode CLI 래퍼 클래스"""
import subprocess
import json
import os
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class OpenCodeClient:
    """OpenCode CLI를 Python에서 사용하기 위한 래퍼 클래스"""
    
    def __init__(self, workspace_path: Optional[str] = None):
        """
        Args:
            workspace_path: OpenCode가 분석할 프로젝트 경로 (Git 저장소)
        """
        self.workspace_path = workspace_path
        self.opencode_cmd = self._find_opencode_command()
        
    def _find_opencode_command(self) -> str:
        """OpenCode CLI 명령어 찾기"""
        # npx를 우선적으로 사용 (npm 설치 문제를 피하기 위해)
        try:
            result = subprocess.run(
                ['npx', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=2,
                shell=True  # Windows에서 실행 정책 문제를 피하기 위해
            )
            if result.returncode == 0:
                logger.info("Using OpenCode via npx (recommended)")
                return 'npx'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 전역 설치 확인 (선택사항)
        try:
            result = subprocess.run(
                ['opencode', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=2,
                shell=True
            )
            if result.returncode == 0:
                logger.info("OpenCode CLI found in PATH")
                return 'opencode'
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        logger.warning("OpenCode CLI not found. Will try to use npx automatically.")
        return 'npx'  # 기본값으로 npx 사용 (자동 다운로드)
    
    def _run_opencode(self, command: List[str], input_data: Optional[str] = None) -> Dict[str, Any]:
        """
        OpenCode CLI 명령 실행
        
        Args:
            command: OpenCode 명령어 리스트
            input_data: stdin으로 전달할 데이터
            
        Returns:
            실행 결과 딕셔너리
        """
        if self.opencode_cmd == 'npx':
            cmd = ['npx', '-y', '@opencode-ai/cli'] + command
        else:
            cmd = [self.opencode_cmd] + command
        
        try:
            env = os.environ.copy()
            if self.workspace_path:
                # 작업 디렉토리를 프로젝트 경로로 설정
                cwd = self.workspace_path
            else:
                cwd = None
            
            process = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,  # 5분 타임아웃
                cwd=cwd,
                env=env,
                shell=True  # Windows PowerShell 실행 정책 문제 해결
            )
            
            result = {
                'success': process.returncode == 0,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'returncode': process.returncode
            }
            
            if not result['success']:
                logger.error(f"OpenCode command failed: {result['stderr']}")
            
            return result
            
        except subprocess.TimeoutExpired:
            logger.error("OpenCode command timed out")
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out after 5 minutes',
                'returncode': -1
            }
        except Exception as e:
            logger.error(f"Error running OpenCode: {str(e)}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def analyze_issue(self, issue_description: str, log_context: Optional[str] = None, 
                     selected_code: Optional[str] = None) -> Dict[str, Any]:
        """
        이슈 설명과 로그 컨텍스트를 기반으로 분석 요청
        
        Args:
            issue_description: 사용자가 입력한 이슈 설명
            log_context: 관련 로그 컨텍스트 (최근 에러 로그 등)
            selected_code: 선택된 코드 스니펫 (선택사항)
            
        Returns:
            분석 결과 딕셔너리
        """
        # 프롬프트 구성
        prompt_parts = []
        
        if issue_description:
            prompt_parts.append(f"## Issue Description\n{issue_description}\n")
        
        if log_context:
            prompt_parts.append(f"## Log Context\n```\n{log_context}\n```\n")
        
        if selected_code:
            prompt_parts.append(f"## Selected Code\n```\n{selected_code}\n```\n")
        
        prompt_parts.append("\nPlease analyze this issue and provide:\n")
        prompt_parts.append("1. Root cause analysis\n")
        prompt_parts.append("2. Suggested fixes\n")
        prompt_parts.append("3. Code changes if applicable\n")
        
        full_prompt = "\n".join(prompt_parts)
        
        # OpenCode run 명령 실행
        # 참고: OpenCode는 프로젝트 컨텍스트를 자동으로 인덱싱하여 사용
        command = ['run', full_prompt]
        
        logger.info("Running OpenCode analysis...")
        result = self._run_opencode(command)
        
        if result['success']:
            return {
                'success': True,
                'analysis': result['stdout'],
                'raw_output': result['stdout']
            }
        else:
            return {
                'success': False,
                'error': result['stderr'],
                'analysis': None
            }
    
    def chat(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        OpenCode와 대화형 채팅
        
        Args:
            message: 사용자 메시지
            conversation_history: 이전 대화 기록 (선택사항)
            
        Returns:
            AI 응답 딕셔너리
        """
        # 대화 히스토리가 있으면 프롬프트에 포함
        if conversation_history:
            history_text = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
                for msg in conversation_history
            ])
            full_prompt = f"{history_text}\n\nUser: {message}\nAI:"
        else:
            full_prompt = message
        
        command = ['run', full_prompt]
        
        logger.info("Sending chat message to OpenCode...")
        result = self._run_opencode(command)
        
        if result['success']:
            return {
                'success': True,
                'response': result['stdout'],
                'raw_output': result['stdout']
            }
        else:
            return {
                'success': False,
                'error': result['stderr'],
                'response': None
            }
    
    def set_workspace(self, workspace_path: str):
        """작업 공간 경로 설정"""
        if os.path.exists(workspace_path):
            self.workspace_path = workspace_path
            logger.info(f"Workspace set to: {workspace_path}")
        else:
            logger.warning(f"Workspace path does not exist: {workspace_path}")
    
    def check_installation(self) -> bool:
        """OpenCode CLI 설치 확인"""
        try:
            if self.opencode_cmd == 'npx':
                # npx는 항상 사용 가능 (없으면 자동 다운로드)
                # npx가 실제로 작동하는지 확인
                result = subprocess.run(
                    ['npx', '--version'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=2,
                    shell=True
                )
                return result.returncode == 0
            else:
                result = subprocess.run(
                    [self.opencode_cmd, '--version'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=2,
                    shell=True
                )
                return result.returncode == 0
        except:
            return False
