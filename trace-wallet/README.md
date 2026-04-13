# Vault Pro

A secure, modern financial tracking system with cross-platform support. Track transactions, analyze spending patterns, and sync SMS-based bank alerts from your mobile device to your desktop vault.

Built with **React**, **Tailwind CSS**, **Electron**, and **Python**.

## Features

### Core Features
- **Transaction Management** - Track income, expenses, and transfers with intelligent categorization
- **Financial Analytics** - Net worth tracking, spending analysis, and transaction history
- **Bank SMS Parsing** - Automatic parsing of Ethiopian bank SMS (CBE, Telebirr, BOA)
- **People Management** - Manage contacts with aliases for easy transaction tracking
- **P2P Sync** - Sync transactions between devices on your local network
- **Data Import/Export** - JSON-based backup and restore functionality

### Desktop Application
- **Modern UI** - Clean, responsive interface with Tailwind CSS
- **Local Database** - SQLite storage with zero cloud dependencies
- **Electron Wrapper** - Native desktop experience across platforms

## Architecture

```
vault_pro/
├── electron/           # Electron main process
│   ├── main.js        # Entry point
│   ├── preload.js     # IPC bridge
│   └── pythonBridge.js # Python communication utility
├── python/            # Python backend
│   ├── database.py    # SQLite operations
│   ├── parser.py      # SMS regex parser
│   ├── server.py      # HTTP sync server
│   ├── sidecar.py     # Electron-Python bridge
│   └── requirements.txt
├── src/               # React source
│   ├── components/    # React components
│   │   ├── Dashboard.jsx
│   │   ├── Transactions.jsx
│   │   ├── People.jsx
│   │   ├── Sync.jsx
│   │   └── Settings.jsx
│   ├── App.jsx        # Main app with routing
│   └── main.jsx       # React entry
├── package.json       # Node dependencies
├── vite.config.js     # Vite configuration
├── tailwind.config.js # Tailwind configuration
└── index.html         # HTML template
```

## Quick Start

### Prerequisites
- **Node.js 20+** - [Download](https://nodejs.org/)
- **Python 3.11+** - [Download](https://python.org/)

### Installation

```bash
cd vault_pro

# Install Node dependencies
npm install

# Install Python dependencies
cd python
pip install -r requirements.txt
cd ..
```

### Development

```bash
# Start Python sidecar (Terminal 1)
python python/sidecar.py

# Start React dev server (Terminal 2)
npm run dev
```

App available at `http://localhost:5173`

### Build for Production

```bash
# Windows
build_windows.bat

# Or manually:
npm run build
npm run dist
```

## P2P Mobile Sync Setup

### Desktop Setup
1. Open the app and go to **Sync** page
2. Enable P2P Server (toggle on)
3. Note your local IP and port (default: 8765)
4. Use QR code or manual pairing to connect mobile

### Mobile App Integration

The mobile app (separate project) should implement:

```javascript
// 1. Discover desktop vault via UDP broadcast on port 5333
// 2. Scan QR code to get connection details
// 3. Send SMS via HTTP POST

const response = await fetch('http://192.168.x.x:8765/api/sms', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Vault-Token': 'your-token'
  },
  body: JSON.stringify({
    body: 'Your bank SMS text here',
    sender: 'CBE',
    metadata: { timestamp: new Date().toISOString() }
  })
});
```

## API Endpoints

### Health Check
```
GET /api/health
Response: {"status": "ok", "version": "1.0"}
```

### Pair Verification
```
GET /api/pair
Headers: X-Vault-Token: <token>
Response: {"status": "paired", "device_id": "vault-desktop"}
```

### Send SMS
```
POST /api/sms
Headers: X-Vault-Token: <token>
Content-Type: application/json
Body: {"body": "...", "sender": "...", "metadata": {...}}
```

### Batch SMS
```
POST /api/sms/batch
Headers: X-Vault-Token: <token>
Content-Type: application/json
Body: {"messages": [{...}, {...}]}
```

## Configuration

### Default Settings
Configuration is stored in `~/.vault_pro/config.json`:

```json
{
  "sms_port": 8765,
  "sms_use_https": false,
  "ssl_cert_path": "",
  "ssl_key_path": "",
  "theme": "dark"
}
```

### Database Location
- Windows: `%USERPROFILE%\.vault_pro\vault.db`
- macOS/Linux: `~/.vault_pro/vault.db`

## Security

- **Local Network Only** - P2P server binds to local network
- **Token Authentication** - UUID-based tokens for device pairing
- **No Cloud** - All data stays on your devices
- **SQLite Encryption** - Optional SQLCipher support

## Tech Stack

- **Frontend**: React 19, React Router 7, Tailwind CSS 4
- **Desktop**: Electron 35
- **Backend**: Python 3.11, aiohttp, SQLite
- **Build**: Vite 6, electron-builder
- **Communication**: UDP broadcast, HTTP/HTTPS

## Screenshots

*Coming soon*

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Inspired by LocalSend for P2P architecture
- Ethiopian bank SMS parsing patterns from community contributions
- Modern UI with Tailwind CSS
