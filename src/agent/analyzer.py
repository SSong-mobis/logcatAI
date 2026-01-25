"""이슈 설명 기반 분석 및 프롬프트 관리"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .opencode_client import OpenCodeClient

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """로그 분석 및 OpenCode 연동 클래스"""
    
    def __init__(self, workspace_path: Optional[str] = None):
        """
        Args:
            workspace_path: 프로젝트 작업 공간 경로
        """
        self.client = OpenCodeClient(workspace_path)
        self.conversation_history: List[Dict[str, str]] = []
        
    def analyze(self, issue_description: str, log_context: Optional[str] = None,
                selected_logs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        이슈 설명과 로그 컨텍스트를 기반으로 분석 수행
        
        Args:
            issue_description: 사용자가 입력한 이슈 설명
            log_context: 로그 컨텍스트 문자열 (직접 제공)
            selected_logs: 선택된 로그 리스트 (구조화된 데이터)
            
        Returns:
            분석 결과 딕셔너리
        """
        # 로그 컨텍스트 구성
        if selected_logs and not log_context:
            log_context = self._format_logs_for_analysis(selected_logs)
        
        # OpenCode 분석 요청
        result = self.client.analyze_issue(
            issue_description=issue_description,
            log_context=log_context
        )
        
        if result['success']:
            # 대화 히스토리에 추가
            self.conversation_history.append({
                'role': 'user',
                'content': f"Issue: {issue_description}"
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': result['analysis']
            })
        
        return result
    
    def chat(self, message: str) -> Dict[str, Any]:
        """
        OpenCode와 대화형 채팅
        
        Args:
            message: 사용자 메시지
            
        Returns:
            AI 응답 딕셔너리
        """
        result = self.client.chat(
            message=message,
            conversation_history=self.conversation_history
        )
        
        if result['success']:
            # 대화 히스토리에 추가
            self.conversation_history.append({
                'role': 'user',
                'content': message
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': result['response']
            })
        
        return result
    
    def _format_logs_for_analysis(self, logs: List[Dict[str, Any]], max_lines: int = 100) -> str:
        """
        구조화된 로그 데이터를 분석용 텍스트로 변환
        
        Args:
            logs: 로그 딕셔너리 리스트
            max_lines: 최대 라인 수 (너무 많으면 잘라냄)
            
        Returns:
            포맷된 로그 문자열
        """
        if not logs:
            return ""
        
        # 최근 로그만 선택
        selected_logs = logs[-max_lines:] if len(logs) > max_lines else logs
        
        formatted_lines = []
        for log in selected_logs:
            # 로그 형식: [Timestamp] Level Tag: Message
            timestamp = log.get('timestamp', '')
            level = log.get('level', 'I')
            tag = log.get('tag', '')
            message = log.get('message', '')
            display = log.get('display', '')
            
            if display:
                line = f"[{timestamp}] {level}/{tag} [{display}]: {message}"
            else:
                line = f"[{timestamp}] {level}/{tag}: {message}"
            
            formatted_lines.append(line)
        
        return "\n".join(formatted_lines)
    
    def clear_history(self):
        """대화 히스토리 초기화"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def set_workspace(self, workspace_path: str):
        """작업 공간 경로 설정"""
        self.client.set_workspace(workspace_path)
    
    def check_installation(self) -> bool:
        """OpenCode 설치 확인"""
        return self.client.check_installation()
