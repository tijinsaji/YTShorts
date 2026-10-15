@echo off
rem One-time setup for Windows: creates a .venv folder and installs ytshorts into it.
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during installation. Then run setup.bat again.
    goto :end
)

%PY% -c "import sys; sys.exit(sys.version_info < (3, 10))"
if errorlevel 1 (
    echo Python 3.10 or newer is required. You have:
    %PY% --version
    goto :end
)

echo Creating virtual environment in .venv ...
%PY% -m venv .venv || goto :fail
echo Installing ytshorts and its requirements ...
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
".venv\Scripts\python.exe" -m pip install -e . || goto :fail

echo.
echo Setup complete. Run make_shorts.bat to get started.
goto :end

:fail
echo.
echo Setup failed. See the messages above.

:end
rem Keep the window open when the script was double-clicked.
echo %cmdcmdline% | find /i "%~0" >nul && pause
endlocal
