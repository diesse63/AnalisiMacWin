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
        // electron-builder may place extraResources under resources/backend/dist or resources/backend
        const fs = require('fs');
        const candidate1 = path.join(process.resourcesPath, 'backend', binaryName);
        const candidate2 = path.join(process.resourcesPath, 'backend', 'dist', binaryName);
        if (fs.existsSync(candidate1)) {
            scriptPath = candidate1;
        } else if (fs.existsSync(candidate2)) {
            scriptPath = candidate2;
        } else {
            // Non trovato: mostriamo errore all'utente e interrompiamo l'avvio del backend
            const { dialog } = require('electron');
            const msg = `Backend executable non trovato in resources. Ho cercato:\n${candidate1}\n${candidate2}\n` +
                        `Assicurati di aver incluso l'eseguibile (es. con PyInstaller) nella cartella backend/dist prima di fare il package.`;
            console.error(msg);
            try { dialog.showErrorBox('Backend mancante', msg); } catch (e) { /* ignore in headless build */ }
            return; // non continuiamo a spawnare un comando inesistente
        }
        command = scriptPath;
        // Passiamo il percorso dati come argomento
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

    pythonProcess.on('error', (err) => {
        console.error('Errore spawn backend:', err);
        try {
            const { dialog } = require('electron');
            dialog.showErrorBox('Errore avvio backend', `Errore avviando il backend: ${err.message}`);
        } catch (e) {}
    });

    pythonProcess.stdout.on('data', (data) => console.log(`[Backend]: ${data}`));
    pythonProcess.stderr.on('data', (data) => console.error(`[Backend Err]: ${data}`));
    pythonProcess.on('close', (code, signal) => console.log(`Backend terminato. code=${code} signal=${signal}`));
}

app.whenReady().then(() => {
    startPythonBackend();
    createWindow();
});

app.on('window-all-closed', () => {
    if (pythonProcess) pythonProcess.kill();
    app.quit();
});