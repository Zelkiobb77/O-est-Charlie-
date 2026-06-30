@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title OSTING - OU EST CHARLY ?  by Zelkiobb

REM ============================================================
REM  Verification de Python
REM ============================================================
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERREUR] Python est introuvable.
    echo Installe Python 3.10+ depuis https://www.python.org/downloads/
    echo et coche bien la case "Add Python to PATH" pendant l'installation.
    echo.
    pause
    exit /b 1
)

REM ============================================================
REM  Verification / installation des dependances (1er lancement)
REM ============================================================
python -c "import rich, pyfiglet, phonenumbers, dns, PIL, whois, requests" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Premiere utilisation : installation des dependances...
    echo.
    python -m pip install -r requirements.txt
    echo.
)

REM ============================================================
REM  Mode passe-plat : OSTING.bat username charly
REM ============================================================
if not "%~1"=="" (
    python -m osting %*
    exit /b %errorlevel%
)

REM ============================================================
REM  Double-clic : on lance le menu interactif colore (Python/rich)
REM ============================================================
python -m osting menu
exit /b %errorlevel%
