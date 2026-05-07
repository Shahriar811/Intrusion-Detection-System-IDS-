$ErrorActionPreference = "Stop"

$HERE = Split-Path -Parent $MyInvocation.MyCommand.Path
$NGROK_EXE = Join-Path $HERE "ngrok.exe"
$TOKEN_FILE = Join-Path $HERE "ngrok_token.txt"
$PORT = 8000

function Write-Section($msg) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host " $msg" -ForegroundColor Cyan
    Write-Host "===============================================================" -ForegroundColor Cyan
    Write-Host ""
}

# ---------------------------------------------------------------
# 1. Check that ngrok auth token is configured
# ---------------------------------------------------------------
if (!(Test-Path $TOKEN_FILE)) {
    Write-Section "First-time setup: ngrok authtoken required"
    Write-Host "1. Create a free account at:"
    Write-Host "     https://dashboard.ngrok.com/signup"
    Write-Host ""
    Write-Host "2. Copy your authtoken from:"
    Write-Host "     https://dashboard.ngrok.com/get-started/your-authtoken"
    Write-Host ""
    Write-Host "3. Create this file and paste the token inside it:"
    Write-Host "     $TOKEN_FILE"
    Write-Host ""
    Write-Host "4. Re-run this script."
    exit 1
}

$TOKEN = (Get-Content $TOKEN_FILE -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($TOKEN)) {
    Write-Host "ngrok_token.txt is empty. Paste your ngrok authtoken into it and try again." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------
# 2. Download ngrok if not present
# ---------------------------------------------------------------
if (!(Test-Path $NGROK_EXE)) {
    Write-Section "Downloading ngrok (one-time)..."
    $zip = Join-Path $HERE "ngrok.zip"
    Invoke-WebRequest -Uri "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $HERE -Force
    Remove-Item $zip -Force
    Write-Host "ngrok installed to: $NGROK_EXE"
}

# ---------------------------------------------------------------
# 3. Register ngrok authtoken
# ---------------------------------------------------------------
& $NGROK_EXE config add-authtoken $TOKEN | Out-Null

# ---------------------------------------------------------------
# 4. Start the FastAPI server in a new PowerShell window
# ---------------------------------------------------------------
$alreadyUp = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$PORT/models" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($r.StatusCode -eq 200) { $alreadyUp = $true }
} catch { }

if (!$alreadyUp) {
    Write-Section "Starting FastAPI server (new window)..."
    $apiStart = "cd `"$HERE`"; `$env:API_HOST='127.0.0.1'; `$env:API_PORT='$PORT'; .\run.ps1"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiStart

    Write-Host "Waiting for API to come up on http://127.0.0.1:$PORT ..."
    Write-Host "(First boot will be slow because TensorFlow + the saved models load on demand.)"
    $ready = $false
    for ($i = 0; $i -lt 180; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$PORT/models" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (!$ready) {
        Write-Host "API did not come up within 6 minutes. Check the other PowerShell window for errors, then re-run this script." -ForegroundColor Red
        exit 1
    }
    Write-Host "API is up." -ForegroundColor Green
} else {
    Write-Host "API is already running on port $PORT. Skipping local startup." -ForegroundColor Green
}

# ---------------------------------------------------------------
# 5. Start the ngrok public tunnel
# ---------------------------------------------------------------
Write-Section "Opening public HTTPS tunnel (ngrok)"
Write-Host "Look below for a line like:  Forwarding  https://XXXX.ngrok-free.app -> http://localhost:$PORT"
Write-Host "That https://XXXX.ngrok-free.app URL is your global API endpoint."
Write-Host ""
Write-Host "Use it in:"
Write-Host "   - Web UI:         https://XXXX.ngrok-free.app/"
Write-Host "   - API Docs:       https://XXXX.ngrok-free.app/docs"
Write-Host "   - Models list:    https://XXXX.ngrok-free.app/models"
Write-Host ""
Write-Host "Press Ctrl+C here to stop the public tunnel (the API keeps running in the other window)."
Write-Host ""

& $NGROK_EXE http $PORT
