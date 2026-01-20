"""
Backup Parser - Core module for parsing iOS backup Manifest.db

This module handles reading and parsing the iOS backup structure,
including the Manifest.db SQLite database that maps hashed filenames
to their original paths.
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Iterator, Any
from datetime import datetime

from ..utils.helpers import read_plist, get_device_info, is_valid_backup_folder
from ..utils.constants import MANIFEST_DB, INFO_PLIST, DOMAINS, DOMAIN_PATHS


@dataclass
class BackupFile:
    """Represents a file within an iOS backup."""
    
    file_id: str  # The SHA1 hash filename in backup
    domain: str   # e.g., "CameraRollDomain"
    relative_path: str  # Original path within domain
    flags: int
    size: int = 0
    mode: int = 0
    mtime: Optional[datetime] = None
    ctime: Optional[datetime] = None
    
    @property
    def full_path(self) -> str:
        """Get the full original path (domain + relative path)."""
        return f"{self.domain}:{self.relative_path}"
    
    @property
    def filename(self) -> str:
        """Get just the filename from the relative path."""
        return Path(self.relative_path).name
    
    @property
    def extension(self) -> str:
        """Get the file extension (lowercase)."""
        return Path(self.relative_path).suffix.lower()
    
    def get_backup_file_path(self, backup_path: Path) -> Path:
        """
        Get the actual file path within the backup folder.
        
        iOS stores files in subdirectories based on first 2 chars of hash.
        e.g., hash "abcdef..." is stored in "ab/abcdef..."
        """
        return backup_path / self.file_id[:2] / self.file_id


@dataclass
class Backup:
    """Represents a complete iOS backup."""
    
    path: Path
    device_name: str = "Unknown Device"
    device_model: str = "Unknown"
    ios_version: str = "Unknown"
    serial_number: str = "Unknown"
    last_backup_date: Optional[datetime] = None
    udid: str = ""
    is_encrypted: bool = False
    
    # Cached file lists by domain
    _files_cache: Dict[str, List[BackupFile]] = field(default_factory=dict)
    
    @property
    def display_name(self) -> str:
        """Get a display-friendly name for the backup."""
        date_str = ""
        if self.last_backup_date:
            date_str = f" ({self.last_backup_date.strftime('%Y-%m-%d')})"
        return f"{self.device_name}{date_str}"
    
    @property
    def manifest_db_path(self) -> Path:
        """Get path to Manifest.db."""
        return self.path / MANIFEST_DB
    
    @property
    def is_valid(self) -> bool:
        """Check if this is a valid backup."""
        return is_valid_backup_folder(self.path)


class BackupParser:
    """
    Parser for iOS backup Manifest.db database.
    
    The Manifest.db contains a 'Files' table with columns:
    - fileID: SHA1 hash of (domain - relativePath)
    - domain: Domain identifier (e.g., CameraRollDomain)
    - relativePath: Original file path within domain
    - flags: File flags
    - file: Binary plist with file metadata
    """
    
    def __init__(self, backup_path: Path):
        """
        Initialize parser with backup path.
        
        Args:
            backup_path: Path to the iOS backup folder
        """
        self.backup_path = Path(backup_path)
        self._connection: Optional[sqlite3.Connection] = None
        self._backup: Optional[Backup] = None
    
    @property
    def backup(self) -> Optional[Backup]:
        """Get the parsed backup info."""
        return self._backup
    
    def open(self) -> bool:
        """
        Open the backup and parse metadata.
        
        Returns:
            True if successful, False otherwise
        """
        if not is_valid_backup_folder(self.backup_path):
            print(f"Invalid backup folder: {self.backup_path}")
            return False
        
        # Parse device info
        device_info = get_device_info(self.backup_path)
        
        # Check for encryption
        manifest_plist = self.backup_path / "Manifest.plist"
        is_encrypted = False
        if manifest_plist.exists():
            manifest_data = read_plist(manifest_plist)
            if manifest_data:
                is_encrypted = manifest_data.get("IsEncrypted", False)
        
        if is_encrypted:
            print("Warning: This backup is encrypted. Only unencrypted backups are supported.")
            return False
        
        # Create Backup object
        self._backup = Backup(
            path=self.backup_path,
            device_name=device_info.get("name", "Unknown Device"),
            device_model=device_info.get("model", "Unknown"),
            ios_version=device_info.get("ios_version", "Unknown"),
            serial_number=device_info.get("serial", "Unknown"),
            last_backup_date=device_info.get("last_backup"),
            udid=device_info.get("udid", self.backup_path.name),
            is_encrypted=is_encrypted,
        )
        
        # Open database connection
        try:
            manifest_db = self.backup_path / MANIFEST_DB
            self._connection = sqlite3.connect(f"file:{manifest_db}?mode=ro", uri=True, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            return True
        except sqlite3.Error as e:
            print(f"Error opening Manifest.db: {e}")
            return False
    
    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def get_files_by_domain(self, domain: str) -> List[BackupFile]:
        """
        Get all files in a specific domain.
        
        Args:
            domain: Domain to query (e.g., "CameraRollDomain")
            
        Returns:
            List of BackupFile objects
        """
        if not self._connection:
            return []
        
        # Check cache
        if domain in self._backup._files_cache:
            return self._backup._files_cache[domain]
        
        files = []
        try:
            cursor = self._connection.execute(
                """
                SELECT fileID, domain, relativePath, flags, file
                FROM Files
                WHERE domain = ?
                """,
                (domain,)
            )
            
            for row in cursor:
                file_metadata = self._parse_file_blob(row["file"])
                
                backup_file = BackupFile(
                    file_id=row["fileID"],
                    domain=row["domain"],
                    relative_path=row["relativePath"],
                    flags=row["flags"],
                    size=file_metadata.get("Size", 0),
                    mode=file_metadata.get("Mode", 0),
                    mtime=file_metadata.get("LastModified"),
                    ctime=file_metadata.get("Birth"),
                )
                files.append(backup_file)
            
            # Cache results
            self._backup._files_cache[domain] = files
            
        except sqlite3.Error as e:
            print(f"Error querying files: {e}")
        
        return files
    
    def get_files_by_domains(self, domains: List[str]) -> List[BackupFile]:
        """
        Get all files from multiple domains.
        
        Args:
            domains: List of domain names
            
        Returns:
            Combined list of BackupFile objects
        """
        all_files = []
        for domain in domains:
            all_files.extend(self.get_files_by_domain(domain))
        return all_files
    
    def get_files_by_path_pattern(
        self, 
        domain: str, 
        path_pattern: str
    ) -> List[BackupFile]:
        """
        Get files matching a path pattern within a domain.
        
        Args:
            domain: Domain to search
            path_pattern: SQL LIKE pattern for relativePath
            
        Returns:
            List of matching BackupFile objects
        """
        if not self._connection:
            return []
        
        files = []
        try:
            cursor = self._connection.execute(
                """
                SELECT fileID, domain, relativePath, flags, file
                FROM Files
                WHERE domain = ? AND relativePath LIKE ?
                """,
                (domain, path_pattern)
            )
            
            for row in cursor:
                file_metadata = self._parse_file_blob(row["file"])
                
                backup_file = BackupFile(
                    file_id=row["fileID"],
                    domain=row["domain"],
                    relative_path=row["relativePath"],
                    flags=row["flags"],
                    size=file_metadata.get("Size", 0),
                    mode=file_metadata.get("Mode", 0),
                    mtime=file_metadata.get("LastModified"),
                    ctime=file_metadata.get("Birth"),
                )
                files.append(backup_file)
                
        except sqlite3.Error as e:
            print(f"Error querying files: {e}")
        
        return files
    
    def get_camera_roll_files(self) -> List[BackupFile]:
        """
        Get all Camera Roll files (photos and videos).
        
        Returns:
            List of BackupFile objects for Camera Roll
        """
        camera_domains = DOMAINS.get("camera_roll", [])
        all_files = []
        
        for domain in camera_domains:
            # Get files from DCIM paths
            for path_prefix in DOMAIN_PATHS.get("camera_roll", []):
                pattern = f"{path_prefix}%"
                files = self.get_files_by_path_pattern(domain, pattern)
                all_files.extend(files)
        
        # Filter to only media files
        from ..utils.constants import MEDIA_EXTENSIONS
        media_files = [f for f in all_files if f.extension in MEDIA_EXTENSIONS]
        
        return media_files
    
    def get_total_file_count(self) -> int:
        """Get total number of files in the backup."""
        if not self._connection:
            return 0
        
        try:
            cursor = self._connection.execute("SELECT COUNT(*) FROM Files")
            return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
    
    def get_domain_stats(self) -> Dict[str, int]:
        """
        Get file count statistics by domain.
        
        Returns:
            Dictionary mapping domain names to file counts
        """
        if not self._connection:
            return {}
        
        stats = {}
        try:
            cursor = self._connection.execute(
                """
                SELECT domain, COUNT(*) as count
                FROM Files
                GROUP BY domain
                ORDER BY count DESC
                """
            )
            for row in cursor:
                stats[row["domain"]] = row["count"]
        except sqlite3.Error as e:
            print(f"Error getting domain stats: {e}")
        
        return stats
    
    def _parse_file_blob(self, blob: bytes) -> Dict[str, Any]:
        """
        Parse the binary plist blob containing file metadata.
        
        Args:
            blob: Binary plist data
            
        Returns:
            Dictionary with file metadata
        """
        if not blob:
            return {}
        
        try:
            import plistlib
            data = plistlib.loads(blob)
            
            result = {}
            if "$objects" in data:
                # NSKeyedArchiver format - extract relevant fields
                objects = data["$objects"]
                for obj in objects:
                    if isinstance(obj, dict):
                        if "Size" in obj:
                            result["Size"] = obj["Size"]
                        if "Mode" in obj:
                            result["Mode"] = obj["Mode"]
                        if "LastModified" in obj:
                            result["LastModified"] = datetime.fromtimestamp(obj["LastModified"])
                        if "Birth" in obj:
                            result["Birth"] = datetime.fromtimestamp(obj["Birth"])
            else:
                # Direct format
                result = data
            
            return result
        except Exception:
            return {}
