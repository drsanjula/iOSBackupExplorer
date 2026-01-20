"""Helper utilities for iOS Backup Explorer."""

import os
import hashlib
import plistlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


def get_file_hash(domain: str, relative_path: str) -> str:
    """
    Generate the SHA1 hash used by iOS to name backup files.
    
    iOS stores files with hashed names: SHA1(domain + "-" + relativePath)
    
    Args:
        domain: The domain (e.g., "CameraRollDomain")
        relative_path: The relative path within the domain
        
    Returns:
        40-character SHA1 hash string
    """
    full_path = f"{domain}-{relative_path}"
    return hashlib.sha1(full_path.encode("utf-8")).hexdigest()


def read_plist(plist_path: Path) -> Optional[Dict[str, Any]]:
    """
    Read and parse a plist file (binary or XML format).
    
    Args:
        plist_path: Path to the plist file
        
    Returns:
        Dictionary with plist contents, or None if failed
    """
    try:
        with open(plist_path, "rb") as f:
            return plistlib.load(f)
    except Exception as e:
        print(f"Error reading plist {plist_path}: {e}")
        return None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB", "256 KB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_timestamp(timestamp: float) -> str:
    """
    Format Unix timestamp to readable date string.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        Formatted date string
    """
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return "Unknown"


def get_file_extension(filename: str) -> str:
    """
    Get lowercase file extension from filename.
    
    Args:
        filename: The filename or path
        
    Returns:
        Lowercase extension with dot (e.g., ".jpg")
    """
    return Path(filename).suffix.lower()


def is_valid_backup_folder(path: Path) -> bool:
    """
    Check if a folder appears to be a valid iOS backup.
    
    A valid iOS backup should contain:
    - Manifest.db or Manifest.mbdb
    - Info.plist
    
    Args:
        path: Path to check
        
    Returns:
        True if folder appears to be a valid backup
    """
    if not path.is_dir():
        return False
    
    has_manifest = (path / "Manifest.db").exists() or (path / "Manifest.mbdb").exists()
    has_info = (path / "Info.plist").exists()
    
    return has_manifest and has_info


def get_device_info(backup_path: Path) -> Dict[str, Any]:
    """
    Extract device information from backup Info.plist.
    
    Args:
        backup_path: Path to backup folder
        
    Returns:
        Dictionary with device info (name, model, iOS version, etc.)
    """
    info_plist = backup_path / "Info.plist"
    info = read_plist(info_plist)
    
    if not info:
        return {"name": "Unknown Device", "error": "Could not read Info.plist"}
    
    return {
        "name": info.get("Device Name", "Unknown Device"),
        "display_name": info.get("Display Name", info.get("Device Name", "Unknown")),
        "model": info.get("Product Type", "Unknown"),
        "ios_version": info.get("Product Version", "Unknown"),
        "serial": info.get("Serial Number", "Unknown"),
        "imei": info.get("IMEI", "Unknown"),
        "phone_number": info.get("Phone Number", "Unknown"),
        "last_backup": info.get("Last Backup Date"),
        "udid": info.get("Unique Identifier", backup_path.name),
    }


def list_available_backups(backup_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    List all available iOS backups in the given directory.
    
    Args:
        backup_dir: Directory to search (defaults to standard backup location)
        
    Returns:
        List of dictionaries with backup info
    """
    from .constants import DEFAULT_BACKUP_PATH
    
    if backup_dir is None:
        backup_dir = DEFAULT_BACKUP_PATH
    
    backups = []
    
    if not backup_dir.exists():
        return backups
    
    for entry in backup_dir.iterdir():
        if entry.is_dir() and is_valid_backup_folder(entry):
            device_info = get_device_info(entry)
            device_info["path"] = entry
            backups.append(device_info)
    
    # Sort by last backup date (newest first)
    backups.sort(
        key=lambda x: x.get("last_backup") or datetime.min,
        reverse=True
    )
    
    return backups


def ensure_dir(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
