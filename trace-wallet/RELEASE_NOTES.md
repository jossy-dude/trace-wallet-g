# Trace Wallet v1.1.2

## CI / GitHub Releases (v1.1.2)

- **GitHub Actions:** The Android job was copying the arm64 split APK from the wrong folder (`apk/release/`). Flutter writes those files under `flutter-apk/`, so the step failed, **`publish-release` never ran**, and nothing appeared on the Releases page. The workflow now uses the correct path (with a fallback) and explicit release asset paths.

---

# Trace Wallet v1.1.1

## Fixes (v1.1.1)

- **Windows desktop (VaultAnalytics.exe):** Load `index.html` via a `file://` URL so the PyWebView window works when packaged; store `vault_data.json` / `vault_config.json` under the OS app-data folder instead of the exe directory.
- **Python API:** `set_window` now assigns `self.window` so minimize / fullscreen / close and file dialogs work.
- **Flutter:** Declare `shelf` and `shelf_router`; avoid crashing the Windows app when the sync server cannot bind to port 8080.
- **CI / releases:** Build the Windows executable on `windows-latest`, build Android on Ubuntu, and attach universal plus arm64-v8a APKs and the AAB to GitHub Releases.
- **Repository:** Stop tracking PyInstaller `build/` and `dist/` artifacts; disable UPX in the spec for more reliable Windows binaries.

---

# Trace Wallet v1.1.0 Release Notes

## 🎉 Major Release: P2P Infrastructure & Mobile Sync

This release introduces a complete LocalSend-style P2P infrastructure for seamless mobile-to-desktop financial data synchronization.

---

## ✨ New Features

### P2P Mobile Sync (LocalSend-Style)
- **UDP Discovery** - Auto-discover desktop vault on local WiFi network (port 5333)
- **QR Code Pairing** - Instant pairing by scanning QR code from desktop app
- **Secure Token Authentication** - UUID-based token verification for all API calls
- **Device Management** - Track and manage paired mobile devices with connection history
- **Batch SMS Sync** - Send multiple bank SMS messages in one batch for efficiency
- **HTTPS Support** - Optional SSL/TLS encryption for local network communication

### Enhanced API Endpoints
- `GET /api/health` - Health check with secure status
- `GET /api/pair` - Pair verification with device info
- `POST /api/sms` - Receive single SMS from mobile
- `POST /api/sms/batch` - Receive batch SMS messages
- `GET /api/relay/pending` - Get pending relay messages
- `POST /api/relay/delivered` - Mark relay as delivered

### UI Enhancements
- **P2P Config Modal** with 3 tabs:
  - QR Code tab for mobile pairing
  - Connection Info tab with IP/port/token display
  - Paired Devices tab with device list and remove functionality
- **Settings Integration** - P2P Mobile Sync section with toggle and status
- **Token Regeneration** - Button to regenerate pairing token on demand
- **Modal Exit/X Buttons** - Fixed all modal close functionality

---

## 🔧 Technical Improvements

### Build System
- **Windows Executable** - PyInstaller with hidden imports for `requests`, `urllib3`, etc.
- **GitHub Actions CI/CD** - Automated builds for Windows and Android
- **Gradle 8.6** - Downgraded from 8.14 for `isar_flutter_libs` compatibility
- **Build Logs** - Captured and uploaded as artifacts for troubleshooting

### Dependencies
- Added `requests>=2.31.0` for Ollama AI integration
- Added `pythonnet>=3.0.0` for Windows pywebview
- Added `mobile_scanner` and `network_info_plus` for Flutter mobile app
- Updated `fastapi` and `uvicorn` versions

### Code Quality
- Fixed bare `except:` clause in `api.py`
- Added comprehensive error handling
- Improved logging throughout P2P pipeline

---

## 🐛 Bug Fixes

1. **Fixed Windows .exe import error** - Added hidden imports for `requests` and dependencies
2. **Fixed modal close buttons** - All modals now properly close with X button and ESC key
3. **Fixed Android Gradle build** - Downgraded to Gradle 8.6 for plugin compatibility
4. **Fixed Dart SDK version** - Updated to Flutter 3.41.6 for SDK 3.11.4 compatibility
5. **Fixed Android license acceptance** - Added automatic license acceptance in CI

---

## 📁 Downloads

### Windows Desktop
- **File:** `VaultAnalytics.exe` (64-bit)
- **Size:** ~64 MB
- **Requirements:** Windows 10/11, no additional dependencies

### Android Mobile
- **File:** `app-release.apk` (arm64-v8a)
- **Size:** ~25 MB
- **Requirements:** Android 8.0+ (API 26+)

### Alternative: App Bundle (Play Store)
- **File:** `app-release.aab`
- For Play Store distribution

---

## 🚀 Quick Start

### Desktop Setup
1. Download and run `VaultAnalytics.exe`
2. Open Settings → P2P Mobile Sync
3. Click "Open Config" to view QR code
4. Enable P2P Server toggle

### Mobile Setup
1. Install the APK on your Android device
2. Open the app and grant SMS permissions
3. Scan the QR code from desktop or wait for UDP discovery
4. Start syncing bank SMS messages!

---

## 🔐 Security

- **Local Network Only** - P2P server binds to `0.0.0.0` but intended for LAN use
- **Token Authentication** - UUID-based tokens for device pairing ( regenerated on demand)
- **Optional HTTPS** - SSL/TLS support for encrypted local communication
- **No Cloud** - All data stays on your devices
- **SHA-256 Passwords** - Master password hashing

---

## 📝 Known Issues

- Windows executable requires manual rebuild for new Python dependencies
- Android app needs manual SDK setup for local builds (use CI artifacts)
- HTTPS certificates must be manually generated and configured

---

## 🔮 Coming in v1.2.0

- Flutter mobile app P2P sync implementation
- Telegram bot integration for remote notifications
- Email relay provider
- Automated HTTPS certificate generation
- iOS support

---

## 📚 Documentation

- [README.md](README.md) - Full project documentation
- [BUILD.md](BUILD.md) - Build instructions for developers
- [GitHub Actions](.github/workflows/build.yml) - CI/CD configuration

---

**Full Changelog:** https://github.com/jossy-dude/Trace-Wallet/compare/v1.0.0...v1.1.0
