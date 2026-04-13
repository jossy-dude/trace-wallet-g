import os
import re

def slice_file(src, dest, imports, start_line, end_line):
    with open(src, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(imports + '\n\n')
        f.writelines(lines[start_line-1:end_line])

os.makedirs('vault/core', exist_ok=True)
os.makedirs('vault/pipeline', exist_ok=True)
os.makedirs('vault/ai', exist_ok=True)

# 1. vault/config.py (Imports + Lines ~1 to 215)
slice_file('main.py', 'vault/config.py', 
'''import hashlib
import os
import json
import logging
from datetime import datetime, timedelta
''', 60, 215)

# 2. vault/pipeline/staging.py (StagingVault 221-344)
slice_file('main.py', 'vault/pipeline/staging.py',
'''import json
import os
import hashlib
import threading
import logging
from datetime import datetime
from vault.config import STAGING_FILE
''', 221, 344)

# 3. vault/pipeline/batch.py (SmartBatchEngine 350-400)
slice_file('main.py', 'vault/pipeline/batch.py',
'''import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict
''', 350, 400)

# 4. vault/pipeline/relay.py (Providers & Router & Engine 406-563)
slice_file('main.py', 'vault/pipeline/relay.py',
'''import logging
import threading
from typing import Dict, List, Any
from datetime import datetime
''', 406, 563)

# 5. vault/core/transformer.py (DataTransformer 646-729)
slice_file('main.py', 'vault/core/transformer.py',
'''import re
import logging
from datetime import datetime
''', 646, 729)

# 6. vault/ai/ollama.py (AIServiceInterface 569-640)
# We will inject the new Ollama request logic here directly!
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_ai = '''import logging
import asyncio
import requests
from typing import Optional

class AIServiceInterface:
    def __init__(self, endpoint="http://localhost:11434", model="llama3.2:1b"):
        self.endpoint = endpoint
        self.model = model
        self.enabled = True
        self.is_connected = False

    def check_connection(self) -> bool:
        """Ping Ollama API to ensure it is alive."""
        try:
            r = requests.get(f"{self.endpoint}/api/tags", timeout=2)
            self.is_connected = r.status_code == 200
            if self.is_connected:
                # Ensure model exists in local library
                models = [m.get('name') for m in r.json().get('models', [])]
                if self.model not in models and f"{self.model}:latest" not in models:
                    logging.warning(f"Ollama connected, but model {self.model} not pulled locally.")
            return self.is_connected
        except Exception:
            self.is_connected = False
            return False

    def categorize_transaction(self, description: str, merchant: str, amount: float) -> str:
        """Prompt Ollama to autonomously categorize unknown transactions."""
        if not self.enabled or not self.is_connected:
            return "General"
            
        prompt = f"Categorize this transaction. Merchant: {merchant}, Description: {description}, Amount: {amount}. Respond ONLY with a single word fitting these categories: Shopping, Housing, Bills, Transport, Phone, Internet, Health, Dining, Education, Entertainment, Transfer, Income, General."
        
        try:
            r = requests.post(f"{self.endpoint}/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 10}
            }, timeout=5)
            
            if r.status_code == 200:
                response = r.json().get("response", "General").strip()
                # Clean up response to ensure single string
                return response.split()[0].capitalize()
        except Exception as e:
            logging.error(f"Ollama categorization failed: {e}")
            
        return "General"
        
    def detect_anomalies(self, transaction: dict, history: list) -> float:
        """0.0 to 1.0 confidence that transaction is an anomaly."""
        return 0.0
'''

with open('vault/ai/ollama.py', 'w', encoding='utf-8') as f:
    f.write(new_ai)

# 7. vault/ui/api.py (VaultPro)
with open('vault/ui/api.py', 'w', encoding='utf-8') as f:
    f.write('''import json
import os
import csv
import io
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
import webview

from vault.config import DATA_FILE, CONFIG_FILE, DEFAULT_SETTINGS, DEFAULT_DATA, BANK_RULES, _merge_defaults
from vault.pipeline.staging import StagingVault
from vault.pipeline.batch import SmartBatchEngine
from vault.pipeline.relay import NotificationRouter, RelayRuleEngine
from vault.core.transformer import DataTransformer
from vault.ai.ollama import AIServiceInterface

''')
    f.writelines(lines[734:2036])

# 8. vault/pipeline/sms_server.py
with open('vault/pipeline/sms_server.py', 'w', encoding='utf-8') as f:
    f.write('''import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from vault.ui.api import VaultPro

''')
    f.writelines(lines[2042:2102])

# Write new main.py launcher
with open('main_new.py', 'w', encoding='utf-8') as f:
    f.write('''import threading
import webview
import logging

from vault.ui.api import VaultPro
from vault.pipeline.sms_server import create_sms_server

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

if __name__ == '__main__':
    # Initialize Core Application Logic
    api = VaultPro()
    
    # Extract config port safely
    port = getattr(api, 'settings', {}).get('sms_port', 8765)
    
    # Start SMS Fast API listener in background thread
    server = create_sms_server(api)
    def run_server():
        import uvicorn
        uvicorn.run(server, host="0.0.0.0", port=port, log_level="error")
        
    threading.Thread(target=run_server, daemon=True).start()
    logging.info(f"SMS Sync Listener active on port {port}")
    
    # Boot the UI
    window = webview.create_window(
        title='Vault Analytics v4.0', 
        url='index.html',
        js_api=api,
        width=1400, 
        height=900,
        frameless=True,
        transparent=True,
        easy_drag=False
    )
    
    webview.start()
''')

print("Extraction script prepared successfully.")
