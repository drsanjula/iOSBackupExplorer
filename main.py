#!/usr/bin/env python3
"""
iOS Backup Explorer - Main Entry Point

A modern PyQt6 desktop application to explore and export iOS backup files.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.ui.main_window import MainWindow
from src.ui.styles import apply_stylesheet
from src.utils.constants import APP_NAME


def main():
    """Main application entry point."""
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("drsanjula")
    app.setOrganizationDomain("github.com/drsanjula")
    
    # Set default font (use San Francisco or fallback)
    font = QFont()
    font.setFamily("SF Pro Text")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setPointSize(13)
    app.setFont(font)
    
    # Apply stylesheet
    apply_stylesheet(app, mode="pro")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
