[CmdletBinding()]
param(
    [string]$SourceIso = "E:\ISO\linuxmint-22.3-cinnamon-64bit.iso",
    [string]$OutputIso,
    [string]$WorkDir,
    [string]$GuestUser = "codex",
    [string]$GuestPassword = "codex",
    [string]$Hostname = "openq4-mint",
    [string]$TargetDisk = "/dev/sda",
    [string]$Timezone = "Etc/UTC",
    [string]$Locale = "en_US.UTF-8",
    [string]$Keyboard = "us"
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).ProviderPath
}

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function ConvertTo-WslPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullPath = Get-FullPath $Path

    if ($fullPath -match '^([A-Za-z]):\\(.*)$') {
        $drive = $matches[1].ToLowerInvariant()
        $rest = $matches[2].Replace("\", "/")
        return "/mnt/$drive/$rest"
    }

    throw "Unsupported path for WSL conversion: $fullPath"
}

function Quote-Bash {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + $Value.Replace("'", "'\''") + "'"
}

$repoRoot = Get-RepoRoot
if (-not $WorkDir) {
    $WorkDir = Join-Path (Join-Path $repoRoot ".tmp") "mint-autoinstall"
}
if (-not $OutputIso) {
    $OutputIso = Join-Path $WorkDir "linuxmint-22.3-cinnamon-openq4-autoinstall.iso"
}

$sourceIsoFull = Get-FullPath $SourceIso
if (-not (Test-Path -LiteralPath $sourceIsoFull)) {
    throw "Linux Mint ISO was not found: $sourceIsoFull"
}

$workDirFull = Get-FullPath $WorkDir
$outputIsoFull = Get-FullPath $OutputIso
New-Item -ItemType Directory -Force -Path $workDirFull | Out-Null

$preseedPath = Join-Path $workDirFull "openq4.seed"
$grubPath = Join-Path $workDirFull "grub.cfg"

$preseed = @"
d-i debian-installer/locale string $Locale
d-i localechooser/supported-locales multiselect $Locale
d-i console-setup/ask_detect boolean false
d-i keyboard-configuration/layoutcode string $Keyboard
d-i keyboard-configuration/modelcode string pc105
d-i netcfg/get_hostname string $Hostname
d-i netcfg/get_domain string local
d-i clock-setup/utc boolean true
d-i time/zone string $Timezone
d-i partman-auto/disk string $TargetDisk
d-i partman-auto/method string regular
d-i partman-auto/choose_recipe select atomic
d-i partman-lvm/device_remove_lvm boolean true
d-i partman-md/device_remove_md boolean true
d-i partman-partitioning/confirm_write_new_label boolean true
d-i partman/choose_partition select finish
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true
d-i passwd/user-fullname string Codex
d-i passwd/username string $GuestUser
d-i passwd/user-password password $GuestPassword
d-i passwd/user-password-again password $GuestPassword
d-i user-setup/encrypt-home boolean false
d-i user-setup/allow-password-weak boolean true
d-i apt-setup/restricted boolean true
d-i apt-setup/universe boolean true
d-i pkgsel/include string open-vm-tools open-vm-tools-desktop openssh-server
ubiquity ubiquity/reboot boolean true
ubiquity ubiquity/success_command string in-target systemctl enable ssh || true; in-target systemctl enable open-vm-tools || true; printf '%s\n' '$GuestUser ALL=(ALL) NOPASSWD:ALL' > /target/etc/sudoers.d/openq4-codex; chmod 0440 /target/etc/sudoers.d/openq4-codex; eject -r /cdrom || true
"@

$grub = @"
loadfont unicode

set timeout=1
set default=0
set color_normal=white/black
set color_highlight=black/light-gray

menuentry "Install Linux Mint for openQ4 (unattended)" --class linuxmint {
    set gfxpayload=keep
    linux /casper/vmlinuz automatic-ubiquity only-ubiquity boot=casper uuid=6e72f523-dc09-4880-8910-93ffa64401c5 username=mint hostname=mint file=/cdrom/preseed/openq4.seed locale=$Locale keyboard-configuration/layoutcode=$Keyboard quiet splash noprompt --
    initrd /casper/initrd.lz
}

menuentry "Start Linux Mint 22.3 Cinnamon 64-bit" --class linuxmint {
    set gfxpayload=keep
    linux /casper/vmlinuz boot=casper uuid=6e72f523-dc09-4880-8910-93ffa64401c5 username=mint hostname=mint quiet splash --
    initrd /casper/initrd.lz
}
"@

Set-Content -LiteralPath $preseedPath -Value $preseed -Encoding ASCII
Set-Content -LiteralPath $grubPath -Value $grub -Encoding ASCII

$sourceWsl = ConvertTo-WslPath $sourceIsoFull
$outputWsl = ConvertTo-WslPath $outputIsoFull
$preseedWsl = ConvertTo-WslPath $preseedPath
$grubWsl = ConvertTo-WslPath $grubPath

$xorrisoCommand = @(
    "xorriso",
    "-indev $(Quote-Bash $sourceWsl)",
    "-outdev $(Quote-Bash $outputWsl)",
    "-map $(Quote-Bash $preseedWsl) /preseed/openq4.seed",
    "-map $(Quote-Bash $grubWsl) /boot/grub/grub.cfg",
    "-boot_image any replay"
) -join " "

$bashCommand = "rm -f $(Quote-Bash $outputWsl); $xorrisoCommand"

& wsl.exe -- bash -lc $bashCommand
if ($LASTEXITCODE -ne 0) {
    throw "xorriso failed with exit code $LASTEXITCODE."
}

Write-Host "Autoinstall ISO created: $outputIsoFull"
[pscustomobject]@{
    IsoPath       = $outputIsoFull
    PreseedPath   = $preseedPath
    GrubPath      = $grubPath
    GuestUser     = $GuestUser
    GuestPassword = $GuestPassword
} | Format-List
