@echo off
REM Build backend exe using PyInstaller (Windows)
if not exist venv (
  echo Verifica di avere Python e pip installati.
)
python -m pip install -r requirements.txt
pyinstaller --onefile --name api api.py
if exist dist\api.exe (
  echo api.exe creato in %cd%\dist\api.exe
  exit /b 0
) else (
  echo ERRORE: api.exe non trovato in %cd%\dist
  exit /b 1
)
