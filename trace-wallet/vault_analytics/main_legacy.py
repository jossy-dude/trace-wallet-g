"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  VAULT ANALYTICS v4.0 — PRODUCTION EDITION                   ║
║                  Autonomous Financial Command Center                         ║
║                  Built with PyWebView + FastAPI + ApexCharts                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  SYSTEM ARCHITECT LOG                                                        ║
║  ────────────────────                                                        ║
║                                                                              ║
║  HOLES FILLED:                                                               ║
║  1. SMS Receiver: FastAPI listener on configurable port (default 8765)       ║
║     accepts P2P sync data from the mobile Flutter app.                       ║
║  2. Staging Vault: staging_vault.json with SHA-256 idempotency.              ║
║  3. Smart Batch: Debounce engine waits for burst SMS before parsing.         ║
║  4. Verification Inbox: New page where user approves SMS data.               ║
║  5. Relay Engine: Copy-paste forwarding with rule-based triggers.            ║
║  6. Interactive Charts: ApexCharts replaces static SVGs.                     ║
║  7. Micro-Interactions: Card tilt, glow hover, page slide transitions.       ║
║  8. Budget Hard Stops: Per-category limits with visual warnings.             ║
║  9. Icon Picker: Searchable Material Symbols (500+ icons).                   ║
║  10. Account Management: Full CRUD for financial accounts.                   ║
║  11. CSV Export: Column-selectable CSV download.                             ║
║  12. Critical Alerts: Dashboard banner for anomalies.                        ║
║  13. Sub-Widgets: Session timer, top category, system health.                ║
║  14. Accent Color + Glass Opacity: User-customizable theming.                ║
║  15. Ollama Future-Proofing: Abstract AI interface ready for integration.    ║
║                                                                              ║
║  UX LOGIC:                                                                   ║
║  - Desktop-first bento grid fills horizontal space with sub-widgets          ║
║  - Every chart has a gear icon → settings modal (type, timescale, data)      ║
║  - Page transitions: slide-in from right with fade for native feel           ║
║  - Cards tilt on hover with perspective transform + glow shadow              ║
║  - Status light: green=synced, amber=syncing, red=error, blue=SMS active    ║
║  - Numbers animate from 0 to value on page render                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import webview
import json
import os
import hashlib
import csv
import io
import xml.etree.ElementTree as ET
import re
import threading
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, List, Any
import math

# ═══════════════════════════════════════════════════════════════════
# § CONFIGURATION & CONSTANTS
# ═══════════════════════════════════════════════════════════════════

DATA_FILE = "vault_data.json"
CONFIG_FILE = "vault_config.json"
STAGING_FILE = "staging_vault.json"

DEFAULT_SETTINGS = {
    "onboarding_completed": False,
    "sms_port": 8765,
    "sms_debounce_seconds": 60,
    "sms_instant_mode": False,
    "sms_listener_enabled": True,
    "bank_start_dates": {
        "CBE": "2024-12-10",
        "Telebirr": "2024-04-11",
        "BOA": "2025-10-13",
        "Dashen": "2024-11-30"
    },
    "bank_regex_overrides": {},
    "accent_hue": 215,
    "accent_saturation": 100,
    "glass_opacity": 45,
    "nav_mode": "sidebar",
    "reduce_motion": False,
    "number_format": "1,234.56",
    "currency": "USD ($)",
    "currency_symbol": "$",
    "language": "en",
    "hard_stop_enabled": True,
    "lock_timeout_minutes": 15,
    "budget_limits": {},
    "relay_rules": [],
    "bank_patterns": {},
    "chart_preferences": {
        "trajectory": {
            "type": "area",
            "scale": "monthly",
            "metrics": {"income": True, "expense": True, "net": True, "fees": False}
        },
        "donut": {
            "type": "donut",
            "scale": "monthly"
        }
    },
    "accounts": [],
    "category_icons": {}
}

DEFAULT_DATA = {
    "password_hash": None,
    "has_setup_password": False,
    "net_worth": 0,
    "monthly_income": 0,
    "monthly_burn": 0,
    "theme": "light",
    "privacy_mask": False,
    "biometrics": True,
    "transactions": [],
    "audit_log": [],
    "goals": [],
    "subscriptions": [],
    "velocity_score": 0,
    "runway_days": 0,
    "health_score": 0,
    "savings_rate": 0,
    "ratio": 0,
    "predictions": [],
    "monthly_totals": {},
    "category_breakdown": {},
    "ghost_fees": [],
    "spending_velocity": {"daily_avg": 0, "weekly_trend": 0, "momentum": "stable"},
    "pending_sms": [],
    "relay_log": [],
    "alerts": []
}

def _merge_defaults(target: dict, defaults: dict) -> dict:
    """
    Recursively merge defaults into target without overwriting user values.
    """
    for key, value in defaults.items():
        if key not in target:
            target[key] = value
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            target[key] = _merge_defaults(target[key], value)
    return target

# ═══════════════════════════════════════════════════════════════════
# § BANK RULES ENGINE (from Praser v4 — Ethiopian Bank Feeds)
# ═══════════════════════════════════════════════════════════════════

BANK_RULES = {
    "CBE": {
        "display": "CBE",
        "full_name": "Commercial Bank of Ethiopia",
        "patterns": {
            "amount": [
                r'debited with etb\s*([\d,.]+)',
                r'transfer(?:r)?ed etb\s*([\d,.]+)',
                r'credited with etb\s*([\d,.]+)',
                r'etb\s*([\d,.]+)\s*(?:has been|was)',
            ],
            "balance": [r'current balance is etb\s*([\d,.]+)', r'balance[:\s]+etb\s*([\d,.]+)'],
            "fee": [r's\.charge of etb\s*([\d,.]+)', r'service charge of etb\s*([\d,.]+)'],
            "vat": [r'vat.*?of etb\s*([\d,.]+)'],
            "merchant": [r'(?:to|from)\s+([a-zA-Z\s.\-]+?)(?:\s+on|,|\s+at)'],
            "date": [r'on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', r'(\d{1,2}\s+\w+\s+\d{4})']
        }
    },
    "Telebirr": {
        "display": "Telebirr",
        "full_name": "Ethio Telecom Mobile Money",
        "patterns": {
            "amount": [
                r'paid etb\s*([\d,.]+)', r'withdrawn? etb\s*([\d,.]+)',
                r'transferred etb\s*([\d,.]+)', r'recharged etb\s*([\d,.]+)',
                r'received etb\s*([\d,.]+)', r'etb\s*([\d,.]+)\s*(?:is|was|has)'
            ],
            "balance": [r'balance is\s*(?:etb)?\s*([\d,.]+)', r'balance[:\s]+([\d,.]+)'],
            "fee": [
                r'service fee.*?is etb\s*([\d,.]+)',
                r'charge\s*([\d,.]+)br',
                r'transaction fee is etb\s*([\d,.]+)'
            ],
            "vat": [r'vat.*?is etb\s*([\d,.]+)', r'tax\s*([\d,.]+)br'],
            "merchant": [
                r'for package\s+(.*?)\s+purchase',
                r'purchased from\s+\d+\s*-\s*([a-zA-Z\s.\-]+)',
                r'from\s+(.*?)\s+(?:on|to)', r'to\s+(.*?)\s+account'
            ],
            "date": [r'on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})']
        }
    },
    "BOA": {
        "display": "BOA",
        "full_name": "Bank of Abyssinia",
        "patterns": {
            "amount": [r'etb\s*([\d,.]+)', r'birr\s*([\d,.]+)'],
            "balance": [r'balance.*?etb\s*([\d,.]+)'],
            "fee": [r'fee.*?etb\s*([\d,.]+)'],
            "vat": [r'vat.*?etb\s*([\d,.]+)'],
            "merchant": [r'(?:to|from)\s+([a-zA-Z\s.\-]+?)(?:\s+on|,)'],
            "date": [r'on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})']
        }
    },
    "Dashen": {
        "display": "Dashen",
        "full_name": "Dashen Bank",
        "patterns": {
            "amount": [r'etb\s*([\d,.]+)', r'birr\s*([\d,.]+)'],
            "balance": [r'balance.*?etb\s*([\d,.]+)'],
            "fee": [r'fee.*?etb\s*([\d,.]+)', r'charge.*?etb\s*([\d,.]+)'],
            "vat": [r'vat.*?etb\s*([\d,.]+)'],
            "merchant": [r'(?:to|from)\s+([a-zA-Z\s.\-]+?)(?:\s+on|,)'],
            "date": [r'on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})']
        }
    }
}

# ═══════════════════════════════════════════════════════════════════
# § STAGING VAULT — Idempotent SMS Buffer with SHA-256 Dedup
# ═══════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════
# § SMART BATCH ENGINE — Debounced SMS Processing
# ═══════════════════════════════════════════════════════════════════

class SmartBatchEngine:
    """
    Debounce strategy for SMS processing.  When a new SMS arrives,
    wait for configurable delay to see if more arrive before
    running parser logic.  Reduces CPU usage during burst sync.
    """

    def __init__(self, process_callback, delay_seconds=60):
        self.process_callback = process_callback
        self.delay_seconds = delay_seconds
        self.timer = None
        self.batch = []
        self.lock = threading.Lock()
        self.instant_mode = False

    def add(self, item):
        """Add item to batch. If instant mode, process immediately."""
        with self.lock:
            self.batch.append(item)
            if self.instant_mode:
                self._flush()
            else:
                self._reset_timer()

    def _reset_timer(self):
        """Reset the debounce timer"""
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.delay_seconds, self._flush)
        self.timer.daemon = True
        self.timer.start()

    def _flush(self):
        """Process all batched items"""
        with self.lock:
            if self.batch:
                items = self.batch.copy()
                self.batch.clear()
        if items:
            try:
                self.process_callback(items)
            except Exception as e:
                logging.error(f"Batch processing error: {e}")

    def set_delay(self, seconds):
        """Update debounce delay"""
        self.delay_seconds = max(5, min(300, seconds))

    def set_instant(self, enabled):
        """Toggle instant processing mode"""
        self.instant_mode = enabled

# ═══════════════════════════════════════════════════════════════════
# § NOTIFICATION RELAY ENGINE — Rule-Based Message Forwarding
# ═══════════════════════════════════════════════════════════════════

class NotificationProvider:
    """Abstract base for notification delivery. Future-proofed for Telegram/Email."""
    def send(self, recipient: str, message: str, metadata: dict = None) -> dict:
        raise NotImplementedError

class InternalRelayProvider(NotificationProvider):
    """
    Built-in relay: stores forwarded messages in relay_log.
    The mobile app can pull these for delivery via its own SMS capability.
    """
    def __init__(self, relay_log: list):
        self.relay_log = relay_log

    def send(self, recipient: str, message: str, metadata: dict = None) -> dict:
        entry = {
            "id": len(self.relay_log) + 1,
            "recipient": recipient,
            "message": message,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "delivered_at": None,
            "metadata": metadata or {}
        }
        self.relay_log.append(entry)
        return {"status": "queued", "relay_id": entry["id"]}

class TelegramProvider(NotificationProvider):
    """Future: Telegram Bot API integration"""
    def __init__(self, bot_token: str = ""):
        self.bot_token = bot_token

    def send(self, recipient: str, message: str, metadata: dict = None) -> dict:
        # Placeholder for future Telegram integration
        return {"status": "not_configured", "message": "Telegram provider not configured"}

class EmailProvider(NotificationProvider):
    """Future: SMTP/SendGrid style integration"""
    def __init__(self, smtp_host: str = "", smtp_user: str = ""):
        self.smtp_host = smtp_host
        self.smtp_user = smtp_user

    def send(self, recipient: str, message: str, metadata: dict = None) -> dict:
        # Placeholder for future Email integration
        return {"status": "not_configured", "message": "Email provider not configured"}

class NotificationRouter(NotificationProvider):
    """
    Routes relay messages to a concrete provider by channel.
    Supported channels: sms (default), telegram, email.
    """
    def __init__(self, providers: dict):
        self.providers = providers or {}

    def send(self, recipient: str, message: str, metadata: dict = None) -> dict:
        md = metadata or {}
        channel = str(md.get("channel", "sms")).lower()
        provider = self.providers.get(channel) or self.providers.get("sms")
        if not provider:
            return {"status": "error", "message": f"No provider configured for channel '{channel}'"}
        result = provider.send(recipient, message, metadata=md)
        if isinstance(result, dict):
            result.setdefault("channel", channel)
        return result

class RelayRuleEngine:
    """
    Evaluates incoming transactions against user-defined relay rules.
    When conditions match, triggers the notification provider.
    """

    def __init__(self, provider: NotificationProvider):
        self.provider = provider
        self.rules = []

    def load_rules(self, rules: list):
        """Load relay rules from settings"""
        self.rules = rules

    def evaluate(self, transaction: dict) -> list:
        """
        Evaluate a transaction against all rules.
        Returns list of triggered relay actions.
        """
        triggered = []
        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            if self._matches(rule, transaction):
                msg = self._format_message(rule, transaction)
                result = self.provider.send(
                    recipient=rule.get("recipient", ""),
                    message=msg,
                    metadata={
                        "rule_id": rule.get("id"),
                        "channel": rule.get("channel", "sms"),
                        "transaction": transaction
                    }
                )
                triggered.append({
                    "rule": rule.get("name", "Unnamed"),
                    "recipient": rule.get("recipient", ""),
                    "channel": rule.get("channel", "sms"),
                    "result": result
                })
        return triggered

    def _matches(self, rule: dict, tx: dict) -> bool:
        """Check if transaction matches rule conditions"""
        conditions = rule.get("conditions", {})

        # Bank filter
        if "bank" in conditions:
            if tx.get("bank", "").lower() != conditions["bank"].lower():
                return False

        # Amount threshold
        if "min_amount" in conditions:
            if float(tx.get("amount", 0)) < float(conditions["min_amount"]):
                return False
        if "max_amount" in conditions:
            if float(tx.get("amount", 0)) > float(conditions["max_amount"]):
                return False

        # Type filter
        if "type" in conditions:
            if tx.get("type", "").lower() != conditions["type"].lower():
                return False

        # Category filter
        if "category" in conditions:
            if tx.get("category", "").lower() != conditions["category"].lower():
                return False

        # Keyword in description
        if "keyword" in conditions:
            if conditions["keyword"].lower() not in tx.get("description", "").lower():
                return False

        return True

    def _format_message(self, rule: dict, tx: dict) -> str:
        """Format relay message using rule template"""
        template = rule.get("message_template",
            "💰 Vault Alert: {type} of {amount} at {merchant}. Balance: {balance}")
        try:
            return template.format(
                type=tx.get("type", "Transaction"),
                amount=tx.get("amount", 0),
                merchant=tx.get("merchant", tx.get("description", "Unknown")),
                bank=tx.get("bank", "Unknown"),
                category=tx.get("category", "General"),
                balance=tx.get("balance_after", "N/A"),
                fee=tx.get("fee", 0),
                date=tx.get("date", ""),
                description=tx.get("description", "")
            )
        except (KeyError, ValueError):
            return f"Vault Alert: {tx.get('type', 'TX')} — {tx.get('amount', 0)}"

# ═══════════════════════════════════════════════════════════════════
# § AI SERVICE INTERFACE — Future-Proofed for Ollama
# ═══════════════════════════════════════════════════════════════════

class AIServiceInterface:
    """
    Abstract interface for AI-powered features.
    Currently returns rule-based fallbacks.
    Ready for Ollama/LLM integration in future.
    """

    def __init__(self):
        self.available = False
        self.model = None

    def check_availability(self) -> dict:
        """Check if AI service is available"""
        # Future: check if Ollama is running on localhost:11434
        return {
            "available": self.available,
            "model": self.model,
            "status": "future_module"
        }

    def categorize_transaction(self, description: str) -> str:
        """
        Auto-categorize a transaction description.
        Falls back to keyword matching when AI is unavailable.
        """
        desc_lower = description.lower()
        keyword_map = {
            "Shopping": ["shop", "store", "market", "mall", "buy", "purchase", "amazon"],
            "Dining": ["restaurant", "food", "coffee", "cafe", "eat", "dinner", "lunch"],
            "Transport": ["uber", "taxi", "bus", "fuel", "gas", "transport", "ride"],
            "Housing": ["rent", "mortgage", "house", "apartment", "maintenance"],
            "Bills": ["electric", "water", "internet", "phone", "bill", "utility"],
            "Health": ["hospital", "pharmacy", "doctor", "medical", "health", "clinic"],
            "Entertainment": ["movie", "netflix", "spotify", "game", "entertainment"],
            "Education": ["school", "university", "course", "book", "tuition"],
            "Salary": ["salary", "wage", "payroll", "income"],
            "Transfer": ["transfer", "send", "receive", "deposit"]
        }
        for cat, keywords in keyword_map.items():
            if any(kw in desc_lower for kw in keywords):
                return cat
        return "Other"

    def generate_insight(self, data: dict) -> str:
        """Generate AI-powered financial insight"""
        # Rule-based fallback until Ollama integrated
        sr = data.get("savings_rate", 0)
        velocity = data.get("spending_velocity", {})
        subs = data.get("subscriptions", [])

        parts = []
        if sr > 30:
            parts.append(f"Strong savings discipline at {sr}%.")
        elif sr > 15:
            parts.append(f"Savings rate at {sr}% — room for improvement.")
        else:
            parts.append(f"Savings critically low at {sr}%. Review expenses urgently.")

        if velocity.get("momentum") == "accelerating":
            parts.append("⚠ Spending velocity increasing.")
        elif velocity.get("momentum") == "decelerating":
            parts.append("✓ Spending velocity slowing — good discipline.")

        if subs:
            total = sum(s.get("amount", 0) for s in subs)
            parts.append(f"{len(subs)} subscriptions totaling ${total:.0f}/mo detected.")

        alerts = data.get("alerts", [])
        if alerts:
            parts.append(f"🔔 {len(alerts)} active alerts require attention.")

        return " ".join(parts) if parts else "Analyzing your financial patterns..."

# ═══════════════════════════════════════════════════════════════════
# § DATA TRANSFORMER — Chart-Ready Data Conversion
# ═══════════════════════════════════════════════════════════════════

class DataTransformer:
    """Advanced data transformer for ApexCharts-ready JSON"""

    @staticmethod
    def transform_for_charts(transactions, mode="monthly"):
        """Convert transactions into chart-ready JSON structure"""
        if not transactions:
            return {"monthly": {}, "categories": {}, "timeline": [], "daily": {}}

        monthly = defaultdict(lambda: {"income": 0, "expense": 0, "net": 0, "fees": 0, "count": 0})
        daily = defaultdict(lambda: {"income": 0, "expense": 0, "net": 0})
        categories = defaultdict(lambda: {"amount": 0, "count": 0})
        weekly = defaultdict(lambda: {"income": 0, "expense": 0, "net": 0})

        for tx in transactions:
            try:
                dt = datetime.fromisoformat(tx.get("date", "").replace("Z", "+00:00"))
                month_key = dt.strftime("%Y-%m")
                day_key = dt.strftime("%Y-%m-%d")
                week_num = dt.isocalendar()[1]
                week_key = f"{dt.year}-W{week_num:02d}"
            except:
                month_key = "unknown"
                day_key = "unknown"
                week_key = "unknown"

            amt = float(tx.get("amount", 0))
            tx_type = tx.get("type", "Expense")
            cat = tx.get("category", "Other")
            fee = float(tx.get("fee", 0)) + float(tx.get("vat", 0))

            if tx_type == "Income":
                monthly[month_key]["income"] += amt
                daily[day_key]["income"] += amt
                weekly[week_key]["income"] += amt
            else:
                monthly[month_key]["expense"] += amt
                daily[day_key]["expense"] += amt
                weekly[week_key]["expense"] += amt
                categories[cat]["amount"] += amt
                categories[cat]["count"] += 1

            monthly[month_key]["fees"] += fee
            monthly[month_key]["count"] += 1
            monthly[month_key]["net"] = monthly[month_key]["income"] - monthly[month_key]["expense"]
            daily[day_key]["net"] = daily[day_key]["income"] - daily[day_key]["expense"]
            weekly[week_key]["net"] = weekly[week_key]["income"] - weekly[week_key]["expense"]

        sorted_months = dict(sorted(monthly.items()))
        sorted_days = dict(sorted(daily.items()))
        sorted_weeks = dict(sorted(weekly.items()))

        return {
            "monthly": {k: {key: round(v, 2) for key, v in val.items()} for k, val in sorted_months.items()},
            "daily": {k: {key: round(v, 2) for key, v in val.items()} for k, val in sorted_days.items()},
            "weekly": {k: {key: round(v, 2) for key, v in val.items()} for k, val in sorted_weeks.items()},
            "categories": dict(categories),
            "timeline": [{"month": k, **v} for k, v in sorted_months.items()],
            "daily_timeline": [{"date": k, **v} for k, v in sorted_days.items()],
        }

    @staticmethod
    def to_apex_series(data: dict, chart_type: str = "area") -> dict:
        """Convert transformer output to ApexCharts series format"""
        timeline = data.get("timeline", [])
        if not timeline:
            return {"series": [], "categories": []}

        income_series = [{"x": t["month"], "y": round(t["income"], 2)} for t in timeline]
        expense_series = [{"x": t["month"], "y": round(t["expense"], 2)} for t in timeline]
        net_series = [{"x": t["month"], "y": round(t["net"], 2)} for t in timeline]

        return {
            "series": [
                {"name": "Income", "data": [t["income"] for t in timeline]},
                {"name": "Expenses", "data": [t["expense"] for t in timeline]},
                {"name": "Net", "data": [t["net"] for t in timeline]}
            ],
            "categories": [t["month"] for t in timeline],
            "donut": {
                "series": [round(v["amount"], 2) for v in data.get("categories", {}).values()],
                "labels": list(data.get("categories", {}).keys())
            }
        }

# ═══════════════════════════════════════════════════════════════════
# § CORE APPLICATION — VaultPro Engine
# ═══════════════════════════════════════════════════════════════════

class VaultPro:
    """
    Master application controller.
    Bridges Python backend with the PyWebView frontend SPA.
    All methods prefixed with _ are internal; public methods
    are exposed to JavaScript via pywebview.api.
    """

    def __init__(self):
        self.window = None
        self.data = {}
        self.settings = {}
        self.transformer = DataTransformer()
        self.staging = StagingVault()
        self.ai = AIServiceInterface()
        self.relay_provider = None
        self.relay_engine = None
        self.batch_engine = None
        self.sms_server_thread = None
        self.session_start = datetime.now().isoformat()

        self.load_data()
        self._load_settings()
        self._init_relay()
        self._init_batch()

    def set_window(self, window):
        self.window = window

    # ─── Settings Management ──────────────────────────────

    def _load_settings(self):
        """Load or create settings file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.settings = json.load(f)
                self.settings = _merge_defaults(self.settings, dict(DEFAULT_SETTINGS))
                # Strip shipped demo accounts on upgrade so the app opens clean.
                demo_accounts = [
                    {"name": "Checking", "type": "bank", "icon": "account_balance", "balance": 0},
                    {"name": "Savings", "type": "bank", "icon": "savings", "balance": 0},
                    {"name": "Cash", "type": "cash", "icon": "payments", "balance": 0}
                ]
                if self.settings.get("accounts") == demo_accounts:
                    self.settings["accounts"] = []
            except:
                self.settings = dict(DEFAULT_SETTINGS)
        else:
            self.settings = dict(DEFAULT_SETTINGS)
            self._save_settings()

    def _save_settings(self):
        """Persist settings to disk"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logging.error(f"Settings save error: {e}")

    def _init_relay(self):
        """Initialize relay engine with internal provider"""
        if "relay_log" not in self.data:
            self.data["relay_log"] = []
        providers = {
            "sms": InternalRelayProvider(self.data["relay_log"]),
            "telegram": TelegramProvider(),
            "email": EmailProvider()
        }
        self.relay_provider = NotificationRouter(providers)
        self.relay_engine = RelayRuleEngine(self.relay_provider)
        self.relay_engine.load_rules(self.settings.get("relay_rules", []))

    def _init_batch(self):
        """Initialize smart batch engine"""
        delay = self.settings.get("sms_debounce_seconds", 60)
        self.batch_engine = SmartBatchEngine(
            process_callback=self._process_sms_batch,
            delay_seconds=delay
        )
        self.batch_engine.set_instant(self.settings.get("sms_instant_mode", False))

    # ─── Audit Logging ─────────────────────────────────────

    def _log_audit(self, event, confidence="HIGH", details=""):
        if "audit_log" not in self.data:
            self.data["audit_log"] = []
        self.data["audit_log"].insert(0, {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "confidence": confidence,
            "details": details
        })
        self.data["audit_log"] = self.data["audit_log"][:500]

    def _looks_like_demo_data(self):
        """
        Detect the previously shipped sample/demo state so the app can migrate
        to a clean first-run experience automatically.
        """
        txs = self.data.get("transactions", [])
        goals = self.data.get("goals", [])
        sources = {t.get("source", "") for t in txs}
        descriptions = {t.get("description", "") for t in txs}
        goal_names = {g.get("name", "") for g in goals}

        return (
            self.data.get("monthly_income") == 14200.0
            and self.data.get("monthly_burn") == 8430.12
            and len(txs) <= 6
            and sources.issubset({"manual", ""})
            and descriptions.issubset({"Shopping", "Between Accounts"})
            and {"New Car", "Japan Trip"}.issubset(goal_names)
        )

    def _clear_demo_data(self):
        """Reset demo data while preserving security and appearance preferences."""
        preserved = {
            "password_hash": self.data.get("password_hash"),
            "has_setup_password": self.data.get("has_setup_password", False),
            "theme": self.data.get("theme", DEFAULT_DATA["theme"]),
            "privacy_mask": self.data.get("privacy_mask", DEFAULT_DATA["privacy_mask"]),
            "biometrics": self.data.get("biometrics", DEFAULT_DATA["biometrics"]),
        }
        self.data = json.loads(json.dumps(DEFAULT_DATA))
        self.data.update(preserved)
        self._log_audit("Demo Data Cleared", "HIGH", "Removed shipped sample balances and transactions")

    # ─── Data Persistence ──────────────────────────────────

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            self.data = json.loads(json.dumps(DEFAULT_DATA))
            self._log_audit("Vault Genesis", "HIGH", "Initial vault created")
            self.save_data()
        else:
            try:
                with open(DATA_FILE, 'r') as f:
                    self.data = json.load(f)
                for key in DEFAULT_DATA:
                    if key not in self.data:
                        self.data[key] = DEFAULT_DATA[key]
                if self._looks_like_demo_data():
                    self._clear_demo_data()
            except json.JSONDecodeError as e:
                self.data = json.loads(json.dumps(DEFAULT_DATA))
                self._log_audit("Data Corruption Recovery", "CRITICAL", str(e))
            except Exception as e:
                self.data = json.loads(json.dumps(DEFAULT_DATA))
                self._log_audit("Data Load Failed", "FAIL", str(e))

    def save_data(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logging.error(f"Save error: {e}")

    # ─── Anomaly Detection ─────────────────────────────────

    def _calculate_anomaly(self, tx):
        """Statistical anomaly detection for transactions"""
        if tx["type"] == "Income":
            return False
        amt = float(tx.get("amount", 0))
        cat = tx.get("category", "Other")
        past = [t["amount"] for t in self.data.get("transactions", [])
                if t["type"] == "Expense" and t.get("category") == cat]

        if len(past) < 3:
            if "fee" in tx.get("description", "").lower() and amt > 50.0:
                self._log_audit("Ghost Fee Detected", "MEDIUM",
                                f"Anomalous fee: {tx['description']} (${amt})")
                return True
            return False

        avg = sum(past) / len(past)
        std_dev = math.sqrt(sum((x - avg) ** 2 for x in past) / len(past)) if len(past) > 1 else 0

        if amt > (avg * 2.5) and amt > 50:
            self._log_audit("Anomaly Threshold", "HIGH",
                            f"{tx['description']} is {amt / avg:.1f}x above {cat} avg")
            return True
        if std_dev > 0 and abs(amt - avg) > (3 * std_dev):
            self._log_audit("Statistical Outlier", "MEDIUM",
                            f"{tx['description']} exceeds 3σ")
            return True
        return False

    # ─── Subscription Detection ────────────────────────────

    def _detect_subscriptions(self):
        """Detect recurring subscription payments"""
        expenses = [t for t in self.data.get("transactions", []) if t.get("type") == "Expense"]
        merchant_groups = defaultdict(list)
        for tx in expenses:
            merchant = tx.get("merchant") or tx.get("description", "Unknown")
            amount = round(float(tx.get("amount", 0)), 2)
            key = f"{merchant}|{amount}"
            merchant_groups[key].append(tx)

        subscriptions = []
        for key, txs in merchant_groups.items():
            if len(txs) >= 2:
                merchant, amount = key.split("|")
                dates = []
                for tx in txs:
                    try:
                        dt = datetime.fromisoformat(tx.get("date", "").replace("Z", "+00:00"))
                        dates.append(dt)
                    except:
                        continue
                if len(dates) >= 2:
                    dates.sort()
                    intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
                    avg_interval = sum(intervals) / len(intervals)
                    if 25 <= avg_interval <= 35:
                        subscriptions.append({
                            "merchant": merchant, "amount": float(amount),
                            "frequency": "Monthly",
                            "next_expected": (dates[-1] + timedelta(days=30)).isoformat(),
                            "confidence": "HIGH" if len(txs) >= 3 else "MEDIUM",
                            "occurrences": len(txs),
                            "total_spent": float(amount) * len(txs)
                        })
        self.data["subscriptions"] = subscriptions
        return subscriptions

    # ─── Spending Velocity ─────────────────────────────────

    def _calculate_velocity(self):
        """Calculate spending velocity and momentum"""
        expenses = [t for t in self.data.get("transactions", []) if t.get("type") == "Expense"]
        if not expenses:
            return {"daily_avg": 0, "weekly_trend": 0, "momentum": "stable"}

        dated = []
        for tx in expenses:
            try:
                dt = datetime.fromisoformat(tx.get("date", "").replace("Z", "+00:00"))
                dated.append((dt, float(tx.get("amount", 0))))
            except:
                continue
        if not dated:
            return {"daily_avg": 0, "weekly_trend": 0, "momentum": "stable"}

        dated.sort(key=lambda x: x[0])
        now = datetime.now()
        recent = [amt for dt, amt in dated if (now - dt).days <= 30]
        daily_avg = sum(recent) / 30 if recent else 0

        last_week = [amt for dt, amt in dated if 0 <= (now - dt).days <= 7]
        prev_week = [amt for dt, amt in dated if 8 <= (now - dt).days <= 14]
        lw_total = sum(last_week)
        pw_total = sum(prev_week)
        weekly_change = ((lw_total - pw_total) / pw_total * 100) if pw_total > 0 else 0

        momentum = "accelerating" if weekly_change > 10 else ("decelerating" if weekly_change < -10 else "stable")
        velocity = {
            "daily_avg": round(daily_avg, 2),
            "weekly_trend": round(weekly_change, 1),
            "momentum": momentum,
            "last_week_total": round(lw_total, 2),
            "prev_week_total": round(pw_total, 2)
        }
        self.data["spending_velocity"] = velocity
        return velocity

    # ─── Runway Calculator ─────────────────────────────────

    def _calculate_runway(self):
        """Calculate financial runway"""
        nw = self.data.get("net_worth", 0)
        burn = self.data.get("monthly_burn", 1)
        income = self.data.get("monthly_income", 0)

        if burn <= 0 or (income >= burn and nw > 0):
            runway_days = 999999
        else:
            daily_burn = burn / 30
            runway_days = int(nw / daily_burn) if daily_burn > 0 else 999999

        self.data["runway_days"] = runway_days
        if runway_days >= 999999:
            self.data["runway_formatted"] = "∞ (Growing)"
        elif runway_days >= 365:
            self.data["runway_formatted"] = f"{runway_days // 365}y {(runway_days % 365) // 30}m"
        elif runway_days >= 30:
            self.data["runway_formatted"] = f"{runway_days // 30}mo {runway_days % 30}d"
        else:
            self.data["runway_formatted"] = f"{runway_days} days"
        return runway_days

    # ─── Goal Progress ─────────────────────────────────────

    def _update_goal_progress(self):
        for goal in self.data.get("goals", []):
            target = float(goal.get("target", 0))
            current = float(goal.get("current", 0))
            if target > 0:
                goal["progress"] = round(min(100, (current / target) * 100), 1)
                goal["remaining"] = round(max(0, target - current), 2)
                monthly_savings = self.data.get("monthly_income", 0) - self.data.get("monthly_burn", 0)
                if monthly_savings > 0 and goal["remaining"] > 0:
                    goal["eta_months"] = round(goal["remaining"] / monthly_savings, 1)
                else:
                    goal["eta_months"] = None

    # ─── Alert Generation ──────────────────────────────────

    def _generate_alerts(self):
        """Generate critical alerts based on financial state"""
        alerts = []
        txs = self.data.get("transactions", [])

        # Budget over-limit alerts
        limits = self.settings.get("budget_limits", {})
        cat_totals = defaultdict(float)
        now = datetime.now()
        for tx in txs:
            if tx.get("type") == "Expense":
                try:
                    dt = datetime.fromisoformat(tx.get("date", "").replace("Z", "+00:00"))
                    if dt.month == now.month and dt.year == now.year:
                        cat_totals[tx.get("category", "Other")] += float(tx.get("amount", 0))
                except:
                    pass

        for cat, limit in limits.items():
            spent = cat_totals.get(cat, 0)
            if limit > 0 and spent >= limit:
                alerts.append({
                    "type": "budget_exceeded",
                    "severity": "critical",
                    "icon": "warning",
                    "title": f"{cat} Budget Exceeded",
                    "message": f"Spent ${spent:,.2f} of ${limit:,.2f} limit",
                    "category": cat
                })
            elif limit > 0 and spent >= limit * 0.85:
                alerts.append({
                    "type": "budget_warning",
                    "severity": "warning",
                    "icon": "info",
                    "title": f"{cat} Budget at {spent / limit * 100:.0f}%",
                    "message": f"${limit - spent:,.2f} remaining this month",
                    "category": cat
                })

        # Recent anomaly alerts
        recent_anomalies = [t for t in txs[:20] if t.get("is_anomaly")]
        for anom in recent_anomalies[:3]:
            alerts.append({
                "type": "anomaly",
                "severity": "warning",
                "icon": "emergency",
                "title": "Anomaly: " + anom.get("description", "Unknown")[:40],
                "message": f"${anom.get('amount', 0):,.2f} flagged as statistical outlier"
            })

        # Ghost fees alert
        ghost_total = sum(float(t.get("fee", 0)) + float(t.get("vat", 0))
                         for t in txs[:50] if t.get("ghost_fee"))
        if ghost_total > 0:
            alerts.append({
                "type": "ghost_fees",
                "severity": "info",
                "icon": "visibility_off",
                "title": "Hidden Fees Detected",
                "message": f"${ghost_total:,.2f} in ghost fees found in recent transactions"
            })

        # Pending SMS alert
        pending = self.staging.get_parsed()
        if pending:
            alerts.append({
                "type": "pending_approval",
                "severity": "info",
                "icon": "inbox",
                "title": f"{len(pending)} SMS Awaiting Approval",
                "message": "Review and approve incoming transactions"
            })

        self.data["alerts"] = alerts
        return alerts

    # ─── Monthly Flow Ratio ────────────────────────────────

    def _calculate_flow_ratios(self):
        """Calculate monthly income-to-expense ratios"""
        txs = self.data.get("transactions", [])
        monthly = defaultdict(lambda: {"income": 0, "expense": 0})
        for tx in txs:
            try:
                dt = datetime.fromisoformat(tx.get("date", "").replace("Z", "+00:00"))
                key = dt.strftime("%Y-%m")
            except:
                continue
            amt = float(tx.get("amount", 0))
            if tx.get("type") == "Income":
                monthly[key]["income"] += amt
            else:
                monthly[key]["expense"] += amt

        ratios = {}
        for month, vals in sorted(monthly.items()):
            exp = vals["expense"] if vals["expense"] > 0 else 1
            ratios[month] = {
                "ratio": round(vals["income"] / exp, 2),
                "income": round(vals["income"], 2),
                "expense": round(vals["expense"], 2),
                "net": round(vals["income"] - vals["expense"], 2)
            }
        self.data["flow_ratios"] = ratios
        return ratios

    # ─────────────────────────────────────────────────────────────────
    # Parser Configuration Helpers
    # ─────────────────────────────────────────────────────────────────

    def _safe_parse_datetime(self, value):
        """Parse flexible date/timestamp inputs into datetime."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            # Accept both second and millisecond epochs.
            ts = float(value)
            if ts > 1_000_000_000_000:
                ts /= 1000.0
            try:
                return datetime.fromtimestamp(ts)
            except Exception:
                return None
        if isinstance(value, str):
            txt = value.strip()
            if not txt:
                return None
            for parser in (
                lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
                lambda s: datetime.strptime(s, "%Y-%m-%d"),
                lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),
                lambda s: datetime.strptime(s, "%d/%m/%Y"),
                lambda s: datetime.strptime(s, "%d-%m-%Y"),
                lambda s: datetime.strptime(s, "%m/%d/%Y"),
            ):
                try:
                    return parser(txt)
                except Exception:
                    continue
            # Numeric string epoch fallback
            if txt.isdigit():
                return self._safe_parse_datetime(float(txt))
        return None

    def _get_bank_start_date(self, bank_display: str):
        """
        Resolve bank start date from settings.
        Returns datetime.min when no restriction is configured.
        """
        raw = self.settings.get("bank_start_dates", {}).get(bank_display)
        parsed = self._safe_parse_datetime(raw)
        return parsed or datetime.min

    def _get_effective_patterns(self, bank_key: str, pattern_kind: str):
        """
        Merge static parser rules with optional user regex overrides.
        User overrides are prepended so they can specialize vendor formats.
        """
        base = list(BANK_RULES.get(bank_key, {}).get("patterns", {}).get(pattern_kind, []))
        overrides = self.settings.get("bank_regex_overrides", {})
        custom = overrides.get(bank_key, {}).get(pattern_kind, [])
        custom = [p for p in custom if isinstance(p, str) and p.strip()]
        return custom + base

    def get_parser_config(self):
        """Expose parser tuning config to the frontend."""
        return {
            "start_dates": self.settings.get("bank_start_dates", {}),
            "regex_overrides": self.settings.get("bank_regex_overrides", {}),
            "banks": list(BANK_RULES.keys())
        }

    def update_parser_config(self, data):
        """
        Update parser start dates and regex overrides from UI.
        Payload:
        {
            "start_dates": {"CBE": "2024-12-10", ...},
            "regex_overrides": {"CBE": {"amount": ["..."]}}
        }
        """
        start_dates = data.get("start_dates")
        regex_overrides = data.get("regex_overrides")

        if isinstance(start_dates, dict):
            sanitized_dates = {}
            for bank, raw in start_dates.items():
                if bank in BANK_RULES:
                    parsed = self._safe_parse_datetime(raw)
                    if parsed:
                        sanitized_dates[bank] = parsed.strftime("%Y-%m-%d")
            self.settings["bank_start_dates"] = sanitized_dates

        if isinstance(regex_overrides, dict):
            sanitized_regex = {}
            for bank, rules in regex_overrides.items():
                if bank not in BANK_RULES or not isinstance(rules, dict):
                    continue
                sanitized_regex[bank] = {}
                for kind, patterns in rules.items():
                    if kind not in {"amount", "balance", "fee", "vat", "merchant", "date"}:
                        continue
                    if isinstance(patterns, list):
                        cleaned = [p.strip() for p in patterns if isinstance(p, str) and p.strip()]
                        sanitized_regex[bank][kind] = cleaned[:20]  # Keep config bounded
            self.settings["bank_regex_overrides"] = sanitized_regex

        self._save_settings()
        self._log_audit("Parser Config Updated", "HIGH", "Bank start dates / regex overrides updated")
        return {"status": "success", "config": self.get_parser_config()}

    # ═══════════════════════════════════════════════════════
    # PUBLIC API — Exposed to JavaScript Frontend
    # ═══════════════════════════════════════════════════════

    def sync_data(self):
        """Full data synchronization with all analytics"""
        self.load_data()
        nw = self.data.get("net_worth", 0)
        burn = self.data.get("monthly_burn", 1)
        inc = self.data.get("monthly_income", 1)

        savings_rate = ((inc - burn) / inc * 100) if inc > 0 else 0
        ratio = inc / burn if burn > 0 else 1

        health = 50
        health += min(30, savings_rate)
        health += min(20, ratio * 10)
        health += min(10, len(self.data.get("transactions", [])) / 10)
        self.data["health_score"] = int(max(0, min(100, health)))
        self.data["savings_rate"] = round(savings_rate, 1)
        self.data["ratio"] = round(ratio, 2)

        # 6-month predictions
        preds = []
        pnw = nw
        for i in range(1, 7):
            pnw += (inc - burn)
            preds.append({
                "month": (datetime.now() + timedelta(days=30 * i)).strftime("%b %Y"),
                "projected_net_worth": round(pnw, 2),
                "delta": round(inc - burn, 2)
            })
        self.data["predictions"] = preds

        # Chart data
        chart_data = self.transformer.transform_for_charts(self.data.get("transactions", []))
        self.data["monthly_totals"] = chart_data["monthly"]
        self.data["category_breakdown"] = chart_data["categories"]
        self.data["chart_timeline"] = chart_data["timeline"]
        self.data["daily_timeline"] = chart_data.get("daily_timeline", [])
        apex_data = self.transformer.to_apex_series(chart_data)
        self.data["apex_series"] = apex_data

        # Analytics
        self._detect_subscriptions()
        self._calculate_velocity()
        self._calculate_runway()
        self._update_goal_progress()
        self._generate_alerts()
        self._calculate_flow_ratios()

        # AI insight
        self.data["ai_insight"] = self.ai.generate_insight(self.data)

        # Session info
        self.data["session_start"] = self.session_start

        # Staging stats
        self.data["staging_stats"] = self.staging.get_stats()

        self._log_audit("Vault Sync", "HIGH", "Full analytics refresh completed")
        self.save_data()
        return self.data

    def get_settings(self):
        """Return all settings to frontend"""
        return self.settings

    def update_setting(self, data):
        """Update a setting with persistence"""
        key = data.get("key")
        value = data.get("value")
        if key:
            self.data[key] = value
            if key in ["theme", "privacy_mask", "biometrics"]:
                self.settings[key] = value
            self._log_audit("Setting Changed", "HIGH", f"{key} = {value}")
            self.save_data()
            self._save_settings()
            return {"status": "success", "key": key, "value": value}
        return {"status": "error", "message": "No key provided"}

    def update_app_settings(self, data):
        """Update app-level settings (accent, glass, nav mode, etc.)"""
        for key, value in data.items():
            self.settings[key] = value
        self._save_settings()

        # Apply runtime changes
        if "sms_debounce_seconds" in data and self.batch_engine:
            self.batch_engine.set_delay(data["sms_debounce_seconds"])
        if "sms_instant_mode" in data and self.batch_engine:
            self.batch_engine.set_instant(data["sms_instant_mode"])
        if "relay_rules" in data and self.relay_engine:
            self.relay_engine.load_rules(data["relay_rules"])

        return {"status": "success"}

    def set_category_icon(self, data):
        """Assign an icon name to a category for instant UI propagation."""
        category = (data.get("category") or "").strip()
        icon = (data.get("icon") or "").strip()
        if not category or not icon:
            return {"status": "error", "message": "category and icon are required"}
        self.settings.setdefault("category_icons", {})[category] = icon
        self._save_settings()
        self._log_audit("Category Icon Updated", "MEDIUM", f"{category} -> {icon}")
        return {"status": "success", "category": category, "icon": icon}

    def add_transaction(self, data):
        """Add a new transaction with anomaly detection + relay evaluation"""
        tx = {
            "id": len(self.data.get("transactions", [])) + 1,
            "date": data.get("date", datetime.now().isoformat()),
            "description": data.get("description", "Manual Entry"),
            "amount": float(data.get("amount", 0.0)),
            "type": data.get("type", "Expense"),
            "category": data.get("category", "Other"),
            "merchant": data.get("merchant", ""),
            "bank": data.get("bank", ""),
            "balance_after": data.get("balance_after"),
            "fee": float(data.get("fee", 0)),
            "vat": float(data.get("vat", 0)),
            "source": data.get("source", "manual"),
            "is_anomaly": False,
            "ghost_fee": False
        }

        desc_lower = tx["description"].lower()
        if any(term in desc_lower for term in ["fee", "charge", "vat", "tax", "service"]):
            if tx["amount"] < 100:
                tx["ghost_fee"] = True

        tx["is_anomaly"] = self._calculate_anomaly(tx)

        if "transactions" not in self.data:
            self.data["transactions"] = []
        self.data["transactions"].insert(0, tx)

        if tx["type"] == "Income":
            self.data["net_worth"] += tx["amount"]
        elif tx["type"] == "Expense":
            self.data["net_worth"] -= tx["amount"]

        # Budget hard-stop check
        budget_warning = None
        limits = self.settings.get("budget_limits", {})
        hard_stop_enabled = self.settings.get("hard_stop_enabled", True)
        if tx["type"] == "Expense" and tx["category"] in limits:
            limit = limits[tx["category"]]
            cat_total = sum(
                float(t.get("amount", 0))
                for t in self.data["transactions"]
                if t.get("type") == "Expense" and t.get("category") == tx["category"]
                   and datetime.fromisoformat(t.get("date", "").replace("Z", "+00:00")).month == datetime.now().month
            )
            if cat_total >= limit:
                budget_warning = f"⚠ {tx['category']} budget exceeded: ${cat_total:,.2f} / ${limit:,.2f}"
                if hard_stop_enabled and cat_total > limit:
                    # Roll back this transaction if hard-stop mode is enabled.
                    self.data["transactions"].pop(0)
                    self.data["net_worth"] += tx["amount"]
                    self.save_data()
                    self._log_audit("Hard Stop Blocked TX", "HIGH", budget_warning)
                    return {
                        "status": "error",
                        "message": f"Hard Stop active. {budget_warning}",
                        "budget_warning": budget_warning
                    }

        # Relay evaluation
        relay_results = []
        if self.relay_engine:
            relay_results = self.relay_engine.evaluate(tx)

        self.save_data()

        msg = "Transaction secured"
        if tx["is_anomaly"]:
            msg += " (Anomaly detected)"
        if tx["ghost_fee"]:
            msg += " (Ghost fee flagged)"
        if budget_warning:
            msg += f" — {budget_warning}"
        if relay_results:
            msg += f" — {len(relay_results)} relay(s) triggered"

        return {
            "status": "success", "message": msg,
            "is_anomaly": tx["is_anomaly"], "ghost_fee": tx["ghost_fee"],
            "budget_warning": budget_warning,
            "relays_triggered": len(relay_results)
        }

    def add_goal(self, data):
        """Add a new wealth goal"""
        if "goals" not in self.data:
            self.data["goals"] = []
        goal = {
            "name": data.get("name", "New Goal"),
            "target": float(data.get("target", 1000)),
            "current": float(data.get("current", 0)),
            "category": data.get("category", "General"),
            "icon": data.get("icon", "flag"),
            "created": datetime.now().isoformat(),
            "progress": 0, "remaining": float(data.get("target", 1000)),
            "eta_months": None
        }
        if goal["target"] > 0:
            goal["progress"] = round(min(100, (goal["current"] / goal["target"]) * 100), 1)
            goal["remaining"] = round(max(0, goal["target"] - goal["current"]), 2)
        self.data["goals"].append(goal)
        self._log_audit("Goal Created", "MEDIUM", f"{goal['name']} (Target: {goal['target']})")
        self.save_data()
        return {"status": "success", "goal": goal}

    def update_goal(self, data):
        """Update goal progress"""
        idx = data.get("index")
        new_current = data.get("current")
        if idx is not None and idx < len(self.data.get("goals", [])):
            goal = self.data["goals"][idx]
            if new_current is not None:
                goal["current"] = float(new_current)
                if goal["target"] > 0:
                    goal["progress"] = round(min(100, (goal["current"] / goal["target"]) * 100), 1)
                    goal["remaining"] = round(max(0, goal["target"] - goal["current"]), 2)
            self.save_data()
            return {"status": "success", "goal": goal}
        return {"status": "error", "message": "Goal not found"}

    def delete_goal(self, data):
        """Delete a goal by index"""
        idx = data.get("index")
        goals = self.data.get("goals", [])
        if idx is not None and 0 <= idx < len(goals):
            removed = goals.pop(idx)
            self._log_audit("Goal Deleted", "MEDIUM", removed.get("name", ""))
            self.save_data()
            return {"status": "success"}
        return {"status": "error", "message": "Goal not found"}

    # ─── SMS / Inbox API ───────────────────────────────────

    def receive_sms(self, data):
        """Receive SMS from mobile app P2P sync"""
        body = data.get("body", "")
        sender = data.get("sender", "")
        metadata = data.get("metadata", {})

        if not body:
            return {"status": "error", "message": "Empty SMS body"}

        result = self.staging.add(body, sender, metadata)
        if result["status"] == "staged":
            self.batch_engine.add(result)
            self._log_audit("SMS Received", "HIGH", f"From {sender}: {body[:50]}...")
        return result

    def get_inbox(self):
        """Get all parsed SMS entries awaiting approval"""
        # First, process any pending entries
        pending = self.staging.get_pending()
        for entry in pending:
            parsed = self._parse_sms_text(entry["body"], entry.get("metadata"))
            if parsed:
                self.staging.mark_parsed(entry["id"], parsed)

        return {
            "parsed": self.staging.get_parsed(),
            "stats": self.staging.get_stats()
        }

    def approve_sms(self, data):
        """Approve a parsed SMS entry and commit to ledger"""
        entry_id = data.get("id")
        overrides = data.get("overrides", {})
        result = self.staging.approve(entry_id, overrides)

        if result["status"] == "approved":
            parsed = result.get("data", {})
            tx_data = {
                "description": parsed.get("description", "SMS Import"),
                "amount": parsed.get("amount", 0),
                "type": parsed.get("type", "Expense"),
                "category": overrides.get("category", parsed.get("category", "SMS Import")),
                "merchant": parsed.get("merchant", ""),
                "bank": parsed.get("bank", ""),
                "balance_after": parsed.get("balance"),
                "fee": parsed.get("fee", 0),
                "vat": parsed.get("vat", 0),
                "source": "sms",
                "date": parsed.get("date", datetime.now().isoformat())
            }
            self.add_transaction(tx_data)
            self._log_audit("SMS Approved", "HIGH", f"Committed: {tx_data['description'][:50]}")

        return result

    def reject_sms(self, data):
        """Reject a parsed SMS entry"""
        entry_id = data.get("id")
        result = self.staging.reject(entry_id)
        if result["status"] == "rejected":
            self._log_audit("SMS Rejected", "MEDIUM", f"Entry {entry_id} rejected by user")
        return result

    def _parse_sms_text(self, text, metadata=None):
        """
        Parse SMS text using bank rules + user overrides.
        Applies bank start-date filtering before an entry reaches the inbox.
        """
        metadata = metadata or {}
        profile = self._detect_bank_profile(text)

        # Resolve timestamp (metadata timestamp/date is preferred, else now).
        sms_dt = (
            self._safe_parse_datetime(metadata.get("timestamp"))
            or self._safe_parse_datetime(metadata.get("date"))
            or datetime.now()
        )

        if not profile:
            amt_match = re.search(r'(?:USD|ETB|Birr|\$)\s?([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
            if amt_match:
                amt = float(amt_match.group(1).replace(',', ''))
                is_credit = any(w in text.lower() for w in ['credited', 'received', 'deposit'])
                return {
                    "amount": abs(amt),
                    "type": "Income" if is_credit else "Expense",
                    "description": text[:120],
                    "bank": "Unknown",
                    "merchant": "",
                    "balance": None,
                    "fee": 0,
                    "vat": 0,
                    "date": sms_dt.isoformat(),
                    "category": self.ai.categorize_transaction(text),
                    "confidence": "LOW"
                }
            return None

        # Find canonical bank key from profile.
        bank_key = None
        for k, v in BANK_RULES.items():
            if v.get("display") == profile.get("display"):
                bank_key = k
                break
        bank_key = bank_key or "CBE"

        # Enforce configurable start date per bank.
        start_date = self._get_bank_start_date(profile.get("display", bank_key))
        if sms_dt < start_date:
            return None

        amount_patterns = self._get_effective_patterns(bank_key, "amount")
        balance_patterns = self._get_effective_patterns(bank_key, "balance")
        fee_patterns = self._get_effective_patterns(bank_key, "fee")
        vat_patterns = self._get_effective_patterns(bank_key, "vat")
        merchant_patterns = self._get_effective_patterns(bank_key, "merchant")

        amt_str = self._extract_with_regex(text, amount_patterns)
        bal_str = self._extract_with_regex(text, balance_patterns)
        fee_str = self._extract_with_regex(text, fee_patterns)
        vat_str = self._extract_with_regex(text, vat_patterns)
        merchant = self._extract_with_regex(text, merchant_patterns)

        if not amt_str:
            return None

        try:
            amt = float(amt_str)
            fee = float(fee_str) if fee_str else 0.0
            vat = float(vat_str) if vat_str else 0.0
            is_credit = any(w in text.lower() for w in ['credited', 'received', 'deposit'])

            desc = text[:140]
            category = self.ai.categorize_transaction(text)
            # Detect likely internal transfers from account-like tokens.
            if re.search(r'\b(?:\d{3,}|account)\b', text, re.IGNORECASE) and "transfer" in text.lower():
                category = "Internal Transfer"

            return {
                "amount": abs(amt),
                "type": "Income" if is_credit else "Expense",
                "description": desc,
                "bank": profile["display"],
                "merchant": merchant or "",
                "balance": float(bal_str) if bal_str else None,
                "fee": fee,
                "vat": vat,
                "date": sms_dt.isoformat(),
                "category": category,
                "confidence": "HIGH" if bal_str else "MEDIUM"
            }
        except ValueError:
            return None

    def _process_sms_batch(self, items):
        """Process a batch of staged SMS entries through the parser"""
        for item in items:
            entry_id = item.get("id")
            if entry_id:
                entries = [e for e in self.staging.entries if e["id"] == entry_id]
                if entries:
                    parsed = self._parse_sms_text(entries[0]["body"], entries[0].get("metadata"))
                    if parsed:
                        self.staging.mark_parsed(entry_id, parsed)
        self._log_audit("Batch Processed", "HIGH", f"{len(items)} SMS entries parsed")

    def _extract_with_regex(self, text, patterns):
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
            except re.error:
                continue
            if match:
                return match.group(1).replace(',', '').strip()
        return None

    def _detect_bank_profile(self, text):
        text_lower = text.lower()
        if "cbe" in text_lower or "commercial bank" in text_lower:
            return BANK_RULES["CBE"]
        elif "telebirr" in text_lower or "ethiotel" in text_lower or re.search(r"\b127\b", text_lower):
            return BANK_RULES["Telebirr"]
        elif "boa" in text_lower or "abyssinia" in text_lower:
            return BANK_RULES["BOA"]
        elif "dashen" in text_lower:
            return BANK_RULES["Dashen"]
        return None

    # ─── Relay API ─────────────────────────────────────────

    def get_relay_rules(self):
        """Get all relay rules"""
        return self.settings.get("relay_rules", [])

    def add_relay_rule(self, data):
        """Add a new relay rule"""
        rules = self.settings.get("relay_rules", [])
        channel = str(data.get("channel", "sms")).lower()
        if channel not in {"sms", "telegram", "email"}:
            channel = "sms"
        rule = {
            "id": len(rules) + 1,
            "name": data.get("name", "New Rule"),
            "enabled": True,
            "conditions": data.get("conditions", {}),
            "channel": channel,
            "recipient": data.get("recipient", ""),
            "message_template": data.get("message_template",
                                         "💰 {type}: {amount} at {merchant}. Balance: {balance}"),
            "created": datetime.now().isoformat()
        }
        rules.append(rule)
        self.settings["relay_rules"] = rules
        self._save_settings()
        self.relay_engine.load_rules(rules)
        self._log_audit("Relay Rule Created", "MEDIUM", rule["name"])
        return {"status": "success", "rule": rule}

    def delete_relay_rule(self, data):
        """Delete a relay rule by id"""
        rule_id = data.get("id")
        rules = self.settings.get("relay_rules", [])
        self.settings["relay_rules"] = [r for r in rules if r.get("id") != rule_id]
        self._save_settings()
        self.relay_engine.load_rules(self.settings["relay_rules"])
        return {"status": "success"}

    def get_relay_log(self):
        """Get relay message log"""
        return self.data.get("relay_log", [])

    # ─── Budget Limits API ─────────────────────────────────

    def set_budget_limit(self, data):
        """Set a per-category budget limit"""
        category = data.get("category")
        limit = float(data.get("limit", 0))
        if category:
            budgets = self.settings.setdefault("budget_limits", {})
            if limit <= 0:
                budgets.pop(category, None)
            else:
                budgets[category] = limit
            self._save_settings()
            self._log_audit("Budget Limit Set", "MEDIUM", f"{category}: ${limit:,.2f}")
            return {"status": "success"}
        return {"status": "error", "message": "No category specified"}

    def get_budget_status(self):
        """Get current budget usage for all categories"""
        limits = self.settings.get("budget_limits", {})
        now = datetime.now()
        cat_totals = defaultdict(float)
        for tx in self.data.get("transactions", []):
            if tx.get("type") == "Expense":
                try:
                    dt = datetime.fromisoformat(tx.get("date", "").replace("Z", "+00:00"))
                    if dt.month == now.month and dt.year == now.year:
                        cat_totals[tx.get("category", "Other")] += float(tx.get("amount", 0))
                except:
                    pass

        status = {}
        for cat, limit in limits.items():
            spent = cat_totals.get(cat, 0)
            status[cat] = {
                "limit": limit, "spent": round(spent, 2),
                "remaining": round(max(0, limit - spent), 2),
                "percentage": round((spent / limit * 100) if limit > 0 else 0, 1),
                "exceeded": spent >= limit if limit > 0 else False
            }
        return status

    # ─── Account Management API ────────────────────────────

    def get_accounts(self):
        return self.settings.get("accounts", [])

    def add_account(self, data):
        accounts = self.settings.get("accounts", [])
        account = {
            "name": data.get("name", "New Account"),
            "type": data.get("type", "bank"),
            "icon": data.get("icon", "account_balance"),
            "balance": float(data.get("balance", 0))
        }
        accounts.append(account)
        self.settings["accounts"] = accounts
        self._save_settings()
        return {"status": "success", "account": account}

    def update_account(self, data):
        idx = data.get("index")
        accounts = self.settings.get("accounts", [])
        if idx is not None and 0 <= idx < len(accounts):
            for key in ["name", "type", "icon", "balance"]:
                if key in data:
                    accounts[idx][key] = data[key]
            self._save_settings()
            return {"status": "success"}
        return {"status": "error"}

    def delete_account(self, data):
        idx = data.get("index")
        accounts = self.settings.get("accounts", [])
        if idx is not None and 0 <= idx < len(accounts):
            accounts.pop(idx)
            self._save_settings()
            return {"status": "success"}
        return {"status": "error"}

    # ─── Export API ────────────────────────────────────────

    def export_data(self, data=None):
        """Export vault data (JSON or CSV)"""
        if not self.window:
            return {"status": "error", "message": "No window"}

        fmt = (data or {}).get("format", "json")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if fmt == "csv":
            filename = f'vault_export_{timestamp}.csv'
            result = self.window.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename)
            if result:
                try:
                    txs = self.data.get("transactions", [])
                    with open(result[0], 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Date", "Description", "Amount", "Type", "Category",
                                         "Merchant", "Bank", "Fee", "VAT", "Anomaly", "Ghost Fee"])
                        for tx in txs:
                            writer.writerow([
                                tx.get("date", ""), tx.get("description", ""),
                                tx.get("amount", 0), tx.get("type", ""),
                                tx.get("category", ""), tx.get("merchant", ""),
                                tx.get("bank", ""), tx.get("fee", 0),
                                tx.get("vat", 0), tx.get("is_anomaly", False),
                                tx.get("ghost_fee", False)
                            ])
                    self._log_audit("CSV Export", "HIGH", f"Exported to {result[0]}")
                    return {"status": "success", "message": f"CSV exported: {os.path.basename(result[0])}"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            return {"status": "cancelled"}
        else:
            filename = f'vault_export_{timestamp}.json'
            result = self.window.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename)
            if result:
                try:
                    with open(result[0], 'w', encoding='utf-8') as f:
                        json.dump({
                            "export_date": datetime.now().isoformat(),
                            "vault_version": "4.0 Production",
                            "data": self.data,
                            "settings": self.settings
                        }, f, indent=4)
                    self._log_audit("JSON Export", "HIGH", f"Exported to {result[0]}")
                    return {"status": "success", "message": f"Exported: {os.path.basename(result[0])}"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            return {"status": "cancelled"}

    def parse_ledger_file(self):
        """Enhanced ledger parser with semantic rules"""
        if not self.window:
            return {"status": "error", "message": "No window"}

        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=('Ledger Files (*.csv;*.xml;*.txt;*.json)', 'All Files (*.*)')
        )
        if not result:
            return {"status": "cancelled"}

        fp = result[0]
        filename = os.path.basename(fp)
        cnt = 0
        errors = []
        ghost_fees_detected = []

        try:
            if fp.endswith('.csv'):
                with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            amt_str = row.get('Amount', '0')
                            amt = float(amt_str.replace(',', ''))
                            tx = {
                                "id": len(self.data.get("transactions", [])) + 1,
                                "date": row.get('Date', datetime.now().isoformat()),
                                "description": row.get('Description', 'CSV Import'),
                                "amount": abs(amt),
                                "type": "Income" if amt > 0 else "Expense",
                                "category": row.get('Category', self.ai.categorize_transaction(row.get('Description', ''))),
                                "merchant": row.get('Merchant', ''),
                                "source": filename, "is_anomaly": False, "ghost_fee": False,
                                "fee": 0, "vat": 0
                            }
                            tx["is_anomaly"] = self._calculate_anomaly(tx)
                            self.data.setdefault("transactions", []).insert(0, tx)
                            cnt += 1
                        except Exception as e:
                            errors.append(str(e))

            elif fp.endswith('.xml'):
                try:
                    tree = ET.parse(fp)
                    root = tree.getroot()
                    transactions = root.findall('.//Transaction') or root.findall('.//transaction') or root.findall('.//*')
                    for n in transactions:
                        try:
                            amt_elem = n.find('Amount') or n.find('amount') or n.find('Value')
                            desc_elem = n.find('Description') or n.find('description') or n.find('Memo')
                            date_elem = n.find('Date') or n.find('date') or n.find('Timestamp')
                            a = float(amt_elem.text) if amt_elem is not None else 0
                            desc = desc_elem.text if desc_elem is not None else "XML Import"
                            date_str = date_elem.text if date_elem is not None else datetime.now().isoformat()
                            tx = {
                                "id": len(self.data.get("transactions", [])) + 1,
                                "date": date_str, "description": desc,
                                "amount": abs(a),
                                "type": "Income" if a > 0 else "Expense",
                                "category": self.ai.categorize_transaction(desc),
                                "source": filename, "is_anomaly": False, "ghost_fee": False,
                                "fee": 0, "vat": 0
                            }
                            tx["is_anomaly"] = self._calculate_anomaly(tx)
                            self.data.setdefault("transactions", []).insert(0, tx)
                            cnt += 1
                        except Exception as e:
                            errors.append(str(e))
                except ET.ParseError as e:
                    return {"status": "degraded", "message": f"XML parse failed: {e}"}

            elif fp.endswith('.txt') or fp.endswith('.sms'):
                with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    messages = re.split(r'\n\n+', content)
                    for msg in messages:
                        if not msg.strip():
                            continue
                        parsed = self._parse_sms_text(msg)
                        if parsed:
                            tx = {
                                "id": len(self.data.get("transactions", [])) + 1,
                                "date": parsed.get("date", datetime.now().isoformat()),
                                "description": parsed.get("description", msg[:80]),
                                "amount": parsed.get("amount", 0),
                                "type": parsed.get("type", "Expense"),
                                "category": parsed.get("category", "SMS Import"),
                                "merchant": parsed.get("merchant", ""),
                                "bank": parsed.get("bank", ""),
                                "balance_after": parsed.get("balance"),
                                "fee": parsed.get("fee", 0),
                                "vat": parsed.get("vat", 0),
                                "source": filename, "is_anomaly": False, "ghost_fee": False
                            }
                            if tx["fee"] > 0 or tx["vat"] > 0:
                                tx["ghost_fee"] = True
                                ghost_fees_detected.append({"amount": tx["fee"] + tx["vat"]})
                            tx["is_anomaly"] = self._calculate_anomaly(tx)
                            self.data.setdefault("transactions", []).insert(0, tx)
                            cnt += 1
            else:
                return {"status": "error", "message": "Unsupported format"}

            self._log_audit("Batch Import", "HIGH" if cnt > 0 else "LOW",
                            f"{cnt} from {filename}, {len(errors)} errors")
            self.save_data()
            return {
                "status": "success" if cnt > 0 else "warning",
                "message": f"Imported {cnt} transactions" + (f" ({len(errors)} errors)" if errors else ""),
                "count": cnt, "ghost_fees": len(ghost_fees_detected), "file": filename
            }

        except Exception as e:
            self._log_audit("Parser Failure", "FAIL", f"{filename}: {e}")
            return {"status": "degraded", "message": f"Import failed: {e}", "count": cnt}

    # ─── Auth API ──────────────────────────────────────────

    def check_password(self, pwd):
        if not self.data.get("has_setup_password"):
            return True
        return hashlib.sha256(pwd.encode('utf-8')).hexdigest() == self.data.get("password_hash")

    def setup_password(self, pwd):
        if len(pwd) < 4:
            return {"status": "error", "message": "Min 4 characters"}
        self.data["password_hash"] = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
        self.data["has_setup_password"] = True
        self._log_audit("Password Updated", "HIGH", "Master password hash rotated")
        self.save_data()
        return {"status": "success", "message": "Password set"}

    def check_auth_status(self):
        return {
            "has_password": self.data.get("has_setup_password", False),
            "theme": self.data.get("theme", "light"),
            "biometrics": self.data.get("biometrics", True)
        }

    # ─── Analytics API ─────────────────────────────────────

    def get_analytics(self):
        return {
            "subscriptions": self.data.get("subscriptions", []),
            "velocity": self.data.get("spending_velocity", {}),
            "runway_days": self.data.get("runway_days", 0),
            "runway_formatted": self.data.get("runway_formatted", "--"),
            "ghost_fees": self.data.get("ghost_fees", []),
            "monthly_totals": self.data.get("monthly_totals", {}),
            "category_breakdown": self.data.get("category_breakdown", {}),
            "apex_series": self.data.get("apex_series", {}),
            "flow_ratios": self.data.get("flow_ratios", {}),
            "alerts": self.data.get("alerts", [])
        }

    def get_ai_status(self):
        """Get AI service status for frontend display"""
        return self.ai.check_availability()

    # ─── Window Control API ────────────────────────────────

    def minimize_window(self):
        if self.window:
            self.window.minimize()

    def maximize_window(self):
        if self.window:
            self.window.toggle_fullscreen()

    def close_window(self):
        if self.window:
            self.window.destroy()


# ═══════════════════════════════════════════════════════════════════
# § SMS RECEIVER — FastAPI Background Server
# ═══════════════════════════════════════════════════════════════════

def create_sms_server(vault_api: VaultPro, port: int = 8765):
    """Create and run FastAPI SMS receiver in background thread"""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn

        app = FastAPI(title="Vault SMS Receiver", version="1.0")
        app.add_middleware(CORSMiddleware, allow_origins=["*"],
                          allow_methods=["*"], allow_headers=["*"])

        @app.post("/api/sms")
        async def receive_sms(payload: dict):
            """Receive SMS from mobile app P2P sync"""
            return vault_api.receive_sms(payload)

        @app.post("/api/sms/batch")
        async def receive_batch(payload: dict):
            """Receive batch of SMS messages"""
            messages = payload.get("messages", [])
            results = []
            for msg in messages:
                results.append(vault_api.receive_sms(msg))
            return {"status": "success", "count": len(results), "results": results}

        @app.get("/api/health")
        async def health():
            return {"status": "ok", "version": "4.0", "timestamp": datetime.now().isoformat()}

        @app.get("/api/relay/pending")
        async def get_pending_relays():
            """Mobile app pulls pending relay messages for delivery"""
            log = vault_api.get_relay_log()
            pending = [r for r in log if r.get("status") == "queued"]
            return {"pending": pending}

        @app.post("/api/relay/delivered")
        async def mark_delivered(payload: dict):
            """Mobile app confirms relay delivery"""
            relay_id = payload.get("relay_id")
            for entry in vault_api.data.get("relay_log", []):
                if entry.get("id") == relay_id:
                    entry["status"] = "delivered"
                    entry["delivered_at"] = datetime.now().isoformat()
                    vault_api.save_data()
                    return {"status": "success"}
            return {"status": "error"}

        def run():
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

        thread = threading.Thread(target=run, daemon=True, name="SMS-Receiver")
        thread.start()
        vault_api._log_audit("SMS Server Started", "HIGH", f"Listening on port {port}")
        return thread

    except ImportError:
        logging.warning("FastAPI/uvicorn not installed. SMS receiver disabled.")
        vault_api._log_audit("SMS Server Skipped", "LOW", "FastAPI not installed")
        return None


# ═══════════════════════════════════════════════════════════════════
# § HTML CONTENT — Complete SPA Frontend
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# § APPLICATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    api = VaultPro()

    # Start SMS receiver in background
    sms_port = api.settings.get("sms_port", 8765)
    if api.settings.get("sms_listener_enabled", True):
        api.sms_server_thread = create_sms_server(api, port=sms_port)

    window = webview.create_window(
        'Vault Analytics v4.0',
        url='index.html',
        js_api=api,
        width=1440, height=900,
        min_size=(1280, 800),
        frameless=True, easy_drag=False
    )
    api.set_window(window)
    webview.start()
