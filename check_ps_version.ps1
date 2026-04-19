Write-Host "PowerShell Version: $($PSVersionTable.PSVersion.Major).$($PSVersionTable.PSVersion.Minor).$($PSVersionTable.PSVersion.Build)"
Write-Host "OS: $($PSVersionTable.OS)"
Write-Host "Platform: $($PSVersionTable.Platform)"
Write-Host ""
Write-Host "=== Python Check ==="
try {
    $pyResult = & python --version 2>&1
    Write-Host "Python: $pyResult"
} catch {
    Write-Host "Python: NOT INSTALLED"
}

Write-Host ""
Write-Host "=== Python3 Check ==="
try {
    $py3Result = & python3 --version 2>&1
    Write-Host "Python3: $py3Result"
} catch {
    Write-Host "Python3: NOT INSTALLED"
}

Write-Host ""
Write-Host "=== Node.js Check ==="
try {
    $nodeResult = & node --version 2>&1
    Write-Host "Node.js: $nodeResult"
} catch {
    Write-Host "Node.js: NOT INSTALLED"
}

Write-Host ""
Write-Host "=== PHP Check ==="
try {
    $phpResult = & php --version 2>&1
    Write-Host "PHP: $($phpResult[0])"
} catch {
    Write-Host "PHP: NOT INSTALLED"
}

Write-Host ""
Write-Host "=== MySQL Check ==="
try {
    $mysqlResult = & mysql --version 2>&1
    Write-Host "MySQL: $mysqlResult"
} catch {
    Write-Host "MySQL: NOT INSTALLED"
}

Write-Host ""
Write-Host "=== Disk Drives ==="
Get-WmiObject Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } | ForEach-Object {
    $free = [Math]::Round($_.FreeSpace / 1GB, 2)
    $total = [Math]::Round($_.Size / 1GB, 2)
    Write-Host "Drive $($_.DeviceID) - Total: ${total}GB, Free: ${free}GB"
}