"""로그 파서 - 로그 라인을 구조화된 데이터로 변환"""
import re
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Rust 파서 사용 시도 (최우선)
RUST_PARSER_AVAILABLE = False
try:
    from core.parser_rust import RustLogParser
    RUST_PARSER_AVAILABLE = True
    logger.info("[Parser] Rust 파서 사용 가능 - 고성능 모드")
except ImportError:
    logger.debug("[Parser] Rust 파서를 사용할 수 없음")

# pylogcatparser 라이브러리 사용 시도
PARSER_AVAILABLE = False
LogCatParser = None

try:
    from pylogcatparser import LogCatParser
    PARSER_AVAILABLE = True
    logger.info("[Parser] pylogcatparser 라이브러리 사용 가능")
except ImportError:
    logger.debug("[Parser] pylogcatparser 라이브러리를 사용할 수 없음 - fallback 파싱 사용")


class LogParser:
    """로그 라인 파서 (Rust 파서 우선 사용)"""
    
    def __init__(self, format_type: str = 'threadtime', use_rust: bool = True):
        """
        Args:
            format_type: 로그 형식 (threadtime, time, brief 등)
            use_rust: Rust 파서 사용 여부 (기본값: True, 사용 가능한 경우)
        """
        self.format_type = format_type
        self.use_rust = use_rust and RUST_PARSER_AVAILABLE
        
        # Rust 파서 초기화
        if self.use_rust:
            try:
                self.rust_parser = RustLogParser(format_type=format_type)
                logger.info("[Parser] ✅ Rust 파서 초기화 완료 - 고성능 모드 활성화")
            except Exception as e:
                logger.warning(f"[Parser] ⚠️ Rust 파서 초기화 실패: {str(e)}, Python 파서 사용")
                self.use_rust = False
                self.rust_parser = None
        else:
            self.rust_parser = None
            if not RUST_PARSER_AVAILABLE:
                logger.debug("[Parser] Rust 파서를 사용할 수 없음 (모듈 미설치)")
    
    def parse(self, line: str) -> Optional[Dict[str, Any]]:
        """
        로그 라인을 파싱하여 구조화된 데이터로 변환
        
        Args:
            line: 로그 라인 문자열
            
        Returns:
            파싱된 로그 딕셔너리 또는 None (파싱 실패 시)
            {
                'timestamp': str,
                'level': str,
                'pid': str,
                'tid': str,
                'tag': str,
                'message': str,
                'display': str,  # AAOS 다중 디스플레이 분류
            }
        """
        line = line.strip()
        if not line:
            return None
        
        # Rust 파서 우선 사용 (가장 빠름)
        if self.use_rust and self.rust_parser:
            try:
                result = self.rust_parser.parse(line)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"[Parser] Rust 파싱 실패, fallback 사용: {str(e)}")
        
        # pylogcatparser 라이브러리 사용 시도 (threadtime 형식)
        if PARSER_AVAILABLE and LogCatParser and self.format_type == 'threadtime':
            try:
                parser = LogCatParser("threadtime")
                
                # 라이브러리의 parse 메서드 사용 시도
                try:
                    if hasattr(parser, 'parse_line'):
                        parsed_obj = parser.parse_line(line)
                    elif hasattr(parser, 'parse'):
                        parsed_obj = parser.parse(line)
                    else:
                        # build_log_line을 사용하려면 정규식으로 먼저 매칭 필요
                        threadtime_regex = r'^(\d{2}\-\d{2})\s+(\d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+(\d+|\-)\s+([VDIWEAF]|\-)\s+([^:]+):\s+(.*)$'
                        match = re.search(threadtime_regex, line)
                        if match:
                            groups = match.groups()
                            parsed_obj = parser.build_log_line(groups)
                        else:
                            raise ValueError("No match")
                    
                    # 파싱된 결과에서 필요한 정보 추출
                    if isinstance(parsed_obj, dict):
                        date = parsed_obj.get('date', '')
                        time_str = parsed_obj.get('time', '')
                        timestamp = f"{date} {time_str}".strip() if date and time_str else ''
                        
                        # level 변환
                        level_str = parsed_obj.get('level', '')
                        level_map = {
                            "verbose": "V", "debug": "D", "info": "I", 
                            "warn": "W", "error": "E", "fatal": "F", "assert": "A"
                        }
                        if level_str in level_map:
                            level = level_map[level_str]
                        elif level_str and level_str[0].upper() in ["V", "D", "I", "W", "E", "F", "A"]:
                            level = level_str[0].upper()
                        else:
                            level = "-"
                        
                        tag = parsed_obj.get('tag', 'Unknown')
                        message = parsed_obj.get('message', '')
                        pid = str(parsed_obj.get('pid', ''))
                        tid = str(parsed_obj.get('tid', ''))
                        
                        # Display ID 자동 분류 (AAOS)
                        display = self._classify_display(tag, message)
                        
                        return {
                            'timestamp': timestamp,
                            'level': level,
                            'pid': pid,
                            'tid': tid,
                            'tag': tag,
                            'message': message,
                            'display': display,
                        }
                    else:
                        raise ValueError("Unexpected parser result type")
                except (AttributeError, ValueError, TypeError) as e:
                    logger.debug(f"[Parser] 라이브러리 파싱 실패: {str(e)}")
                    # fallback 사용
                    pass
            except Exception as e:
                logger.debug(f"[Parser] 라이브러리 사용 실패: {str(e)}")
                # fallback 사용
                pass
        
        # Fallback: 직접 파싱
        return self._parse_fallback(line)
    
    def _parse_fallback(self, line: str) -> Optional[Dict[str, Any]]:
        """Fallback 파싱 (정규식 기반)"""
        # 시간 패턴 찾기
        time_pattern = r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'
        time_match = re.match(time_pattern, line)
        
        if not time_match:
            return None
        
        timestamp = time_match.group(1)
        remaining = line[len(timestamp):].strip()
        
        # 형식 1: mm-dd HH:MM:SS.mmm  PID  -  -  Tag: Message (Level 없음)
        threadtime_simple_pattern = r'^(\d+)\s+-\s+-\s+([^:]+):\s+(.*)$'
        threadtime_simple_match = re.match(threadtime_simple_pattern, remaining)
        if threadtime_simple_match:
            pid = threadtime_simple_match.group(1)
            tid = '-'
            tag = threadtime_simple_match.group(2).strip()
            message = threadtime_simple_match.group(3).strip()
            level = "-"
            display = self._classify_display(tag, message)
            return {
                'timestamp': timestamp,
                'level': level,
                'pid': pid,
                'tid': tid,
                'tag': tag,
                'message': message,
                'display': display,
            }
        
        # 형식 2: mm-dd HH:MM:SS.mmm  Level  -  -  PID  TID  Level  Tag: Message
        threadtime_complex_pattern = r'^([VDIWEAF])\s+-\s+-\s+(\d+)\s+(\d+)\s+([VDIWEAF])\s+([^:]+):\s*(.*)$'
        threadtime_complex_match = re.match(threadtime_complex_pattern, remaining)
        if threadtime_complex_match:
            level = threadtime_complex_match.group(4)
            pid = threadtime_complex_match.group(2)
            tid = threadtime_complex_match.group(3)
            tag = threadtime_complex_match.group(5).strip()
            message = threadtime_complex_match.group(6).strip()
            display = self._classify_display(tag, message)
            return {
                'timestamp': timestamp,
                'level': level,
                'pid': pid,
                'tid': tid,
                'tag': tag,
                'message': message,
                'display': display,
            }
        
        # 형식 3: Level/Tag(  PID  TID  Message
        level_tag_pattern = r'^([DIWEFV])/([^(]+)\(\s*([^)]*?)\s*\)\s+(.*)$'
        level_tag_match = re.match(level_tag_pattern, remaining)
        if level_tag_match:
            level = level_tag_match.group(1)
            tag = level_tag_match.group(2).strip()
            pid_tid = level_tag_match.group(3).strip()
            message = level_tag_match.group(4).strip()
            
            # PID와 TID 분리
            pid_tid_parts = pid_tid.split()
            pid = pid_tid_parts[0] if pid_tid_parts else '-'
            tid = pid_tid_parts[1] if len(pid_tid_parts) > 1 else '-'
            
            display = self._classify_display(tag, message)
            return {
                'timestamp': timestamp,
                'level': level,
                'pid': pid,
                'tid': tid,
                'tag': tag,
                'message': message,
                'display': display,
            }
        
        # 파싱 실패
        return None
    
    def _classify_display(self, tag: str, message: str) -> str:
        """
        AAOS 다중 디스플레이 자동 분류
        
        Args:
            tag: 로그 태그
            message: 로그 메시지
            
        Returns:
            Display ID 또는 "Main"
        """
        # Display ID 패턴 찾기
        display_patterns = [
            (r'displayId[:\s]+(\d+)', 'displayId'),
            (r'display[:\s]+(\d+)', 'display'),
            (r'Display\s+(\d+)', 'Display'),
        ]
        
        for pattern, _ in display_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                display_id = match.group(1)
                # Display ID에 따른 분류
                if display_id == '0':
                    return 'Main'
                elif display_id == '1':
                    return 'Cluster'
                elif display_id == '2':
                    return 'IVI'
                else:
                    return f'Display {display_id}'
        
        # 태그 기반 분류
        tag_lower = tag.lower()
        if 'cluster' in tag_lower:
            return 'Cluster'
        elif 'ivi' in tag_lower or 'infotainment' in tag_lower:
            return 'IVI'
        elif 'passenger' in tag_lower:
            return 'Passenger'
        
        # 기본값
        return 'Main'
