@echo off
REM Build script for Vault Pro Desktop
echo Building Vault Pro for Windows...

cd vault_pro

REM Install Node dependencies
echo Installing Node.js dependencies...
call npm install

REM Install Python dependencies
echo Installing Python dependencies...
cd python
call pip install -r requirements.txt
cd ..

REM Build React app
echo Building React app...
call npm run build

REM Build Electron app
echo Building Electron app...
call npm run dist

if %ERRORLEVEL% == 0 (
    echo Build successful!
    echo Executable location: dist-electron\Vault Pro Setup.exe
) else (
    echo Build failed.
)

pause
