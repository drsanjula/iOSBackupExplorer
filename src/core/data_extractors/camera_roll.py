"""
Camera Roll Extractor - Extract photos and videos from iOS backups.

This module handles extracting Camera Roll media files from iOS backups,
preserving original filenames and maintaining proper file extensions.
"""

import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Callable, Generator
from datetime import datetime

from ..backup_parser import BackupParser, BackupFile
from ...utils.constants import MEDIA_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from ...utils.helpers import format_file_size, ensure_dir


@dataclass
class MediaFile:
    """Represents a media file from Camera Roll."""
    
    backup_file: BackupFile
    backup_path: Path  # Path to the backup folder
    
    @property
    def filename(self) -> str:
        """Original filename."""
        return self.backup_file.filename
    
    @property
    def extension(self) -> str:
        """File extension (lowercase)."""
        return self.backup_file.extension
    
    @property
    def is_image(self) -> bool:
        """Check if file is an image."""
        return self.extension in IMAGE_EXTENSIONS
    
    @property
    def is_video(self) -> bool:
        """Check if file is a video."""
        return self.extension in VIDEO_EXTENSIONS
    
    @property
    def size(self) -> int:
        """File size in bytes."""
        return self.backup_file.size
    
    @property
    def size_formatted(self) -> str:
        """Human-readable file size."""
        return format_file_size(self.size)
    
    @property
    def modified_date(self) -> Optional[datetime]:
        """Last modified date."""
        return self.backup_file.mtime
    
    @property
    def source_path(self) -> Path:
        """Path to the file in the backup."""
        return self.backup_file.get_backup_file_path(self.backup_path)
    
    @property
    def original_path(self) -> str:
        """Original path on the device."""
        return self.backup_file.relative_path
    
    def exists(self) -> bool:
        """Check if the source file exists."""
        return self.source_path.exists()
    
    def get_preview_data(self, max_size: int = 1024 * 1024) -> Optional[bytes]:
        """
        Get file data for preview (limited size for images).
        
        Args:
            max_size: Maximum bytes to read
            
        Returns:
            File bytes or None if file doesn't exist
        """
        if not self.exists():
            return None
        
        try:
            with open(self.source_path, "rb") as f:
                return f.read(max_size)
        except Exception:
            return None


@dataclass
class ExportProgress:
    """Progress information for export operation."""
    
    current: int
    total: int
    current_file: str
    bytes_copied: int
    total_bytes: int
    
    @property
    def percentage(self) -> float:
        """Get progress percentage (0-100)."""
        if self.total == 0:
            return 0
        return (self.current / self.total) * 100
    
    @property
    def bytes_percentage(self) -> float:
        """Get bytes progress percentage (0-100)."""
        if self.total_bytes == 0:
            return 0
        return (self.bytes_copied / self.total_bytes) * 100


class CameraRollExtractor:
    """
    Extractor for Camera Roll photos and videos.
    
    Handles:
    - Listing all Camera Roll media files
    - Filtering by type (photos/videos)
    - Exporting with original filenames
    - Progress reporting during export
    """
    
    def __init__(self, parser: BackupParser):
        """
        Initialize extractor with a backup parser.
        
        Args:
            parser: BackupParser instance (must be opened)
        """
        self.parser = parser
        self._media_files: Optional[List[MediaFile]] = None
    
    @property
    def backup_path(self) -> Path:
        """Get the backup path."""
        return self.parser.backup_path
    
    def get_all_media(self) -> List[MediaFile]:
        """
        Get all Camera Roll media files.
        
        Returns:
            List of MediaFile objects
        """
        if self._media_files is not None:
            return self._media_files
        
        backup_files = self.parser.get_camera_roll_files()
        
        self._media_files = [
            MediaFile(backup_file=bf, backup_path=self.backup_path)
            for bf in backup_files
            if bf.flags != 2  # flags=2 indicates directory
        ]
        
        # Sort by modified date (newest first)
        self._media_files.sort(
            key=lambda x: x.modified_date or datetime.min,
            reverse=True
        )
        
        return self._media_files
    
    def get_photos(self) -> List[MediaFile]:
        """Get only image files."""
        return [f for f in self.get_all_media() if f.is_image]
    
    def get_videos(self) -> List[MediaFile]:
        """Get only video files."""
        return [f for f in self.get_all_media() if f.is_video]
    
    def get_stats(self) -> dict:
        """
        Get statistics about Camera Roll.
        
        Returns:
            Dictionary with counts and sizes
        """
        all_media = self.get_all_media()
        photos = self.get_photos()
        videos = self.get_videos()
        
        total_size = sum(f.size for f in all_media)
        photo_size = sum(f.size for f in photos)
        video_size = sum(f.size for f in videos)
        
        return {
            "total_count": len(all_media),
            "photo_count": len(photos),
            "video_count": len(videos),
            "total_size": total_size,
            "total_size_formatted": format_file_size(total_size),
            "photo_size": photo_size,
            "photo_size_formatted": format_file_size(photo_size),
            "video_size": video_size,
            "video_size_formatted": format_file_size(video_size),
        }
    
    def export_all(
        self,
        destination: Path,
        progress_callback: Optional[Callable[[ExportProgress], None]] = None,
        filter_type: Optional[str] = None,  # "photos", "videos", or None for all
    ) -> Generator[ExportProgress, None, int]:
        """
        Export all Camera Roll files to destination.
        
        Args:
            destination: Destination folder path
            progress_callback: Optional callback for progress updates
            filter_type: Optional filter ("photos" or "videos")
            
        Yields:
            ExportProgress objects
            
        Returns:
            Number of successfully exported files
        """
        # Get files based on filter
        if filter_type == "photos":
            files = self.get_photos()
        elif filter_type == "videos":
            files = self.get_videos()
        else:
            files = self.get_all_media()
        
        if not files:
            return 0
        
        # Ensure destination exists
        ensure_dir(destination)
        
        total_files = len(files)
        total_bytes = sum(f.size for f in files)
        bytes_copied = 0
        successful = 0
        
        # Track filenames to handle duplicates
        used_names: dict = {}
        
        for i, media_file in enumerate(files):
            # Generate unique filename
            filename = media_file.filename
            if filename in used_names:
                used_names[filename] += 1
                name_part = Path(filename).stem
                ext = Path(filename).suffix
                filename = f"{name_part}_{used_names[filename]}{ext}"
            else:
                used_names[filename] = 0
            
            dest_path = destination / filename
            
            progress = ExportProgress(
                current=i + 1,
                total=total_files,
                current_file=filename,
                bytes_copied=bytes_copied,
                total_bytes=total_bytes,
            )
            
            yield progress
            
            if progress_callback:
                progress_callback(progress)
            
            # Copy file
            try:
                if media_file.exists():
                    shutil.copy2(media_file.source_path, dest_path)
                    bytes_copied += media_file.size
                    successful += 1
            except Exception as e:
                print(f"Error copying {filename}: {e}")
        
        return successful
    
    def export_files(
        self,
        files: List[MediaFile],
        destination: Path,
        progress_callback: Optional[Callable[[ExportProgress], None]] = None,
    ) -> int:
        """
        Export specific files to destination.
        
        Args:
            files: List of MediaFile objects to export
            destination: Destination folder path
            progress_callback: Optional callback for progress updates
            
        Returns:
            Number of successfully exported files
        """
        if not files:
            return 0
        
        ensure_dir(destination)
        
        total_files = len(files)
        total_bytes = sum(f.size for f in files)
        bytes_copied = 0
        successful = 0
        
        used_names: dict = {}
        
        for i, media_file in enumerate(files):
            filename = media_file.filename
            if filename in used_names:
                used_names[filename] += 1
                name_part = Path(filename).stem
                ext = Path(filename).suffix
                filename = f"{name_part}_{used_names[filename]}{ext}"
            else:
                used_names[filename] = 0
            
            dest_path = destination / filename
            
            if progress_callback:
                progress = ExportProgress(
                    current=i + 1,
                    total=total_files,
                    current_file=filename,
                    bytes_copied=bytes_copied,
                    total_bytes=total_bytes,
                )
                progress_callback(progress)
            
            try:
                if media_file.exists():
                    shutil.copy2(media_file.source_path, dest_path)
                    bytes_copied += media_file.size
                    successful += 1
            except Exception as e:
                print(f"Error copying {filename}: {e}")
        
        return successful
