import sys
import os
import logging
import threading

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # 메인 스레드 ID (나중에 시그널 슬롯이 어느 스레드에서 도는지 비교용)
    print(f"[Main] 메인 스레드 ID: {threading.get_ident()}")
    app = QApplication(sys.argv)
    
    # TODO: Setup dark theme (pyqtdarktheme.apply() when available)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
