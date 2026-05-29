# 薄封装：转发到 Python（与 hooks.json 一致，便于手动测试）
param(
  [Parameter(Mandatory = $true)]
  [string]$Status
)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $scriptDir 'set-status.py'
$raw = [Console]::In.ReadToEnd()
if ($raw) {
  $raw | & python -u $py $Status
} else {
  & python -u $py $Status
}
