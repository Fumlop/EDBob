@echo off
echo === EDAPGui Installation ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python nicht gefunden. Bitte Python 3.11+ installieren.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist "venv" (
    echo Erstelle virtuelle Umgebung...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Aktualisiere pip...
python -m pip install --upgrade pip

echo Installiere Abhaengigkeiten...
pip install -r requirements.txt

echo.
echo === Installation abgeschlossen ===
echo Starten mit: start_ed_ap.bat
pause
