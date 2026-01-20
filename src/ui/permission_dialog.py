"""
Permission Dialog - Handle macOS permission requests.

This module provides dialogs for requesting system permissions
like Full Disk Access on macOS.
"""

import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap


class PermissionDialog(QDialog):
    """
    Dialog for requesting Full Disk Access permission.
    
    Shows instructions and provides a button to open System Settings.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Permission Required")
        self.setModal(True)
        self.setFixedSize(500, 380)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Icon
        icon_label = QLabel("🔒")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Title
        title = QLabel("Full Disk Access Required")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Message
        message = QLabel(
            "iOS Backup Explorer needs Full Disk Access to read your iOS backups.\n\n"
            "This permission is required because macOS protects the backup folder "
            "for your privacy and security."
        )
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(message)
        
        # Instructions
        instructions = QFrame()
        instructions.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 122, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        inst_layout = QVBoxLayout(instructions)
        inst_layout.setSpacing(8)
        
        steps = [
            "1. Click 'Open System Settings' below",
            "2. Find 'Terminal' (or 'Python') in the list",
            "3. Toggle the switch to enable access",
            "4. Restart iOS Backup Explorer",
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet("font-size: 12px;")
            inst_layout.addWidget(step_label)
        
        layout.addWidget(instructions)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        browse_btn = QPushButton("Browse Custom Folder")
        browse_btn.clicked.connect(self._on_browse)
        browse_btn.setStyleSheet("padding: 10px 20px;")
        button_layout.addWidget(browse_btn)
        
        button_layout.addStretch()
        
        settings_btn = QPushButton("Open System Settings")
        settings_btn.setObjectName("primaryButton")
        settings_btn.clicked.connect(self._open_settings)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0066DD;
            }
        """)
        button_layout.addWidget(settings_btn)
        
        layout.addLayout(button_layout)
    
    def _open_settings(self):
        """Open System Settings to Full Disk Access."""
        try:
            # macOS Ventura and later use System Settings
            # Earlier versions use System Preferences
            subprocess.run([
                "open", 
                "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
            ], check=False)
        except Exception as e:
            print(f"Error opening System Settings: {e}")
            # Fallback: try opening System Preferences directly
            try:
                subprocess.run([
                    "open", 
                    "/System/Applications/System Settings.app"
                ], check=False)
            except:
                pass
        
        self.accept()
    
    def _on_browse(self):
        """Close dialog and let user browse for a custom folder."""
        self.reject()  # Return Rejected so caller knows to show browse dialog


class PermissionChecker:
    """
    Utility class for checking and requesting permissions.
    """
    
    @staticmethod
    def check_full_disk_access() -> bool:
        """
        Check if the app has Full Disk Access.
        
        Returns:
            True if access is granted
        """
        from ..utils.helpers import check_backup_access
        has_access, _ = check_backup_access()
        return has_access
    
    @staticmethod
    def show_permission_dialog(parent=None) -> bool:
        """
        Show the permission request dialog.
        
        Args:
            parent: Parent widget
            
        Returns:
            True if user clicked "Open Settings", False if "Browse Custom"
        """
        dialog = PermissionDialog(parent)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    
    @staticmethod
    def request_permission_if_needed(parent=None) -> tuple[bool, bool]:
        """
        Check permission and show dialog if needed.
        
        Args:
            parent: Parent widget
            
        Returns:
            Tuple of (has_permission, user_opened_settings)
        """
        if PermissionChecker.check_full_disk_access():
            return True, False
        
        user_opened_settings = PermissionChecker.show_permission_dialog(parent)
        return False, user_opened_settings
