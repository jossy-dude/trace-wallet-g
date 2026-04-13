import logging
import os
import pathlib
import sys

import webview

from vault.ui.api import VaultPro
from vault.pipeline.sms_server import create_sms_server

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _ui_entry_url() -> str:
    """Resolve index.html for dev and for PyInstaller onefile (_MEIPASS)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return pathlib.Path(os.path.join(base, "index.html")).resolve().as_uri()


if __name__ == '__main__':
    # Initialize Core Application Logic
    api = VaultPro()

    # Extract config port and HTTPS setting safely
    port = getattr(api, 'settings', {}).get('sms_port', 8765)
    use_https = getattr(api, 'settings', {}).get('sms_use_https', False)

    # Start SMS FastAPI listener in background thread
    # create_sms_server handles its own thread internally
    server_thread = create_sms_server(api, port=port, use_https=use_https)
    if server_thread:
        logging.info(f"SMS P2P Server active on port {port} ({'HTTPS' if use_https else 'HTTP'})")
    else:
        logging.warning("SMS P2P Server could not be started (FastAPI/uvicorn may not be installed)")

    # Boot the UI (file:// URL so the frozen .exe loads the bundled HTML reliably)
    window = webview.create_window(
        title='Vault Analytics v4.0',
        url=_ui_entry_url(),
        js_api=api,
        width=1400,
        height=900,
        frameless=True,
        transparent=True,
        easy_drag=False,
    )

    api.set_window(window)
    webview.start()
