const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

function createWindow() {
    // ... (codice context-menu precedente o importazione) ...
    
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'index.html'));
}

function startPythonBackend() {
    let scriptPath;
    let command;
    let args = [];
    
    // Calcola dove salvare i dati (DB/PDF)
    // Se siamo in modalità Portable Windows, usiamo la cartella dell'EXE.
    // Altrimenti usiamo i documenti o la cartella utente.
    let dataPath;
    if (process.env.PORTABLE_EXECUTABLE_DIR) {
        // Caso Windows Portable (es. Chiavetta USB)
        dataPath = process.env.PORTABLE_EXECUTABLE_DIR;
    } else {
        // Caso Sviluppo o Mac o Installato
        // path.dirname(app.getPath('exe')) su Mac è dentro il pacchetto .app (scomodo),
        // meglio usare userData o lasciar decidere a python.
        dataPath = app.getPath('userData'); 
    }

    if (app.isPackaged) {
        // --- PRODUZIONE ---
        const binaryName = process.platform === 'win32' ? 'api.exe' : 'api';
        scriptPath = path.join(process.resourcesPath, 'backend', binaryName);
        command = scriptPath;
        // Passiamo il percorso dati come argomento al Python
        args = ['--data-dir', dataPath]; 
    } else {
        // --- SVILUPPO ---
        scriptPath = path.join(__dirname, '../backend/api.py');
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        command = pythonCmd;
        args = [scriptPath, '--data-dir', dataPath];
    }

    console.log(`Avvio Python: ${command} con args: ${args}`);

    pythonProcess = spawn(command, args);

    pythonProcess.stdout.on('data', (data) => console.log(`[Python]: ${data}`));
    pythonProcess.stderr.on('data', (data) => console.error(`[Python Err]: ${data}`));
}

app.whenReady().then(() => {
    startPythonBackend();
    createWindow();
});

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill();
    app.quit();
});