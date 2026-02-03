"""로그 버퍼 관리 - 슬라이딩 윈도우 컨텍스트 버퍼"""
from collections import deque
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LogBuffer:
    """로그 버퍼 - 최근 N개의 로그를 메모리에 보관"""
    
    def __init__(self, max_size: int = 1000):
        """
        Args:
            max_size: 최대 보관 로그 수
        """
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
        self.error_logs: deque = deque(maxlen=100)  # 에러 로그만 별도 보관
    
    def add(self, log_data: Dict[str, Any]):
        """
        로그 추가
        
        Args:
            log_data: 파싱된 로그 딕셔너리
        """
        if not log_data:
            return
        
        self.buffer.append(log_data)
        
        # 에러 레벨 로그는 별도 보관
        level = log_data.get('level', '').upper()
        if level in ['E', 'F', 'A']:  # Error, Fatal, Assert
            self.error_logs.append(log_data)
    
    def get_recent(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        최근 N개의 로그 반환
        
        Args:
            count: 가져올 로그 수
            
        Returns:
            최근 로그 리스트
        """
        return list(self.buffer)[-count:]
    
    def get_error_logs(self, count: int = 50) -> List[Dict[str, Any]]:
        """
        최근 에러 로그 반환
        
        Args:
            count: 가져올 에러 로그 수
            
        Returns:
            최근 에러 로그 리스트
        """
        return list(self.error_logs)[-count:]
    
    def get_context_around_error(self, error_index: int, context_lines: int = 10) -> List[Dict[str, Any]]:
        """
        특정 에러 주변의 컨텍스트 로그 반환
        
        Args:
            error_index: 에러 로그 인덱스
            context_lines: 앞뒤로 가져올 로그 수
            
        Returns:
            컨텍스트 로그 리스트
        """
        if error_index < 0 or error_index >= len(self.error_logs):
            return []
        
        error_log = self.error_logs[error_index]
        error_timestamp = error_log.get('timestamp', '')
        
        # 전체 버퍼에서 해당 에러 주변 로그 찾기
        context = []
        found_error = False
        
        for log in self.buffer:
            if log == error_log:
                found_error = True
                context.append(log)
            elif found_error:
                context.append(log)
                if len(context) >= context_lines * 2 + 1:
                    break
            elif error_timestamp and log.get('timestamp') == error_timestamp:
                # 타임스탬프로 찾기
                found_error = True
                context.append(log)
        
        return context
    
    def clear(self):
        """버퍼 초기화"""
        self.buffer.clear()
        self.error_logs.clear()
    
    def size(self) -> int:
        """현재 버퍼 크기"""
        return len(self.buffer)
    
    def error_count(self) -> int:
        """에러 로그 수"""
        return len(self.error_logs)
