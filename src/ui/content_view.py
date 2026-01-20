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
    QStackedWidget, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QPixmap, QImage

from ..core.backup_parser import BackupParser, Backup
from ..core.data_extractors.camera_roll import CameraRollExtractor, MediaFile, ExportProgress
from ..core.data_extractors.contacts import ContactsExtractor, Contact
from ..core.data_extractors.messages import MessagesExtractor, Chat
from ..core.data_extractors.notes import NotesExtractor, Note
from ..core.data_extractors.call_history import CallHistoryExtractor, CallRecord
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


class LoadWorker(QThread):
    """Worker thread for loading data."""
    
    finished = pyqtSignal(object)  # data (list of items)
    stats_ready = pyqtSignal(dict)  # stats dict
    error = pyqtSignal(str)
    
    def __init__(self, fetch_func: Callable, stats_func: Callable = None):
        super().__init__()
        self.fetch_func = fetch_func
        self.stats_func = stats_func
    
    def run(self):
        """Run the load operation."""
        try:
            # Fetch stats first if available
            if self.stats_func:
                stats = self.stats_func()
                self.stats_ready.emit(stats)
            
            # Fetch data
            data = self.fetch_func()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class ExportWorker(QThread):
    """Worker thread for exporting files with detailed stats."""
    
    # current, total, filename, stats_dict
    progress = pyqtSignal(int, int, str, dict)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    
    def __init__(self, extractor: CameraRollExtractor, destination: Path, filter_type: str = None):
        super().__init__()
        self.extractor = extractor
        self.destination = destination
        self.filter_type = filter_type
        self._cancelled = False
    
    def run(self):
        """Run the export operation."""
        import time
        try:
            successful = 0
            start_time = time.time()
            
            for p in self.extractor.export_all(
                self.destination,
                filter_type=self.filter_type
            ):
                if self._cancelled:
                    break
                
                # Calculate stats
                elapsed = time.time() - start_time
                rate = p.current / elapsed if elapsed > 0 else 0
                remaining_items = p.total - p.current
                eta_seconds = remaining_items / rate if rate > 0 else 0
                
                stats = {
                    "rate": f"{rate:.1f} files/s",
                    "eta": f"{int(eta_seconds)}s",
                    "elapsed": f"{int(elapsed)}s",
                    "percentage": p.percentage
                }
                
                self.progress.emit(p.current, p.total, p.current_file, stats)
                successful = p.current
            
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
        self._current_category: str = "camera_roll"
        self._export_worker: Optional[ExportWorker] = None
        self._load_worker: Optional[LoadWorker] = None
        self._mode: str = "pro"
        
        # Extractors for different data types
        self._camera_extractor: Optional[CameraRollExtractor] = None
        self._contacts_extractor: Optional[ContactsExtractor] = None
        self._messages_extractor: Optional[MessagesExtractor] = None
        self._notes_extractor: Optional[NotesExtractor] = None
        self._calls_extractor: Optional[CallHistoryExtractor] = None
        
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
        
        # Loading state
        self.loading_state = EmptyState(
            "⏳",
            "Loading Data...",
            "Please wait while we analyze your backup."
        )
        self.stack.addWidget(self.loading_state)
        
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
        
        # Stats container
        stats_layout = QHBoxLayout()
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #333; font-weight: 500;")
        stats_layout.addWidget(self.progress_label)
        
        stats_layout.addStretch()
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        stats_layout.addWidget(self.stats_label)
        
        progress_layout.addLayout(stats_layout)
        
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
        
        # Initialize all extractors
        self._camera_extractor = CameraRollExtractor(self._parser)
        self._contacts_extractor = ContactsExtractor(self._parser)
        self._messages_extractor = MessagesExtractor(self._parser)
        self._notes_extractor = NotesExtractor(self._parser)
        self._calls_extractor = CallHistoryExtractor(self._parser)
        
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
        
        # Stop previous load if running
        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.wait()
        
        self.stack.setCurrentWidget(self.loading_state)
        # Process events to show loading state immediately
        QApplication.processEvents()
        
        fetch_func = None
        stats_func = None
        columns = []
        
        if category == "camera_roll" and self._camera_extractor:
            fetch_func = self._camera_extractor.get_all_media
            stats_func = self._camera_extractor.get_stats
            columns = ["Filename", "Type", "Size", "Date"]
            
        elif category == "contacts" and self._contacts_extractor:
            fetch_func = self._contacts_extractor.get_all_contacts
            stats_func = self._contacts_extractor.get_stats
            columns = ["Name", "Phone", "Email", "Organization"]
            
        elif category == "messages" and self._messages_extractor:
            fetch_func = self._messages_extractor.get_all_chats
            stats_func = self._messages_extractor.get_stats
            columns = ["Contact", "Messages", "Last Message", "Preview"]
            
        elif category == "notes" and self._notes_extractor:
            fetch_func = self._notes_extractor.get_all_notes
            stats_func = self._notes_extractor.get_stats
            columns = ["Title", "Words", "Modified", "Preview"]
            
        elif category == "call_history" and self._calls_extractor:
            fetch_func = self._calls_extractor.get_all_calls
            stats_func = self._calls_extractor.get_stats
            columns = ["Phone Number", "Type", "Duration", "Date"]
        
        if fetch_func:
            self._setup_table_columns(columns)
            self._start_loading(fetch_func, stats_func)
        else:
            self._clear_table()
            self.stack.setCurrentWidget(self.content_widget)

    def _setup_table_columns(self, labels: List[str]):
        """Setup table columns."""
        self.table.setColumnCount(len(labels))
        self.table.setHorizontalHeaderLabels(labels)
        self.table.setRowCount(0)

    def _start_loading(self, fetch_func, stats_func):
        """Start the background load worker."""
        self._load_worker = LoadWorker(fetch_func, stats_func)
        self._load_worker.stats_ready.connect(self._on_stats_ready)
        self._load_worker.finished.connect(self._on_load_finished)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.start()

    @pyqtSlot(dict)
    def _on_stats_ready(self, stats: dict):
        """Handle stats update."""
        category = self._current_category
        
        if category == "camera_roll":
            self.stat_total.update_value(str(stats["total_count"]))
            self.stat_photos.update_value(str(stats["photo_count"]))
            self.stat_videos.update_value(str(stats["video_count"]))
            self.stat_size.update_value(stats["total_size_formatted"])
            
        elif category == "contacts":
            self.stat_total.update_value(str(stats["total_count"]))
            self.stat_photos.update_value(f"📞 {stats['with_phones']}")
            self.stat_videos.update_value(f"📧 {stats['with_emails']}")
            self.stat_size.update_value("-")
            
        elif category == "messages":
            self.stat_total.update_value(str(stats["chat_count"]))
            self.stat_photos.update_value(f"💬 {stats['message_count']}")
            self.stat_videos.update_value(f"📱 iMsg: {stats['imessage_count']}")
            self.stat_size.update_value(f"📨 SMS: {stats['sms_count']}")
            
        elif category == "notes":
            self.stat_total.update_value(str(stats["note_count"]))
            self.stat_photos.update_value(f"📝 {stats['total_words']} words")
            self.stat_videos.update_value("-")
            self.stat_size.update_value("-")
            
        elif category == "call_history":
            self.stat_total.update_value(str(stats["total_calls"]))
            self.stat_photos.update_value(f"📥 {stats['incoming']}")
            self.stat_videos.update_value(f"📤 {stats['outgoing']}")
            self.stat_size.update_value(f"📵 {stats['missed']}")

    @pyqtSlot(object)
    def _on_load_finished(self, data: object):
        """Handle load completion."""
        self.stack.setCurrentWidget(self.content_widget)
        
        category = self._current_category
        if category == "camera_roll":
            self._populate_camera_roll(data)
        elif category == "contacts":
            self._populate_contacts(data)
        elif category == "messages":
            self._populate_messages(data)
        elif category == "notes":
            self._populate_notes(data)
        elif category == "call_history":
            self._populate_call_history(data)
    
    @pyqtSlot(str)
    def _on_load_error(self, error: str):
        """Handle load error."""
        self.stack.setCurrentWidget(self.content_widget)
        # Maybe show error in empty state instead?
        QMessageBox.warning(self, "Load Error", f"Failed to load data: {error}")
    
    def _clear_table(self):
        """Clear the table and reset stats."""
        self.table.setRowCount(0)
        self.stat_total.update_value("0")
        self.stat_photos.update_value("-")
        self.stat_videos.update_value("-")
        self.stat_size.update_value("-")
    
    def _populate_camera_roll(self, files: List[MediaFile]):
        """Populate table with Camera Roll data."""
        self.table.setRowCount(len(files))
        
        for row, media in enumerate(files):
            self.table.setItem(row, 0, QTableWidgetItem(media.filename))
            type_str = "📷 Photo" if media.is_image else "🎬 Video"
            self.table.setItem(row, 1, QTableWidgetItem(type_str))
            self.table.setItem(row, 2, QTableWidgetItem(media.size_formatted))
            date_str = media.modified_date.strftime("%Y-%m-%d %H:%M") if media.modified_date else ""
            self.table.setItem(row, 3, QTableWidgetItem(date_str))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, media)
    
    def _populate_contacts(self, contacts: List[Contact]):
        """Populate table with Contacts data."""
        self.table.setRowCount(len(contacts))
        
        for row, contact in enumerate(contacts):
            self.table.setItem(row, 0, QTableWidgetItem(contact.display_name))
            self.table.setItem(row, 1, QTableWidgetItem(contact.primary_phone))
            self.table.setItem(row, 2, QTableWidgetItem(contact.primary_email))
            self.table.setItem(row, 3, QTableWidgetItem(contact.organization))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, contact)
    
    def _populate_messages(self, chats: List[Chat]):
        """Populate table with Messages data."""
        self.table.setRowCount(len(chats))
        
        for row, chat in enumerate(chats):
            self.table.setItem(row, 0, QTableWidgetItem(chat.display_name))
            self.table.setItem(row, 1, QTableWidgetItem(str(chat.message_count)))
            date_str = chat.last_message_date.strftime("%Y-%m-%d %H:%M") if chat.last_message_date else ""
            self.table.setItem(row, 2, QTableWidgetItem(date_str))
            self.table.setItem(row, 3, QTableWidgetItem(chat.preview[:50] + "..." if len(chat.preview) > 50 else chat.preview))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, chat)
    
    def _populate_notes(self, notes: List[Note]):
        """Populate table with Notes data."""
        self.table.setRowCount(len(notes))
        
        for row, note in enumerate(notes):
            self.table.setItem(row, 0, QTableWidgetItem(note.title))
            self.table.setItem(row, 1, QTableWidgetItem(str(note.word_count)))
            self.table.setItem(row, 2, QTableWidgetItem(note.modified_formatted))
            preview = note.preview[:50] + "..." if len(note.preview) > 50 else note.preview
            self.table.setItem(row, 3, QTableWidgetItem(preview))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, note)
    
    def _populate_call_history(self, calls: List[CallRecord]):
        """Populate table with Call History data."""
        self.table.setRowCount(len(calls))
        
        for row, call in enumerate(calls):
            self.table.setItem(row, 0, QTableWidgetItem(call.phone_number))
            self.table.setItem(row, 1, QTableWidgetItem(f"{call.call_type_icon} {call.call_type_name}"))
            self.table.setItem(row, 2, QTableWidgetItem(call.duration_formatted))
            self.table.setItem(row, 3, QTableWidgetItem(call.date_formatted))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, call)
    
    def _on_selection_changed(self):
        """Handle table selection changes."""
        selected = self.table.selectedItems()
        self.export_selected_btn.setEnabled(len(selected) > 0)
    
    def _export_all(self):
        """Export all data based on current category."""
        destination = self._get_export_destination()
        if not destination:
            return
        
        category = self._current_category
        
        if category == "camera_roll" and self._camera_extractor:
            self._start_camera_export(destination)
        elif category == "contacts" and self._contacts_extractor:
            self._export_contacts(destination)
        elif category == "messages" and self._messages_extractor:
            self._export_messages(destination)
        elif category == "notes" and self._notes_extractor:
            self._export_notes(destination)
        elif category == "call_history" and self._calls_extractor:
            self._export_calls(destination)
    
    def _export_selected(self):
        """Export selected items (Camera Roll only for now)."""
        if self._current_category != "camera_roll" or not self._camera_extractor:
            # For non-camera categories, export all
            self._export_all()
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
    
    def _export_contacts(self, destination: Path):
        """Export contacts as vCards."""
        count = self._contacts_extractor.export_all_vcards(destination)
        QMessageBox.information(
            self, "Export Complete",
            f"Successfully exported {count} contacts as vCard files."
        )
        self.export_finished.emit(count)
    
    def _export_messages(self, destination: Path):
        """Export messages as text files."""
        count = self._messages_extractor.export_all_chats(destination)
        QMessageBox.information(
            self, "Export Complete",
            f"Successfully exported {count} conversations as text files."
        )
        self.export_finished.emit(count)
    
    def _export_notes(self, destination: Path):
        """Export notes as text files."""
        count = self._notes_extractor.export_all_notes(destination)
        QMessageBox.information(
            self, "Export Complete",
            f"Successfully exported {count} notes as text files."
        )
        self.export_finished.emit(count)
    
    def _export_calls(self, destination: Path):
        """Export call history as CSV."""
        csv_path = destination / "call_history.csv"
        success = self._calls_extractor.export_all_calls(csv_path)
        if success:
            stats = self._calls_extractor.get_stats()
            QMessageBox.information(
                self, "Export Complete",
                f"Successfully exported {stats['total_calls']} call records to:\n{csv_path}"
            )
            self.export_finished.emit(stats['total_calls'])
        else:
            QMessageBox.warning(self, "Export Failed", "Failed to export call history.")
    
    def _start_camera_export(self, destination: Path):
        """Start Camera Roll export in background thread."""
        self.export_started.emit()
        
        self.progress_container.show()
        self.progress_bar.setValue(0)
        self.export_all_btn.setEnabled(False)
        self.export_selected_btn.setEnabled(False)
        
        self._export_worker = ExportWorker(self._camera_extractor, destination)
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()
    
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
    
    def _start_export_files(self, files: List[MediaFile], destination: Path):
        """Start exporting specific files."""
        if not self._camera_extractor:
            return
        
        self.export_started.emit()
        
        self.progress_container.show()
        self.progress_bar.setValue(0)
        self.export_all_btn.setEnabled(False)
        self.export_selected_btn.setEnabled(False)
        
        # Export directly (could be threaded for large selections)
        self.stats_label.setText("Exporting selected files...")
        
        def progress_callback(p: ExportProgress):
            self.progress_bar.setValue(int(p.percentage))
            self.progress_label.setText(f"Exporting: {p.current_file}")
            # Ensure UI updates during blocking operation
            QApplication.processEvents()
        
        count = self._camera_extractor.export_files(files, destination, progress_callback)
        self._on_export_finished(count)
    
    @pyqtSlot(int, int, str, dict)
    def _on_export_progress(self, current: int, total: int, filename: str, stats: dict):
        """Handle export progress update with detailed stats."""
        # Update progress bar
        self.progress_bar.setValue(int(stats.get("percentage", 0)))
        
        # Update filename label (truncate if too long)
        display_name = filename
        if len(display_name) > 40:
            display_name = "..." + display_name[-37:]
        self.progress_label.setText(f"Exporting: {display_name}")
        
        # Update stats label
        rate = stats.get("rate", "-")
        eta = stats.get("eta", "-")
        self.stats_label.setText(f"Speed: {rate} • ETA: {eta} • {current}/{total}")
    
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
