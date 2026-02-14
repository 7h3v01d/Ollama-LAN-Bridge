@echo off
:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script MUST be run as Administrator.
    echo Right-click this file and select "Run as Administrator".
    pause
    exit /b
)

echo ---------------------------------------------------------
echo 🛠️  Configuring Ollama for LAN Access...
echo ---------------------------------------------------------

:: 1. Set System Environment Variable
echo [*] Setting OLLAMA_HOST to 0.0.0.0...
setx OLLAMA_HOST "0.0.0.0" /m

:: 2. Add Firewall Rule for Port 11434
echo [*] Opening Firewall Port 11434 (Inbound)...
netsh advfirewall firewall add rule name="Ollama LAN Access" dir=in action=allow protocol=TCP localport=11434

if %errorLevel% == 0 (
    echo.
    echo ---------------------------------------------------------
    echo ✅ SUCCESS: Environment set and Firewall rule added.
    echo.
    echo ⚠️  ACTION REQUIRED:
    echo 1. Right-click the Ollama icon in your System Tray and "Quit".
    echo 2. Relaunch Ollama from the Start Menu.
    echo ---------------------------------------------------------
) else (
    echo [ERROR] Something went wrong with the firewall configuration.
)

pause