[CmdletBinding()]
param(
    [string]$IsoPath = "E:\ISO\linuxmint-22.3-cinnamon-64bit.iso",
    [string]$VmName = "openQ4-LinuxMint",
    [string]$VmRoot,
    [int]$MemoryMB = 8192,
    [int]$CpuCount = 4,
    [int]$DiskGB = 96,
    [int]$DataDiskGB = 32,
    [switch]$Force,
    [switch]$DiskFirst,
    [switch]$DetachIso,
    [switch]$EnableVnc,
    [int]$VncPort = 5901,
    [string]$VncPassword = "",
    [switch]$Start,
    [ValidateSet("gui", "nogui")]
    [string]$StartMode = "gui"
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).ProviderPath
}

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function ConvertTo-VmxPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FullPath $Path).Replace("\", "/")
}

function Find-VMwareWorkstation {
    $roots = New-Object System.Collections.Generic.List[string]

    if ($env:VMWARE_WORKSTATION_HOME) {
        $roots.Add($env:VMWARE_WORKSTATION_HOME)
    }

    foreach ($registryPath in @(
        "HKLM:\SOFTWARE\VMware, Inc.\VMware Workstation",
        "HKLM:\SOFTWARE\WOW6432Node\VMware, Inc.\VMware Workstation"
    )) {
        $props = Get-ItemProperty -Path $registryPath -ErrorAction SilentlyContinue
        if ($props -and $props.InstallPath) {
            $roots.Add($props.InstallPath)
        }
    }

    foreach ($candidate in @(
        "C:\Program Files\VMware\VMware Workstation",
        "C:\Program Files (x86)\VMware\VMware Workstation"
    )) {
        $roots.Add($candidate)
    }

    foreach ($root in ($roots | Select-Object -Unique)) {
        if (-not $root) {
            continue
        }

        $root = Get-FullPath $root
        $vmrun = Join-Path $root "vmrun.exe"
        $vdisk = Join-Path $root "vmware-vdiskmanager.exe"
        if ((Test-Path -LiteralPath $vmrun) -and (Test-Path -LiteralPath $vdisk)) {
            return [pscustomobject]@{
                Root  = $root
                Vmrun = $vmrun
                Vdisk = $vdisk
            }
        }
    }

    throw "VMware Workstation tools were not found. Set VMWARE_WORKSTATION_HOME or install VMware Workstation."
}

function Assert-PathInside {
    param(
        [Parameter(Mandatory = $true)][string]$Child,
        [Parameter(Mandatory = $true)][string]$Parent
    )

    $resolvedChild = (Resolve-Path -LiteralPath $Child).ProviderPath
    $resolvedParent = (Resolve-Path -LiteralPath $Parent).ProviderPath.TrimEnd("\")
    $prefix = "$resolvedParent\"
    if (-not $resolvedChild.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate on '$resolvedChild' because it is not under '$resolvedParent'."
    }
}

function Format-VmxEntry {
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [string]$Value
    )

    if ($null -eq $Value) {
        $Value = ""
    }
    $escaped = $Value.Replace('"', '\"')
    return "$Key = `"$escaped`""
}

function Set-VmxEntries {
    param(
        [Parameter(Mandatory = $true)][string]$VmxPath,
        [Parameter(Mandatory = $true)]$Entries
    )

    $lines = @()
    if (Test-Path -LiteralPath $VmxPath) {
        $lines = @(Get-Content -LiteralPath $VmxPath)
    }

    foreach ($key in $Entries.Keys) {
        $line = Format-VmxEntry -Key $key -Value ([string]$Entries[$key])
        $pattern = "^\s*$([regex]::Escape($key))\s*="
        $updated = $false
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match $pattern) {
                $lines[$i] = $line
                $updated = $true
                break
            }
        }

        if (-not $updated) {
            $lines += $line
        }
    }

    Set-Content -LiteralPath $VmxPath -Value $lines -Encoding ASCII
}

function Get-VmxEntries {
    param([Parameter(Mandatory = $true)][string]$VmxPath)

    $entries = @{}
    if (-not (Test-Path -LiteralPath $VmxPath)) {
        return $entries
    }

    foreach ($line in Get-Content -LiteralPath $VmxPath) {
        if ($line -match '^\s*([^=\s]+)\s*=\s*"(.*)"\s*$') {
            $entries[$matches[1]] = $matches[2].Replace('\"', '"')
        }
    }

    return $entries
}

function Remove-VmxEntries {
    param(
        [Parameter(Mandatory = $true)][string]$VmxPath,
        [Parameter(Mandatory = $true)][string[]]$Keys
    )

    if (-not (Test-Path -LiteralPath $VmxPath)) {
        return
    }

    $lines = @(Get-Content -LiteralPath $VmxPath)
    foreach ($key in $Keys) {
        $pattern = "^\s*$([regex]::Escape($key))\s*="
        $lines = @($lines | Where-Object { $_ -notmatch $pattern })
    }

    Set-Content -LiteralPath $VmxPath -Value $lines -Encoding ASCII
}

function Add-SharedFolderEntries {
    param(
        [Parameter(Mandatory = $true)]$Entries,
        [Parameter(Mandatory = $true)]$Shares
    )

    $Entries["isolation.tools.hgfs.disable"] = "FALSE"
    $Entries["hgfs.mapRootShare"] = "TRUE"
    $Entries["sharedFolder.maxNum"] = [string]$Shares.Count

    for ($i = 0; $i -lt $Shares.Count; $i++) {
        $share = $Shares[$i]
        $prefix = "sharedFolder$i"
        $Entries["$prefix.present"] = "TRUE"
        $Entries["$prefix.enabled"] = "TRUE"
        $Entries["$prefix.readAccess"] = "TRUE"
        $Entries["$prefix.writeAccess"] = $(if ($share.Writable) { "TRUE" } else { "FALSE" })
        $Entries["$prefix.hostPath"] = ConvertTo-VmxPath $share.Path
        $Entries["$prefix.guestName"] = $share.Name
        $Entries["$prefix.expiration"] = "never"
        $Entries["$prefix.followSymlinks"] = "TRUE"
    }
}

$repoRoot = Get-RepoRoot
if (-not $VmRoot) {
    $VmRoot = Join-Path (Join-Path $repoRoot ".tmp") "vmware"
}

$isoFullPath = Get-FullPath $IsoPath
if (-not (Test-Path -LiteralPath $isoFullPath)) {
    throw "Linux Mint ISO was not found: $isoFullPath"
}

$vmware = Find-VMwareWorkstation
$vmRootFullPath = Get-FullPath $VmRoot
$vmDir = Join-Path $vmRootFullPath $VmName
$vmxPath = Join-Path $vmDir "$VmName.vmx"
$diskPath = Join-Path $vmDir "$VmName.vmdk"

New-Item -ItemType Directory -Force -Path $vmRootFullPath | Out-Null

if ($Force -and (Test-Path -LiteralPath $vmDir)) {
    Assert-PathInside -Child $vmDir -Parent $vmRootFullPath
    Remove-Item -LiteralPath $vmDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $vmDir | Out-Null

if (-not (Test-Path -LiteralPath $diskPath)) {
    Write-Host "Creating VMware disk: $diskPath ($DiskGB GB)"
    & $vmware.Vdisk -c -s "${DiskGB}GB" -a lsilogic -t 0 $diskPath
    if ($LASTEXITCODE -ne 0) {
        throw "vmware-vdiskmanager failed with exit code $LASTEXITCODE."
    }
}

$existingVmxEntries = Get-VmxEntries -VmxPath $vmxPath
$dataDiskFileName = $existingVmxEntries["scsi0:1.fileName"]
if (-not $dataDiskFileName) {
    $legacyDataDisk = Join-Path $vmDir "$VmName-0.vmdk"
    if (Test-Path -LiteralPath $legacyDataDisk) {
        $dataDiskFileName = Split-Path -Leaf $legacyDataDisk
    } else {
        $dataDiskFileName = "$VmName-data.vmdk"
    }
}

$dataDiskPath = Join-Path $vmDir $dataDiskFileName
if (-not (Test-Path -LiteralPath $dataDiskPath)) {
    Write-Host "Creating VMware data disk: $dataDiskPath ($DataDiskGB GB)"
    & $vmware.Vdisk -c -s "${DataDiskGB}GB" -a lsilogic -t 0 $dataDiskPath
    if ($LASTEXITCODE -ne 0) {
        throw "vmware-vdiskmanager failed with exit code $LASTEXITCODE."
    }
}

$entries = [ordered]@{
    ".encoding"                         = "UTF-8"
    "config.version"                    = "8"
    "virtualHW.version"                 = "22"
    "virtualHW.productCompatibility"    = "hosted"
    "displayName"                       = $VmName
    "guestOS"                           = "ubuntu-64"
    "firmware"                          = "bios"
    "uuid.action"                       = "create"
    "memsize"                           = [string]$MemoryMB
    "numvcpus"                          = [string]$CpuCount
    "cpuid.coresPerSocket"              = [string]$CpuCount
    "hpet0.present"                     = "TRUE"
    "vmci0.present"                     = "TRUE"
    "pciBridge0.present"                = "TRUE"
    "pciBridge4.present"                = "TRUE"
    "pciBridge4.virtualDev"             = "pcieRootPort"
    "pciBridge4.functions"              = "8"
    "pciBridge5.present"                = "TRUE"
    "pciBridge5.virtualDev"             = "pcieRootPort"
    "pciBridge5.functions"              = "8"
    "pciBridge6.present"                = "TRUE"
    "pciBridge6.virtualDev"             = "pcieRootPort"
    "pciBridge6.functions"              = "8"
    "pciBridge7.present"                = "TRUE"
    "pciBridge7.virtualDev"             = "pcieRootPort"
    "pciBridge7.functions"              = "8"
    "tools.syncTime"                    = "TRUE"
    "bios.bootDelay"                    = "3000"
    "bios.bootOrder"                    = $(if ($DiskFirst -or $DetachIso) { "hdd,cdrom" } else { "cdrom,hdd" })
    "usb.present"                       = "TRUE"
    "ehci.present"                      = "TRUE"
    "usb_xhci.present"                  = "TRUE"
    "sound.present"                     = "TRUE"
    "sound.autoDetect"                  = "TRUE"
    "sound.virtualDev"                  = "hdaudio"
    "ethernet0.present"                 = "TRUE"
    "ethernet0.connectionType"          = "nat"
    "ethernet0.virtualDev"              = "e1000e"
    "ethernet0.addressType"             = "generated"
    "mks.enable3d"                      = "TRUE"
    "svga.graphicsMemoryKB"             = "1048576"
    "svga.vramSize"                     = "268435456"
    "svga.autodetect"                   = "FALSE"
    "scsi0.present"                     = "TRUE"
    "scsi0.virtualDev"                  = "lsilogic"
    "scsi0:0.present"                   = "TRUE"
    "scsi0:0.fileName"                  = (Split-Path -Leaf $diskPath)
    "scsi0:0.deviceType"                = "scsi-hardDisk"
    "scsi0:1.present"                   = "TRUE"
    "scsi0:1.fileName"                  = $dataDiskFileName
    "scsi0:1.deviceType"                = "scsi-hardDisk"
    "ide1:0.present"                    = "TRUE"
    "ide1:0.fileName"                   = (ConvertTo-VmxPath $isoFullPath)
    "ide1:0.deviceType"                 = "cdrom-image"
    "ide1:0.startConnected"             = $(if ($DetachIso) { "FALSE" } else { "TRUE" })
    "floppy0.present"                   = "FALSE"
    "serial0.present"                   = "FALSE"
    "parallel0.present"                 = "FALSE"
}

if ($EnableVnc) {
    $entries["RemoteDisplay.vnc.enabled"] = "TRUE"
    $entries["RemoteDisplay.vnc.port"] = [string]$VncPort
    $entries["RemoteDisplay.vnc.password"] = $VncPassword
}

$shares = New-Object System.Collections.Generic.List[object]
$shares.Add([pscustomobject]@{ Name = "openQ4"; Path = $repoRoot; Writable = $true })

$gameLibs = Get-FullPath (Join-Path (Split-Path -Parent $repoRoot) "openQ4-game")
if (Test-Path -LiteralPath $gameLibs) {
    $shares.Add([pscustomobject]@{ Name = "openQ4-game"; Path = $gameLibs; Writable = $false })
} else {
    Write-Warning "openQ4-game was not found at $gameLibs; skipping that shared folder."
}

$quake4 = "C:\Program Files (x86)\Steam\steamapps\common\Quake 4"
if (Test-Path -LiteralPath $quake4) {
    $shares.Add([pscustomobject]@{ Name = "Quake4"; Path = $quake4; Writable = $false })
} else {
    Write-Warning "Quake 4 install was not found at '$quake4'; runtime smoke will need a basepath later."
}

$downloads = Join-Path $env:USERPROFILE "Downloads"
if (Test-Path -LiteralPath $downloads) {
    $shares.Add([pscustomobject]@{ Name = "Downloads"; Path = $downloads; Writable = $false })
}

Add-SharedFolderEntries -Entries $entries -Shares $shares
Remove-VmxEntries -VmxPath $vmxPath -Keys @(
    "sata0.present",
    "sata0:1.present",
    "sata0:1.fileName",
    "sata0:1.deviceType",
    "sata0:1.startConnected",
    "sata0.pciSlotNumber",
    "mks.forceDiscreteGPU",
    "scsi0.pciSlotNumber",
    "usb.pciSlotNumber",
    "ethernet0.pciSlotNumber",
    "sound.pciSlotNumber",
    "ehci.pciSlotNumber",
    "usb_xhci.pciSlotNumber",
    "vmci0.pciSlotNumber",
    "pciBridge0.pciSlotNumber",
    "pciBridge4.pciSlotNumber",
    "pciBridge5.pciSlotNumber",
    "pciBridge6.pciSlotNumber",
    "pciBridge7.pciSlotNumber",
    "vmotion.checkpointFBSize",
    "vmotion.checkpointSVGAPrimarySize",
    "vmotion.svga.mobMaxSize",
    "vmotion.svga.graphicsMemoryKB",
    "vmotion.svga.supports3D",
    "vmotion.svga.baseCapsLevel",
    "vmotion.svga.maxPointSize",
    "vmotion.svga.maxTextureSize",
    "vmotion.svga.maxVolumeExtent",
    "vmotion.svga.maxTextureAnisotropy",
    "vmotion.svga.lineStipple",
    "vmotion.svga.dxMaxConstantBuffers",
    "vmotion.svga.dxProvokingVertex",
    "vmotion.svga.sm41",
    "vmotion.svga.multisample2x",
    "vmotion.svga.multisample4x",
    "vmotion.svga.msFullQuality",
    "vmotion.svga.logicOps",
    "vmotion.svga.bc67",
    "vmotion.svga.sm5",
    "vmotion.svga.multisample8x",
    "vmotion.svga.logicBlendOps",
    "vmotion.svga.maxForcedSampleCount",
    "vmotion.svga.gl43"
)
Set-VmxEntries -VmxPath $vmxPath -Entries $entries

Write-Host "VM configured: $vmxPath"
Write-Host "Shared folders:"
foreach ($share in $shares) {
    $mode = if ($share.Writable) { "writable" } else { "readonly" }
    Write-Host "  $($share.Name): $($share.Path) ($mode)"
}

if ($Start) {
    Write-Host "Starting VM through VMware Workstation ($StartMode)..."
    & $vmware.Vmrun -T ws start $vmxPath $StartMode
    if ($LASTEXITCODE -ne 0) {
        throw "vmrun start failed with exit code $LASTEXITCODE."
    }
}

[pscustomobject]@{
    VmxPath = $vmxPath
    VmDir   = $vmDir
    IsoPath = $isoFullPath
    Vmrun   = $vmware.Vmrun
} | Format-List
