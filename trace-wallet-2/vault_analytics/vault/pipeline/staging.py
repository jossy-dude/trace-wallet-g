import json
import os
import hashlib
import threading
import logging
from datetime import datetime
from vault.config import STAGING_FILE


class StagingVault:
    """
    Resilient staging area for incoming SMS data.
    Uses SHA-256 hashing to prevent duplicate entries even if
    sync is interrupted and resumed.
    """

    def __init__(self, filepath=STAGING_FILE):
        self.filepath = filepath
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        """Load staging data from disk"""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = data.get("entries", [])
                    self.processed_hashes = set(data.get("processed_hashes", []))
            else:
                self.entries = []
                self.processed_hashes = set()
        except (json.JSONDecodeError, Exception):
            self.entries = []
            self.processed_hashes = set()

    def _save(self):
        """Persist staging data to disk"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "entries": self.entries,
                    "processed_hashes": list(self.processed_hashes),
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logging.error(f"Staging save error: {e}")

    def _hash_sms(self, sms_body: str, sender: str = "") -> str:
        """Generate unique hash for SMS to prevent duplicates"""
        content = f"{sender}|{sms_body}".strip().lower()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def add(self, sms_body: str, sender: str = "", metadata: dict = None) -> dict:
        """Add SMS to staging if not already processed"""
        with self.lock:
            h = self._hash_sms(sms_body, sender)
            if h in self.processed_hashes:
                return {"status": "duplicate", "hash": h}

            entry = {
                "id": len(self.entries) + 1,
                "hash": h,
                "body": sms_body,
                "sender": sender,
                "received_at": datetime.now().isoformat(),
                "status": "pending",  # pending | parsed | approved | rejected
                "parsed_data": None,
                "metadata": metadata or {}
            }
            self.entries.append(entry)
            self._save()
            return {"status": "staged", "id": entry["id"], "hash": h}

    def get_pending(self) -> list:
        """Get all entries awaiting processing"""
        with self.lock:
            return [e for e in self.entries if e["status"] == "pending"]

    def get_parsed(self) -> list:
        """Get all parsed entries awaiting user approval"""
        with self.lock:
            return [e for e in self.entries if e["status"] == "parsed"]

    def mark_parsed(self, entry_id: int, parsed_data: dict):
        """Mark entry as parsed with extracted data"""
        with self.lock:
            for e in self.entries:
                if e["id"] == entry_id:
                    e["status"] = "parsed"
                    e["parsed_data"] = parsed_data
                    e["parsed_at"] = datetime.now().isoformat()
                    break
            self._save()

    def approve(self, entry_id: int, user_overrides: dict = None) -> dict:
        """User approves a parsed entry for commitment to master ledger"""
        with self.lock:
            for e in self.entries:
                if e["id"] == entry_id:
                    e["status"] = "approved"
                    e["approved_at"] = datetime.now().isoformat()
                    if user_overrides:
                        if e["parsed_data"]:
                            e["parsed_data"].update(user_overrides)
                    self.processed_hashes.add(e["hash"])
                    self._save()
                    return {"status": "approved", "data": e.get("parsed_data", {})}
            return {"status": "error", "message": "Entry not found"}

    def reject(self, entry_id: int) -> dict:
        """User rejects a parsed entry"""
        with self.lock:
            for e in self.entries:
                if e["id"] == entry_id:
                    e["status"] = "rejected"
                    e["rejected_at"] = datetime.now().isoformat()
                    self.processed_hashes.add(e["hash"])
                    self._save()
                    return {"status": "rejected"}
            return {"status": "error", "message": "Entry not found"}

    def get_stats(self) -> dict:
        """Get staging vault statistics"""
        with self.lock:
            return {
                "total": len(self.entries),
                "pending": sum(1 for e in self.entries if e["status"] == "pending"),
                "parsed": sum(1 for e in self.entries if e["status"] == "parsed"),
                "approved": sum(1 for e in self.entries if e["status"] == "approved"),
                "rejected": sum(1 for e in self.entries if e["status"] == "rejected"),
                "dedup_count": len(self.processed_hashes)
            }
