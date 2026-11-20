[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$Revision,

    [string]$Destination
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$commit = & git -C $repo rev-parse --verify --end-of-options "$Revision^{commit}"
if ($LASTEXITCODE -ne 0) {
    throw "Git revision not found: $Revision"
}

if (-not $Destination) {
    $codexDirectory = $env:CODEX_HOME
    if (-not $codexDirectory) {
        $codexDirectory = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
    }
    $Destination = Join-Path $codexDirectory 'pets\kirino-chibi'
}
$Destination = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Destination)
$tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$temp = Join-Path $tempRoot ('kirino-restore-' + [Guid]::NewGuid().ToString('N'))
$zip = Join-Path $temp 'package.zip'
$staged = Join-Path $temp 'staged'
$backup = Join-Path $temp 'backup'
$files = @('spritesheet.webp', 'pet.json')
$keepBackup = $false
[void](New-Item -ItemType Directory -Path $temp)

try {
    & git -C $repo archive --format=zip "--output=$zip" $commit -- pet/spritesheet.webp pet/pet.json
    if ($LASTEXITCODE -ne 0) {
        throw "The selected commit does not contain the complete pet package: $Revision"
    }
    Expand-Archive -LiteralPath $zip -DestinationPath $staged
    $package = Join-Path $staged 'pet'
    $manifest = Get-Content -LiteralPath (Join-Path $package 'pet.json') -Encoding UTF8 -Raw | ConvertFrom-Json
    if ($manifest.id -ne 'kirino-chibi' -or $manifest.spritesheetPath -ne 'spritesheet.webp') {
        throw 'The manifest does not match the Kirino pet package.'
    }
    if ((Get-Item -LiteralPath (Join-Path $package 'spritesheet.webp')).Length -eq 0) {
        throw 'The sprite sheet is empty.'
    }

    [void](New-Item -ItemType Directory -Path $Destination -Force)
    [void](New-Item -ItemType Directory -Path $backup)
    foreach ($file in $files) {
        $target = Join-Path $Destination $file
        if (Test-Path -LiteralPath $target -PathType Container) {
            throw "Expected an installation file but found a directory: $target"
        }
        if (Test-Path -LiteralPath $target -PathType Leaf) {
            Copy-Item -LiteralPath $target -Destination $backup
        }
    }

    $attempted = @()
    try {
        foreach ($file in $files) {
            $source = Join-Path $package $file
            $target = Join-Path $Destination $file
            $attempted += $file
            Copy-Item -LiteralPath $source -Destination $target -Force
            if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash) {
                throw "Hash verification failed for $target"
            }
        }
    }
    catch {
        $installFailure = $_
        try {
            foreach ($file in $attempted) {
                $saved = Join-Path $backup $file
                $target = Join-Path $Destination $file
                if (Test-Path -LiteralPath $saved -PathType Leaf) {
                    Copy-Item -LiteralPath $saved -Destination $target -Force
                }
                elseif (Test-Path -LiteralPath $target -PathType Leaf) {
                    Remove-Item -LiteralPath $target -Force
                }
            }
        }
        catch {
            $keepBackup = $true
            throw "Installation failed: $installFailure. Automatic recovery failed: $_. Backup: $backup"
        }
        throw $installFailure
    }

    Write-Output "Installed $Revision ($commit) to $Destination"
}
finally {
    $resolvedTemp = (Resolve-Path -LiteralPath $temp).ProviderPath
    if (-not $keepBackup -and $resolvedTemp -eq $temp -and $resolvedTemp.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}
