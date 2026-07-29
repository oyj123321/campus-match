# CampusMatch: pull SQLite DB from Tencent Lighthouse to this PC every N days (via Task Scheduler).
# Requires: OpenSSH client + passwordless SSH to the server (see scripts/README-backup.md).

$ErrorActionPreference = "Stop"

$ServerHost = "106.53.82.216"
$ServerUser = "ubuntu"
$RemoteDb   = "/opt/campus-match/instance/campus_match.db"
$BackupDir  = "D:\backup\campus-match"
$KeepDays   = 60
$LogFile    = Join-Path $BackupDir "backup.log"

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$dest  = Join-Path $BackupDir "campus_match_$stamp.db"
$target = "${ServerUser}@${ServerHost}:${RemoteDb}"

function Write-Log([string]$msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

try {
    Write-Log "START pull $target -> $dest"
    & scp -o BatchMode=yes -o ConnectTimeout=20 $target $dest
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $dest)) {
        throw "scp failed (exit=$LASTEXITCODE). Is SSH key authorized on the server? Is the PC online?"
    }
    $size = (Get-Item $dest).Length
    Write-Log "OK saved $dest ($size bytes)"

    # prune old backups
    Get-ChildItem $BackupDir -Filter "campus_match_*.db" |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } |
        ForEach-Object {
            Write-Log "prune $($_.Name)"
            Remove-Item $_.FullName -Force
        }
    exit 0
}
catch {
    Write-Log "FAIL $($_.Exception.Message)"
    exit 1
}
