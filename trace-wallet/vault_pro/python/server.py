"""
Network Host Service - HTTP Server for Desktop
Handles sync from mobile devices and P2P connections
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import asdict
from pathlib import Path
from collections import defaultdict

from aiohttp import web
import aiohttp_cors

from database import db, VaultTransaction, VaultPerson, PairedDevice
from parser import parser

# Rate limiting storage
request_history = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 100    # requests per window

class SyncServer:
    """HTTP server for handling sync requests"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.sync_buffer: List[Dict] = []
        self.last_sync_time: Optional[datetime] = None
        self.sync_cooldown = timedelta(minutes=10)
        
        # Setup CORS - more restrictive for security
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="X-Vault-Version",
                allow_headers=["Content-Type", "X-Vault-Token", "X-Vault-Device-ID"],
                allow_methods=["GET", "POST", "OPTIONS"],
                max_age=3600
            )
        })
        
        # Routes
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/sync/transactions', self.sync_transactions)
        self.app.router.add_post('/p2p/handshake', self.p2p_handshake)
        self.app.router.add_post('/p2p/sync', self.p2p_sync)
        self.app.router.add_get('/api/transactions', self.get_transactions)
        self.app.router.add_get('/api/people', self.get_people)
        self.app.router.add_post('/api/transaction', self.add_transaction)
        self.app.router.add_post('/api/person', self.add_person)
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def start(self):
        """Start the server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"Vault Server running on http://{self.host}:{self.port}")
        return runner
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }, headers={'X-Vault-Version': '1.0.0'})
    
    async def sync_transactions(self, request: web.Request) -> web.Response:
        """Handle transaction sync from mobile"""
        try:
            now = datetime.now()
            
            # Check cooldown
            if self.last_sync_time and (now - self.last_sync_time) < self.sync_cooldown:
                # Buffer mode
                body = await request.json()
                self.sync_buffer.extend(body)
                
                return web.json_response({
                    'status': 'buffered',
                    'message': 'Cooldown active. Transactions queued.',
                    'buffer_count': len(self.sync_buffer)
                })
            
            self.last_sync_time = now
            
            # Process incoming transactions
            body = await request.json()
            transactions = body if isinstance(body, list) else [body]
            
            # Add buffered transactions
            if self.sync_buffer:
                transactions = self.sync_buffer + transactions
                self.sync_buffer.clear()
            
            processed_count = 0
            
            for tx_data in transactions:
                # Check for duplicates
                existing = self._find_duplicate(tx_data)
                if existing:
                    continue
                
                # Parse transaction
                raw_text = tx_data.get('raw_text', '')
                parse_result = parser.process_raw_transaction(raw_text)
                
                # Create transaction object
                transaction = VaultTransaction(
                    raw_text=raw_text,
                    amount=parse_result.amount,
                    balance=parse_result.balance,
                    fee=parse_result.fee,
                    date=tx_data.get('date', datetime.now().isoformat()),
                    sender_alias=parse_result.entity_name or tx_data.get('sender_alias'),
                    category=parse_result.bank or 'Requires Review',
                    is_approved=False
                )
                
                # Check date filtering
                try:
                    tx_date = datetime.fromisoformat(transaction.date.replace('Z', '+00:00'))
                    if parser.should_ignore(transaction.category, tx_date):
                        continue
                except:
                    pass
                
                # Map to person
                if transaction.sender_alias:
                    person = db.find_person_by_alias(transaction.sender_alias)
                    if person:
                        transaction.sender_alias = person.name
                
                # Ghost fee reconciliation
                ghost = self._check_ghost_fee(transaction)
                if ghost:
                    db.add_transaction(ghost)
                
                # Save transaction
                db.add_transaction(transaction)
                processed_count += 1
            
            return web.json_response({
                'status': 'success',
                'count': processed_count
            })
            
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def p2p_handshake(self, request: web.Request) -> web.Response:
        """Handle P2P device handshake"""
        try:
            body = await request.json()
            device_id = body.get('device_id')
            device_name = body.get('name', 'Unknown Device')
            
            # Store device as pending
            device = PairedDevice(
                device_id=device_id,
                name=device_name,
                device_type='mobile' if 'MOBILE' in str(device_id) else 'desktop',
                is_trusted=False,
                added_at=datetime.now().isoformat()
            )
            db.add_device(device)
            
            return web.json_response({
                'status': 'waiting_for_approval',
                'local_id': 'DESKTOP_001',
                'local_name': 'Vault Pro Desktop'
            })
            
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def p2p_sync(self, request: web.Request) -> web.Response:
        """Handle P2P sync request"""
        device_id = request.headers.get('X-Vault-Device-ID')
        
        if not device_id:
            return web.json_response({
                'status': 'error',
                'message': 'Device ID required'
            }, status=401)
        
        device = db.get_device(device_id)
        if not device or not device.is_trusted:
            return web.json_response({
                'status': 'error',
                'message': 'Device not trusted'
            }, status=403)
        
        # Process sync (similar to regular sync)
        return await self.sync_transactions(request)
    
    async def get_transactions(self, request: web.Request) -> web.Response:
        """Get all transactions (API endpoint)"""
        pending_only = request.query.get('pending') == 'true'
        
        if pending_only:
            transactions = db.get_pending_transactions()
        else:
            transactions = db.get_all_transactions()
        
        return web.json_response({
            'transactions': [t.to_dict() for t in transactions]
        })
    
    async def get_people(self, request: web.Request) -> web.Response:
        """Get all people (API endpoint)"""
        people = db.get_all_people()
        return web.json_response({
            'people': [p.to_dict() for p in people]
        })
    
    async def add_transaction(self, request: web.Request) -> web.Response:
        """Add a new transaction (API endpoint)"""
        try:
            body = await request.json()
            transaction = VaultTransaction(
                raw_text=body.get('raw_text', ''),
                amount=body.get('amount'),
                balance=body.get('balance'),
                fee=body.get('fee'),
                date=body.get('date', datetime.now().isoformat()),
                sender_alias=body.get('sender_alias'),
                category=body.get('category', 'Other'),
                is_approved=body.get('is_approved', False)
            )
            tx_id = db.add_transaction(transaction)
            return web.json_response({
                'status': 'success',
                'id': tx_id
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    async def add_person(self, request: web.Request) -> web.Response:
        """Add a new person (API endpoint)"""
        try:
            body = await request.json()
            person = VaultPerson(
                name=body.get('name', ''),
                aliases=body.get('aliases', []),
                monthly_fee=body.get('monthly_fee', 0.0)
            )
            person_id = db.add_person(person)
            return web.json_response({
                'status': 'success',
                'id': person_id
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    def _find_duplicate(self, tx_data: Dict) -> Optional[VaultTransaction]:
        """Check if transaction already exists"""
        raw_text = tx_data.get('raw_text', '')
        date = tx_data.get('date', '')
        
        # Search in recent transactions
        transactions = db.get_all_transactions(limit=100)
        for tx in transactions:
            if tx.raw_text == raw_text and tx.date == date:
                return tx
        return None
    
    def _check_ghost_fee(self, transaction: VaultTransaction) -> Optional[VaultTransaction]:
        """Check for ghost fees and create adjustment if needed"""
        if not transaction.balance or not transaction.category:
            return None
        
        if transaction.category == 'Requires Review':
            return None
        
        # Get last transaction for this bank
        # This would need a new method in database.py
        # For now, return None
        return None


async def main():
    """Main entry point"""
    server = SyncServer()
    runner = await server.start()
    
    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == '__main__':
    asyncio.run(main())
