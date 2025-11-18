"""
UR10e 控制 UI 主程式入口

此檔案負責應用程式的初始化與啟動。
"""

import sys
import signal
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from ui_mainwindow import MainWindow
from config import Config


def setup_logging():
    """設定日誌系統"""
    # 創建 logs 目錄
    log_dir = Path(Config.LOGS_DIR)
    log_dir.mkdir(exist_ok=True)

    # 日誌格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 設定根日誌器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # 檔案輸出
            logging.FileHandler(
                log_dir / f'ur10e_control_{Path(__file__).stem}.log',
                encoding='utf-8'
            ),
            # 控制台輸出
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("UR10e Control UI Starting")
    logger.info("=" * 60)


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    全域異常處理器

    捕獲未處理的異常並記錄到日誌
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # 允許 Ctrl+C 中斷
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger(__name__)
    logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))

    # Display error dialog
    error_msg = f"A critical error occurred:\n\n{exc_type.__name__}: {exc_value}"
    QMessageBox.critical(None, "System Error", error_msg)


# Global reference to main window for signal handler
_main_window_instance = None

def signal_handler(signum, frame):
    """
    Handle interrupt signals (Ctrl-C)

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger = logging.getLogger(__name__)
    logger.info("\n" + "="*60)
    logger.info("Interrupt signal received (Ctrl-C), shutting down...")
    logger.info("="*60)

    # Disconnect robot controller if window exists
    global _main_window_instance
    if _main_window_instance is not None:
        try:
            logger.info("Disconnecting robot controller...")
            if hasattr(_main_window_instance, 'robot_controller'):
                _main_window_instance.robot_controller.disconnect()
            logger.info("Robot controller disconnected")
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")

    # Quit application
    QApplication.quit()

    # Force exit if Qt doesn't quit properly
    import sys
    sys.exit(0)


def load_stylesheet(app: QApplication):
    """
    載入 QSS 樣式表 (可選)

    Args:
        app: QApplication 實例
    """
    style_file = Path(Config.ASSETS_DIR) / "style.qss"

    if style_file.exists():
        try:
            with open(style_file, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
                app.setStyleSheet(stylesheet)
                logging.info(f"Stylesheet loaded: {style_file}")
        except Exception as e:
            logging.warning(f"Failed to load stylesheet: {e}")
    else:
        logging.info("Stylesheet file not found, using default style")


def main():
    """主函數"""
    # 設定日誌
    setup_logging()
    logger = logging.getLogger(__name__)

    # 設定全域異常處理器
    sys.excepthook = exception_hook

    # 啟用高 DPI 縮放 (必須在創建 QApplication 之前設定)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 創建 QApplication
    app = QApplication(sys.argv)

    # 設定應用程式資訊
    app.setApplicationName("UR10e Control UI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("UR10e Project")

    # 設定 Ctrl-C 信號處理
    signal.signal(signal.SIGINT, signal_handler)

    # Create a timer to allow Python to process signals
    # PyQt event loop blocks signal handling, so we need to wake it up periodically
    timer = QTimer()
    timer.start(500)  # Wake up every 500ms to process signals
    timer.timeout.connect(lambda: None)  # No-op, just to process events

    logger.info("Signal handlers configured (Ctrl-C enabled)")

    # 載入樣式表 (可選)
    load_stylesheet(app)

    try:
        # Create main window
        logger.info("Creating main window...")
        main_window = MainWindow()

        # Store global reference for signal handler
        global _main_window_instance
        _main_window_instance = main_window

        # Show window
        main_window.show()
        logger.info("Main window displayed")

        # Start event loop
        logger.info("Entering application event loop")
        exit_code = app.exec_()

        logger.info(f"Application exited with code: {exit_code}")
        return exit_code

    except Exception as e:
        logger.critical(f"Application startup failed: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Startup Failed",
            f"Unable to start application:\n\n{str(e)}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
