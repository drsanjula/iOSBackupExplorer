"""
Sidebar - Navigation sidebar with backup selection and data type categories.
"""

from pathlib import Path
from typing import Optional, List, Callable, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..utils.constants import DATA_TYPES, DEFAULT_BACKUP_PATH


class SidebarSection(QFrame):
    """A section in the sidebar with a title and list."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarSection")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Section title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sidebarTitle")
        layout.addWidget(self.title_label)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("sidebarList")
        layout.addWidget(self.list_widget)
    
    def add_item(self, text: str, icon: str = "", data: Any = None) -> QListWidgetItem:
        """Add an item to the section list."""
        display_text = f"{icon}  {text}" if icon else text
        item = QListWidgetItem(display_text)
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.list_widget.addItem(item)
        return item
    
    def clear(self):
        """Clear all items."""
        self.list_widget.clear()
    
    def get_selected_data(self) -> Any:
        """Get the data of the currently selected item."""
        current = self.list_widget.currentItem()
        if current:
            return current.data(Qt.ItemDataRole.UserRole)
        return None


class Sidebar(QWidget):
    """
    Main sidebar widget with backup selection and category navigation.
    
    Signals:
        backup_selected: Emitted when a backup is selected (path)
        category_selected: Emitted when a data category is selected (key)
        mode_changed: Emitted when Lite/Pro mode is toggled (mode string)
    """
    
    backup_selected = pyqtSignal(Path)
    category_selected = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(260)
        
        self._current_mode = "pro"  # "lite" or "pro"
        self._backups: List[Dict[str, Any]] = []
        self._needs_permission = False
        
        self._setup_ui()
        self._connect_signals()
        self._load_backups()
    
    def _setup_ui(self):
        """Set up the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # App title
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(16, 20, 16, 16)
        
        title = QLabel("📱 iOS Backup Explorer")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        title_layout.addWidget(title)
        
        layout.addWidget(title_container)
        
        # Mode toggle
        self.mode_container = QWidget()
        self.mode_container.setObjectName("modeToggle")
        mode_layout = QHBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(12, 8, 12, 8)
        mode_layout.setSpacing(4)
        
        self.lite_btn = QPushButton("Lite")
        self.lite_btn.setCheckable(True)
        self.lite_btn.setChecked(False)
        
        self.pro_btn = QPushButton("Pro")
        self.pro_btn.setCheckable(True)
        self.pro_btn.setChecked(True)
        
        mode_layout.addWidget(self.lite_btn)
        mode_layout.addWidget(self.pro_btn)
        
        layout.addWidget(self.mode_container)
        
        # Backups section
        self.backups_section = SidebarSection("BACKUPS")
        layout.addWidget(self.backups_section)
        
        # Browse button
        browse_container = QWidget()
        browse_layout = QHBoxLayout(browse_container)
        browse_layout.setContentsMargins(16, 8, 16, 16)
        
        self.browse_btn = QPushButton("📂 Browse Custom...")
        self.browse_btn.setObjectName("browseButton")
        browse_layout.addWidget(self.browse_btn)
        
        layout.addWidget(browse_container)
        
        # Categories section
        self.categories_section = SidebarSection("DATA TYPES")
        layout.addWidget(self.categories_section)
        
        # Populate categories
        self._populate_categories()
        
        # Spacer
        layout.addStretch()
        
        # Version info
        version_label = QLabel("v0.1.0")
        version_label.setObjectName("versionLabel")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #888; font-size: 11px; padding: 10px;")
        layout.addWidget(version_label)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.backups_section.list_widget.itemClicked.connect(self._on_backup_clicked)
        self.categories_section.list_widget.itemClicked.connect(self._on_category_clicked)
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        
        self.lite_btn.clicked.connect(lambda: self._set_mode("lite"))
        self.pro_btn.clicked.connect(lambda: self._set_mode("pro"))
    
    def _load_backups(self):
        """Load available backups from default location."""
        from ..utils.helpers import list_available_backups, check_backup_access
        
        self.backups_section.clear()
        
        # Check if we have access
        has_access, message = check_backup_access()
        
        if not has_access:
            # Show permission required message
            item = self.backups_section.add_item("Permission required", "🔒")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setToolTip(message)
            
            # Add clickable "Request Access" button
            request_item = self.backups_section.add_item("Request Access...", "⚙️")
            request_item.setData(Qt.ItemDataRole.UserRole, "__request_permission__")
            request_item.setToolTip("Click to open System Settings")
            
            self._needs_permission = True
            return
        
        self._needs_permission = False
        self._backups = list_available_backups()
        
        if not self._backups:
            item = self.backups_section.add_item("No backups found", "❌")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setToolTip("Use 'Browse Custom...' to select a backup folder")
        else:
            for backup in self._backups:
                display_name = backup.get("display_name", backup.get("name", "Unknown"))
                model = backup.get("model", "")
                if model:
                    display_name = f"{display_name}"
                self.backups_section.add_item(display_name, "📱", backup.get("path"))
    
    def _populate_categories(self):
        """Populate the data types section."""
        self.categories_section.clear()
        
        for key, info in DATA_TYPES.items():
            item = self.categories_section.add_item(
                info["name"],
                info["icon"],
                key
            )
            
            # Mark pro-only items
            if info.get("pro_only", False) and self._current_mode == "lite":
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip("Available in Pro mode")
    
    def _set_mode(self, mode: str):
        """Set the current mode (lite or pro)."""
        self._current_mode = mode
        
        self.lite_btn.setChecked(mode == "lite")
        self.pro_btn.setChecked(mode == "pro")
        
        # Re-populate categories with new mode
        self._populate_categories()
        
        self.mode_changed.emit(mode)
    
    def _on_backup_clicked(self, item: QListWidgetItem):
        """Handle backup selection."""
        data = item.data(Qt.ItemDataRole.UserRole)
        
        # Check if this is the permission request action
        if data == "__request_permission__":
            self._request_permission()
            return
        
        # Normal backup selection
        if data and isinstance(data, Path):
            self.backup_selected.emit(data)
    
    def _request_permission(self):
        """Show permission dialog and handle result."""
        from .permission_dialog import PermissionDialog
        
        dialog = PermissionDialog(self)
        result = dialog.exec()
        
        if result == dialog.DialogCode.Rejected:
            # User chose to browse custom folder
            self._on_browse_clicked()
    
    def _on_category_clicked(self, item: QListWidgetItem):
        """Handle category selection."""
        key = item.data(Qt.ItemDataRole.UserRole)
        if key:
            info = DATA_TYPES.get(key, {})
            # Check if pro-only in lite mode
            if info.get("pro_only", False) and self._current_mode == "lite":
                return
            self.category_selected.emit(key)
    
    def _on_browse_clicked(self):
        """Handle browse button click."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select iOS Backup Folder",
            str(DEFAULT_BACKUP_PATH),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            path = Path(folder)
            self.backup_selected.emit(path)
    
    def get_current_mode(self) -> str:
        """Get the current mode (lite or pro)."""
        return self._current_mode
    
    def refresh_backups(self):
        """Refresh the backup list."""
        self._load_backups()
