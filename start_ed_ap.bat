@echo off

if not exist "venv\Scripts\python.exe" (
    echo Erstelle virtuelle Umgebung...
    python -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo Fehler: Python nicht gefunden. Bitte Python 3.13+ installieren.
        pause
        exit /b 1
    )
    echo Installiere Abhaengigkeiten...
    venv\Scripts\python -m pip install --upgrade pip
    venv\Scripts\python -m pip install -r requirements.txt
)

echo Starte EDBob...
venv\Scripts\python.exe -m src.gui.EDBob
