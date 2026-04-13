import json
import os
import csv
import io
import re
import math
import time
import asyncio
import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
import webview

from vault.config import DATA_FILE, CONFIG_FILE, DEFAULT_SETTINGS, DEFAULT_DATA, BANK_RULES, _merge_defaults
from vault.pipeline.staging import StagingVault
from vault.pipeline.batch import SmartBatchEngine
from vault.pipeline.relay import NotificationRouter, RelayRuleEngine, InternalRelayProvider, TelegramProvider, EmailProvider
from vault.core.transformer import DataTransformer
from vault.ai.ollama import AIServiceInterface

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
        import uuid
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.settings = json.load(f)
                self.settings = _merge_defaults(self.settings, dict(DEFAULT_SETTINGS))
                
                # Ensure SMS P2P Token exists
                if not self.settings.get("sms_token"):
                    self.settings["sms_token"] = str(uuid.uuid4())
                    
                # Strip shipped demo accounts on upgrade so the app opens clean.
                demo_accounts = [
                    {"name": "Checking", "type": "bank", "icon": "account_balance", "balance": 0},
                    {"name": "Savings", "type": "bank", "icon": "savings", "balance": 0},
                    {"name": "Cash", "type": "cash", "icon": "payments", "balance": 0}
                ]
                if self.settings.get("accounts") == demo_accounts:
                    self.settings["accounts"] = []
            except Exception:
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
            raise Exception(f"Failed to update settings: {str(e)}")

    def get_p2p_config(self):
        """Returns P2P pairing configuration for the frontend QR generator"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except:
            ip = "127.0.0.1"

        use_https = self.settings.get("sms_use_https", False)
        return {
            "ip": ip,
            "port": self.settings.get("sms_port", 8765),
            "token": self.settings.get("sms_token", ""),
            "protocol": "https" if use_https else "http"
        }

    # ─── Data Access & Export ─────────────────────────────────

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
        try:
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
            
            # Month-over-Month Comparison
            txs = self.data.get("transactions", [])
            now = datetime.now()
            this_month_val = sum(t.get("amount", 0) for t in txs if datetime.fromisoformat(t.get("date")).month == now.month)
            last_month = (now.month - 1) if now.month > 1 else 12
            last_month_val = sum(t.get("amount", 0) for t in txs if datetime.fromisoformat(t.get("date")).month == last_month)
            self.data["mom_change"] = ((this_month_val - last_month_val) / last_month_val * 100) if last_month_val > 0 else 0
            
            # Flow Ratio calculation (real-time Income vs Expense)
            self.data["flow_ratio"] = f"{round(ratio, 2)}:1"
    
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
            if hasattr(self, 'staging'):
                self.data["staging_stats"] = self.staging.get_stats()
            elif hasattr(self, 'batch_engine'):
                self.data["staging_stats"] = self.batch_engine.get_stats()
    
            self._log_audit("Vault Sync", "HIGH", "Full analytics refresh completed")
            self.save_data()
            return self.data
            
        except Exception as e:
            logging.error(f"SYNC FATAL EXCEPTION: {e}")
            return {"status": "degraded", "message": f"Engine failed: {str(e)}"}

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

    def test_ollama_connection(self, data):
        """Test connection to a local Ollama instance via the vault.ai.ollama provider."""
        url = data.get("url", "http://localhost:11434")
        model = data.get("model", "llama3.2:1b")
        
        self.ai.endpoint = url
        self.ai.model = model
        
        if self.ai.check_connection():
            self._log_audit("Ollama Connected", "HIGH", f"Model {model} via {url}")
            return {"status": "ok", "message": "Connection verified"}
        else:
            self._log_audit("Ollama Connection Refused", "LOW", f"Failed at {url}")
            return {"status": "error", "message": "Connection refused"}

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

    def update_transaction(self, data):
        """Update an existing transaction and accurately adjust net worth."""
        tx_id = data.get("id")
        transactions = self.data.get("transactions", [])
        tx_index = next((i for i, t in enumerate(transactions) if t["id"] == tx_id), None)

        if tx_index is None:
            return {"status": "error", "message": "Transaction not found"}

        old_tx = transactions[tx_index]
        new_amount = float(data.get("amount", old_tx["amount"]))
        new_type = data.get("type", old_tx["type"])

        # Revert old impact
        if old_tx["type"] == "Income":
            self.data["net_worth"] -= old_tx["amount"]
        elif old_tx["type"] == "Expense":
            self.data["net_worth"] += old_tx["amount"]

        # Apply new variables
        old_tx.update({
            "amount": new_amount,
            "type": new_type,
            "category": data.get("category", old_tx["category"]),
            "merchant": data.get("merchant", old_tx.get("merchant", "")),
            "description": data.get("description", old_tx.get("description", "")),
            "date": data.get("date", old_tx["date"])
        })
        
        # Recalculate anomaly and ghost fee with new text/amount
        desc_lower = old_tx["description"].lower()
        old_tx["ghost_fee"] = old_tx["amount"] < 100 and any(term in desc_lower for term in ["fee", "charge", "vat", "tax", "service"])
        old_tx["is_anomaly"] = self._calculate_anomaly(old_tx)

        # Apply new impact
        if new_type == "Income":
            self.data["net_worth"] += new_amount
        elif new_type == "Expense":
            self.data["net_worth"] -= new_amount

        self.save_data()
        self._log_audit("Transaction Updated", "HIGH", f"Updated TX ID {tx_id}")
        return {"status": "success", "message": "Transaction updated successfully"}

    def delete_transaction(self, data):
        """Delete a transaction and restore balance impact."""
        tx_id = data.get("id")
        transactions = self.data.get("transactions", [])
        tx_index = next((i for i, t in enumerate(transactions) if t["id"] == tx_id), None)

        if tx_index is None:
            return {"status": "error", "message": "Transaction not found"}

        old_tx = transactions.pop(tx_index)
        if old_tx["type"] == "Income":
            self.data["net_worth"] -= old_tx["amount"]
        elif old_tx["type"] == "Expense":
            self.data["net_worth"] += old_tx["amount"]

        self.save_data()
        self._log_audit("Transaction Deleted", "HIGH", f"Deleted TX ID {tx_id}")
        return {"status": "success", "message": "Transaction permanently deleted"}

    def create_custom_category(self, data):
        """Creates a custom category for the UI."""
        cat_type = data.get("type", "expense") # expense | income | transfer
        name = data.get("name", "New").strip()
        icon = data.get("icon", "category")
        color = data.get("color", "bg-surface-container text-on-surface-variant")
        
        if "custom_categories" not in self.settings:
            self.settings["custom_categories"] = {"expense": [], "income": [], "transfer": []}
            
        # Ensure array exists for type
        if cat_type not in self.settings["custom_categories"]:
            self.settings["custom_categories"][cat_type] = []
            
        self.settings["custom_categories"][cat_type].append({
            "name": name,
            "icon": icon,
            "color": color
        })
        self._save_settings()
        self._log_audit("Category Created", "MEDIUM", f"{name} ({cat_type})")
        return {"status": "success", "message": f"Category {name} created"}

    def get_p2p_status(self):
        """Syncthing-inspired P2P status report"""
        return {
            "enabled": self.settings.get("sms_listener_enabled", True),
            "port": self.settings.get("sms_port", 8765),
            "paired_devices_count": len(self.settings.get("paired_devices", [])),
            "discovery_active": True,
            "relay_active": self.settings.get("p2p_relay_enabled", True),
            "local_id": self.settings.get("device_id")
        }

    def update_p2p_settings(self, data):
        """Update P2P listener configuration"""
        if "sms_listener_enabled" in data:
            self.settings["sms_listener_enabled"] = data["sms_listener_enabled"]
        if "sms_port" in data:
            self.settings["sms_port"] = data["sms_port"]
        if "p2p_relay_enabled" in data:
            self.settings["p2p_relay_enabled"] = data["p2p_relay_enabled"]
            
        self._save_settings()
        return {"status": "success"}
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

    def get_p2p_config(self):
        """Get local device info for P2P pairing"""
        return {
            "device_id": self.settings.get("device_id"),
            "device_name": self.settings.get("device_name"),
            "paired_count": len(self.settings.get("paired_devices", [])),
            "p2p_enabled": self.settings.get("p2p_enabled", True)
        }

    def pair_device(self, data):
        """Add a new P2P device by ID"""
        device_id = data.get("device_id")
        name = data.get("name", "Unknown Device")
        if not device_id: return {"status": "error", "message": "Missing Device ID"}
        
        devices = self.settings.get("paired_devices", [])
        if any(d["id"] == device_id for d in devices):
            return {"status": "error", "message": "Device already paired"}
            
        devices.append({
            "id": device_id,
            "name": name,
            "added_at": datetime.now().isoformat(),
            "last_sync": None,
            "status": "trusted"
        })
        self.settings["paired_devices"] = devices
        self._save_settings()
        return {"status": "success", "message": f"Device {name} paired successfully"}

    def get_paired_devices(self):
        """Return list of trusted devices"""
        return self.settings.get("paired_devices", [])

    def sync_p2p(self, data):
        """Incoming sync request from another device (Syncthing-inspired)"""
        remote_id = data.get("device_id")
        remote_hash = data.get("data_hash")
        remote_data = data.get("payload", {})
        
        # Verify device is trusted
        devices = self.settings.get("paired_devices", [])
        device = next((d for d in devices if d["id"] == remote_id), None)
        if not device:
            return {"status": "untrusted", "message": "Device not paired. Authorization required."}
            
        # Delta Check: If hashes match, no update needed
        local_hash = hashlib.sha256(json.dumps(self.data, sort_keys=True).encode()).hexdigest()
        if remote_hash == local_hash:
            return {"status": "in_sync", "message": "Data already up to date"}
            
        # Conflict Resolution: Simple 'Last Writer Wins' for now, with audit logging
        if remote_data:
            logging.info(f"P2P: Incoming sync from {device['name']} ({remote_id})")
            # Update local data with remote payload
            for key in self.settings.get("sync_folders", []):
                if key in remote_data:
                    # Merge logic (avoid duplicates)
                    if isinstance(self.data.get(key), list):
                        existing_ids = {item.get("id") for item in self.data[key] if "id" in item}
                        for item in remote_data[key]:
                            if item.get("id") not in existing_ids:
                                self.data[key].append(item)
                    else:
                        self.data[key] = remote_data[key]
            
            # Update device last sync timestamp
            device["last_sync"] = datetime.now().isoformat()
            self._save_settings()
            self.save_data()
            self._log_audit("P2P Sync", "HIGH", f"Synchronized with {device['name']}")
            return {"status": "success", "hash": hashlib.sha256(json.dumps(self.data, sort_keys=True).encode()).hexdigest()}
            
        return {"status": "error", "message": "Malformed sync payload"}

    def search_transactions(self, data):
        """Advanced multi-parameter search and filter"""
        query = data.get("query", "").lower()
        cat = data.get("category")
        bank = data.get("bank")
        tx_type = data.get("type")
        is_anomaly = data.get("is_anomaly")
        is_ghost = data.get("is_ghost")
        
        txs = self.data.get("transactions", [])
        results = []
        
        for tx in txs:
            # Type Filter
            if tx_type and tx.get("type") != tx_type: continue
            # Category Filter
            if cat and tx.get("category") != cat: continue
            # Bank Filter
            if bank and tx.get("bank") != bank: continue
            # Anomaly Filter
            if is_anomaly is not None and tx.get("is_anomaly") != is_anomaly: continue
            # Ghost Filter
            if is_ghost is not None and tx.get("ghost_fee") != is_ghost: continue
            
            # Query Filter (Description or Merchant)
            if query:
                desc = tx.get("description", "").lower()
                merc = tx.get("merchant", "").lower()
                if query not in desc and query not in merc:
                    continue
            
            results.append(tx)
            
        return results

    def get_audit_stats(self):
        """Return audit summary for the UI"""
        log = self.data.get("audit_log", [])
        high = len([l for l in log if l.get("confidence") == "HIGH"])
        low = len([l for l in log if l.get("confidence") in ["LOW", "FAIL"]])
        
        last_sync = "Never"
        sync_events = [l for l in log if l.get("event") == "Vault Sync"]
        if sync_events:
            last_sync = sync_events[0].get("timestamp")
            
        return {
            "total": len(log),
            "high": high,
            "low": low,
            "last_sync": last_sync
        }

    def update_profile(self, data):
        """Update user profile info"""
        self.settings["profile_name"] = data.get("name", "Vault User")
        self._save_settings()
        return {"status": "success"}

    def get_profile_data(self):
        """Get profile and session stats"""
        txs = self.data.get("transactions", [])
        start = datetime.fromisoformat(self.session_start)
        now = datetime.now()
        duration = str(now - start).split('.')[0]
        
        # Calculate days active (unique dates in transactions)
        unique_dates = {tx.get("date", "")[:10] for tx in txs if tx.get("date")}
        
        return {
            "name": self.settings.get("profile_name", "Vault User"),
            "tx_count": len(txs),
            "days_active": len(unique_dates),
            "health": self.data.get("health_score", "--"),
            "session_duration": duration
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
        # Batch processing: wait for debounce and run all in one smooth cycle
        logging.info(f"Batch Processing {len(items)} SMS entries...")
        for item in items:
            entry_id = item.get("id")
            if entry_id:
                # Optimized: Directly access staging to mark parsed
                entry = next((e for e in self.staging.entries if e["id"] == entry_id), None)
                if entry:
                    parsed = self._parse_sms_text(entry["body"], entry.get("metadata"))
                    if parsed:
                        self.staging.mark_parsed(entry_id, parsed)
        self._log_audit("Batch Processed", "HIGH", f"{len(items)} SMS entries parsed in smooth cycle")

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

    # ─── P2P / Paired Devices API ────────────────────────────

    def get_paired_devices(self):
        """Get list of paired/connected devices"""
        devices = self.data.get("paired_devices", [])
        # Sort by last seen, most recent first
        devices.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
        return {"devices": devices, "count": len(devices)}

    def remove_paired_device(self, data):
        """Remove a paired device by ID"""
        device_id = data.get("id")
        devices = self.data.get("paired_devices", [])
        original_count = len(devices)
        self.data["paired_devices"] = [d for d in devices if d.get("id") != device_id]
        if len(self.data["paired_devices"]) < original_count:
            self.save_data()
            self._log_audit("Device Removed", "MEDIUM", f"Removed paired device {device_id}")
            return {"status": "success"}
        return {"status": "error", "message": "Device not found"}

    def regenerate_p2p_token(self):
        """Generate a new P2P pairing token"""
        import uuid
        new_token = str(uuid.uuid4())
        self.settings["sms_token"] = new_token
        self._save_settings()
        self._log_audit("P2P Token Regenerated", "HIGH", "New pairing token generated")
        return {"status": "success", "token": new_token}

    def get_p2p_status(self):
        """Get current P2P server status"""
        return {
            "enabled": self.settings.get("sms_listener_enabled", True),
            "port": self.settings.get("sms_port", 8765),
            "use_https": self.settings.get("sms_use_https", False),
            "token_prefix": self.settings.get("sms_token", "")[:8] + "...",
            "paired_devices_count": len(self.data.get("paired_devices", []))
        }

    def update_p2p_settings(self, data):
        """Update P2P server settings"""
        if "sms_port" in data:
            self.settings["sms_port"] = int(data["sms_port"])
        if "sms_use_https" in data:
            self.settings["sms_use_https"] = bool(data["sms_use_https"])
        if "sms_listener_enabled" in data:
            self.settings["sms_listener_enabled"] = bool(data["sms_listener_enabled"])
        self._save_settings()
        self._log_audit("P2P Settings Updated", "HIGH", "SMS server settings changed")
        return {"status": "success"}

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
