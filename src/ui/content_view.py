"""
Content View - Main content area displaying files and stats.
"""

from pathlib import Path
from typing import Optional, List, Callable
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QFrame,
    QProgressBar, QFileDialog, QMessageBox, QGridLayout,
    QStackedWidget, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPixmap, QImage

from ..core.backup_parser import BackupParser, Backup
from ..core.data_extractors.camera_roll import CameraRollExtractor, MediaFile, ExportProgress
from ..utils.helpers import format_file_size
from ..utils.constants import DATA_TYPES


class StatCard(QFrame):
    """A card displaying a single statistic."""
    
    def __init__(self, icon: str, value: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statsCard")
        self.setMinimumWidth(150)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        layout.addWidget(self.value_label)
        
        # Label
        self.label_label = QLabel(label)
        self.label_label.setObjectName("statLabel")
        layout.addWidget(self.label_label)
    
    def update_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)


class EmptyState(QWidget):
    """Empty state placeholder with icon, title, and message."""
    
    def __init__(self, icon: str, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setObjectName("emptyIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel(title)
        title_label.setObjectName("emptyTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Message
        message_label = QLabel(message)
        message_label.setObjectName("emptyMessage")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)


class ExportWorker(QThread):
    """Worker thread for exporting files."""
    
    progress = pyqtSignal(int, int, str)  # current, total, filename
    finished = pyqtSignal(int)  # successful count
    error = pyqtSignal(str)
    
    def __init__(self, extractor: CameraRollExtractor, destination: Path, filter_type: str = None):
        super().__init__()
        self.extractor = extractor
        self.destination = destination
        self.filter_type = filter_type
        self._cancelled = False
    
    def run(self):
        """Run the export operation."""
        try:
            successful = 0
            for progress in self.extractor.export_all(
                self.destination,
                filter_type=self.filter_type
            ):
                if self._cancelled:
                    break
                self.progress.emit(progress.current, progress.total, progress.current_file)
                successful = progress.current
            
            self.finished.emit(successful)
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        """Cancel the export operation."""
        self._cancelled = True


class ContentView(QWidget):
    """
    Main content view displaying stats, file list, and export controls.
    
    Signals:
        export_started: Emitted when export begins
        export_finished: Emitted when export completes (count)
    """
    
    export_started = pyqtSignal()
    export_finished = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self._parser: Optional[BackupParser] = None
        self._backup: Optional[Backup] = None
        self._extractor: Optional[CameraRollExtractor] = None
        self._current_category: str = "camera_roll"
        self._export_worker: Optional[ExportWorker] = None
        self._mode: str = "pro"
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the content UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Stacked widget for different views
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Empty state (no backup selected)
        self.empty_state = EmptyState(
            "📱",
            "Select a Backup",
            "Choose an iOS backup from the sidebar to view its contents."
        )
        self.stack.addWidget(self.empty_state)
        
        # Content container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 0, 24, 24)
        self.content_layout.setSpacing(20)
        
        # Header
        self._setup_header()
        
        # Stats cards
        self._setup_stats()
        
        # File table
        self._setup_table()
        
        # Export controls
        self._setup_export_controls()
        
        self.stack.addWidget(self.content_widget)
        self.stack.setCurrentWidget(self.empty_state)
    
    def _setup_header(self):
        """Set up the content header."""
        header = QWidget()
        header.setObjectName("contentHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(4)
        
        # Title row
        title_row = QHBoxLayout()
        
        self.header_title = QLabel("Camera Roll")
        self.header_title.setObjectName("headerTitle")
        title_row.addWidget(self.header_title)
        
        title_row.addStretch()
        
        # Device info
        self.device_label = QLabel("")
        self.device_label.setObjectName("headerSubtitle")
        title_row.addWidget(self.device_label)
        
        header_layout.addLayout(title_row)
        
        # Subtitle
        self.header_subtitle = QLabel("Photos and videos from your device")
        self.header_subtitle.setObjectName("headerSubtitle")
        header_layout.addWidget(self.header_subtitle)
        
        self.content_layout.addWidget(header)
    
    def _setup_stats(self):
        """Set up stats cards."""
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(16)
        
        self.stat_total = StatCard("📁", "0", "TOTAL FILES")
        self.stat_photos = StatCard("📷", "0", "PHOTOS")
        self.stat_videos = StatCard("🎬", "0", "VIDEOS")
        self.stat_size = StatCard("💾", "0 MB", "TOTAL SIZE")
        
        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self.stat_photos)
        stats_layout.addWidget(self.stat_videos)
        stats_layout.addWidget(self.stat_size)
        stats_layout.addStretch()
        
        self.content_layout.addWidget(stats_container)
    
    def _setup_table(self):
        """Set up the file table."""
        self.table = QTableWidget()
        self.table.setObjectName("fileTable")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Filename", "Type", "Size", "Date"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        
        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.content_layout.addWidget(self.table, 1)  # Stretch factor
    
    def _setup_export_controls(self):
        """Set up export controls."""
        export_container = QWidget()
        export_layout = QVBoxLayout(export_container)
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.setSpacing(12)
        
        # Progress bar (hidden by default)
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888; font-size: 12px;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_container.hide()
        export_layout.addWidget(self.progress_container)
        
        # Button row
        button_row = QHBoxLayout()
        button_row.addStretch()
        
        self.export_selected_btn = QPushButton("Export Selected")
        self.export_selected_btn.clicked.connect(self._export_selected)
        self.export_selected_btn.setEnabled(False)
        button_row.addWidget(self.export_selected_btn)
        
        self.export_all_btn = QPushButton("Export All")
        self.export_all_btn.setObjectName("primaryButton")
        self.export_all_btn.clicked.connect(self._export_all)
        button_row.addWidget(self.export_all_btn)
        
        export_layout.addLayout(button_row)
        
        self.content_layout.addWidget(export_container)
        
        # Connect table selection
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_backup(self, backup_path: Path):
        """
        Set the current backup to display.
        
        Args:
            backup_path: Path to the backup folder
        """
        # Close existing parser
        if self._parser:
            self._parser.close()
        
        # Open new parser
        self._parser = BackupParser(backup_path)
        if not self._parser.open():
            QMessageBox.warning(
                self,
                "Invalid Backup",
                f"Could not open backup at:\n{backup_path}\n\nMake sure this is a valid, unencrypted iOS backup."
            )
            return
        
        self._backup = self._parser.backup
        self._extractor = CameraRollExtractor(self._parser)
        
        # Update header
        if self._backup:
            self.device_label.setText(
                f"{self._backup.device_name} • iOS {self._backup.ios_version}"
            )
        
        # Show content
        self.stack.setCurrentWidget(self.content_widget)
        
        # Load current category
        self._load_category(self._current_category)
    
    def set_category(self, category: str):
        """
        Set the current data category to display.
        
        Args:
            category: Category key (e.g., "camera_roll")
        """
        self._current_category = category
        
        if self._parser:
            self._load_category(category)
    
    def set_mode(self, mode: str):
        """
        Set Lite/Pro mode.
        
        Args:
            mode: "lite" or "pro"
        """
        self._mode = mode
        # Could show/hide pro features here
    
    def _load_category(self, category: str):
        """Load and display a data category."""
        info = DATA_TYPES.get(category, {})
        
        self.header_title.setText(info.get("name", category))
        self.header_subtitle.setText(info.get("description", ""))
        
        if category == "camera_roll" and self._extractor:
            self._load_camera_roll()
        else:
            # Placeholder for other categories
            self.table.setRowCount(0)
            self.stat_total.update_value("0")
            self.stat_photos.update_value("0")
            self.stat_videos.update_value("0")
            self.stat_size.update_value("0 MB")
    
    def _load_camera_roll(self):
        """Load Camera Roll data."""
        if not self._extractor:
            return
        
        # Get stats
        stats = self._extractor.get_stats()
        
        self.stat_total.update_value(str(stats["total_count"]))
        self.stat_photos.update_value(str(stats["photo_count"]))
        self.stat_videos.update_value(str(stats["video_count"]))
        self.stat_size.update_value(stats["total_size_formatted"])
        
        # Populate table
        files = self._extractor.get_all_media()
        self.table.setRowCount(len(files))
        
        for row, media in enumerate(files):
            # Filename
            self.table.setItem(row, 0, QTableWidgetItem(media.filename))
            
            # Type
            type_str = "📷 Photo" if media.is_image else "🎬 Video"
            self.table.setItem(row, 1, QTableWidgetItem(type_str))
            
            # Size
            self.table.setItem(row, 2, QTableWidgetItem(media.size_formatted))
            
            # Date
            date_str = ""
            if media.modified_date:
                date_str = media.modified_date.strftime("%Y-%m-%d %H:%M")
            self.table.setItem(row, 3, QTableWidgetItem(date_str))
            
            # Store reference
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, media)
    
    def _on_selection_changed(self):
        """Handle table selection changes."""
        selected = self.table.selectedItems()
        self.export_selected_btn.setEnabled(len(selected) > 0)
    
    def _export_all(self):
        """Export all files."""
        if not self._extractor:
            return
        
        destination = self._get_export_destination()
        if not destination:
            return
        
        self._start_export(destination)
    
    def _export_selected(self):
        """Export selected files."""
        if not self._extractor:
            return
        
        # Get selected files
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        files = []
        for row in selected_rows:
            item = self.table.item(row, 0)
            if item:
                media = item.data(Qt.ItemDataRole.UserRole)
                if media:
                    files.append(media)
        
        destination = self._get_export_destination()
        if not destination:
            return
        
        # Export selected files
        self._start_export_files(files, destination)
    
    def _get_export_destination(self) -> Optional[Path]:
        """Show folder picker and return selected path."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Export Destination",
            str(Path.home() / "Desktop"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            return Path(folder)
        return None
    
    def _start_export(self, destination: Path):
        """Start export in background thread."""
        self.export_started.emit()
        
        self.progress_container.show()
        self.progress_bar.setValue(0)
        self.export_all_btn.setEnabled(False)
        self.export_selected_btn.setEnabled(False)
        
        self._export_worker = ExportWorker(self._extractor, destination)
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()
    
    def _start_export_files(self, files: List[MediaFile], destination: Path):
        """Start exporting specific files."""
        self.export_started.emit()
        
        self.progress_container.show()
        self.progress_bar.setValue(0)
        self.export_all_btn.setEnabled(False)
        self.export_selected_btn.setEnabled(False)
        
        # Export directly (could be threaded for large selections)
        def progress_callback(p: ExportProgress):
            self.progress_bar.setValue(int(p.percentage))
            self.progress_label.setText(f"Exporting: {p.current_file}")
        
        count = self._extractor.export_files(files, destination, progress_callback)
        self._on_export_finished(count)
    
    @pyqtSlot(int, int, str)
    def _on_export_progress(self, current: int, total: int, filename: str):
        """Handle export progress update."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"Exporting: {filename} ({current}/{total})")
    
    @pyqtSlot(int)
    def _on_export_finished(self, count: int):
        """Handle export completion."""
        self.progress_container.hide()
        self.export_all_btn.setEnabled(True)
        self._on_selection_changed()  # Re-enable selected button if applicable
        
        QMessageBox.information(
            self,
            "Export Complete",
            f"Successfully exported {count} files."
        )
        
        self.export_finished.emit(count)
    
    @pyqtSlot(str)
    def _on_export_error(self, error: str):
        """Handle export error."""
        self.progress_container.hide()
        self.export_all_btn.setEnabled(True)
        self._on_selection_changed()
        
        QMessageBox.critical(
            self,
            "Export Error",
            f"An error occurred during export:\n{error}"
        )
    
    def cleanup(self):
        """Clean up resources."""
        if self._export_worker:
            self._export_worker.cancel()
            self._export_worker.wait()
        
        if self._parser:
            self._parser.close()
