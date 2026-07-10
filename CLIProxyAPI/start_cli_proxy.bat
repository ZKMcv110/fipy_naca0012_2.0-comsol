@echo off
setlocal

set "ROOT=%~dp0"
set "EXE=%ROOT%dist\CLIProxyAPI_7.0.6_windows_amd64\cli-proxy-api.exe"
set "CONFIG=%ROOT%config.yaml"
set "PIDFILE=%ROOT%.cliproxy.pid"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Start-Process -FilePath '%EXE%' -ArgumentList '-config','%CONFIG%','-local-model' -WorkingDirectory '%ROOT%' -WindowStyle Hidden -PassThru; Set-Content -Path '%PIDFILE%' -Value $p.Id; Write-Host ('CLIProxyAPI started. PID=' + $p.Id + ', URL=http://127.0.0.1:5055')"

endlocal
