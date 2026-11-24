@echo off
rem Launch the game with an interpreter that actually has pygame and numpy.
rem pygame has no wheel for Python 3.14 yet (pip tries to build from source and fails),
rem so bare "python move.py" breaks if 3.14 is first on PATH. This picks a working one.
setlocal
cd /d "%~dp0"

set "PY="

rem 1) the known-good local install
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" call :try "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

rem 2) ask the py launcher, newest supported first
for %%V in (3.13 3.12 3.11 3.10 3.9) do (
    if not defined PY (
        for /f "delims=" %%i in ('py -%%V -c "import sys;print(sys.executable)" 2^>nul') do call :try "%%i"
    )
)

rem 3) anything named python on PATH
if not defined PY (
    for /f "delims=" %%i in ('where python 2^>nul') do call :try "%%i"
)

if not defined PY (
    echo.
    echo   No Python with pygame and numpy was found.
    echo.
    echo   pygame has no wheel for Python 3.14, so installing it there fails to build.
    echo   Install both on 3.13 instead:
    echo.
    echo       py -3.13 -m pip install pygame numpy
    echo.
    pause
    exit /b 1
)

if /i "%~1"=="check" (
    echo Would run with: %PY%
    "%PY%" -c "import sys,pygame,numpy;print('Python',sys.version.split()[0],'| pygame',pygame.version.ver,'| numpy',numpy.__version__)"
    exit /b 0
)

"%PY%" move.py
if errorlevel 1 pause
exit /b %errorlevel%

:try
if defined PY goto :eof
"%~1" -c "import pygame, numpy" >nul 2>&1 && set "PY=%~1"
goto :eof
