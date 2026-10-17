@echo off
rem Run make-subtitles: burn subtitles from a text file into a video.
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo ytshorts is not set up yet. Run setup.bat first.
    goto :end
)
"%~dp0.venv\Scripts\python.exe" -m ytshorts.make_subtitles %*

:end
rem Keep the window open when the script was double-clicked.
echo %cmdcmdline% | find /i "%~0" >nul && pause
