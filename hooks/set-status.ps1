param(
  [Parameter(Mandatory = $true)]
  [string]$Status
)

$aliases = @{ working = 'busy'; done = 'success'; idle = 'success' }
if ($aliases.ContainsKey($Status)) { $Status = $aliases[$Status] }

$allowed = @('demo','thinking','ai','busy','success','error','alarm','traffic','off')
if ($allowed -notcontains $Status) { $Status = 'busy' }

$raw = [Console]::In.ReadToEnd()
$sessionId = $null

function Get-SessionKey($obj) {
  if (-not $obj) { return $null }

  foreach ($key in @(
      'conversation_id','conversationId','chat_id','chatId',
      'session_id','sessionId','agentId','composer_id','composerId','thread_id','threadId'
    )) {
    if ($obj.PSObject.Properties.Name -contains $key -and $obj.$key) {
      return [string]$obj.$key
    }
  }

  $parts = @()
  if ($obj.PSObject.Properties.Name -contains 'workspace_roots' -and $obj.workspace_roots) {
    foreach ($w in $obj.workspace_roots) { if ($w) { $parts += [string]$w } }
  }
  if ($obj.PSObject.Properties.Name -contains 'cwd' -and $obj.cwd) {
    $parts += [string]$obj.cwd
  }
  if ($obj.PSObject.Properties.Name -contains 'workspace_folder' -and $obj.workspace_folder) {
    $parts += [string]$obj.workspace_folder
  }

  if ($parts.Count -gt 0) {
    $hash = [System.BitConverter]::ToString(
      [System.Security.Cryptography.SHA256]::Create().ComputeHash(
        [Text.Encoding]::UTF8.GetBytes(($parts -join '|'))
      )
    ).Replace('-','').Substring(0, 16)
    return "ws_$hash"
  }

  return $null
}

try {
  if ($raw) {
    $obj = $raw | ConvertFrom-Json
    $sessionId = Get-SessionKey $obj
  }
}
catch {}

if (-not $sessionId) { $sessionId = 'default' }
$sessionId = ($sessionId -replace '[\\/:*?"<>|]', '_').Trim()
if (-not $sessionId) { $sessionId = 'default' }

$statusDir = "$env:USERPROFILE\.cursor\status"
New-Item -ItemType Directory -Path $statusDir -Force | Out-Null

$file = Join-Path $statusDir "$sessionId.json"
$payload = @{
  status = $Status
  ts     = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
} | ConvertTo-Json -Compress
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($file, $payload, $utf8)

# 忙碌类事件刷新心跳，防止工具间隔时误显示绿灯
$busyLike = @('busy','thinking','ai','demo')
if ($busyLike -contains $Status) {
  $hb = Join-Path $statusDir '_heartbeat.json'
  $hbPayload = @{ ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ') } | ConvertTo-Json -Compress
  [System.IO.File]::WriteAllText($hb, $hbPayload, $utf8)
}

try {
  $log = Join-Path $statusDir 'hook.log'
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Status | $sessionId" | Add-Content -Path $log -Encoding UTF8
  $lines = Get-Content $log -Tail 200 -ErrorAction SilentlyContinue
  if ($lines) { $lines | Set-Content $log -Encoding UTF8 }
}
catch {}
