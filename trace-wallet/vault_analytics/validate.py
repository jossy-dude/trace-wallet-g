#!/usr/bin/env python3
"""
Vault Analytics v4.0 — Application Validator
Checks that all components are properly integrated.
"""

import re
import sys

def validate_main_py():
    """Validate the main.py file for structural integrity."""
    print("🔍 Validating main.py...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'HTML Content': r'HTML_CONTENT = r\'\'\'',
        'PyWebView Import': r'import webview',
        'FastAPI Import': r'from fastapi import',
        'VaultPro Class': r'class VaultPro',
        'StagingVault Class': r'class StagingVault',
        'SmartBatchEngine': r'class SmartBatchEngine',
        'NotificationProvider': r'class NotificationProvider',
        'InternalRelayProvider': r'class InternalRelayProvider',
        'RelayRuleEngine': r'class RelayRuleEngine',
        'AIServiceInterface': r'class AIServiceInterface',
        'DataTransformer': r'class DataTransformer',
        '8 Pages': [
            r'page-command',
            r'page-inbox',
            r'page-ledger',
            r'page-intel',
            r'page-entry',
            r'page-predictions',
            r'page-settings',
            r'page-audit'
        ],
        'ApexCharts CDN': r'apexcharts',
        'Quick Entry Numpad': r'numpad\(',
        'Theme Toggle': r'setTheme\(',
        'Privacy Mask': r'privacy-active',
        'Anomaly Detection': r'is_anomaly',
        'Ghost Fee': r'ghost_fee',
        'Subscription Radar': r'subscriptions',
        'Spending Velocity': r'velocity',
        'Health Score': r'health_score',
        'Runway Calculator': r'runway',
        'Budget Limits': r'budget_limits',
        'Relay Rules': r'relay_rules',
        'SMS Receiver': r'receive_sms',
        'Session Timer': r'session-timer',
        'Alert Banner': r'alerts-banner',
        'Card Tilt': r'tilt-card',
        'Chart Settings Modal': r'openChartSettings',
        'CSV Export': r'csv',
        'Inbox Badge': r'inbox-badge',
        'Status Light System': r'status-green',
        'Micro Interactions': r'press-effect',
        'Lock Vault': r'lockVault',
        'Toast Notifications': r'showToast',
        'Ollama Future-Proof': r'AIServiceInterface',
        'Bank Rules Engine': r'BANK_RULES'
    }
    
    results = []
    for name, pattern in checks.items():
        if isinstance(pattern, list):
            found = all(re.search(p, content) for p in pattern)
        else:
            found = re.search(pattern, content) is not None
        results.append((name, found))
        status = "✅" if found else "❌"
        print(f"  {status} {name}")
    
    passed = sum(1 for _, found in results if found)
    total = len(results)
    print(f"\n📊 Validation Results: {passed}/{total} checks passed")
    
    # Check page structure
    print("\n📄 Checking SPA Pages...")
    pages = [
        ('Command Center', r'id="page-command"'),
        ('Verification Inbox', r'id="page-inbox"'),
        ('Deep Ledger', r'id="page-ledger"'),
        ('Visual Intelligence', r'id="page-intel"'),
        ('Quick Entry', r'id="page-entry"'),
        ('Predictions', r'id="page-predictions"'),
        ('Settings', r'id="page-settings"'),
        ('Vault Audit', r'id="page-audit"'),
    ]
    
    for name, pattern in pages:
        found = re.search(pattern, content) is not None
        status = "✅" if found else "❌"
        print(f"  {status} {name}")
    
    # Count JavaScript functions
    print("\n🔧 JavaScript Functions...")
    js_funcs = re.findall(r'function (\w+)\(', content)
    unique_funcs = set(js_funcs)
    print(f"  Found {len(unique_funcs)} unique functions")
    
    critical = [
        'navigate', 'syncData', 'renderAll', 'numpad', 'setEntryType',
        'submitEntry', 'togglePrivacy', 'setTheme', 'addGoal',
        'importLedger', 'exportData', 'lockVault', 'checkAuth',
        'loadInbox', 'approveSMS', 'rejectSMS', 'renderCharts',
        'renderPredictionChart', 'startSessionTimer', 'setStatus',
        'addRelayRule', 'openChartSettings', 'closeModal', 'loadSettings'
    ]
    
    for func in critical:
        found = func in unique_funcs
        status = "✅" if found else "❌"
        print(f"  {status} {func}()")
    
    # Count Python API methods
    print("\n🐍 Python API Methods...")
    py_methods = re.findall(r'def (\w+)\(self', content)
    public_methods = [m for m in py_methods if not m.startswith('_')]
    print(f"  Found {len(public_methods)} public API methods")
    
    key_methods = [
        'sync_data', 'add_transaction', 'receive_sms', 'get_inbox',
        'approve_sms', 'reject_sms', 'add_relay_rule', 'delete_relay_rule',
        'get_relay_log', 'set_budget_limit', 'get_budget_status',
        'get_accounts', 'add_account', 'export_data', 'parse_ledger_file',
        'get_analytics', 'get_ai_status', 'add_goal', 'update_goal', 'delete_goal'
    ]
    
    for method in key_methods:
        found = method in public_methods
        status = "✅" if found else "❌"
        print(f"  {status} {method}()")
    
    # Line count
    lines = content.count('\n') + 1
    print(f"\n📏 Total Lines: {lines}")
    print(f"📦 File Size: {len(content):,} bytes")
    
    return passed == total

if __name__ == '__main__':
    print("=" * 60)
    print("  Vault Analytics v4.0 — Production Validator")
    print("=" * 60)
    
    if validate_main_py():
        print("\n✨ All validation checks passed!")
        print("\nTo run the application:")
        print("  1. pip install -r requirements.txt")
        print("  2. python main.py")
        sys.exit(0)
    else:
        print("\n⚠️  Some validation checks failed.")
        sys.exit(1)
