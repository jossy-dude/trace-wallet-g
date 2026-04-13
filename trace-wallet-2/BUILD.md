# Build Instructions

## Tech Stack

- **Frontend**: React.js 19, React Router, Tailwind CSS
- **Desktop**: Electron
- **Backend**: Python 3.11+, aiohttp, SQLite
- **Build Tool**: Vite

## Prerequisites

### For Desktop Build:
- **Node.js 20+** - [Download from nodejs.org](https://nodejs.org/)
- **Python 3.11+** - [Download from python.org](https://python.org/)
- **Git**

## Installation

### 1. Clone and Navigate

```bash
cd vault_pro
```

### 2. Install Node Dependencies

```bash
npm install
```

### 3. Install Python Dependencies

```bash
cd python
pip install -r requirements.txt
cd ..
```

## Development

### Start Development Server

```bash
# Terminal 1: Start Python sidecar
python python/sidecar.py

# Terminal 2: Start React dev server
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
# Build React app
npm run build

# Build Electron app
npm run dist
```

## Build Scripts

### Windows

Double-click `build_windows.bat` or run:

```cmd
build_windows.bat
```

## Project Structure

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
│   ├── App.jsx        # Main app
│   └── main.jsx       # React entry
├── package.json       # Node dependencies
├── vite.config.js     # Vite configuration
├── tailwind.config.js # Tailwind configuration
└── index.html         # HTML template
```

## Database

SQLite database is stored at:
- Windows: `%USERPROFILE%/.vault_pro/vault.db`
- macOS/Linux: `~/.vault_pro/vault.db`

## Features

- Dashboard with transaction analytics
- Transaction management with filtering and search
- People/contact management with aliases
- P2P sync between desktop and mobile
- SMS parsing for CBE, Telebirr, BOA banks
- Import/Export functionality

## GitHub Actions

Automated builds for Windows, macOS, and Linux on every push to main.

See `.github/workflows/build.yml`

## Version Info

Update version in:
- `package.json` - version field
- `python/sidecar.py` - VERSION constant
