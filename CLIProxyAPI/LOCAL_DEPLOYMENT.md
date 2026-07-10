# Local Deployment

CLIProxyAPI has been deployed locally in this folder.

## Start

Run:

```bat
start_cli_proxy.bat
```

Service URL:

```text
http://127.0.0.1:5055
```

Local test API key:

```text
local-test-key
```

## Stop

Run:

```bat
stop_cli_proxy.bat
```

## Smoke Test

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:5055/v1/models -Headers @{Authorization='Bearer local-test-key'} -UseBasicParsing
```

The service can start without upstream accounts, but `/v1/models` will return an empty list until Gemini, Claude, Codex, OpenAI-compatible, or other provider credentials are added to `config.yaml` or imported through the supported login commands.
