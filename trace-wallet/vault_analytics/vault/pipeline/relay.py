import logging
import threading
from typing import Dict, List, Any
from datetime import datetime


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

        # If/Then logic for Category Overrides (Power-User Tool)
        if "if_desc_contains" in conditions:
            if conditions["if_desc_contains"].lower() in tx.get("description", "").lower():
                if "then_category" in conditions:
                    tx["category"] = conditions["then_category"]
                    return True # Trigger relay if matched

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
