import logging
import asyncio
import threading
import os
import uuid
from datetime import datetime

from vault.ui.api import VaultPro

def create_sms_server(vault_api: VaultPro, port: int = 8765, use_https: bool = False):
    """Create and run FastAPI SMS receiver with P2P security in background thread"""
    try:
        from fastapi import FastAPI, Depends, HTTPException, Header, Request
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        from vault.pipeline.discovery import VaultDiscoveryServer

        app = FastAPI(title="Vault SMS Receiver", version="1.0")
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

        # Initialize paired devices tracking
        if "paired_devices" not in vault_api.data:
            vault_api.data["paired_devices"] = []

        # Dependency to enforce Valid P2P Device ID
        def verify_p2p_device(x_vault_device_id: str = Header(None, alias="X-Vault-Device-ID")):
            paired_devices = vault_api.settings.get("paired_devices", [])
            if not any(d["id"] == x_vault_device_id for d in paired_devices):
                # Check if it's the very first device and we're in "Pairing Mode"
                # For now, require explicit pairing via the UI
                raise HTTPException(status_code=401, detail="Unauthorized P2P Device")
            return x_vault_device_id

        @app.post("/api/p2p/handshake")
        async def p2p_handshake(payload: dict):
            """Initial handshake for device discovery"""
            remote_id = payload.get("device_id")
            remote_name = payload.get("name")
            return {
                "status": "waiting_for_approval",
                "local_id": vault_api.settings.get("device_id"),
                "local_name": vault_api.settings.get("device_name")
            }

        @app.post("/api/p2p/sync")
        async def p2p_sync(request: Request, payload: dict, device_id: str = Depends(verify_p2p_device)):
            """Full P2P sync (Syncthing-inspired delta sync)"""
            client_ip = request.client.host if request.client else "unknown"
            logging.info(f"P2P Sync: Inbound from {device_id} ({client_ip})")
            
            # Pass to API for hash check and merge
            result = vault_api.sync_p2p(payload)
            return result

        @app.post("/api/sms")
        async def receive_sms(request: Request, payload: dict, token: str = Depends(verify_token)):
            """Receive SMS from mobile app P2P sync"""
            # Log sync event for audit
            client_ip = request.client.host if request.client else "unknown"
            logging.info(f"P2P: Sync request from {client_ip}")
            
            _track_device(request, vault_api)
            return vault_api.receive_sms(payload)

        @app.post("/api/sms/batch")
        async def receive_batch(request: Request, payload: dict, token: str = Depends(verify_token)):
            """Receive batch of SMS messages securely"""
            _track_device(request, vault_api)
            messages = payload.get("messages", [])
            results = [vault_api.receive_sms(msg) for msg in messages]
            return {"status": "success", "count": len(results), "results": results}

        @app.get("/api/health")
        async def health():
            return {"status": "ok", "version": "4.0", "timestamp": datetime.now().isoformat(), "secure": use_https}

        @app.get("/api/pair")
        async def get_pair_info(token: str = Depends(verify_token)):
            """Get pairing info for mobile app"""
            return {
                "status": "paired",
                "version": "4.0",
                "device_id": "vault-desktop",
                "alias": vault_api.settings.get("profile_name", "Windows Vault")
            }

        @app.get("/api/relay/pending")
        async def get_pending_relays(token: str = Depends(verify_token)):
            log = vault_api.get_relay_log()
            pending = [r for r in log if r.get("status") == "queued"]
            return {"pending": pending}

        @app.post("/api/relay/delivered")
        async def mark_delivered(payload: dict, token: str = Depends(verify_token)):
            relay_id = payload.get("relay_id")
            for entry in vault_api.data.get("relay_log", []):
                if entry.get("id") == relay_id:
                    entry["status"] = "delivered"
                    entry["delivered_at"] = datetime.now().isoformat()
                    vault_api.save_data()
                    return {"status": "success"}
            return {"status": "error"}

        def _track_device(request: Request, vault_api):
            """Track connected devices for paired devices list"""
            try:
                client_ip = request.client.host if request.client else "unknown"
                devices = vault_api.data.setdefault("paired_devices", [])
                existing = next((d for d in devices if d.get("ip") == client_ip), None)
                if existing:
                    existing["last_seen"] = datetime.now().isoformat()
                    existing["connection_count"] = existing.get("connection_count", 0) + 1
                else:
                    devices.append({
                        "id": str(uuid.uuid4())[:8],
                        "ip": client_ip,
                        "last_seen": datetime.now().isoformat(),
                        "connection_count": 1,
                        "alias": f"Mobile Device ({client_ip})"
                    })
                # Keep only last 10 devices
                vault_api.data["paired_devices"] = devices[-10:]
            except Exception:
                pass  # Non-critical feature

        def run():
            # Start UDP Discovery engine before bringing up HTTP port
            token = vault_api.settings.get("sms_token", "")
            discovery = VaultDiscoveryServer(port, token, use_https)
            discovery.start()

            # HTTPS configuration
            ssl_config = None
            if use_https:
                ssl_cert = vault_api.settings.get("ssl_cert_path", "")
                ssl_key = vault_api.settings.get("ssl_key_path", "")
                if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
                    ssl_config = {"certfile": ssl_cert, "keyfile": ssl_key}
                else:
                    logging.warning("HTTPS enabled but certificates not found. Using HTTP.")
                    use_https = False

            protocol = "https" if use_https and ssl_config else "http"
            vault_api._log_audit("SMS P2P Server Started", "HIGH", f"Listening on port {port} ({protocol.upper()})")

            uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning", 
                        ssl_certfile=ssl_config.get("certfile") if ssl_config else None,
                        ssl_keyfile=ssl_config.get("keyfile") if ssl_config else None)

        thread = threading.Thread(target=run, daemon=True, name="SMS-Receiver")
        thread.start()
        return thread

    except ImportError:
        logging.warning("FastAPI/uvicorn not installed. SMS receiver disabled.")
        vault_api._log_audit("SMS Server Skipped", "LOW", "FastAPI not installed")
        return None
