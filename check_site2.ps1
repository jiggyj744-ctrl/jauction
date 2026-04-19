# Check main page
Write-Host "=== MAIN PAGE ==="
$r = Invoke-WebRequest -Uri 'https://gfauction.co.kr/main/main.php' -UseBasicParsing -TimeoutSec 15
Write-Host "Status: $($r.StatusCode)"
$text = $r.Content.Substring(0, [Math]::Min(5000, $r.Content.Length))
Write-Host $text

Write-Host ""
Write-Host "=== ROBOTS.TXT ==="
try {
    $r2 = Invoke-WebRequest -Uri 'https://gfauction.co.kr/robots.txt' -UseBasicParsing -TimeoutSec 10
    Write-Host $r2.Content
} catch {
    Write-Host "No robots.txt found"
}

Write-Host ""
Write-Host "=== SITEMAP ==="
try {
    $r3 = Invoke-WebRequest -Uri 'https://gfauction.co.kr/sitemap.xml' -UseBasicParsing -TimeoutSec 10
    Write-Host $r3.Content.Substring(0, [Math]::Min(2000, $r3.Content.Length))
} catch {
    Write-Host "No sitemap.xml found"
}