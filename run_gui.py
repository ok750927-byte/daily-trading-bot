"""Small runner to launch the recovered GUI implementation.

Use this instead of the damaged `gui_app.py` while the original is being cleaned.
"""
import sys

from gui_app_recovered import TradingBotGUI
from PyQt6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    gui = TradingBotGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
