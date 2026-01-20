"""
Call History Extractor - Extract call logs from iOS backups.

This module handles extracting call history from the CallHistory.storedata
or call_history.db database in iOS backups.
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

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


@dataclass
class CallRecord:
    """Represents a phone call record."""
    
    id: int
    address: str  # Phone number
    date: Optional[datetime]
    duration: int  # Duration in seconds
    call_type: int  # 1=incoming, 2=outgoing, 3=missed, etc.
    answered: bool
    
    @property
    def phone_number(self) -> str:
        """Get formatted phone number."""
        return self.address or "Unknown"
    
    @property
    def date_formatted(self) -> str:
        """Get formatted date string."""
        if self.date:
            return self.date.strftime("%Y-%m-%d %H:%M")
        return ""
    
    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string."""
        if self.duration == 0:
            return "0:00"
        
        minutes = self.duration // 60
        seconds = self.duration % 60
        
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        
        return f"{minutes}:{seconds:02d}"
    
    @property
    def call_type_name(self) -> str:
        """Get call type as string."""
        types = {
            1: "Incoming",
            2: "Outgoing", 
            3: "Missed",
            4: "Cancelled",
            5: "Blocked",
        }
        return types.get(self.call_type, "Unknown")
    
    @property
    def call_type_icon(self) -> str:
        """Get icon for call type."""
        icons = {
            1: "📥",  # Incoming
            2: "📤",  # Outgoing
            3: "📵",  # Missed
            4: "❌",  # Cancelled
            5: "🚫",  # Blocked
        }
        return icons.get(self.call_type, "📞")


class CallHistoryExtractor:
    """
    Extractor for call history from iOS backups.
    
    Reads the CallHistory database to extract call records.
    """
    
    def __init__(self, parser: BackupParser):
        """
        Initialize extractor with a backup parser.
        
        Args:
            parser: BackupParser instance (must be opened)
        """
        self.parser = parser
        self._calls: Optional[List[CallRecord]] = None
        self._db_path: Optional[Path] = None
    
    @property
    def backup_path(self) -> Path:
        """Get the backup path."""
        return self.parser.backup_path
    
    def _find_callhistory_db(self) -> Optional[Path]:
        """Find the Call History database in the backup."""
        if self._db_path:
            return self._db_path
        
        # Search for CallHistory.storedata (modern) or call_history.db (legacy)
        search_patterns = [
            ("HomeDomain", "Library/CallHistoryDB/CallHistory.storedata"),
            ("WirelessDomain", "Library/CallHistory/call_history.db"),
        ]
        
        for domain, path in search_patterns:
            files = self.parser.get_files_by_path_pattern(domain, f"%{path.split('/')[-1]}")
            if files:
                self._db_path = files[0].get_backup_file_path(self.backup_path)
                if self._db_path.exists():
                    return self._db_path
        
        return None
    
    def get_all_calls(self) -> List[CallRecord]:
        """
        Get all call records from the backup.
        
        Returns:
            List of CallRecord objects
        """
        if self._calls is not None:
            return self._calls
        
        db_path = self._find_callhistory_db()
        if not db_path or not db_path.exists():
            self._calls = []
            return self._calls
        
        calls = []
        
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            
            # Try modern CallHistory.storedata schema first
            try:
                cursor = conn.execute("""
                    SELECT 
                        Z_PK as id,
                        ZADDRESS as address,
                        ZDATE as date,
                        ZDURATION as duration,
                        ZCALLTYPE as call_type,
                        ZANSWERED as answered
                    FROM ZCALLRECORD
                    ORDER BY ZDATE DESC
                """)
                
                for row in cursor:
                    call = CallRecord(
                        id=row["id"],
                        address=row["address"] or "",
                        date=apple_timestamp_to_datetime(row["date"]),
                        duration=int(row["duration"] or 0),
                        call_type=row["call_type"] or 0,
                        answered=bool(row["answered"]),
                    )
                    calls.append(call)
                    
            except sqlite3.OperationalError:
                # Fall back to legacy schema
                cursor = conn.execute("""
                    SELECT 
                        ROWID as id,
                        address,
                        date,
                        duration,
                        flags as call_type,
                        read as answered
                    FROM call
                    ORDER BY date DESC
                """)
                
                for row in cursor:
                    # Legacy dates are Unix timestamps
                    call_date = None
                    if row["date"]:
                        try:
                            call_date = datetime.fromtimestamp(row["date"])
                        except (ValueError, OSError):
                            pass
                    
                    call = CallRecord(
                        id=row["id"],
                        address=row["address"] or "",
                        date=call_date,
                        duration=int(row["duration"] or 0),
                        call_type=row["call_type"] or 0,
                        answered=bool(row["answered"]),
                    )
                    calls.append(call)
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Error reading call history database: {e}")
        
        self._calls = calls
        return self._calls
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about call history."""
        calls = self.get_all_calls()
        
        incoming = sum(1 for c in calls if c.call_type == 1)
        outgoing = sum(1 for c in calls if c.call_type == 2)
        missed = sum(1 for c in calls if c.call_type == 3)
        total_duration = sum(c.duration for c in calls)
        
        return {
            "total_calls": len(calls),
            "incoming": incoming,
            "outgoing": outgoing,
            "missed": missed,
            "total_duration": total_duration,
            "total_duration_formatted": self._format_duration(total_duration),
        }
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds} seconds"
        
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minutes"
        
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours} hours, {minutes} minutes"
    
    def export_all_calls(self, destination: Path) -> bool:
        """
        Export all call history as a CSV file.
        
        Args:
            destination: Destination file path
            
        Returns:
            True if successful
        """
        calls = self.get_all_calls()
        
        if not calls:
            return False
        
        try:
            import csv
            
            with open(destination, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    "Date",
                    "Phone Number",
                    "Type",
                    "Duration",
                    "Answered"
                ])
                
                # Data
                for call in calls:
                    writer.writerow([
                        call.date_formatted,
                        call.phone_number,
                        call.call_type_name,
                        call.duration_formatted,
                        "Yes" if call.answered else "No"
                    ])
            
            return True
        except Exception as e:
            print(f"Error exporting call history: {e}")
            return False
