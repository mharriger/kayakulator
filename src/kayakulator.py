"""
Main entrypoint for the application.
Sets up the GUI, and handles the modeling and output if run with --no-gui flag
"""

import faulthandler
faulthandler.enable()
import builtins
builtins.NO_SOLIDS = False

from gui.mainwindow import MainWindow
from PySide6.QtWidgets import QApplication
import settings_manager

if __name__ == "__main__":
    settings_manager.settings = settings_manager.SettingsManager() # Set this to an instance of a different subclass of SettingsManager to manage settings differently
    app = QApplication()

    window = MainWindow()
    window.show()

    # Start the event loop.
    app.exec()