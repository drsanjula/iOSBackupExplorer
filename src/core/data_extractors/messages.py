"""
Messages Extractor - Extract iMessage/SMS from iOS backups.

This module handles extracting messages from the sms.db
database in iOS backups.
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..backup_parser import BackupParser, BackupFile
from ...utils.helpers import format_file_size


# iOS uses a different epoch (2001-01-01) for dates
APPLE_EPOCH = datetime(2001, 1, 1)


def apple_timestamp_to_datetime(timestamp: int) -> Optional[datetime]:
    """Convert Apple timestamp to datetime."""
    if not timestamp:
        return None
    try:
        # Timestamps can be in nanoseconds or seconds
        if timestamp > 1e12:
            timestamp = timestamp / 1e9
        delta = datetime.fromtimestamp(0) - APPLE_EPOCH
        return datetime.fromtimestamp(timestamp) - delta
    except (ValueError, OSError):
        return None


@dataclass
class Message:
    """Represents an iMessage/SMS message."""
    
    text: str
    date: Optional[datetime]
    is_from_me: bool
    chat_id: int
    handle_id: int
    service: str = ""  # "iMessage" or "SMS"
    
    @property
    def date_formatted(self) -> str:
        """Get formatted date string."""
        if self.date:
            return self.date.strftime("%Y-%m-%d %H:%M:%S")
        return ""


@dataclass 
class Chat:
    """Represents a conversation/chat."""
    
    chat_id: int
    display_name: str
    participants: List[str] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    last_message_date: Optional[datetime] = None
    
    @property
    def message_count(self) -> int:
        """Get number of messages."""
        return len(self.messages)
    
    @property
    def preview(self) -> str:
        """Get preview of last message."""
        if self.messages:
            return self.messages[-1].text[:100]
        return ""


class MessagesExtractor:
    """
    Extractor for iMessage/SMS from iOS backups.
    
    Reads the sms.db database to extract messages.
    """
    
    def __init__(self, parser: BackupParser):
        """
        Initialize extractor with a backup parser.
        
        Args:
            parser: BackupParser instance (must be opened)
        """
        self.parser = parser
        self._chats: Optional[List[Chat]] = None
        self._db_path: Optional[Path] = None
    
    @property
    def backup_path(self) -> Path:
        """Get the backup path."""
        return self.parser.backup_path
    
    def _find_sms_db(self) -> Optional[Path]:
        """Find the SMS database in the backup."""
        if self._db_path:
            return self._db_path
        
        # Search for sms.db
        files = self.parser.get_files_by_path_pattern(
            "HomeDomain",
            "Library/SMS/sms.db"
        )
        
        if files:
            self._db_path = files[0].get_backup_file_path(self.backup_path)
            return self._db_path
        
        return None
    
    def get_all_chats(self) -> List[Chat]:
        """
        Get all chats/conversations from the backup.
        
        Returns:
            List of Chat objects with messages
        """
        if self._chats is not None:
            return self._chats
        
        db_path = self._find_sms_db()
        if not db_path or not db_path.exists():
            self._chats = []
            return self._chats
        
        chats = {}
        handles = {}
        
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            
            # Get handles (phone numbers/emails)
            cursor = conn.execute("SELECT ROWID, id FROM handle")
            for row in cursor:
                handles[row["ROWID"]] = row["id"]
            
            # Get chats
            cursor = conn.execute("""
                SELECT ROWID, chat_identifier, display_name
                FROM chat
            """)
            
            for row in cursor:
                chat_id = row["ROWID"]
                display_name = row["display_name"] or row["chat_identifier"] or "Unknown"
                chats[chat_id] = Chat(
                    chat_id=chat_id,
                    display_name=display_name,
                )
            
            # Get messages with their chat associations
            cursor = conn.execute("""
                SELECT 
                    m.ROWID,
                    m.text,
                    m.date,
                    m.is_from_me,
                    m.handle_id,
                    m.service,
                    cmj.chat_id
                FROM message m
                LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                ORDER BY m.date
            """)
            
            for row in cursor:
                chat_id = row["chat_id"]
                if chat_id not in chats:
                    continue
                
                msg_date = apple_timestamp_to_datetime(row["date"])
                
                message = Message(
                    text=row["text"] or "",
                    date=msg_date,
                    is_from_me=bool(row["is_from_me"]),
                    chat_id=chat_id,
                    handle_id=row["handle_id"] or 0,
                    service=row["service"] or "",
                )
                
                chats[chat_id].messages.append(message)
                
                if msg_date:
                    if not chats[chat_id].last_message_date or msg_date > chats[chat_id].last_message_date:
                        chats[chat_id].last_message_date = msg_date
            
            # Add participant handles to chats
            cursor = conn.execute("""
                SELECT chat_id, handle_id
                FROM chat_handle_join
            """)
            
            for row in cursor:
                chat_id = row["chat_id"]
                handle_id = row["handle_id"]
                if chat_id in chats and handle_id in handles:
                    chats[chat_id].participants.append(handles[handle_id])
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Error reading messages database: {e}")
        
        # Sort chats by last message date (newest first)
        chat_list = list(chats.values())
        chat_list.sort(
            key=lambda c: c.last_message_date or datetime.min,
            reverse=True
        )
        
        self._chats = chat_list
        return self._chats
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about messages."""
        chats = self.get_all_chats()
        
        total_messages = sum(c.message_count for c in chats)
        imessages = sum(
            1 for c in chats 
            for m in c.messages 
            if m.service == "iMessage"
        )
        
        return {
            "chat_count": len(chats),
            "message_count": total_messages,
            "imessage_count": imessages,
            "sms_count": total_messages - imessages,
        }
    
    def export_chat_txt(self, chat: Chat, destination: Path) -> bool:
        """
        Export a chat as a text file.
        
        Args:
            chat: Chat to export
            destination: Destination file path
            
        Returns:
            True if successful
        """
        try:
            lines = [f"Chat with: {chat.display_name}", "=" * 50, ""]
            
            for msg in chat.messages:
                sender = "Me" if msg.is_from_me else chat.display_name
                date_str = msg.date_formatted
                lines.append(f"[{date_str}] {sender}:")
                lines.append(f"  {msg.text}")
                lines.append("")
            
            with open(destination, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            return True
        except Exception as e:
            print(f"Error exporting chat: {e}")
            return False
    
    def export_all_chats(self, destination: Path) -> int:
        """
        Export all chats as text files.
        
        Args:
            destination: Destination folder
            
        Returns:
            Number of exported chats
        """
        chats = self.get_all_chats()
        
        if not chats:
            return 0
        
        destination.mkdir(parents=True, exist_ok=True)
        
        successful = 0
        for chat in chats:
            if not chat.messages:
                continue
            
            filename = f"{chat.display_name}.txt"
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in " ._-@+")
            
            filepath = destination / filename
            
            if self.export_chat_txt(chat, filepath):
                successful += 1
        
        return successful
