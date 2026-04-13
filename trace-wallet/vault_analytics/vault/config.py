import hashlib
import os
import sys
import json
import logging
from datetime import datetime, timedelta


def _app_data_dir() -> str:
    """
    Directory for vault JSON files. PyInstaller builds use a real user data path;
    development uses the vault_analytics folder (parent of the vault package).
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
        elif sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
        else:
            base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
        d = os.path.join(base, "TraceWallet", "VaultAnalytics")
        os.makedirs(d, exist_ok=True)
        return d
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


_DATA = _app_data_dir()
DATA_FILE = os.path.join(_DATA, "vault_data.json")
CONFIG_FILE = os.path.join(_DATA, "vault_config.json")
STAGING_FILE = os.path.join(_DATA, "staging_vault.json")

DEFAULT_SETTINGS = {
    "onboarding_completed": False,
    "sms_port": 8765,
    "sms_debounce_seconds": 60,
    "sms_instant_mode": False,
    "sms_listener_enabled": True,
    "sms_use_https": False,
    "ssl_cert_path": "",
    "ssl_key_path": "",
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
    "category_icons": {},
    "device_id": hashlib.sha256(os.urandom(32)).hexdigest()[:16].upper(),
    "device_name": os.environ.get("COMPUTERNAME", "Vault-Desktop"),
    "paired_devices": [],
    "sync_folders": ["transactions", "goals", "audit_log"],
    "p2p_enabled": True,
    "p2p_relay_enabled": True
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
            "amount": [
                r'debited with etb\s*([\d,.]+)',
                r'credited with etb\s*([\d,.]+)',
                r'etb\s*([\d,.]+)', 
                r'birr\s*([\d,.]+)'
            ],
            "balance": [r'balance.*?etb\s*([\d,.]+)', r'bal\s*([\d,.]+)'],
            "fee": [r'fee.*?etb\s*([\d,.]+)', r's\.charge\s*([\d,.]+)'],
            "vat": [r'vat.*?etb\s*([\d,.]+)'],
            "merchant": [r'(?:to|from)\s+([a-zA-Z\s.\-]+?)(?:\s+on|,|\s+at)'],
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
