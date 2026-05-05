"""
Main entrypoint for the application.
Sets up the GUI, and handles the modeling and output if run with --no-gui flag
"""

from gui.mainwindow import MainWindow
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication()

    window = MainWindow()
    window.show()

    # Start the event loop.
    app.exec()