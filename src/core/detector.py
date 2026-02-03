"""에러 및 비정상 패턴 감지기"""
import re
import logging
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """에러 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorPattern:
    """에러 패턴 정의"""
    
    def __init__(self, name: str, pattern: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 description: str = ""):
        """
        Args:
            name: 패턴 이름
            pattern: 정규표현식 패턴
            severity: 심각도
            description: 패턴 설명
        """
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.severity = severity
        self.description = description
    
    def match(self, text: str) -> Optional[re.Match]:
        """텍스트에서 패턴 매칭"""
        return self.pattern.search(text)


class ErrorDetector:
    """에러 및 비정상 패턴 감지기"""
    
    def __init__(self):
        self.patterns: List[ErrorPattern] = []
        self.on_error_detected: Optional[Callable[[Dict[str, Any]], None]] = None
        self._init_default_patterns()
    
    def _init_default_patterns(self):
        """기본 에러 패턴 초기화"""
        # Android 일반 에러 패턴
        default_patterns = [
            ErrorPattern(
                "NullPointerException",
                r'NullPointerException',
                ErrorSeverity.HIGH,
                "Null 포인터 예외"
            ),
            ErrorPattern(
                "OutOfMemoryError",
                r'OutOfMemoryError',
                ErrorSeverity.CRITICAL,
                "메모리 부족 오류"
            ),
            ErrorPattern(
                "ANR",
                r'ANR\s+in',
                ErrorSeverity.CRITICAL,
                "Application Not Responding"
            ),
            ErrorPattern(
                "Crash",
                r'FATAL\s+EXCEPTION|Process.*died',
                ErrorSeverity.CRITICAL,
                "앱 크래시"
            ),
            ErrorPattern(
                "IllegalStateException",
                r'IllegalStateException',
                ErrorSeverity.MEDIUM,
                "잘못된 상태 예외"
            ),
            ErrorPattern(
                "NetworkError",
                r'NetworkError|SocketException|ConnectException',
                ErrorSeverity.MEDIUM,
                "네트워크 오류"
            ),
            ErrorPattern(
                "PermissionDenied",
                r'Permission\s+denied|SecurityException',
                ErrorSeverity.MEDIUM,
                "권한 거부"
            ),
            # AAOS 특화 패턴
            ErrorPattern(
                "VHALError",
                r'VHAL.*error|VehicleHal.*failed',
                ErrorSeverity.HIGH,
                "VHAL 오류"
            ),
            ErrorPattern(
                "CarServiceError",
                r'CarService.*error|CarService.*failed',
                ErrorSeverity.HIGH,
                "CarService 오류"
            ),
        ]
        
        self.patterns.extend(default_patterns)
        logger.info(f"[Detector] {len(self.patterns)}개의 기본 에러 패턴 초기화")
    
    def add_pattern(self, pattern: ErrorPattern):
        """커스텀 패턴 추가"""
        self.patterns.append(pattern)
        logger.info(f"[Detector] 패턴 추가: {pattern.name}")
    
    def detect(self, log_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        로그에서 에러 패턴 감지
        
        Args:
            log_data: 파싱된 로그 딕셔너리
            
        Returns:
            감지된 에러 정보 또는 None
            {
                'pattern': ErrorPattern,
                'match': re.Match,
                'log': Dict[str, Any],
                'severity': ErrorSeverity,
            }
        """
        if not log_data:
            return None
        
        level = log_data.get('level', '').upper()
        tag = log_data.get('tag', '')
        message = log_data.get('message', '')
        
        # 로그 레벨이 Error 이상인 경우
        if level in ['E', 'F', 'A']:
            # 패턴 매칭
            for pattern in self.patterns:
                match = pattern.match(message) or pattern.match(tag)
                if match:
                    error_info = {
                        'pattern': pattern,
                        'match': match,
                        'log': log_data,
                        'severity': pattern.severity,
                        'description': pattern.description,
                    }
                    
                    # 콜백 호출
                    if self.on_error_detected:
                        self.on_error_detected(error_info)
                    
                    return error_info
        
        return None
    
    def detect_in_text(self, text: str) -> List[Dict[str, Any]]:
        """
        텍스트에서 모든 에러 패턴 감지
        
        Args:
            text: 검색할 텍스트
            
        Returns:
            감지된 에러 정보 리스트
        """
        detected = []
        
        for pattern in self.patterns:
            match = pattern.match(text)
            if match:
                detected.append({
                    'pattern': pattern,
                    'match': match,
                    'severity': pattern.severity,
                    'description': pattern.description,
                })
        
        return detected
