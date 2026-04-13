import socket
import json
import time
import threading
import logging

class VaultDiscoveryServer:
    def __init__(self, port, token, use_https=False):
        self.port = port
        self.token = token
        self.use_https = use_https
        self.running = False
        self._thread = None

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._broadcast_loop, daemon=True, name="UDP-Discovery")
        self._thread.start()
        logging.info("UDP Discovery broadcast started on port 5333")

    def stop(self):
        self.running = False

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _broadcast_loop(self):
        # Broadcast address for local network
        addr = ('<broadcast>', 5333)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # LocalSend compatible signature for easy scanning, altered slightly for Vault
        protocol = "https" if self.use_https else "http"

        while self.running:
            try:
                ip = self._get_local_ip()
                payload = json.dumps({
                    "id": "vault-desktop",
                    "alias": "Vault Analytics Command",
                    "deviceModel": "Windows PC",
                    "deviceType": "desktop",
                    "ip": ip,
                    "port": self.port,
                    "protocol": protocol,
                    "token": self.token[:8] + "..."  # Show token prefix for verification
                })
                sock.sendto(payload.encode('utf-8'), addr)
            except Exception as e:
                pass # Ignore network errors during broadcast
            time.sleep(3)
        sock.close()
