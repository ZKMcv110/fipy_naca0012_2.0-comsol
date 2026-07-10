@echo off
setlocal

set "ROOT=%~dp0"
set "PIDFILE=%ROOT%.cliproxy.pid"

if not exist "%PIDFILE%" (
  echo PID file not found: %PIDFILE%
  echo If the service is running, stop it from Task Manager or use:
  echo   powershell -NoProfile -Command "Get-Process cli-proxy-api | Stop-Process"
  exit /b 1
)

for /f "usebackq delims=" %%p in ("%PIDFILE%") do set "PID=%%p"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Stop-Process -Id %PID% -ErrorAction SilentlyContinue; Write-Host 'CLIProxyAPI stopped if it was running.'"
del "%PIDFILE%" >nul 2>nul

endlocal
