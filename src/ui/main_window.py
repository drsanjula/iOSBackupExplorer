"""
Main Window - Primary application window combining all UI components.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMenuBar, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence

from .sidebar import Sidebar
from .content_view import ContentView
from .styles import apply_stylesheet, is_dark_mode
from ..utils.constants import APP_NAME, APP_VERSION, MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT


class MainWindow(QMainWindow):
    """
    Main application window for iOS Backup Explorer.
    
    Layout:
    ┌────────────────────────────────────────────────┐
    │                    Menu Bar                     │
    ├──────────┬─────────────────────────────────────┤
    │          │                                      │
    │  Sidebar │           Content View               │
    │          │                                      │
    │ - Backups│  - Header (title, device info)      │
    │ - Types  │  - Stats cards                       │
    │ - Mode   │  - File table                        │
    │          │  - Export controls                   │
    │          │                                      │
    └──────────┴─────────────────────────────────────┘
    """
    
    def __init__(self):
        super().__init__()
        
        self._current_mode = "pro"
        
        self._setup_window()
        self._setup_menu_bar()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_window(self):
        """Configure the main window."""
        self.setWindowTitle(f"{APP_NAME}")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        # Set a reasonable default size
        self.resize(1400, 900)
        
        # Center on screen
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _setup_menu_bar(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Backup...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_backup)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        refresh_action = QAction("Refresh Backups", self)
        refresh_action.setShortcut(QKeySequence("Cmd+R"))
        refresh_action.triggered.connect(self._on_refresh)
        file_menu.addAction(refresh_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        self.lite_mode_action = QAction("Lite Mode", self)
        self.lite_mode_action.setCheckable(True)
        self.lite_mode_action.triggered.connect(lambda: self._set_mode("lite"))
        view_menu.addAction(self.lite_mode_action)
        
        self.pro_mode_action = QAction("Pro Mode", self)
        self.pro_mode_action.setCheckable(True)
        self.pro_mode_action.setChecked(True)
        self.pro_mode_action.triggered.connect(lambda: self._set_mode("pro"))
        view_menu.addAction(self.pro_mode_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction(f"About {APP_NAME}", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_ui(self):
        """Set up the main UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        
        # Sidebar
        self.sidebar = Sidebar()
        splitter.addWidget(self.sidebar)
        
        # Content view
        self.content_view = ContentView()
        splitter.addWidget(self.content_view)
        
        # Set initial sizes (sidebar fixed, content stretches)
        splitter.setSizes([260, 1140])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Sidebar signals
        self.sidebar.backup_selected.connect(self._on_backup_selected)
        self.sidebar.category_selected.connect(self._on_category_selected)
        self.sidebar.mode_changed.connect(self._on_mode_changed)
        
        # Content view signals
        self.content_view.export_finished.connect(self._on_export_finished)
    
    def _on_backup_selected(self, path: Path):
        """Handle backup selection from sidebar."""
        self.content_view.set_backup(path)
    
    def _on_category_selected(self, category: str):
        """Handle category selection from sidebar."""
        self.content_view.set_category(category)
    
    def _on_mode_changed(self, mode: str):
        """Handle mode change from sidebar."""
        self._set_mode(mode)
    
    def _set_mode(self, mode: str):
        """Set the application mode (lite or pro)."""
        self._current_mode = mode
        
        # Update menu checkmarks
        self.lite_mode_action.setChecked(mode == "lite")
        self.pro_mode_action.setChecked(mode == "pro")
        
        # Update content view
        self.content_view.set_mode(mode)
        
        # Refresh stylesheet if needed
        from PyQt6.QtWidgets import QApplication
        apply_stylesheet(QApplication.instance(), mode)
    
    def _on_open_backup(self):
        """Handle File > Open Backup."""
        self.sidebar._on_browse_clicked()
    
    def _on_refresh(self):
        """Handle View > Refresh."""
        self.sidebar.refresh_backups()
    
    def _on_export_finished(self, count: int):
        """Handle export completion."""
        # Could show notification or update status bar
        pass
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"""<h2>{APP_NAME}</h2>
            <p>Version {APP_VERSION}</p>
            <p>A modern app to explore and export iOS backup files.</p>
            <p><b>Features:</b></p>
            <ul>
                <li>📷 Camera Roll export</li>
                <li>👥 Contacts export (Pro)</li>
                <li>💬 Messages export (Pro)</li>
                <li>📝 Notes export (Pro)</li>
                <li>📞 Call history (Pro)</li>
            </ul>
            <p>Made with ❤️ using PyQt6</p>
            """
        )
    
    def closeEvent(self, event):
        """Handle window close."""
        # Clean up resources
        self.content_view.cleanup()
        event.accept()
