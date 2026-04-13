import logging
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
                models = [m.get('name') for m in r.json().get('models', [])]
                if self.model not in models and f"{self.model}:latest" not in models:
                    logging.warning(f"Ollama connected, but model {self.model} not pulled locally.")
            return self.is_connected
        except Exception:
            self.is_connected = False
            return False

    def check_availability(self) -> dict:
        """Report AI service status for frontend display."""
        connected = self.check_connection()
        return {
            "available": connected,
            "model": self.model,
            "endpoint": self.endpoint,
            "status": "online" if connected else "offline"
        }

    def generate_insight(self, data: dict) -> str:
        """Generate a short AI insight summary from vault data."""
        if not self.enabled or not self.is_connected:
            nw = data.get("net_worth", 0)
            sr = data.get("savings_rate", 0)
            txs = len(data.get("transactions", []))
            if txs == 0:
                return "Add your first transaction to unlock AI-powered insights."
            if sr > 20:
                return f"Strong savings rate at {sr}%. Your financial discipline is paying off."
            elif sr > 0:
                return f"Moderate savings at {sr}%. Consider reviewing discretionary spending."
            else:
                return "Spending exceeds income. Review your budget limits and subscriptions."

        prompt = f"""Analyze this financial snapshot and give ONE short insight (max 20 words):
Net Worth: ${data.get('net_worth', 0):,.2f}
Monthly Income: ${data.get('monthly_income', 0):,.2f}
Monthly Burn: ${data.get('monthly_burn', 0):,.2f}
Savings Rate: {data.get('savings_rate', 0)}%
Health Score: {data.get('health_score', 0)}/100
Transactions: {len(data.get('transactions', []))}"""

        try:
            r = requests.post(f"{self.endpoint}/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 40}
            }, timeout=8)
            if r.status_code == 200:
                return r.json().get("response", "Analysis complete.").strip()[:120]
        except Exception as e:
            logging.error(f"Ollama insight generation failed: {e}")
        return "AI engine offline. Using rule-based analysis."

    def categorize_transaction(self, description: str, merchant: str = "", amount: float = 0.0) -> str:
        """Prompt Ollama to autonomously categorize unknown transactions.
        
        Accepts flexible arguments: can be called with just description text
        (e.g. from SMS parsing) or with all three parameters.
        """
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
                return response.split()[0].capitalize()
        except Exception as e:
            logging.error(f"Ollama categorization failed: {e}")
            
        return "General"
        
    def detect_anomalies(self, transaction: dict, history: list) -> float:
        """0.0 to 1.0 confidence that transaction is an anomaly."""
        return 0.0

