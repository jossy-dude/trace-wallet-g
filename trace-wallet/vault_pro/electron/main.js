const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Python sidecar process
let pythonProcess = null;

// Create the browser window
function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset',
    show: false
  });

  // Load the app
  const isDev = process.env.NODE_ENV === 'development';
  
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  return mainWindow;
}

// Start Python sidecar
function startPythonSidecar() {
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
  const sidecarPath = path.join(__dirname, '../python/sidecar.py');
  
  try {
    pythonProcess = spawn(pythonPath, [sidecarPath], {
      stdio: ['pipe', 'pipe', 'pipe'],
      detached: false
    });

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString().trim();
      if (output) {
        console.log('Python:', output);
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const error = data.toString().trim();
      if (error) {
        console.error('Python Error:', error);
      }
    });

    pythonProcess.on('error', (error) => {
      console.error('Failed to start Python sidecar:', error);
      // Show error dialog to user
      const { dialog } = require('electron');
      dialog.showErrorBox('Python Sidecar Error', 
        'Failed to start Python backend. Please ensure Python 3.11+ is installed.');
    });

    pythonProcess.on('close', (code) => {
      console.log(`Python sidecar exited with code ${code}`);
      pythonProcess = null;
    });
  } catch (error) {
    console.error('Exception starting Python sidecar:', error);
  }
}

// Cleanup function for Python process
function cleanupPythonProcess() {
  if (pythonProcess) {
    console.log('Cleaning up Python sidecar...');
    try {
      // Send SIGTERM first for graceful shutdown
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
      } else {
        pythonProcess.kill('SIGTERM');
        // Force kill after 2 seconds if still running
        setTimeout(() => {
          if (pythonProcess && !pythonProcess.killed) {
            pythonProcess.kill('SIGKILL');
          }
        }, 2000);
      }
    } catch (error) {
      console.error('Error cleaning up Python process:', error);
    }
    pythonProcess = null;
  }
}

// IPC handlers for Python communication
ipcMain.handle('python-command', async (event, command, data) => {
  return new Promise((resolve, reject) => {
    if (!pythonProcess || pythonProcess.killed) {
      reject(new Error('Python sidecar not running'));
      return;
    }

    const message = JSON.stringify({ command, data }) + '\n';
    let response = '';
    let timeoutId;

    const onData = (data) => {
      response += data.toString();
      const lines = response.split('\n');
      
      for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        try {
          const result = JSON.parse(line);
          cleanup();
          resolve(result);
          return;
        } catch (e) {
          // Not valid JSON, log and continue
          console.warn('Non-JSON output from Python:', line);
        }
      }
      
      response = lines[lines.length - 1];
    };

    const onError = (error) => {
      cleanup();
      reject(new Error(`Python process error: ${error.message}`));
    };

    const cleanup = () => {
      if (timeoutId) clearTimeout(timeoutId);
      if (pythonProcess) {
        pythonProcess.stdout.off('data', onData);
        pythonProcess.off('error', onError);
      }
    };

    pythonProcess.stdout.on('data', onData);
    pythonProcess.once('error', onError);
    
    try {
      pythonProcess.stdin.write(message);
    } catch (error) {
      cleanup();
      reject(new Error(`Failed to write to Python stdin: ${error.message}`));
      return;
    }

    // Timeout after 15 seconds (increased from 10)
    timeoutId = setTimeout(() => {
      cleanup();
      reject(new Error(`Command '${command}' timeout after 15s`));
    }, 15000);
  });
});

// App event handlers
app.whenReady().then(() => {
  createWindow();
  startPythonSidecar();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  cleanupPythonProcess();
  
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  cleanupPythonProcess();
});

app.on('quit', () => {
  cleanupPythonProcess();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  cleanupPythonProcess();
  app.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
