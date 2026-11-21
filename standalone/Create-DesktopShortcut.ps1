[CmdletBinding()]
param(
    [string]$Executable = (Join-Path $PSScriptRoot 'publish\KirinoDesktopPet.exe')
)

$ErrorActionPreference = 'Stop'
$program = Get-Item -LiteralPath $Executable
if ($program.PSIsContainer -or $program.Name -ne 'KirinoDesktopPet.exe') {
    throw 'Select KirinoDesktopPet.exe from the extracted Windows package.'
}

$desktop = [Environment]::GetFolderPath('DesktopDirectory')
$link = Join-Path $desktop '桐乃桌面宠物.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $program.FullName
$shortcut.WorkingDirectory = $program.DirectoryName
$shortcut.IconLocation = $program.FullName + ',0'
$shortcut.Save()
Write-Output $link
