const { app, BrowserWindow } = require('electron');
// Import dinamico per compatibilità cross-platform
let contextMenu;
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

function createWindow() {
        // Import dinamico ES module
        import('electron-context-menu').then(mod => {
            mod.default({
                window: mainWindow,
                showCopyImage: false,
                showSaveImage: false,
                showInspectElement: true,
                prepend: (defaultActions, params, browserWindow) => []
            });
        }).catch(() => {});
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // Abilita menu contestuale di default sugli input
    mainWindow.webContents.on('context-menu', (event, params) => {
        if (params.isEditable) {
            mainWindow.webContents.executeJavaScript('document.execCommand("copy")');
        }
    });
}

function startPythonBackend() {
    let scriptPath;
    let command;
    let args = [];


    if (app.isPackaged) {
        // --- MODALITÀ PRODUZIONE (App installata) ---
        const binaryName = process.platform === 'win32' ? 'api.exe' : 'api';
        scriptPath = path.join(process.resourcesPath, 'backend', binaryName);
        command = scriptPath;
        args = [];
        console.log("Produzione: Avvio backend da", scriptPath);
    } else {
        // --- MODALITÀ SVILUPPO (npm run dev) ---
        scriptPath = path.join(__dirname, '../backend/api.py');
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        command = pythonCmd;
        args = [scriptPath];
        console.log("Sviluppo: Avvio python da", scriptPath);
    }

    pythonProcess = spawn(command, args);

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python]: ${data}`);
    });
    
    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Err]: ${data}`);
    });
    
    pythonProcess.on('error', (err) => {
        console.error("Impossibile avviare Python:", err);
    });
}

app.whenReady().then(() => {
    startPythonBackend();
    createWindow();
});

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill();
    app.quit();
});