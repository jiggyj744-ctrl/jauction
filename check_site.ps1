$r = Invoke-WebRequest -Uri 'https://gfauction.co.kr' -UseBasicParsing -TimeoutSec 15
Write-Host "Status: $($r.StatusCode)"
Write-Host "Content-Type: $($r.Headers['Content-Type'])"
Write-Host "Server: $($r.Headers['Server'])"
Write-Host "=== First 3000 chars ==="
$text = $r.Content.Substring(0, [Math]::Min(3000, $r.Content.Length))
Write-Host $text