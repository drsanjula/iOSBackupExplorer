"""
Notes Extractor - Extract notes from iOS backups.

This module handles extracting notes from the NoteStore.sqlite
database in iOS backups.
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import html
import re

from ..backup_parser import BackupParser, BackupFile


# iOS uses a different epoch (2001-01-01) for dates
APPLE_EPOCH = datetime(2001, 1, 1)


def apple_timestamp_to_datetime(timestamp: float) -> Optional[datetime]:
    """Convert Apple timestamp to datetime."""
    if not timestamp:
        return None
    try:
        # Core Data timestamps are seconds since 2001-01-01
        delta = datetime.fromtimestamp(0) - APPLE_EPOCH
        return datetime.fromtimestamp(timestamp) - delta
    except (ValueError, OSError):
        return None


def strip_html(text: str) -> str:
    """Strip HTML tags from text."""
    if not text:
        return ""
    # Decode HTML entities
    text = html.unescape(text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


@dataclass
class Note:
    """Represents a note from the Notes app."""
    
    id: int
    title: str
    content: str  # Plain text content
    html_content: str = ""  # Original HTML content
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    folder: str = "Notes"
    
    @property
    def preview(self) -> str:
        """Get preview of note content."""
        text = self.content[:200]
        if len(self.content) > 200:
            text += "..."
        return text
    
    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())
    
    @property
    def created_formatted(self) -> str:
        """Get formatted creation date."""
        if self.created_date:
            return self.created_date.strftime("%Y-%m-%d %H:%M")
        return ""
    
    @property
    def modified_formatted(self) -> str:
        """Get formatted modification date."""
        if self.modified_date:
            return self.modified_date.strftime("%Y-%m-%d %H:%M")
        return ""


class NotesExtractor:
    """
    Extractor for notes from iOS backups.
    
    Reads the NoteStore.sqlite database to extract notes.
    """
    
    def __init__(self, parser: BackupParser):
        """
        Initialize extractor with a backup parser.
        
        Args:
            parser: BackupParser instance (must be opened)
        """
        self.parser = parser
        self._notes: Optional[List[Note]] = None
        self._db_path: Optional[Path] = None
    
    @property
    def backup_path(self) -> Path:
        """Get the backup path."""
        return self.parser.backup_path
    
    def _find_notes_db(self) -> Optional[Path]:
        """Find the Notes database in the backup."""
        if self._db_path:
            return self._db_path
        
        # Search for NoteStore.sqlite - try different locations
        search_patterns = [
            ("AppDomainGroup-group.com.apple.notes", "NoteStore.sqlite"),
            ("HomeDomain", "Library/Notes/notes.sqlite"),
        ]
        
        for domain, path in search_patterns:
            files = self.parser.get_files_by_path_pattern(domain, f"%{path}")
            if files:
                self._db_path = files[0].get_backup_file_path(self.backup_path)
                if self._db_path.exists():
                    return self._db_path
        
        return None
    
    def get_all_notes(self) -> List[Note]:
        """
        Get all notes from the backup.
        
        Returns:
            List of Note objects
        """
        if self._notes is not None:
            return self._notes
        
        db_path = self._find_notes_db()
        if not db_path or not db_path.exists():
            self._notes = []
            return self._notes
        
        notes = []
        
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            
            # Try modern Notes schema first
            try:
                cursor = conn.execute("""
                    SELECT 
                        n.Z_PK as id,
                        n.ZTITLE1 as title,
                        nd.ZDATA as data,
                        n.ZCREATIONDATE1 as created,
                        n.ZMODIFICATIONDATE1 as modified
                    FROM ZICCLOUDSYNCINGOBJECT n
                    LEFT JOIN ZICNOTEDATA nd ON n.ZNOTEDATA = nd.Z_PK
                    WHERE n.ZTITLE1 IS NOT NULL
                """)
                
                for row in cursor:
                    content = ""
                    if row["data"]:
                        try:
                            # Try to decode as zlib compressed
                            import zlib
                            data = zlib.decompress(row["data"], -15)
                            content = strip_html(data.decode("utf-8", errors="ignore"))
                        except:
                            content = strip_html(str(row["data"]))
                    
                    note = Note(
                        id=row["id"],
                        title=row["title"] or "Untitled",
                        content=content,
                        created_date=apple_timestamp_to_datetime(row["created"]),
                        modified_date=apple_timestamp_to_datetime(row["modified"]),
                    )
                    notes.append(note)
                    
            except sqlite3.OperationalError:
                # Fall back to legacy schema
                cursor = conn.execute("""
                    SELECT 
                        ROWID as id,
                        title,
                        body,
                        creation_date as created,
                        modification_date as modified
                    FROM note
                """)
                
                for row in cursor:
                    note = Note(
                        id=row["id"],
                        title=row["title"] or "Untitled",
                        content=strip_html(row["body"] or ""),
                        html_content=row["body"] or "",
                        created_date=apple_timestamp_to_datetime(row["created"]),
                        modified_date=apple_timestamp_to_datetime(row["modified"]),
                    )
                    notes.append(note)
            
            conn.close()
            
            # Sort by modification date (newest first)
            notes.sort(
                key=lambda n: n.modified_date or datetime.min,
                reverse=True
            )
            
        except sqlite3.Error as e:
            print(f"Error reading notes database: {e}")
        
        self._notes = notes
        return self._notes
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about notes."""
        notes = self.get_all_notes()
        
        total_words = sum(n.word_count for n in notes)
        
        return {
            "note_count": len(notes),
            "total_words": total_words,
        }
    
    def export_note_txt(self, note: Note, destination: Path) -> bool:
        """
        Export a note as a text file.
        
        Args:
            note: Note to export
            destination: Destination file path
            
        Returns:
            True if successful
        """
        try:
            lines = [
                note.title,
                "=" * len(note.title),
                "",
                f"Created: {note.created_formatted}",
                f"Modified: {note.modified_formatted}",
                "",
                "-" * 50,
                "",
                note.content,
            ]
            
            with open(destination, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            return True
        except Exception as e:
            print(f"Error exporting note: {e}")
            return False
    
    def export_all_notes(self, destination: Path) -> int:
        """
        Export all notes as text files.
        
        Args:
            destination: Destination folder
            
        Returns:
            Number of exported notes
        """
        notes = self.get_all_notes()
        
        if not notes:
            return 0
        
        destination.mkdir(parents=True, exist_ok=True)
        
        successful = 0
        for note in notes:
            filename = f"{note.title}.txt"
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in " ._-")
            filename = filename[:100]  # Limit length
            
            filepath = destination / filename
            
            if self.export_note_txt(note, filepath):
                successful += 1
        
        return successful
