@echo off
echo ========================================
echo Git Manager - Build Executable
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
echo.

echo Building executable...
pyinstaller --onefile --windowed --name="GitManager" --icon=NONE git_manager.py
echo.

if exist "dist\GitManager.exe" (
    echo ========================================
    echo Build successful!
    echo Executable location: dist\GitManager.exe
    echo ========================================
) else (
    echo ========================================
    echo Build failed! Check the output above for errors.
    echo ========================================
)

echo.
pause
