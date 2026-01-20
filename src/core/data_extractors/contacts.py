"""
Contacts Extractor - Extract contacts from iOS backups.

This module handles extracting contacts from the AddressBook.sqlitedb
database in iOS backups.
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from ..backup_parser import BackupParser, BackupFile
from ...utils.helpers import format_file_size


@dataclass
class Contact:
    """Represents a contact from the Address Book."""
    
    first_name: str = ""
    last_name: str = ""
    organization: str = ""
    phone_numbers: List[str] = None
    emails: List[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.phone_numbers is None:
            self.phone_numbers = []
        if self.emails is None:
            self.emails = []
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else self.organization or "Unknown"
    
    @property
    def display_name(self) -> str:
        """Get display name (full name or organization)."""
        name = self.full_name
        if name == "Unknown" and self.organization:
            return self.organization
        return name
    
    @property
    def primary_phone(self) -> str:
        """Get primary phone number."""
        return self.phone_numbers[0] if self.phone_numbers else ""
    
    @property
    def primary_email(self) -> str:
        """Get primary email."""
        return self.emails[0] if self.emails else ""
    
    def to_vcard(self) -> str:
        """Export contact as vCard 3.0 format."""
        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"N:{self.last_name};{self.first_name};;;",
            f"FN:{self.full_name}",
        ]
        
        if self.organization:
            lines.append(f"ORG:{self.organization}")
        
        for phone in self.phone_numbers:
            lines.append(f"TEL;TYPE=CELL:{phone}")
        
        for email in self.emails:
            lines.append(f"EMAIL:{email}")
        
        if self.notes:
            # Escape newlines in notes
            escaped_notes = self.notes.replace("\n", "\\n")
            lines.append(f"NOTE:{escaped_notes}")
        
        lines.append("END:VCARD")
        
        return "\n".join(lines)


class ContactsExtractor:
    """
    Extractor for contacts from iOS backups.
    
    Reads the AddressBook.sqlitedb database to extract contacts.
    """
    
    def __init__(self, parser: BackupParser):
        """
        Initialize extractor with a backup parser.
        
        Args:
            parser: BackupParser instance (must be opened)
        """
        self.parser = parser
        self._contacts: Optional[List[Contact]] = None
        self._db_path: Optional[Path] = None
    
    @property
    def backup_path(self) -> Path:
        """Get the backup path."""
        return self.parser.backup_path
    
    def _find_addressbook_db(self) -> Optional[Path]:
        """Find the AddressBook database in the backup."""
        if self._db_path:
            return self._db_path
        
        # Search for AddressBook.sqlitedb
        files = self.parser.get_files_by_path_pattern(
            "HomeDomain",
            "Library/AddressBook/AddressBook.sqlitedb"
        )
        
        if files:
            self._db_path = files[0].get_backup_file_path(self.backup_path)
            return self._db_path
        
        return None
    
    def get_all_contacts(self) -> List[Contact]:
        """
        Get all contacts from the backup.
        
        Returns:
            List of Contact objects
        """
        if self._contacts is not None:
            return self._contacts
        
        db_path = self._find_addressbook_db()
        if not db_path or not db_path.exists():
            self._contacts = []
            return self._contacts
        
        contacts = []
        
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            
            # Get all persons
            cursor = conn.execute("""
                SELECT ROWID, First, Last, Organization, Note
                FROM ABPerson
            """)
            
            persons = {row["ROWID"]: Contact(
                first_name=row["First"] or "",
                last_name=row["Last"] or "",
                organization=row["Organization"] or "",
                notes=row["Note"] or "",
            ) for row in cursor}
            
            # Get phone numbers
            cursor = conn.execute("""
                SELECT record_id, value
                FROM ABMultiValue
                WHERE property = 3
            """)
            
            for row in cursor:
                if row["record_id"] in persons:
                    persons[row["record_id"]].phone_numbers.append(row["value"])
            
            # Get emails
            cursor = conn.execute("""
                SELECT record_id, value
                FROM ABMultiValue
                WHERE property = 4
            """)
            
            for row in cursor:
                if row["record_id"] in persons:
                    persons[row["record_id"]].emails.append(row["value"])
            
            conn.close()
            
            contacts = list(persons.values())
            
            # Sort by name
            contacts.sort(key=lambda c: c.display_name.lower())
            
        except sqlite3.Error as e:
            print(f"Error reading contacts database: {e}")
        
        self._contacts = contacts
        return self._contacts
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about contacts."""
        contacts = self.get_all_contacts()
        
        with_phones = sum(1 for c in contacts if c.phone_numbers)
        with_emails = sum(1 for c in contacts if c.emails)
        
        return {
            "total_count": len(contacts),
            "with_phones": with_phones,
            "with_emails": with_emails,
        }
    
    def export_all_vcards(self, destination: Path) -> int:
        """
        Export all contacts as individual vCard files.
        
        Args:
            destination: Destination folder
            
        Returns:
            Number of exported contacts
        """
        contacts = self.get_all_contacts()
        
        if not contacts:
            return 0
        
        destination.mkdir(parents=True, exist_ok=True)
        
        successful = 0
        for contact in contacts:
            filename = f"{contact.display_name}.vcf"
            # Sanitize filename
            filename = "".join(c for c in filename if c.isalnum() or c in " ._-")
            
            filepath = destination / filename
            
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(contact.to_vcard())
                successful += 1
            except Exception as e:
                print(f"Error exporting {filename}: {e}")
        
        return successful
    
    def export_all_single_vcf(self, destination: Path) -> bool:
        """
        Export all contacts as a single vCard file.
        
        Args:
            destination: Destination file path
            
        Returns:
            True if successful
        """
        contacts = self.get_all_contacts()
        
        if not contacts:
            return False
        
        try:
            vcards = [c.to_vcard() for c in contacts]
            content = "\n".join(vcards)
            
            with open(destination, "w", encoding="utf-8") as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"Error exporting contacts: {e}")
            return False
