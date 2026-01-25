import subprocess
import os
import re
import json
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QPushButton, QMenu, QMessageBox, QInputDialog, QLineEdit, QComboBox, QCheckBox, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QRect
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent, QMouseEvent, QCursor, QPainter, QColor, QPen, QLinearGradient, QBrush
from collections import deque

logger = logging.getLogger(__name__)

class BaseWidget(QFrame):
    """대시보드 위젯의 기본 클래스"""
    widget_closed = pyqtSignal(object)  # 위젯 삭제 시그널
    widget_dragged = pyqtSignal(object, QPoint)  # 위젯 드래그 시그널
    widget_resized = pyqtSignal(object, int, int)  # 위젯 크기 변경 시그널 (그리드 단위)
    
    # 그리드 셀 크기 정의
    CELL_WIDTH = 280
    CELL_HEIGHT = 200
    CELL_SPACING = 10
    
    def __init__(self, title, parent=None, icon="📊", accent_color="#4a9eff", grid_cols=1, grid_rows=1):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.icon = icon
        self.accent_color = accent_color
        self.grid_cols = grid_cols  # 그리드 열 수 (1, 2, 3...)
        self.grid_rows = grid_rows  # 그리드 행 수 (1, 2, 3...)
        
        # 그리드 단위로 크기 계산
        width = (self.CELL_WIDTH * grid_cols) + (self.CELL_SPACING * (grid_cols - 1))
        height = (self.CELL_HEIGHT * grid_rows) + (self.CELL_SPACING * (grid_rows - 1))
        self.setFixedSize(width, height)  # 고정 크기
        
        # 드래그 관련 변수
        self.drag_start_position = None
        self.is_dragging = False
        
        # 스타일 적용
        self._apply_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 헤더 (아이콘 + 제목 + 닫기 버튼)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 아이콘
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(icon_label)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            font-weight: bold; 
            font-size: 13px; 
            color: {self.accent_color};
            background: transparent;
        """)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setMaximumSize(24, 24)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid #555;
                border-radius: 12px;
                font-size: 14px;
                color: #aaa;
            }}
            QPushButton:hover {{
                background-color: #ff4444;
                border: 1px solid #ff6666;
                color: white;
            }}
        """)
        self.close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(self.close_btn)
        
        layout.addLayout(header_layout)
        
        # 콘텐츠 영역 (서브클래스에서 구현)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        layout.addWidget(self.content_widget)
        
        # 마우스 추적 활성화
        self.setMouseTracking(True)
    
    def _apply_style(self):
        """위젯 스타일 적용"""
        self.setStyleSheet(f"""
            BaseWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e1e2e, stop:1 #2b2b3d);
                border: 2px solid {self.accent_color}40;
                border-radius: 12px;
                padding: 8px;
            }}
            BaseWidget:hover {{
                border: 2px solid {self.accent_color}80;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252538, stop:1 #2f2f42);
            }}
        """)
    
    def mousePressEvent(self, event):
        """마우스 누름 이벤트 (드래그 시작)"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 드래그만 가능, 리사이즈는 비활성화
            self.drag_start_position = event.position().toPoint()
            self.is_dragging = False
        elif event.button() == Qt.MouseButton.RightButton:
            # 우클릭 메뉴로 크기 변경
            self._show_size_menu(event.globalPosition().toPoint())
        super().mousePressEvent(event)
    
    def _show_size_menu(self, global_pos):
        """위젯 크기 변경 메뉴 표시"""
        menu = QMenu(self)
        menu.setTitle("Widget Size")
        
        sizes = [
            ("1x1", 1, 1),
            ("1x2", 1, 2),
            ("2x1", 2, 1),
            ("2x2", 2, 2),
            ("2x3", 2, 3),
            ("3x2", 3, 2),
        ]
        
        for label, cols, rows in sizes:
            action = QAction(f"{label} ({cols}x{rows})", self)
            if self.grid_cols == cols and self.grid_rows == rows:
                action.setEnabled(False)  # 현재 크기는 비활성화
            action.triggered.connect(lambda checked, c=cols, r=rows: self._change_size(c, r))
            menu.addAction(action)
        
        menu.exec(global_pos)
    
    def _change_size(self, cols, rows):
        """위젯 크기 변경 (그리드 단위)"""
        self.grid_cols = cols
        self.grid_rows = rows
        width = (self.CELL_WIDTH * cols) + (self.CELL_SPACING * (cols - 1))
        height = (self.CELL_HEIGHT * rows) + (self.CELL_SPACING * (rows - 1))
        self.setFixedSize(width, height)
        # 크기 변경 시 서브클래스에서 폰트 크기 업데이트
        if hasattr(self, '_update_font_size'):
            self._update_font_size()
        self.widget_resized.emit(self, cols, rows)
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트 (드래그 중)"""
        pos = event.position().toPoint()
        
        if self.drag_start_position is not None:
            # 드래그 중
            distance = (pos - self.drag_start_position).manhattanLength()
            if distance > 10:  # 10픽셀 이상 이동하면 드래그 시작
                if not self.is_dragging:
                    self.is_dragging = True
                    # 드래그 시작 시각 효과
                    self.setStyleSheet(f"""
                        BaseWidget {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2a3a4a, stop:1 #3a4a5a);
                            border: 2px solid {self.accent_color};
                            border-radius: 12px;
                            padding: 8px;
                            opacity: 0.9;
                        }}
                    """)
                    self.raise_()  # 위젯을 맨 앞으로
                # 드래그 위치 전달
                global_pos = self.mapToGlobal(pos)
                self.widget_dragged.emit(self, global_pos)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """마우스 놓기 이벤트 (드래그 종료)"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                # 드래그 종료 시각 효과 제거
                self._apply_style()
                self.is_dragging = False
            self.drag_start_position = None
        super().mouseReleaseEvent(event)
    
    def _on_close(self):
        """위젯 닫기"""
        reply = QMessageBox.question(
            self, "Delete Widget", 
            f"Delete '{self.title_label.text()}' widget?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.widget_closed.emit(self)
            self.deleteLater()
    
    def update_data(self, data):
        """데이터 업데이트 (서브클래스에서 구현)"""
        pass


class GraphWidget(QWidget):
    """그래프를 그리는 위젯"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_history = []  # 데이터 히스토리 [(value, timestamp), ...]
        self.max_history = 50  # 최대 저장 개수
        self.min_value = 0
        self.max_value = 100
        self.line_color = QColor(0, 255, 0)  # 초록색
        self.setMinimumHeight(80)
        self._needs_update = False  # 업데이트 필요 플래그
    
    def add_data_point(self, value):
        """데이터 포인트 추가"""
        import time
        timestamp = time.time()
        self.data_history.append((value, timestamp))
        
        # 최대 개수 제한
        if len(self.data_history) > self.max_history:
            self.data_history.pop(0)
        
        # min/max 값 업데이트 (필요할 때만)
        if self.data_history:
            values = [v for v, _ in self.data_history]
            new_min = min(values) * 0.9 if min(values) > 0 else 0
            new_max = max(values) * 1.1 if max(values) < 100 else 100
            
            # 값이 크게 변하지 않으면 스케일 업데이트 스킵
            if abs(new_min - self.min_value) > (self.max_value - self.min_value) * 0.1 or \
               abs(new_max - self.max_value) > (self.max_value - self.min_value) * 0.1:
                self.min_value = new_min
                self.max_value = new_max
        
        self._needs_update = True
    
    def paintEvent(self, event):
        """그래프 그리기 (업데이트 필요할 때만)"""
        if not self._needs_update and not self.data_history:
            return
        
        self._needs_update = False
        if not self.data_history:
            return
    
    def clear_history(self):
        """히스토리 초기화"""
        self.data_history = []
        self.update()
    
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        padding = 5
        
        # 배경 그리기 (그라데이션)
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(25, 25, 35))
        gradient.setColorAt(1, QColor(20, 20, 30))
        painter.fillRect(0, 0, width, height, QBrush(gradient))
        
        # 데이터 범위 계산
        value_range = self.max_value - self.min_value
        if value_range == 0:
            value_range = 1
        
        # 그래프 영역
        graph_x = padding
        graph_y = padding
        graph_width = width - 2 * padding
        graph_height = height - 2 * padding
        
        # 그리드 라인 그리기 (간소화: 3개만, 반투명)
        pen = QPen(QColor(60, 60, 70, 100), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for i in range(3):
            y = graph_y + (graph_height * i / 2)
            painter.drawLine(graph_x, int(y), graph_x + graph_width, int(y))
        
        # 데이터 라인 그리기
        if len(self.data_history) > 1:
            pen = QPen(self.line_color, 2)
            painter.setPen(pen)
            
            # 포인트 계산 최적화 (샘플링)
            num_points = len(self.data_history)
            if num_points > 30:
                # 30개 이상이면 샘플링하여 그리기
                step = num_points / 30
                points = []
                for i in range(30):
                    idx = int(i * step)
                    if idx < num_points:
                        value, _ = self.data_history[idx]
                        x = graph_x + (graph_width * i / 29)
                        normalized_value = (value - self.min_value) / value_range
                        y = graph_y + graph_height - (graph_height * normalized_value)
                        points.append((int(x), int(y)))
            else:
                points = []
                for idx, (value, _) in enumerate(self.data_history):
                    x = graph_x + (graph_width * idx / (num_points - 1))
                    normalized_value = (value - self.min_value) / value_range
                    y = graph_y + graph_height - (graph_height * normalized_value)
                    points.append((int(x), int(y)))
            
            # 라인 그리기 (두께 증가)
            pen = QPen(self.line_color, 2.5)
            painter.setPen(pen)
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
            
            # 그라데이션 영역 채우기 (선 아래)
            if len(points) > 1:
                gradient = QLinearGradient(0, graph_y, 0, graph_y + graph_height)
                fill_color = QColor(self.line_color)
                fill_color.setAlpha(30)
                gradient.setColorAt(0, fill_color)
                fill_color.setAlpha(0)
                gradient.setColorAt(1, fill_color)
                
                # 폴리곤으로 영역 채우기
                from PyQt6.QtGui import QPolygon
                polygon = QPolygon()
                polygon.append(QPoint(graph_x, graph_y + graph_height))  # 왼쪽 하단
                for x, y in points:
                    polygon.append(QPoint(x, y))
                polygon.append(QPoint(graph_x + graph_width, graph_y + graph_height))  # 오른쪽 하단
                painter.setBrush(QBrush(gradient))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(polygon)
            
            # 마지막 포인트 강조 (더 크게)
            if points:
                pen = QPen(self.line_color, 1)
                painter.setPen(pen)
                painter.setBrush(self.line_color)
                painter.drawEllipse(points[-1][0] - 4, points[-1][1] - 4, 8, 8)
                # 외곽 흰색 원
                painter.setBrush(Qt.BrushStyle.NoBrush)
                pen = QPen(QColor(255, 255, 255, 150), 1)
                painter.setPen(pen)
                painter.drawEllipse(points[-1][0] - 5, points[-1][1] - 5, 10, 10)


class CPUWidget(BaseWidget):
    """CPU 사용률 위젯"""
    def __init__(self, parent=None, grid_cols=1, grid_rows=1):
        super().__init__("CPU Usage", parent, icon="⚡", accent_color="#00ff88", grid_cols=grid_cols, grid_rows=grid_rows)
        
        # 그래프 표시 체크박스
        self.show_graph_cb = QCheckBox("Show Graph")
        self.show_graph_cb.setStyleSheet("color: #aaa; font-size: 10px;")
        self.show_graph_cb.setChecked(False)
        self.show_graph_cb.toggled.connect(self._on_graph_toggle)
        header_layout = self.layout().itemAt(0).layout()  # 헤더 레이아웃 가져오기
        header_layout.insertWidget(1, self.show_graph_cb)
        
        self.value_label = QLabel("0%")
        self._update_font_size()  # 그리드 크기에 따라 폰트 크기 조정
        self.content_layout.addWidget(self.value_label)
    
    def _update_font_size(self):
        """그리드 크기에 따라 폰트 크기 조정"""
        total_cells = self.grid_cols * self.grid_rows
        if total_cells >= 4:  # 2x2 이상
            font_size = 40
        elif total_cells >= 2:  # 1x2 또는 2x1
            font_size = 36
        else:  # 1x1
            font_size = 32
        
        self.value_label.setStyleSheet(f"""
            font-size: {font_size}px; 
            color: #00ff88; 
            font-weight: bold;
            background: transparent;
            padding: 5px;
        """)
        
        # 그래프 위젯
        self.graph_widget = GraphWidget(self)
        self.graph_widget.line_color = QColor(0, 255, 136)  # 네온 그린
        self.graph_widget.setVisible(False)
        self.content_layout.addWidget(self.graph_widget)
        
        self.content_layout.addStretch()
    
    def _on_graph_toggle(self, checked):
        """그래프 표시 토글"""
        self.graph_widget.setVisible(checked)
        # 그래프 표시 여부에 따라 폰트 크기 조정
        self._update_font_size()
    
    def update_data(self, data):
        """CPU 사용률 업데이트"""
        if isinstance(data, (int, float)):
            self.value_label.setText(f"{data:.1f}%")
            self._update_font_size()  # 그리드 크기에 맞게 폰트 크기 조정
            if self.show_graph_cb.isChecked():
                self.graph_widget.add_data_point(data)
        elif isinstance(data, str):
            self.value_label.setText(data)
            # 연결 안됨 메시지는 다른 스타일로 표시
            if "연결 안됨" in data or "Error" in data or "N/A" in data:
                total_cells = self.grid_cols * self.grid_rows
                font_size = 20 if total_cells == 1 else 24
                self.value_label.setStyleSheet(f"""
                    font-size: {font_size}px; 
                    color: #ff6666; 
                    font-weight: bold;
                    background: transparent;
                    padding: 5px;
                """)
            else:
                self._update_font_size()


class MemoryWidget(BaseWidget):
    """메모리 사용량 위젯"""
    def __init__(self, parent=None, grid_cols=1, grid_rows=1):
        super().__init__("Memory", parent, icon="💾", accent_color="#4a9eff", grid_cols=grid_cols, grid_rows=grid_rows)
        
        # 그래프 표시 체크박스
        self.show_graph_cb = QCheckBox("Show Graph")
        self.show_graph_cb.setStyleSheet("color: #aaa; font-size: 10px;")
        self.show_graph_cb.setChecked(False)
        self.show_graph_cb.toggled.connect(self._on_graph_toggle)
        header_layout = self.layout().itemAt(0).layout()  # 헤더 레이아웃 가져오기
        header_layout.insertWidget(1, self.show_graph_cb)
        
        self.value_label = QLabel("0 MB / 0 MB")
        self.percent_label = QLabel("0%")
        self._update_font_size()  # 그리드 크기에 따라 폰트 크기 조정
        self.content_layout.addWidget(self.value_label)
        self.content_layout.addWidget(self.percent_label)
    
    def _update_font_size(self):
        """그리드 크기에 따라 폰트 크기 조정"""
        total_cells = self.grid_cols * self.grid_rows
        if total_cells >= 4:  # 2x2 이상
            value_font = 24
            percent_font = 20
        elif total_cells >= 2:  # 1x2 또는 2x1
            value_font = 22
            percent_font = 18
        else:  # 1x1
            value_font = 20
            percent_font = 16
        
        self.value_label.setStyleSheet(f"""
            font-size: {value_font}px; 
            color: #4a9eff; 
            font-weight: bold;
            background: transparent;
        """)
        self.percent_label.setStyleSheet(f"""
            font-size: {percent_font}px; 
            color: #88aaff; 
            background: transparent;
        """)
        
        # 그래프 위젯
        self.graph_widget = GraphWidget(self)
        self.graph_widget.line_color = QColor(74, 158, 255)  # 밝은 파란색
        self.graph_widget.setVisible(False)
        self.content_layout.addWidget(self.graph_widget)
        
        self.content_layout.addStretch()
    
    def _on_graph_toggle(self, checked):
        """그래프 표시 토글"""
        self.graph_widget.setVisible(checked)
    
    def update_data(self, data):
        """메모리 사용량 업데이트"""
        if isinstance(data, dict):
            used = data.get('used', 0)
            total = data.get('total', 0)
            percent = (used / total * 100) if total > 0 else 0
            self.value_label.setText(f"{used:.1f} MB / {total:.1f} MB")
            self.percent_label.setText(f"{percent:.1f}%")
            self._update_font_size()  # 그리드 크기에 맞게 폰트 크기 조정
            if self.show_graph_cb.isChecked():
                self.graph_widget.add_data_point(percent)
        elif isinstance(data, str):
            self.value_label.setText(data)
            self.percent_label.setText("")
            # 연결 안됨 메시지는 다른 스타일로 표시
            if "연결 안됨" in data or "Error" in data or "N/A" in data:
                total_cells = self.grid_cols * self.grid_rows
                font_size = 18 if total_cells == 1 else 22
                self.value_label.setStyleSheet(f"""
                    font-size: {font_size}px; 
                    color: #ff6666; 
                    font-weight: bold;
                    background: transparent;
                """)
            else:
                self._update_font_size()


class VHALWidget(BaseWidget):
    """VHAL Property 모니터링 위젯"""
    def __init__(self, property_id=None, property_name=None, parent=None, grid_cols=1, grid_rows=1):
        title = f"VHAL: {property_name or property_id or 'Property'}"
        super().__init__(title, parent, icon="🚗", accent_color="#ffaa00", grid_cols=grid_cols, grid_rows=grid_rows)
        self.property_id = property_id
        self.property_name = property_name
        
        # 그래프 표시 체크박스
        self.show_graph_cb = QCheckBox("Show Graph")
        self.show_graph_cb.setStyleSheet("color: #aaa; font-size: 10px;")
        self.show_graph_cb.setChecked(False)
        self.show_graph_cb.toggled.connect(self._on_graph_toggle)
        header_layout = self.layout().itemAt(0).layout()  # 헤더 레이아웃 가져오기
        header_layout.insertWidget(1, self.show_graph_cb)
        
        self.value_label = QLabel("-")
        self._update_font_size()  # 그리드 크기에 따라 폰트 크기 조정
        self.content_layout.addWidget(self.value_label)
        
        if self.property_id:
            id_label = QLabel(f"ID: {self.property_id}")
            id_label.setStyleSheet("""
                font-size: 11px; 
                color: #888; 
                background: transparent;
            """)
            self.content_layout.addWidget(id_label)
        
        # 그래프 위젯
        self.graph_widget = GraphWidget(self)
        self.graph_widget.line_color = QColor(255, 170, 0)  # 오렌지
        self.graph_widget.setVisible(False)
        self.content_layout.addWidget(self.graph_widget)
        
        self.content_layout.addStretch()
    
    def _update_font_size(self):
        """그리드 크기에 따라 폰트 크기 조정"""
        total_cells = self.grid_cols * self.grid_rows
        if total_cells >= 4:  # 2x2 이상
            font_size = 24
        elif total_cells >= 2:  # 1x2 또는 2x1
            font_size = 22
        else:  # 1x1
            font_size = 20
        
        self.value_label.setStyleSheet(f"""
            font-size: {font_size}px; 
            color: #ffaa00; 
            font-weight: bold;
            background: transparent;
        """)
    
    def _on_graph_toggle(self, checked):
        """그래프 표시 토글"""
        self.graph_widget.setVisible(checked)
    
    def update_data(self, data):
        """VHAL Property 값 업데이트"""
        if isinstance(data, (int, float)):
            self.value_label.setText(str(data))
            self._update_font_size()  # 그리드 크기에 맞게 폰트 크기 조정
            if self.show_graph_cb.isChecked():
                self.graph_widget.add_data_point(float(data))
        elif isinstance(data, str):
            self.value_label.setText(str(data))
            # 연결 안됨 메시지는 다른 스타일로 표시
            if "연결 안됨" in data or "Error" in data or "N/A" in data or "Invalid" in data:
                total_cells = self.grid_cols * self.grid_rows
                font_size = 18 if total_cells == 1 else 22
                self.value_label.setStyleSheet(f"""
                    font-size: {font_size}px; 
                    color: #ff6666; 
                    font-weight: bold;
                    background: transparent;
                """)
            else:
                self._update_font_size()
            # 숫자로 변환 가능하면 그래프에 추가
            if self.show_graph_cb.isChecked():
                try:
                    num_value = float(data)
                    self.graph_widget.add_data_point(num_value)
                except ValueError:
                    pass
        elif isinstance(data, dict):
            value = data.get('value', '-')
            self.value_label.setText(str(value))


class CustomADBWidget(BaseWidget):
    """커스텀 ADB 스크립트 위젯"""
    def __init__(self, command=None, parser_func=None, parent=None, grid_cols=1, grid_rows=1):
        title = f"ADB: {command or 'Custom Script'}"
        super().__init__(title, parent, grid_cols=grid_cols, grid_rows=grid_rows)
        self.command = command
        self.parser_func = parser_func
        
        self.value_label = QLabel("No data")
        self.value_label.setStyleSheet("font-size: 12px; color: #aaa;")
        self.value_label.setWordWrap(True)
        self.content_layout.addWidget(self.value_label)
        self.content_layout.addStretch()
    
    def update_data(self, data):
        """ADB 명령 결과 업데이트"""
        if self.parser_func:
            try:
                parsed = self.parser_func(data)
                self.value_label.setText(str(parsed))
            except Exception as e:
                self.value_label.setText(f"Parse Error: {str(e)}")
        else:
            self.value_label.setText(str(data)[:200])  # 최대 200자


class DataCollectionThread(QThread):
    """백그라운드에서 ADB 명령을 실행하는 스레드"""
    data_ready = pyqtSignal(object, object)  # (widget, data)
    
    def __init__(self, adb_path, device_id, widgets):
        super().__init__()
        self.adb_path = adb_path
        self.device_id = device_id
        self.widgets = widgets
    
    def run(self):
        """백그라운드에서 데이터 수집"""
        for widget in self.widgets:
            try:
                if isinstance(widget, CPUWidget):
                    # adb shell top -n 1으로 CPU 사용률 추출
                    # 여러 방법 시도
                    result = None
                    
                    # 방법 1: top 명령 (일부 디바이스에서 작동하지 않을 수 있음)
                    try:
                        result = subprocess.run(
                            [self.adb_path, '-s', self.device_id, 'shell', 'top', '-n', '1', '-d', '1'],
                            capture_output=True,
                            text=True,
                            timeout=2,
                            encoding='utf-8',
                            errors='ignore'
                        )
                    except:
                        pass
                    
                    cpu_usage = None
                    
                    if result and result.returncode == 0:
                        output = result.stdout
                        # 여러 패턴 시도
                        # 패턴 1: "CPU: 5.2% usr 2.1% sys 0.0% nic 92.7% idle"
                        cpu_match = re.search(r'CPU:\s+([\d.]+)%\s+usr', output)
                        if cpu_match:
                            cpu_usage = float(cpu_match.group(1))
                        else:
                            # 패턴 2: "CPU: 5.2%" (간단한 형식)
                            cpu_match = re.search(r'CPU:\s+([\d.]+)%', output)
                            if cpu_match:
                                cpu_usage = float(cpu_match.group(1))
                            else:
                                # 패턴 3: idle을 찾아서 100 - idle 계산
                                idle_match = re.search(r'([\d.]+)%\s+idle', output)
                                if idle_match:
                                    idle = float(idle_match.group(1))
                                    cpu_usage = max(0, 100.0 - idle)
                    
                    # 방법 2: top이 실패하면 /proc/stat 사용
                    if cpu_usage is None:
                        try:
                            stat_result = subprocess.run(
                                [self.adb_path, '-s', self.device_id, 'shell', 'cat', '/proc/stat'],
                                capture_output=True,
                                text=True,
                                timeout=2,
                                encoding='utf-8',
                                errors='ignore'
                            )
                            if stat_result.returncode == 0:
                                # /proc/stat의 첫 번째 줄 파싱
                                # cpu  1234 567 890 12345 678 901 234 0 0 0
                                lines = stat_result.stdout.strip().split('\n')
                                if lines:
                                    cpu_line = lines[0]
                                    parts = cpu_line.split()
                                    if len(parts) >= 8:
                                        # user, nice, system, idle 계산
                                        user = int(parts[1])
                                        nice = int(parts[2])
                                        system = int(parts[3])
                                        idle = int(parts[4])
                                        total = user + nice + system + idle
                                        if total > 0:
                                            cpu_usage = ((user + nice + system) / total) * 100.0
                        except:
                            pass
                    
                    # 방법 3: dumpsys cpuinfo 사용
                    if cpu_usage is None:
                        try:
                            cpuinfo_result = subprocess.run(
                                [self.adb_path, '-s', self.device_id, 'shell', 'dumpsys', 'cpuinfo'],
                                capture_output=True,
                                text=True,
                                timeout=2,
                                encoding='utf-8',
                                errors='ignore'
                            )
                            if cpuinfo_result.returncode == 0:
                                # "Load: X.XX / X.XX / X.XX" 형식 찾기
                                load_match = re.search(r'Load:\s+([\d.]+)', cpuinfo_result.stdout)
                                if load_match:
                                    load = float(load_match.group(1))
                                    # Load average를 CPU 사용률로 근사 (최대 100%로 제한)
                                    cpu_usage = min(100.0, load * 20)  # 근사치
                        except:
                            pass
                    
                    if cpu_usage is not None:
                        self.data_ready.emit(widget, cpu_usage)
                    else:
                        self.data_ready.emit(widget, "N/A")
                
                elif isinstance(widget, MemoryWidget):
                    # adb shell dumpsys meminfo로 메모리 정보 추출
                    result = subprocess.run(
                        [self.adb_path, '-s', self.device_id, 'shell', 'dumpsys', 'meminfo'],
                        capture_output=True,
                        text=True,
                        timeout=2,  # 타임아웃 단축
                        encoding='utf-8',
                        errors='ignore'
                    )
                    if result.returncode == 0:
                        total_match = re.search(r'Total RAM:\s+(\d+)\s+kB', result.stdout)
                        if total_match:
                            total_kb = int(total_match.group(1))
                            total_mb = total_kb / 1024
                            used_mb = total_mb * 0.3  # 30% 사용 중으로 가정
                            self.data_ready.emit(widget, {'used': used_mb, 'total': total_mb})
                        else:
                            self.data_ready.emit(widget, {'used': 0, 'total': 0})
                    else:
                        self.data_ready.emit(widget, "Error")
                
                elif isinstance(widget, VHALWidget):
                    if widget.property_id:
                        try:
                            prop_id = int(widget.property_id, 16) if widget.property_id.startswith('0x') else int(widget.property_id)
                            result = subprocess.run(
                                [self.adb_path, '-s', self.device_id, 'shell', 'getprop', f'vendor.vhal.property.{prop_id}'],
                                capture_output=True,
                                text=True,
                                timeout=1,  # 타임아웃 단축
                                encoding='utf-8',
                                errors='ignore'
                            )
                            if result.returncode == 0 and result.stdout.strip():
                                self.data_ready.emit(widget, result.stdout.strip())
                            else:
                                self.data_ready.emit(widget, "N/A")
                        except ValueError:
                            self.data_ready.emit(widget, "Invalid ID")
                    else:
                        self.data_ready.emit(widget, "N/A")
                
                elif isinstance(widget, CustomADBWidget):
                    if widget.command:
                        cmd_parts = widget.command.split()
                        result = subprocess.run(
                            [self.adb_path, '-s', self.device_id, 'shell'] + cmd_parts,
                            capture_output=True,
                            text=True,
                            timeout=3,  # 타임아웃 단축
                            encoding='utf-8',
                            errors='ignore'
                        )
                        if result.returncode == 0:
                            self.data_ready.emit(widget, result.stdout)
                        else:
                            self.data_ready.emit(widget, f"Error: {result.stderr[:100]}")
                    else:
                        self.data_ready.emit(widget, "No command")
            except subprocess.TimeoutExpired:
                self.data_ready.emit(widget, "Timeout")
            except Exception as e:
                self.data_ready.emit(widget, f"Error: {str(e)[:50]}")


class DashboardContainer(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._setup_data()
        # 창 크기 변경 시 레이아웃 업데이트
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._on_resize_timeout)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # 여백 추가
        self.setStyleSheet("background: transparent;")  # 배경 투명
        
        # 헤더 (제목 + 위젯 추가 버튼)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("📊 AAOS Extensible Dashboard")
        title.setStyleSheet("""
            font-weight: bold; 
            font-size: 16px; 
            color: #4a9eff;
            padding: 5px;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 버튼 그룹
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.save_btn = QPushButton("💾 Save Dashboard")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4ec9b0, stop:1 #3a9d8f);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5ed9c0, stop:1 #4aad9f);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a9d8f, stop:1 #2a7d6f);
            }
        """)
        self.save_btn.clicked.connect(self._save_dashboard)
        buttons_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton("📂 Load Dashboard")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9cdcfe, stop:1 #7cbcde);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #aceefe, stop:1 #8cccee);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7cbcde, stop:1 #5c9cbe);
            }
        """)
        self.load_btn.clicked.connect(self._load_dashboard)
        buttons_layout.addWidget(self.load_btn)
        
        self.add_widget_btn = QPushButton("➕ Add Widget")
        self.add_widget_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a9eff, stop:1 #357abd);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 16px;
                margin-right: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5ab0ff, stop:1 #4080cd);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #357abd, stop:1 #2a5a9d);
            }
        """)
        self.add_widget_btn.clicked.connect(self._show_add_widget_menu)
        buttons_layout.addWidget(self.add_widget_btn)
        
        header_layout.addLayout(buttons_layout)
        
        layout.addLayout(header_layout)
        
        # 스크롤 영역 추가 (창 크기에 맞춰 자동 조정, 세로 스크롤만)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)  # 위젯 컨테이너 크기는 수동으로 설정
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 가로 스크롤 비활성화
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 세로 스크롤만
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            /* 스크롤바 스타일 개선 */
            QScrollBar:vertical {
                background: #1e1e2e;
                width: 12px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #4a5568;
                min-height: 30px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5a6578;
            }
            QScrollBar::handle:vertical:pressed {
                background: #6a7588;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        
        # 위젯 그리드 (드래그 앤 드롭 가능)
        self.widget_container = QWidget()
        self.widget_container.setStyleSheet("background: transparent;")  # 배경 투명
        self.grid_layout = QGridLayout(self.widget_container)
        self.grid_layout.setSpacing(BaseWidget.CELL_SPACING)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        
        # 스크롤 영역에 위젯 컨테이너 추가
        self.scroll_area.setWidget(self.widget_container)
        layout.addWidget(self.scroll_area, 1)  # stretch factor 1로 최대한 공간 사용
    
    def _setup_data(self):
        self.widgets = []  # 위젯 리스트
        self.widget_positions = {}  # 위젯의 그리드 위치 저장 {widget: (row, col)}
        self.widget_grid_sizes = {}  # 위젯의 그리드 크기 저장 {widget: (cols, rows)}
        self._last_max_cols = None  # 마지막 최대 열 수 (재배열 판단용)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_all_widgets)
        self.update_timer.setInterval(1000)  # 1초마다 업데이트
        self.current_device_id = None  # 현재 선택된 디바이스 ID
        
        # 드래그 앤 드롭을 위한 설정
        self.dragged_widget = None
        self.widget_container.setAcceptDrops(True)
        
        # 데이터 수집 스레드
        self.data_collection_thread = None
        self.pending_updates = {}  # 위젯별 업데이트 대기 중인 데이터
        
        # UI 업데이트 타이머 (그래프 등 무거운 업데이트는 덜 자주)
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self._apply_pending_updates)
        self.ui_update_timer.setInterval(100)  # 100ms마다 UI 업데이트
        
        # 자동 업데이트 시작
        self.update_timer.start()
        self.ui_update_timer.start()
    
    def resizeEvent(self, event):
        """창 크기 변경 시 호출"""
        super().resizeEvent(event)
        # 짧은 딜레이 후 레이아웃 업데이트 (크기 변경 완료 후)
        self.resize_timer.start(100)
    
    def _on_resize_timeout(self):
        """크기 변경 완료 후 레이아웃 업데이트 (위젯 재배열)"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 창 크기가 변하면 열 수가 달라지므로 위젯 재배열
        old_max_cols = getattr(self, '_last_max_cols', None)
        scroll_width = self.scroll_area.viewport().width()
        if scroll_width <= 0:
            scroll_width = self.scroll_area.width()
        if scroll_width <= 0:
            scroll_width = self.width()
        
        if scroll_width > 0:
            cell_with_spacing = BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING
            new_max_cols = max(1, int(scroll_width / cell_with_spacing))
        else:
            new_max_cols = 4
        
        logger.info(f"[RESIZE] Window resized: old_max_cols={old_max_cols}, new_max_cols={new_max_cols}, scroll_width={scroll_width}, widget_count={len(self.widgets)}")
        
        # 현재 위젯 위치 로그
        for widget in self.widgets:
            pos = self.widget_positions.get(widget, "None")
            size = self.widget_grid_sizes.get(widget, "None")
            logger.debug(f"[RESIZE] Before: widget={type(widget).__name__}, pos={pos}, size={size}")
        
        # 열 수가 변경되었거나 처음이면 위젯 재배열
        self._update_widget_layout()
        
        # 재배치 후 위젯 위치 로그
        for widget in self.widgets:
            pos = self.widget_positions.get(widget, "None")
            size = self.widget_grid_sizes.get(widget, "None")
            logger.debug(f"[RESIZE] After: widget={type(widget).__name__}, pos={pos}, size={size}")
    
    def _show_add_widget_menu(self):
        """위젯 추가 메뉴 표시"""
        menu = QMenu(self)
        
        # 기본 위젯
        cpu_action = QAction("CPU Usage", self)
        cpu_action.triggered.connect(lambda: self._add_widget("cpu"))
        menu.addAction(cpu_action)
        
        memory_action = QAction("Memory", self)
        memory_action.triggered.connect(lambda: self._add_widget("memory"))
        menu.addAction(memory_action)
        
        menu.addSeparator()
        
        # VHAL 위젯
        vhal_action = QAction("VHAL Property...", self)
        vhal_action.triggered.connect(self._add_vhal_widget)
        menu.addAction(vhal_action)
        
        menu.addSeparator()
        
        # 커스텀 ADB 스크립트
        adb_action = QAction("Custom ADB Script...", self)
        adb_action.triggered.connect(self._add_adb_widget)
        menu.addAction(adb_action)
        
        menu.exec(self.add_widget_btn.mapToGlobal(self.add_widget_btn.rect().bottomLeft()))
    
    def _add_widget(self, widget_type):
        """위젯 추가"""
        widget = None
        
        if widget_type == "cpu":
            widget = CPUWidget(self)
        elif widget_type == "memory":
            widget = MemoryWidget(self)
        
        if widget:
            widget.widget_closed.connect(self._remove_widget)
            widget.widget_dragged.connect(self._on_widget_dragged)
            widget.widget_resized.connect(self._on_widget_resized)
            self.widgets.append(widget)
            # 초기 그리드 크기 저장
            self.widget_grid_sizes[widget] = (widget.grid_cols, widget.grid_rows)
            self._update_widget_layout()
    
    def _add_vhal_widget(self):
        """VHAL Property 위젯 추가"""
        property_id, ok1 = QInputDialog.getText(
            self, "VHAL Property", "Property ID (hex):", text="0x11400b62"
        )
        if not ok1 or not property_id:
            return
        
        property_name, ok2 = QInputDialog.getText(
            self, "VHAL Property", "Property Name (optional):", text=""
        )
        if not ok2:
            return
        
        widget = VHALWidget(property_id=property_id, property_name=property_name or None, parent=self.widget_container)
        widget.widget_closed.connect(self._remove_widget)
        widget.widget_dragged.connect(self._on_widget_dragged)
        widget.widget_resized.connect(self._on_widget_resized)
        self.widgets.append(widget)
        # 초기 그리드 크기 저장
        self.widget_grid_sizes[widget] = (widget.grid_cols, widget.grid_rows)
        self._update_widget_layout()
    
    def _add_adb_widget(self):
        """커스텀 ADB 스크립트 위젯 추가"""
        command, ok = QInputDialog.getText(
            self, "Custom ADB Script", "ADB Command (e.g., 'dumpsys meminfo'):", text="dumpsys meminfo"
        )
        if not ok or not command:
            return
        
        widget = CustomADBWidget(command=command, parent=self.widget_container)
        widget.widget_closed.connect(self._remove_widget)
        widget.widget_dragged.connect(self._on_widget_dragged)
        widget.widget_resized.connect(self._on_widget_resized)
        self.widgets.append(widget)
        # 초기 그리드 크기 저장
        self.widget_grid_sizes[widget] = (widget.grid_cols, widget.grid_rows)
        self._update_widget_layout()
    
    def _remove_widget(self, widget):
        """위젯 제거"""
        if widget in self.widgets:
            self.widgets.remove(widget)
            if widget in self.widget_positions:
                del self.widget_positions[widget]
            if widget in self.widget_grid_sizes:
                del self.widget_grid_sizes[widget]
            widget.deleteLater()
            self._update_widget_layout()
    
    def _update_widget_layout(self):
        """위젯 레이아웃 업데이트 (그리드 기반)"""
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)
        
        # 스크롤 영역의 실제 너비를 기준으로 최대 열 수 계산
        # 스크롤바 너비 고려 (세로 스크롤바가 있을 수 있음)
        scroll_width = self.scroll_area.viewport().width()  # viewport 너비 사용 (스크롤바 제외)
        if scroll_width <= 0:
            scroll_width = self.scroll_area.width()
        if scroll_width <= 0:
            scroll_width = self.width()
        if scroll_width <= 0:
            scroll_width = 600  # 최소 기본값
        
        # 셀 너비와 간격을 고려하여 최대 열 수 계산
        cell_with_spacing = BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING
        max_cols = max(1, int(scroll_width / cell_with_spacing))
        
        old_max_cols = getattr(self, '_last_max_cols', None)
        logger.debug(f"[LAYOUT] scroll_width={scroll_width}, max_cols={max_cols}, old_max_cols={old_max_cols}, widget_count={len(self.widgets)}")
        
        # 최대 열 수 저장 (재배열 판단용)
        self._last_max_cols = max_cols
        
        # 그리드 레이아웃의 열 수를 max_cols에 맞춰 조정
        # 셀 크기를 고정하기 위해 stretch를 0으로 설정하고 최소 크기만 설정
        current_cols = self.grid_layout.columnCount()
        
        # 열 수가 부족하면 추가
        if max_cols > current_cols:
            for col in range(current_cols, max_cols):
                self.grid_layout.setColumnMinimumWidth(col, BaseWidget.CELL_WIDTH)
                self.grid_layout.setColumnStretch(col, 0)  # stretch 비활성화 (고정 크기)
        
        # 모든 열에 고정 크기 설정 (stretch 없이)
        for col in range(max_cols):
            self.grid_layout.setColumnMinimumWidth(col, BaseWidget.CELL_WIDTH)
            self.grid_layout.setColumnStretch(col, 0)  # stretch 비활성화 (고정 크기)
        
        # 열이 줄어들었을 때는 stretch를 0으로 설정 (사용하지 않는 열)
        for col in range(max_cols, current_cols):
            self.grid_layout.setColumnStretch(col, 0)
        
        # 행도 고정 크기로 설정 (먼저 최대 행 계산)
        max_row = 0
        for widget in self.widgets:
            r, c = self.widget_positions.get(widget, (0, 0))
            grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
            max_row = max(max_row, r + grid_rows)
        
        # 행 크기 고정 (위젯이 없어도 최소 1행은 설정)
        for row in range(max(max_row, 1)):
            self.grid_layout.setRowMinimumHeight(row, BaseWidget.CELL_HEIGHT)
            self.grid_layout.setRowStretch(row, 0)  # stretch 비활성화 (고정 크기)
        
        logger.debug(f"[LAYOUT] Grid layout: max_cols={max_cols}, current_cols={current_cols}, actual_cols={self.grid_layout.columnCount()}, max_row={max_row}")
        
        # 기존 위젯 제거 (레이아웃에서 완전히 제거)
        # 모든 위젯을 먼저 제거하고 레이아웃을 완전히 초기화
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    # 위젯을 레이아웃에서 완전히 제거
                    self.grid_layout.removeWidget(widget)
                    widget.setParent(None)
        
        # 레이아웃을 완전히 초기화하기 위해 모든 아이템 제거
        # takeAt으로 제거한 후에도 레이아웃이 남아있을 수 있으므로
        for row in range(self.grid_layout.rowCount()):
            for col in range(self.grid_layout.columnCount()):
                item = self.grid_layout.itemAtPosition(row, col)
                if item:
                    self.grid_layout.removeItem(item)
        
        logger.debug(f"[LAYOUT] Cleared grid layout. Remaining items: {self.grid_layout.count()}")
        
        # 위젯을 배치 (좌표 기반, 겹침 방지)
        # 이미 배치된 위젯들이 차지하는 공간 추적
        occupied = set()  # {(row, col)} 형태로 차지된 셀 저장
        
        logger.debug(f"[LAYOUT] Starting widget placement. Total widgets: {len(self.widgets)}")
        
        # 먼저 모든 위젯의 기존 위치를 검증하고, 유효하지 않은 위치는 None으로 설정
        # 이렇게 하면 배치 순서와 관계없이 겹침을 방지할 수 있음
        validated_positions = {}
        for widget in self.widgets:
            existing_pos = self.widget_positions.get(widget)
            if existing_pos:
                ex_row, ex_col = existing_pos
                grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
                
                # 범위 체크 (위젯 크기가 변경되었을 수 있으므로 현재 크기로 확인)
                if ex_col + grid_cols <= max_cols and ex_col >= 0 and ex_row >= 0:
                    validated_positions[widget] = existing_pos
                else:
                    logger.debug(f"[LAYOUT] Widget {type(widget).__name__}: existing_pos=({ex_row}, {ex_col}) invalid (out of bounds with size {grid_cols}x{grid_rows})")
                    validated_positions[widget] = None
            else:
                validated_positions[widget] = None
        
        # 이제 다른 위젯과 겹치는지 확인 (모든 조합 체크)
        # 겹침이 발견되면 둘 다 무효화하지 않고, 우선순위에 따라 하나만 유효하게 유지
        # 위젯 리스트 순서대로 우선순위 부여 (먼저 나온 위젯이 우선)
        for i, widget in enumerate(self.widgets):
            existing_pos = validated_positions.get(widget)
            if existing_pos is None:
                continue
                
            ex_row, ex_col = existing_pos
            grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
            
            # 이전 위젯들과 겹치는지 확인 (우선순위가 높은 위젯들)
            is_overlapping = False
            for j, other_widget in enumerate(self.widgets):
                if j >= i:  # 자신과 이후 위젯은 체크하지 않음
                    break
                    
                other_pos = validated_positions.get(other_widget)
                if other_pos is None:
                    continue
                    
                other_row, other_col = other_pos
                other_cols, other_rows = self.widget_grid_sizes.get(other_widget, (other_widget.grid_cols, other_widget.grid_rows))
                
                # 겹침 체크: 두 사각형이 겹치는지 확인
                if not (ex_row + grid_rows <= other_row or other_row + other_rows <= ex_row or
                        ex_col + grid_cols <= other_col or other_col + other_cols <= ex_col):
                    is_overlapping = True
                    logger.warning(f"[LAYOUT] Widget[{i}] {type(widget).__name__}: existing_pos=({ex_row}, {ex_col}) overlaps with Widget[{j}] {type(other_widget).__name__} at ({other_row}, {other_col})")
                    break
            
            if is_overlapping:
                validated_positions[widget] = None
                logger.debug(f"[LAYOUT] Widget[{i}] {type(widget).__name__}: Invalidated due to overlap")
        
        # 창이 커졌을 때 재배치를 위해: max_cols가 증가했으면 기존 위치를 무효화하여 재배치
        if old_max_cols is not None and max_cols > old_max_cols:
            logger.info(f"[LAYOUT] Window expanded: max_cols increased from {old_max_cols} to {max_cols}, forcing re-layout for better positioning")
            # 창이 커졌을 때는 모든 위치를 무효화하여 재배치 (더 효율적인 배치 가능)
            for widget in self.widgets:
                validated_positions[widget] = None
        
        # 위젯 크기가 변경된 경우: 크기가 커진 위젯이 다른 위젯과 겹칠 수 있으므로 재검증
        # 크기가 작아진 위젯은 기존 위치를 유지할 수 있지만, 커진 위젯은 재배치 필요
        # 위젯 리스트 순서대로 우선순위 부여하여 겹침 해결
        for i, widget in enumerate(self.widgets):
            existing_pos = validated_positions.get(widget)
            if existing_pos is None:
                continue
            
            ex_row, ex_col = existing_pos
            grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
            
            # 이전 위젯들과 겹치는지 확인 (우선순위가 높은 위젯들)
            # 크기가 커진 위젯이 이전 위젯과 겹치면 재배치
            for j, other_widget in enumerate(self.widgets):
                if j >= i:  # 자신과 이후 위젯은 체크하지 않음
                    break
                
                other_pos = validated_positions.get(other_widget)
                if other_pos is None:
                    continue
                
                other_row, other_col = other_pos
                other_cols, other_rows = self.widget_grid_sizes.get(other_widget, (other_widget.grid_cols, other_widget.grid_rows))
                
                # 겹침 체크: 두 사각형이 겹치는지
                if not (ex_row + grid_rows <= other_row or other_row + other_rows <= ex_row or
                        ex_col + grid_cols <= other_col or other_col + other_cols <= ex_col):
                    # 겹침 발견: 크기가 변경된 위젯의 위치를 무효화 (우선순위가 낮으므로)
                    logger.warning(f"[LAYOUT] Widget[{i}] {type(widget).__name__} at ({ex_row}, {ex_col}) with size ({grid_cols}x{grid_rows}) overlaps with Widget[{j}] {type(other_widget).__name__} at ({other_row}, {other_col})")
                    validated_positions[widget] = None
                    break
        
        # 이제 배치 시작 (실시간으로 occupied 체크)
        for idx, widget in enumerate(self.widgets):
            grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
            widget_type = type(widget).__name__
            
            # 검증된 위치 사용
            existing_pos = validated_positions.get(widget)
            row, col = None, None
            
            if existing_pos:
                # 기존 위치가 있으면, 실제로 occupied와 겹치는지 다시 확인
                ex_row, ex_col = existing_pos
                is_actually_available = True
                for dr in range(grid_rows):
                    for dc in range(grid_cols):
                        check_pos = (ex_row + dr, ex_col + dc)
                        if check_pos in occupied:
                            is_actually_available = False
                            logger.warning(f"[LAYOUT] Widget[{idx}] {widget_type}: validated position ({ex_row}, {ex_col}) actually overlaps with occupied cells!")
                            break
                    if not is_actually_available:
                        break
                
                if is_actually_available:
                    row, col = ex_row, ex_col
                    logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: Using validated existing position ({row}, {col}), size=({grid_cols}x{grid_rows})")
                else:
                    logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: Validated position ({ex_row}, {ex_col}) not actually available, finding new position")
            else:
                logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: No valid existing position, size=({grid_cols}x{grid_rows})")
            
            # 위치를 찾지 못했으면 새로 찾기
            if row is None or col is None:
                old_pos = self.widget_positions.get(widget, "None")
                row, col = self._find_next_available_position(
                    grid_cols, grid_rows, max_cols, occupied
                )
                logger.info(f"[LAYOUT] Widget[{idx}] {widget_type}: Found new position ({row}, {col}), old_pos={old_pos}, occupied_count={len(occupied)}")
            
            # 위치 저장
            self.widget_positions[widget] = (row, col)
            
            # 차지하는 공간을 occupied에 추가
            occupied_before = len(occupied)
            for dr in range(grid_rows):
                for dc in range(grid_cols):
                    cell_pos = (row + dr, col + dc)
                    if cell_pos in occupied:
                        logger.error(f"[LAYOUT] Widget[{idx}] {widget_type}: CRITICAL! Cell {cell_pos} already occupied! This should not happen!")
                    occupied.add(cell_pos)
            
            occupied_after = len(occupied)
            logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: Placed at ({row}, {col}), occupied: {occupied_before} -> {occupied_after} (+{occupied_after - occupied_before})")
            
            # 위젯 배치 (절대 위치로 직접 계산, QGridLayout 사용 안 함)
            # 1. 레이아웃에서 완전히 제거
            self.grid_layout.removeWidget(widget)
            
            # 2. 부모를 None으로 설정했다가 다시 컨테이너로 설정 (레이아웃 영향 제거)
            old_parent = widget.parent()
            if old_parent:
                widget.setParent(None)
            
            # 3. 컨테이너에 직접 추가 (레이아웃 없이)
            widget.setParent(self.widget_container)
            
            # 4. 절대 위치 계산
            x = col * (BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING)
            y = row * (BaseWidget.CELL_HEIGHT + BaseWidget.CELL_SPACING)
            width = (BaseWidget.CELL_WIDTH * grid_cols) + (BaseWidget.CELL_SPACING * (grid_cols - 1))
            height = (BaseWidget.CELL_HEIGHT * grid_rows) + (BaseWidget.CELL_SPACING * (grid_rows - 1))
            
            # 5. 위젯의 위치와 크기를 직접 설정 (레이아웃 사용 안 함)
            widget.setGeometry(x, y, width, height)
            
            # 6. 위젯을 보이게 설정
            widget.show()
            
            # 7. 레이아웃 업데이트 방지 (위젯이 레이아웃에 의해 이동되지 않도록)
            widget.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect, False)
            
            logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: Set geometry at ({x}, {y}), size=({width}x{height}), grid_pos=({row}, {col})")
            
            # 디버깅: 실제 배치 확인
            actual_geometry = widget.geometry()
            if actual_geometry.x() != x or actual_geometry.y() != y:
                logger.warning(f"[LAYOUT] Widget[{idx}] {widget_type}: Geometry mismatch! Expected=({x}, {y}), Actual=({actual_geometry.x()}, {actual_geometry.y()})")
            logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: Final geometry=({actual_geometry.x()}, {actual_geometry.y()}), size=({actual_geometry.width()}x{actual_geometry.height()})")
        
        logger.debug(f"[LAYOUT] Placement complete. Final occupied cells: {len(occupied)}")
        
        # 그리드 레이아웃의 실제 셀 크기 확인
        logger.debug(f"[LAYOUT] Grid layout cell sizes:")
        for col in range(min(max_cols, self.grid_layout.columnCount())):
            col_width = self.grid_layout.columnMinimumWidth(col)
            col_stretch = self.grid_layout.columnStretch(col)
            logger.debug(f"[LAYOUT] Column[{col}]: min_width={col_width}, stretch={col_stretch}, expected={BaseWidget.CELL_WIDTH}")
        
        max_row = 0
        for widget in self.widgets:
            r, c = self.widget_positions.get(widget, (0, 0))
            grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
            max_row = max(max_row, r + grid_rows)
        
        for row in range(min(max_row, self.grid_layout.rowCount())):
            row_height = self.grid_layout.rowMinimumHeight(row)
            row_stretch = self.grid_layout.rowStretch(row)
            logger.debug(f"[LAYOUT] Row[{row}]: min_height={row_height}, stretch={row_stretch}, expected={BaseWidget.CELL_HEIGHT}")
        
        # 모든 위젯의 실제 위치 확인 (레이아웃 사용 안 하므로 geometry만 확인)
        logger.debug(f"[LAYOUT] Verifying widget positions:")
        for idx, widget in enumerate(self.widgets):
            widget_type = type(widget).__name__
            expected_pos = self.widget_positions.get(widget, "None")
            grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
            
            # 예상 절대 위치 계산
            if isinstance(expected_pos, tuple):
                expected_row, expected_col = expected_pos
                expected_x = expected_col * (BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING)
                expected_y = expected_row * (BaseWidget.CELL_HEIGHT + BaseWidget.CELL_SPACING)
            else:
                expected_x = expected_y = None
            
            # 위젯의 실제 위치(geometry) 확인
            widget_geometry = widget.geometry()
            actual_x = widget_geometry.x()
            actual_y = widget_geometry.y()
            actual_width = widget_geometry.width()
            actual_height = widget_geometry.height()
            
            expected_width = (BaseWidget.CELL_WIDTH * grid_cols) + (BaseWidget.CELL_SPACING * (grid_cols - 1))
            expected_height = (BaseWidget.CELL_HEIGHT * grid_rows) + (BaseWidget.CELL_SPACING * (grid_rows - 1))
            
            if expected_x is not None:
                if actual_x == expected_x and actual_y == expected_y:
                    logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: Position OK - expected=({expected_x}, {expected_y}), actual=({actual_x}, {actual_y}), size=({grid_cols}x{grid_rows})")
                else:
                    logger.warning(f"[LAYOUT] Widget[{idx}] {widget_type}: Position MISMATCH - expected=({expected_x}, {expected_y}), actual=({actual_x}, {actual_y}), size=({grid_cols}x{grid_rows})")
            
            if actual_width == expected_width and actual_height == expected_height:
                logger.debug(f"[LAYOUT] Widget[{idx}] {widget_type}: Size OK - actual=({actual_width}x{actual_height}), expected=({expected_width}x{expected_height})")
            else:
                logger.warning(f"[LAYOUT] Widget[{idx}] {widget_type}: Size MISMATCH - actual=({actual_width}x{actual_height}), expected=({expected_width}x{expected_height})")
            
            # 다른 위젯과 겹치는지 확인
            for other_idx, other_widget in enumerate(self.widgets):
                if other_idx == idx:
                    continue
                other_geometry = other_widget.geometry()
                # 겹침 체크: 두 사각형이 겹치는지
                if not (actual_x + actual_width <= other_geometry.x() or 
                       other_geometry.x() + other_geometry.width() <= actual_x or
                       actual_y + actual_height <= other_geometry.y() or
                       other_geometry.y() + other_geometry.height() <= actual_y):
                    logger.error(f"[LAYOUT] Widget[{idx}] {widget_type}: OVERLAPS with Widget[{other_idx}] {type(other_widget).__name__}! "
                               f"Widget[{idx}] geometry=({actual_x}, {actual_y}, {actual_width}, {actual_height}), "
                               f"Widget[{other_idx}] geometry=({other_geometry.x()}, {other_geometry.y()}, {other_geometry.width()}, {other_geometry.height()})")
        
        # 위젯 컨테이너의 크기 설정 (스크롤 영역 viewport 너비에 맞춰 가로 크기 고정)
        scroll_width = self.scroll_area.viewport().width()  # viewport 너비 사용
        if scroll_width <= 0:
            scroll_width = self.scroll_area.width()
        if scroll_width <= 0:
            scroll_width = self.width()
        if scroll_width <= 0:
            scroll_width = 600  # 최소 기본값
        
        cell_with_spacing = BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING
        max_cols = max(1, int(scroll_width / cell_with_spacing))
        # 컨테이너 가로 크기를 스크롤 영역 viewport에 정확히 맞춤 (가로 스크롤 방지)
        container_width = max_cols * (BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING) - BaseWidget.CELL_SPACING
        
        # 최대 행 계산
        max_row = 0
        for widget in self.widgets:
            r, c = self.widget_positions.get(widget, (0, 0))
            grid_cols, grid_rows = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
            max_row = max(max_row, r + grid_rows)
        
        # 컨테이너 크기 설정 (가로는 스크롤 영역에 맞춤, 세로는 내용에 맞게)
        container_height = max_row * (BaseWidget.CELL_HEIGHT + BaseWidget.CELL_SPACING) - BaseWidget.CELL_SPACING
        if container_height < 100:
            container_height = 100  # 최소 높이
        
        self.widget_container.setFixedWidth(container_width)  # 가로 크기 고정
        self.widget_container.setMinimumHeight(container_height)  # 세로는 최소 높이만 설정
    
    def _find_next_available_position(self, grid_cols, grid_rows, max_cols, occupied):
        """위젯을 배치할 수 있는 다음 위치 찾기 (겹침 방지)"""
        import logging
        logger = logging.getLogger(__name__)
        
        row = 0
        col = 0
        max_iterations = 10000  # 무한 루프 방지
        iteration = 0
        
        logger.debug(f"[FIND_POS] Looking for position: size=({grid_cols}x{grid_rows}), max_cols={max_cols}, occupied_count={len(occupied)}")
        
        while iteration < max_iterations:
            iteration += 1
            
            # 가로 범위 체크
            if col + grid_cols > max_cols:
                # 가로가 꽉 차면 다음 행으로
                col = 0
                row += 1
                if iteration % 100 == 0:
                    logger.debug(f"[FIND_POS] Iteration {iteration}: Moved to row {row}")
                continue
            
            # 겹침 체크: 이 위치에 배치 가능한지 확인
            can_place = True
            conflicting_cells = []
            for dr in range(grid_rows):
                for dc in range(grid_cols):
                    check_pos = (row + dr, col + dc)
                    if check_pos in occupied:
                        can_place = False
                        conflicting_cells.append(check_pos)
            
            if can_place:
                logger.debug(f"[FIND_POS] Found position ({row}, {col}) after {iteration} iterations")
                return (row, col)
            elif iteration <= 10:  # 처음 10번만 로그
                logger.debug(f"[FIND_POS] Position ({row}, {col}) occupied, conflicting_cells={conflicting_cells[:3]}")
            
            # 다음 위치로 이동
            col += 1
        
        # 무한 루프 방지: 최상단 왼쪽 반환
        logger.error(f"[FIND_POS] Max iterations reached! Returning (0, 0) as fallback")
        return (0, 0)
    
    def _on_widget_dragged(self, widget, global_pos):
        """위젯 드래그 중 호출"""
        self.dragged_widget = widget
        # 드롭 영역으로 변환
        local_pos = self.widget_container.mapFromGlobal(global_pos)
        self._handle_drag_over(local_pos)
    
    def _handle_drag_over(self, pos):
        """드래그 중인 위치에서 위젯 위치 변경 (좌표 기반)"""
        if not self.dragged_widget:
            return
        
        if self.dragged_widget not in self.widgets:
            return
        
        # 그리드 셀 크기로 위치 계산
        cell_width = BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING
        cell_height = BaseWidget.CELL_HEIGHT + BaseWidget.CELL_SPACING
        
        # 새로운 위치 계산
        new_col = max(0, int(pos.x() / cell_width))
        new_row = max(0, int(pos.y() / cell_height))
        
        # 위젯의 그리드 크기 가져오기
        grid_cols, grid_rows = self.widget_grid_sizes.get(
            self.dragged_widget, 
            (self.dragged_widget.grid_cols, self.dragged_widget.grid_rows)
        )
        
        # 스크롤 영역 viewport 너비를 기준으로 최대 열 수 계산
        scroll_width = self.scroll_area.viewport().width()
        if scroll_width <= 0:
            scroll_width = self.scroll_area.width()
        if scroll_width <= 0:
            scroll_width = self.width()
        
        if scroll_width > 0:
            cell_with_spacing = BaseWidget.CELL_WIDTH + BaseWidget.CELL_SPACING
            max_cols = max(1, int(scroll_width / cell_with_spacing))
        else:
            max_cols = 4  # 기본값
        
        # 위젯이 가로 범위를 넘지 않도록
        if new_col + grid_cols > max_cols:
            new_col = max(0, max_cols - grid_cols)
        
        # 현재 위치와 다르면 재배치
        current_pos = self.widget_positions.get(self.dragged_widget, (0, 0))
        target_pos = (new_row, new_col)
        
        if target_pos != current_pos:
            # 다른 위젯과 겹치는지 확인
            occupied_positions = set()
            for w, (r, c) in self.widget_positions.items():
                if w != self.dragged_widget:
                    w_cols, w_rows = self.widget_grid_sizes.get(w, (w.grid_cols, w.grid_rows))
                    for dr in range(w_rows):
                        for dc in range(w_cols):
                            occupied_positions.add((r + dr, c + dc))
            
            # 목표 위치가 비어있는지 확인
            can_place = True
            for dr in range(grid_rows):
                for dc in range(grid_cols):
                    if (target_pos[0] + dr, target_pos[1] + dc) in occupied_positions:
                        can_place = False
                        break
                if not can_place:
                    break
            
            if can_place:
                # 위치 업데이트
                self.widget_positions[self.dragged_widget] = target_pos
                self._update_widget_layout()
    
    def _on_widget_resized(self, widget, grid_cols, grid_rows):
        """위젯 크기 변경 시 호출 (그리드 단위)"""
        import logging
        logger = logging.getLogger(__name__)
        
        old_size = self.widget_grid_sizes.get(widget, (widget.grid_cols, widget.grid_rows))
        logger.info(f"[RESIZE] Widget {type(widget).__name__} size changed from {old_size} to ({grid_cols}, {grid_rows})")
        
        # 그리드 크기 저장
        self.widget_grid_sizes[widget] = (grid_cols, grid_rows)
        
        # 위젯 크기가 변경되면 재배치 필요 (크기가 커지면 겹칠 수 있음)
        # 기존 위치는 유지하되, 겹치면 재배치
        self._update_widget_layout()
    
    def _find_adb_path(self):
        """adb.exe 경로 찾기"""
        adb_path = 'adb'
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=2)
            if result.returncode == 0:
                return adb_path
        except:
            pass
        
        android_home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
        if android_home:
            adb_path = os.path.join(android_home, 'platform-tools', 'adb.exe')
            if os.path.exists(adb_path):
                return adb_path
        
        common_paths = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Android', 'Sdk', 'platform-tools', 'adb.exe'),
            os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Android', 'Sdk', 'platform-tools', 'adb.exe'),
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return 'adb'
    
    def set_device_id(self, device_id):
        """현재 디바이스 ID 설정"""
        self.current_device_id = device_id
    
    def _get_device_id(self):
        """현재 디바이스 ID 가져오기 (MainWindow에서 설정)"""
        # MainWindow에서 device_id를 받아올 수 있도록 나중에 연결
        return self.current_device_id
    
    def _update_all_widgets(self):
        """모든 위젯 데이터 수집 (백그라운드 스레드에서 실행)"""
        device_id = self._get_device_id()
        if not device_id:
            # 디바이스가 연결되지 않았으면 "연결 안됨" 메시지 표시
            for widget in self.widgets:
                if isinstance(widget, CPUWidget):
                    self.pending_updates[widget] = "연결 안됨"
                elif isinstance(widget, MemoryWidget):
                    self.pending_updates[widget] = "연결 안됨"
                elif isinstance(widget, VHALWidget):
                    self.pending_updates[widget] = "연결 안됨"
                elif isinstance(widget, CustomADBWidget):
                    self.pending_updates[widget] = "연결 안됨"
            return
        
        # 백그라운드 스레드에서 데이터 수집
        if self.data_collection_thread and self.data_collection_thread.isRunning():
            return  # 이미 실행 중이면 스킵
        
        self.data_collection_thread = DataCollectionThread(
            self._find_adb_path(),
            device_id,
            self.widgets
        )
        self.data_collection_thread.data_ready.connect(self._on_data_ready)
        self.data_collection_thread.start()
    
    def _on_data_ready(self, widget, data):
        """데이터 수집 완료 시 호출"""
        self.pending_updates[widget] = data
    
    def _apply_pending_updates(self):
        """대기 중인 업데이트를 UI에 적용"""
        if not self.pending_updates:
            return
        
        # 배치 업데이트로 UI 블로킹 최소화
        updates = self.pending_updates.copy()
        self.pending_updates.clear()
        
        for widget, data in updates.items():
            if widget in self.widgets:  # 위젯이 아직 존재하는지 확인
                widget.update_data(data)
    
    def _save_dashboard(self):
        """대시보드 설정 저장"""
        from PyQt6.QtWidgets import QFileDialog
        
        # 저장할 파일 경로 선택
        default_path = Path.home() / "dashboard_config.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "대시보드 설정 저장",
            str(default_path),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # 위젯 정보 수집
            widgets_data = []
            for widget in self.widgets:
                widget_data = {
                    'type': self._get_widget_type(widget),
                    'grid_cols': widget.grid_cols,
                    'grid_rows': widget.grid_rows,
                }
                
                # 위치 정보 (widget_positions는 (row, col) 튜플 또는 dict 형태)
                if widget in self.widget_positions:
                    pos = self.widget_positions[widget]
                    if isinstance(pos, tuple):
                        # (row, col) 튜플 형태
                        row, col = pos
                        widget_data['position'] = {'row': row, 'col': col}
                    elif isinstance(pos, dict):
                        # dict 형태
                        widget_data['position'] = {'row': pos.get('row', pos.get('r', 0)), 'col': pos.get('col', pos.get('c', 0))}
                    else:
                        # 기타 형태는 무시
                        pass
                
                # 위젯별 특수 설정
                if isinstance(widget, VHALWidget):
                    widget_data['property_id'] = widget.property_id
                    widget_data['property_name'] = widget.property_name
                    widget_data['show_graph'] = widget.show_graph_cb.isChecked()
                elif isinstance(widget, CustomADBWidget):
                    widget_data['command'] = widget.command
                
                widgets_data.append(widget_data)
            
            # JSON으로 저장
            config = {
                'version': '1.0',
                'widgets': widgets_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "저장 완료", f"대시보드 설정이 저장되었습니다:\n{file_path}")
            logger.info(f"[Dashboard] 설정 저장 완료: {file_path}, 위젯 수: {len(widgets_data)}")
            
        except Exception as e:
            logger.error(f"[Dashboard] 설정 저장 실패: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "저장 실패", f"대시보드 설정 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def _load_dashboard(self):
        """대시보드 설정 불러오기"""
        from PyQt6.QtWidgets import QFileDialog
        
        # 불러올 파일 경로 선택
        default_path = Path.home() / "dashboard_config.json"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "대시보드 설정 불러오기",
            str(default_path.parent),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            # 기존 위젯 모두 제거
            reply = QMessageBox.question(
                self,
                "대시보드 불러오기",
                "현재 대시보드의 모든 위젯이 제거됩니다. 계속하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # 기존 위젯 제거
            for widget in self.widgets[:]:  # 복사본으로 반복
                self._remove_widget(widget)
            
            # JSON 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if 'widgets' not in config:
                QMessageBox.warning(self, "파일 형식 오류", "올바른 대시보드 설정 파일이 아닙니다.")
                return
            
            # 위젯 복원
            for widget_data in config['widgets']:
                widget_type = widget_data.get('type')
                grid_cols = widget_data.get('grid_cols', 1)
                grid_rows = widget_data.get('grid_rows', 1)
                
                widget = None
                
                if widget_type == 'cpu':
                    widget = CPUWidget(self, grid_cols=grid_cols, grid_rows=grid_rows)
                elif widget_type == 'memory':
                    widget = MemoryWidget(self, grid_cols=grid_cols, grid_rows=grid_rows)
                elif widget_type == 'vhal':
                    property_id = widget_data.get('property_id')
                    property_name = widget_data.get('property_name')
                    widget = VHALWidget(
                        property_id=property_id,
                        property_name=property_name,
                        parent=self,
                        grid_cols=grid_cols,
                        grid_rows=grid_rows
                    )
                    if widget_data.get('show_graph', False):
                        widget.show_graph_cb.setChecked(True)
                elif widget_type == 'custom_adb':
                    command = widget_data.get('command')
                    widget = CustomADBWidget(
                        command=command,
                        parent=self,
                        grid_cols=grid_cols,
                        grid_rows=grid_rows
                    )
                
                if widget:
                    widget.widget_closed.connect(self._remove_widget)
                    widget.widget_dragged.connect(self._on_widget_dragged)
                    widget.widget_resized.connect(self._on_widget_resized)
                    self.widgets.append(widget)
                    self.widget_grid_sizes[widget] = (grid_cols, grid_rows)
                    
                    # 위치 복원 (기존 코드와 호환되도록 튜플 형태로 저장)
                    if 'position' in widget_data:
                        pos = widget_data['position']
                        row = pos.get('row', 0)
                        col = pos.get('col', 0)
                        # 기존 코드는 (row, col) 튜플 형태를 사용
                        self.widget_positions[widget] = (row, col)
            
            # 레이아웃 업데이트
            self._update_widget_layout()
            
            QMessageBox.information(self, "불러오기 완료", f"대시보드 설정을 불러왔습니다:\n{file_path}\n위젯 수: {len(self.widgets)}")
            logger.info(f"[Dashboard] 설정 불러오기 완료: {file_path}, 위젯 수: {len(self.widgets)}")
            
        except json.JSONDecodeError as e:
            logger.error(f"[Dashboard] JSON 파싱 오류: {str(e)}")
            QMessageBox.warning(self, "파일 오류", f"JSON 파일 형식이 올바르지 않습니다:\n{str(e)}")
        except Exception as e:
            logger.error(f"[Dashboard] 설정 불러오기 실패: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "불러오기 실패", f"대시보드 설정 불러오기 중 오류가 발생했습니다:\n{str(e)}")
    
    def _get_widget_type(self, widget):
        """위젯 타입 반환"""
        if isinstance(widget, CPUWidget):
            return 'cpu'
        elif isinstance(widget, MemoryWidget):
            return 'memory'
        elif isinstance(widget, VHALWidget):
            return 'vhal'
        elif isinstance(widget, CustomADBWidget):
            return 'custom_adb'
        else:
            return 'unknown'
