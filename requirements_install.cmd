@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python 3.10 or newer.
    pause
    exit /b 1
)

if not exist env (
    echo Creating virtual environment...
    python -m venv env
)

call env\Scripts\activate

python -m pip install --upgrade pip
python -m pip install --upgrade --force-reinstall --no-cache-dir -r requirements.txt

if errorlevel 1 (
    echo Failed to install required packages.
    pause
    exit /b 1
)

echo Installation completed.
pause
