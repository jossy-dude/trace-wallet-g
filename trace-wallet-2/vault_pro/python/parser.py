"""
Regex Parser Service - Ported from Dart to Python
Handles parsing of bank SMS messages
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class ParseResult:
    bank: Optional[str]
    amount: Optional[float]
    balance: Optional[float]
    fee: Optional[float]
    entity_name: Optional[str]
    is_valid: bool

class SemanticBankRules:
    """Bank-specific parsing rules"""
    
    CBE = {
        'display': 'CBE',
        'amt_logic': [
            r'debited with etb\s*([\d,.]+)',
            r'transfer(?:r)?ed etb\s*([\d,.]+)',
            r'credited with etb\s*([\d,.]+)'
        ],
        'bal_logic': [r'current balance is etb\s*([\d,.]+)'],
        'fee_logic': [
            r's\.charge of etb\s*([\d,.]+)', 
            r'service charge of etb\s*([\d,.]+)'
        ],
        'vat_logic': [r'vat.*?of etb\s*([\d,.]+)'],
        'name_logic': [
            r'(?:to|from)\s+([a-zA-Z\s.\-]+?)(?:\s+on|,|\s+at)'
        ],
    }

    TELEBIRR = {
        'display': 'Telebirr',
        'amt_logic': [
            r'paid etb\s*([\d,.]+)',
            r'withdrawn? etb\s*([\d,.]+)',
            r'transferred etb\s*([\d,.]+)',
            r'recharged etb\s*([\d,.]+)',
            r'received etb\s*([\d,.]+)'
        ],
        'bal_logic': [r'balance is\s*(?:etb)?\s*([\d,.]+)'],
        'fee_logic': [
            r'service fee.*?is etb\s*([\d,.]+)', 
            r'charge\s*([\d,.]+)br',
            r'transaction fee is etb\s*([\d,.]+)'
        ],
        'vat_logic': [
            r'vat.*?is etb\s*([\d,.]+)', 
            r'tax\s*([\d,.]+)br'
        ],
        'name_logic': [
            r'for package\s+(.*?)\s+purchase',
            r'purchased from\s+\d+\s*-\s*([a-zA-Z\s.\-]+)',
            r'from\s+(.*?)\s+(?:on|to)',
            r'to\s+(.*?)\s+account'
        ],
    }

    BOA = {
        'display': 'BOA',
        'amt_logic': [
            r'debited with etb\s*([\d,.]+)',
            r'credited with etb\s*([\d,.]+)',
            r'etb\s*([\d,.]+)', 
            r'birr\s*([\d,.]+)'
        ],
        'bal_logic': [
            r'balance.*?etb\s*([\d,.]+)', 
            r'bal\s*([\d,.]+)'
        ],
        'fee_logic': [
            r'fee.*?etb\s*([\d,.]+)', 
            r's\.charge\s*([\d,.]+)'
        ],
        'vat_logic': [r'vat.*?etb\s*([\d,.]+)'],
        'name_logic': [
            r'(?:to|from)\s+([a-zA-Z\s.\-]+?)(?:\s+on|,|\s+at)'
        ],
    }

    # Start dates for filtering old SMS
    START_DATES = {
        'CBE': datetime(2024, 12, 10),
        'TELEBIRR': datetime(2024, 4, 11),
        'BOA': datetime(2025, 10, 13),
        'DEFAULT': datetime(2024, 1, 1),
    }


class RegexParserService:
    """Singleton parser service"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.rules = SemanticBankRules()
    
    def should_ignore(self, category: Optional[str], date: datetime) -> bool:
        """Check if transaction should be ignored based on category and date"""
        if not category:
            return False
        start_date = self.rules.START_DATES.get(
            category.upper(), 
            self.rules.START_DATES['DEFAULT']
        )
        return date < start_date
    
    def _parse_decimal(self, text: Optional[str]) -> Optional[float]:
        """Safely parse a decimal string"""
        if not text:
            return None
        cleaned = text.replace(',', '').strip()
        if cleaned.endswith('.'):
            cleaned = cleaned[:-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _parse_value(self, body: str, patterns: List[str]) -> Optional[str]:
        """Try to match any of the patterns and return first capture group"""
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _identify_profile(self, body: str, sender: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Determine which bank rules to use"""
        lower_body = body.lower()
        lower_sender = (sender or '').lower()
        
        if 'cbe' in lower_body or 'commercial bank' in lower_body or 'cbe' in lower_sender:
            return self.rules.CBE
        elif 'telebirr' in lower_body or '127' in lower_body or 'ethiotel' in lower_body:
            return self.rules.TELEBIRR
        elif 'boa' in lower_body or 'abyssinia' in lower_body:
            return self.rules.BOA
        return None
    
    def process_raw_transaction(self, raw_text: str, sender: Optional[str] = None) -> ParseResult:
        """Parse a raw transaction message"""
        body = raw_text.lower()
        profile = self._identify_profile(body, sender)
        
        if not profile:
            # Fallback generic parsing
            return self._fallback_parse(raw_text)
        
        # Extract values using bank-specific rules
        amt_raw = self._parse_value(raw_text, profile['amt_logic'])
        bal_raw = self._parse_value(raw_text, profile['bal_logic'])
        fee_raw = self._parse_value(raw_text, profile['fee_logic'])
        vat_raw = self._parse_value(raw_text, profile['vat_logic'])
        name_raw = self._parse_value(raw_text, profile['name_logic'])
        
        # Parse amounts
        amount = self._parse_decimal(amt_raw)
        balance = self._parse_decimal(bal_raw)
        
        # Combine fee and VAT
        parsed_fee = self._parse_decimal(fee_raw) or 0.0
        parsed_vat = self._parse_decimal(vat_raw) or 0.0
        fee = parsed_fee + parsed_vat if (parsed_fee + parsed_vat) > 0 else None
        
        # Clean entity name
        entity_name = name_raw.strip() if name_raw else None
        
        return ParseResult(
            bank=profile['display'],
            amount=amount,
            balance=balance,
            fee=fee,
            entity_name=entity_name,
            is_valid=amount is not None
        )
    
    def _fallback_parse(self, raw_text: str) -> ParseResult:
        """Generic parsing for non-bank messages"""
        body = raw_text.lower()
        
        # Try to find any currency amount
        amount_pattern = r'(?:USD|KSh|Rs|\$|KES|GBP|£)\s?(\d+(?:,\d{3})*(?:\.\d{2})?)'
        match = re.search(amount_pattern, raw_text, re.IGNORECASE)
        amount = self._parse_decimal(match.group(1)) if match else None
        
        # Try to determine if income or expense
        is_expense = any(word in body for word in ['sent', 'paid', 'debited'])
        is_income = any(word in body for word in ['received', 'credited'])
        
        if amount and is_expense:
            amount = -abs(amount)
        
        # Extract entity name (generic pattern)
        entity_match = re.search(
            r'(?:to|from|at|received)\s+([A-Z0-9\s-]+?)(?:\s+on|\s+at|\s+via|\.|$)',
            raw_text,
            re.IGNORECASE
        )
        entity_name = entity_match.group(1).strip() if entity_match else None
        
        return ParseResult(
            bank='Other',
            amount=amount,
            balance=None,
            fee=None,
            entity_name=entity_name,
            is_valid=amount is not None
        )
    
    def extract_probable_entity(self, body: str, sender: Optional[str] = None) -> Optional[str]:
        """Extract probable entity name from transaction text"""
        profile = self._identify_profile(body, sender)
        
        if profile:
            name_raw = self._parse_value(body, profile['name_logic'])
            if name_raw:
                return name_raw.strip()
        
        # Generic fallback
        match = re.search(
            r'(?:to|from|at|received)\s+([A-Z0-9\s-]+?)(?:\s+on|\s+at|\s+via|\.|$)',
            body,
            re.IGNORECASE
        )
        return match.group(1).strip() if match else None
    
    def detect_transaction_type(self, raw_text: str) -> str:
        """Detect if transaction is income or expense"""
        lower = raw_text.lower()
        if any(word in lower for word in ['received', 'credited', 'deposit', 'income']):
            return 'INCOME'
        elif any(word in lower for word in ['sent', 'paid', 'debited', 'withdrawal', 'expense']):
            return 'EXPENSE'
        return 'UNKNOWN'


# Global instance
parser = RegexParserService()
