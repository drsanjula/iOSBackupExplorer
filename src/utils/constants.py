"""Constants used throughout the iOS Backup Explorer."""

import os
from pathlib import Path

# Default iOS backup location on macOS
DEFAULT_BACKUP_PATH = Path.home() / "Library" / "Application Support" / "MobileSync" / "Backup"

# iOS backup file structure
MANIFEST_DB = "Manifest.db"
MANIFEST_PLIST = "Manifest.plist"
INFO_PLIST = "Info.plist"
STATUS_PLIST = "Status.plist"

# Domain identifiers for different data types in iOS backups
DOMAINS = {
    "camera_roll": ["CameraRollDomain", "MediaDomain"],
    "contacts": ["HomeDomain"],
    "messages": ["HomeDomain"],
    "notes": ["AppDomainGroup-group.com.apple.notes"],
    "call_history": ["HomeDomain", "WirelessDomain"],
}

# File paths within domains (relative paths in backup)
DOMAIN_PATHS = {
    "camera_roll": [
        "Media/DCIM",
        "Media/PhotoData",
    ],
    "contacts": [
        "Library/AddressBook/AddressBook.sqlitedb",
        "Library/AddressBook/AddressBookImages.sqlitedb",
    ],
    "messages": [
        "Library/SMS/sms.db",
        "Library/SMS/Attachments",
    ],
    "notes": [
        "NoteStore.sqlite",
    ],
    "call_history": [
        "Library/CallHistoryDB/CallHistory.storedata",
        "Library/CallHistory/call_history.db",
    ],
}

# Supported media extensions for Camera Roll
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif", ".bmp", ".tiff", ".webp"}
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v", ".avi", ".3gp"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# App metadata
APP_NAME = "iOS Backup Explorer"
APP_VERSION = "0.1.0"
APP_AUTHOR = "drsanjula"

# UI Constants
SIDEBAR_WIDTH = 250
PREVIEW_PANEL_WIDTH = 300
MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 700

# Export settings
DEFAULT_EXPORT_FOLDER = Path.home() / "Desktop" / "iOS_Export"
CHUNK_SIZE = 1024 * 1024  # 1MB for file copying

# Data type display info
DATA_TYPES = {
    "camera_roll": {
        "name": "Camera Roll",
        "icon": "📷",
        "description": "Photos and videos from your device",
        "pro_only": False,
    },
    "contacts": {
        "name": "Contacts",
        "icon": "👥",
        "description": "Address book contacts",
        "pro_only": True,
    },
    "messages": {
        "name": "Messages",
        "icon": "💬",
        "description": "iMessage and SMS conversations",
        "pro_only": True,
    },
    "notes": {
        "name": "Notes",
        "icon": "📝",
        "description": "Notes app content",
        "pro_only": True,
    },
    "call_history": {
        "name": "Call History",
        "icon": "📞",
        "description": "Phone call logs",
        "pro_only": True,
    },
}
