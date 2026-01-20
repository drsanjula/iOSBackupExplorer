"""
Preview Panel - Image and file preview for Pro mode.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage

from ..core.data_extractors.camera_roll import MediaFile
from ..utils.constants import IMAGE_EXTENSIONS


class PreviewPanel(QWidget):
    """
    Preview panel for displaying image thumbnails and file info.
    
    Used in Pro mode to show a preview of selected files.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("previewPanel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)
        
        self._current_file: Optional[MediaFile] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the preview panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("Preview")
        header.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(header)
        
        # Image preview container
        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            padding: 8px;
        """)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        preview_layout.addWidget(self.image_label)
        
        layout.addWidget(self.preview_container)
        
        # File info section
        self.info_container = QWidget()
        info_layout = QVBoxLayout(self.info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)
        
        # Filename
        self.filename_label = QLabel("No file selected")
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet("font-weight: 500;")
        info_layout.addWidget(self.filename_label)
        
        # Details
        self.details_label = QLabel("")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("color: #888; font-size: 12px;")
        info_layout.addWidget(self.details_label)
        
        layout.addWidget(self.info_container)
        
        # Spacer
        layout.addStretch()
        
        # Initial state
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show empty state when no file is selected."""
        self.image_label.setText("📷\n\nSelect a file\nto preview")
        self.image_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.05);
            border-radius: 8px;
            padding: 20px;
            color: #888;
            font-size: 13px;
        """)
        self.filename_label.setText("No file selected")
        self.details_label.setText("")
    
    def set_file(self, media_file: Optional[MediaFile]):
        """
        Set the file to preview.
        
        Args:
            media_file: MediaFile to preview, or None to clear
        """
        self._current_file = media_file
        
        if not media_file:
            self._show_empty_state()
            return
        
        # Update filename
        self.filename_label.setText(media_file.filename)
        
        # Update details
        details = []
        details.append(f"Type: {'Photo' if media_file.is_image else 'Video'}")
        details.append(f"Size: {media_file.size_formatted}")
        if media_file.modified_date:
            details.append(f"Date: {media_file.modified_date.strftime('%Y-%m-%d %H:%M')}")
        details.append(f"Path: {media_file.original_path}")
        
        self.details_label.setText("\n".join(details))
        
        # Load preview
        if media_file.is_image:
            self._load_image_preview(media_file)
        else:
            self._show_video_placeholder(media_file)
    
    def _load_image_preview(self, media_file: MediaFile):
        """Load and display image preview."""
        try:
            if not media_file.exists():
                self.image_label.setText("📷\n\nFile not found")
                return
            
            # Load image
            pixmap = QPixmap(str(media_file.source_path))
            
            if pixmap.isNull():
                # Try loading as raw data
                data = media_file.get_preview_data(max_size=5 * 1024 * 1024)
                if data:
                    image = QImage()
                    if image.loadFromData(data):
                        pixmap = QPixmap.fromImage(image)
            
            if pixmap.isNull():
                self.image_label.setText("📷\n\nCannot preview\nthis format")
                return
            
            # Scale to fit
            scaled = pixmap.scaled(
                self.image_label.size() - QSize(20, 20),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled)
            self.image_label.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 8px;
                padding: 8px;
            """)
            
        except Exception as e:
            self.image_label.setText(f"📷\n\nPreview error:\n{str(e)[:50]}")
    
    def _show_video_placeholder(self, media_file: MediaFile):
        """Show placeholder for video files."""
        self.image_label.setText(f"🎬\n\n{media_file.filename}\n\nVideo preview\nnot available")
        self.image_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.05);
            border-radius: 8px;
            padding: 20px;
            color: #888;
            font-size: 12px;
        """)
    
    def clear(self):
        """Clear the preview."""
        self._current_file = None
        self._show_empty_state()
    
    def resizeEvent(self, event):
        """Handle resize to update image scaling."""
        super().resizeEvent(event)
        
        # Re-scale image if one is displayed
        if self._current_file and self._current_file.is_image:
            self._load_image_preview(self._current_file)
