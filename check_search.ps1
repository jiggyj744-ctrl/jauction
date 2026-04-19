# Check search list page
Write-Host "=== SEARCH LIST PAGE ==="
$url = 'https://gfauction.co.kr/search/search_list.php?aresult=all&sno=2026'
$r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15
Write-Host "Status: $($r.StatusCode)"
$text = $r.Content.Substring(0, [Math]::Min(8000, $r.Content.Length))
Write-Host $text