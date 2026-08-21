[CmdletBinding()]
param(
    [ValidateSet("Start", "Ip", "Bootstrap", "Assets", "Build", "Smoke", "Launcher", "All", "Snapshot", "Stop")]
    [string[]]$Action = @("All"),
    [string]$VmName = "openQ4-LinuxMint",
    [string]$VmRoot,
    [string]$VmxPath,
    [string]$GuestUser = "codex",
    [securestring]$GuestPassword,
    [string]$GuestPasswordPlain,
    [ValidateSet("gui", "nogui")]
    [string]$StartMode = "gui",
    [int]$ToolsTimeoutSeconds = 300,
    [string]$SnapshotName = "openq4-ready",
    [string]$GuestBasePath = "/mnt/openq4-data/Quake4",
    [string]$GuestHostRepoShare = "/mnt/hgfs/openQ4",
    [string]$GuestHostGameLibsShare = "/mnt/hgfs/openQ4-game",
    [string]$GuestHostResultsDir,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).ProviderPath
}

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
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
        if (Test-Path -LiteralPath $vmrun) {
            return [pscustomobject]@{ Root = $root; Vmrun = $vmrun }
        }
    }

    throw "VMware Workstation vmrun.exe was not found."
}

function ConvertFrom-SecureStringToPlainText {
    param([Parameter(Mandatory = $true)][securestring]$Secure)
    $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Invoke-Vmrun {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$AllowFailure
    )

    & $script:Vmrun -T ws @Arguments
    $exitCode = $LASTEXITCODE
    if (($exitCode -ne 0) -and -not $AllowFailure) {
        throw "vmrun failed with exit code ${exitCode}: $($Arguments -join ' ')"
    }
    return $exitCode
}

function Invoke-GuestVmrun {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $guestArgs = @("-gu", $script:GuestUser, "-gp", $script:GuestPasswordPlain)
    & $script:Vmrun -T ws @guestArgs @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "guest vmrun failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

function Test-VmRunning {
    $running = & $script:Vmrun -T ws list
    return ($running -contains $script:VmxPath)
}

function Start-openQ4Vm {
    if (Test-VmRunning) {
        Write-Host "VM is already running."
        return
    }

    Write-Host "Starting VM ($StartMode): $script:VmxPath"
    Invoke-Vmrun -Arguments @("start", $script:VmxPath, $StartMode) | Out-Null
}

function Wait-VMwareTools {
    param([int]$TimeoutSeconds)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $state = & $script:Vmrun -T ws checkToolsState $script:VmxPath 2>$null
        if ($LASTEXITCODE -eq 0 -and ($state -match "running")) {
            Write-Host "VMware Tools are running."
            return
        }

        Write-Host "Waiting for VMware Tools... ($state)"
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for VMware Tools. Finish the Mint install, reboot into the installed desktop, and install/open-vm-tools if needed."
}

function Enable-openQ4SharedFolders {
    Write-Host "Enabling VMware shared folders."
    Invoke-Vmrun -Arguments @("enableSharedFolders", $script:VmxPath) -AllowFailure | Out-Null
}

function Copy-AndRunGuestScript {
    param(
        [Parameter(Mandatory = $true)][string]$HostScript,
        [Parameter(Mandatory = $true)][string]$GuestScriptName,
        [string[]]$ScriptArguments = @()
    )

    if (-not (Test-Path -LiteralPath $HostScript)) {
        throw "Guest script not found: $HostScript"
    }

    $guestDir = "/tmp/openq4-vmware"
    $guestPath = "$guestDir/$GuestScriptName"
    Invoke-GuestVmrun -Arguments @("runProgramInGuest", $script:VmxPath, "/bin/mkdir", "-p", $guestDir)
    Invoke-GuestVmrun -Arguments @("CopyFileFromHostToGuest", $script:VmxPath, $HostScript, $guestPath)
    Invoke-GuestVmrun -Arguments @("runProgramInGuest", $script:VmxPath, "/bin/chmod", "+x", $guestPath)

    $envArgs = @(
        "OPENQ4_SUDO_PASSWORD=$script:GuestPasswordPlain",
        "OPENQ4_BASEPATH=$script:GuestBasePath",
        "OPENQ4_HOST_REPO_SHARE=$script:GuestHostRepoShare",
        "OPENQ4_HOST_GAMELIBS_SHARE=$script:GuestHostGameLibsShare"
    )
    if ($script:GuestHostResultsDir) {
        $envArgs += "OPENQ4_HOST_RESULTS_DIR=$script:GuestHostResultsDir"
    }
    Invoke-GuestVmrun -Arguments (@("runProgramInGuest", $script:VmxPath, "/usr/bin/env") + $envArgs + @("/bin/bash", $guestPath) + $ScriptArguments)
}

$repoRoot = Get-RepoRoot
if (-not $VmRoot) {
    $VmRoot = Join-Path (Join-Path $repoRoot ".tmp") "vmware"
}
if (-not $VmxPath) {
    $VmxPath = Join-Path (Join-Path (Get-FullPath $VmRoot) $VmName) "$VmName.vmx"
}
$VmxPath = Get-FullPath $VmxPath
if (-not (Test-Path -LiteralPath $VmxPath)) {
    throw "VMX was not found: $VmxPath. Run tools/vmware/New-openQ4LinuxMintVm.ps1 first."
}

$vmware = Find-VMwareWorkstation
$script:Vmrun = $vmware.Vmrun
$script:VmxPath = $VmxPath
$script:GuestUser = $GuestUser
$script:GuestBasePath = $GuestBasePath
$script:GuestHostRepoShare = $GuestHostRepoShare
$script:GuestHostGameLibsShare = $GuestHostGameLibsShare
$script:GuestHostResultsDir = $GuestHostResultsDir

$needsGuestLogin = @($Action | Where-Object { $_ -in @("Bootstrap", "Assets", "Build", "Smoke", "Launcher", "All") }).Count -gt 0
if ($needsGuestLogin) {
    if (-not $GuestPasswordPlain) {
        if (-not $GuestPassword) {
            $GuestPassword = Read-Host "Guest password for '$GuestUser'" -AsSecureString
        }
        $GuestPasswordPlain = ConvertFrom-SecureStringToPlainText -Secure $GuestPassword
    }
    $script:GuestPasswordPlain = $GuestPasswordPlain
}

if (($Action -contains "Start") -or ($Action -contains "All") -or ($Action -contains "Bootstrap") -or ($Action -contains "Assets") -or ($Action -contains "Build") -or ($Action -contains "Smoke") -or ($Action -contains "Launcher") -or ($Action -contains "Ip")) {
    if (-not $NoStart) {
        Start-openQ4Vm
    }
}

if ($needsGuestLogin) {
    Wait-VMwareTools -TimeoutSeconds $ToolsTimeoutSeconds
    Enable-openQ4SharedFolders
}

$guestDir = Join-Path $PSScriptRoot "guest"
$bootstrapScript = Join-Path $guestDir "openq4-linux-mint-bootstrap.sh"
$assetScript = Join-Path $guestDir "openq4-linux-install-quake4-assets.sh"
$buildScript = Join-Path $guestDir "openq4-linux-sync-build-test.sh"

foreach ($item in $Action) {
    switch ($item) {
        "Start" {
            Start-openQ4Vm
        }
        "Ip" {
            Invoke-Vmrun -Arguments @("getGuestIPAddress", $script:VmxPath, "-wait") | Out-Null
        }
        "Bootstrap" {
            Copy-AndRunGuestScript -HostScript $bootstrapScript -GuestScriptName "openq4-linux-mint-bootstrap.sh"
        }
        "Assets" {
            Copy-AndRunGuestScript -HostScript $assetScript -GuestScriptName "openq4-linux-install-quake4-assets.sh"
        }
        "Build" {
            Copy-AndRunGuestScript -HostScript $buildScript -GuestScriptName "openq4-linux-sync-build-test.sh" -ScriptArguments @("build")
        }
        "Smoke" {
            Copy-AndRunGuestScript -HostScript $buildScript -GuestScriptName "openq4-linux-sync-build-test.sh" -ScriptArguments @("smoke")
        }
        "Launcher" {
            Copy-AndRunGuestScript -HostScript $buildScript -GuestScriptName "openq4-linux-sync-build-test.sh" -ScriptArguments @("launcher")
        }
        "All" {
            Copy-AndRunGuestScript -HostScript $bootstrapScript -GuestScriptName "openq4-linux-mint-bootstrap.sh"
            Copy-AndRunGuestScript -HostScript $assetScript -GuestScriptName "openq4-linux-install-quake4-assets.sh"
            Copy-AndRunGuestScript -HostScript $buildScript -GuestScriptName "openq4-linux-sync-build-test.sh" -ScriptArguments @("all")
            Invoke-Vmrun -Arguments @("snapshot", $script:VmxPath, $SnapshotName) -AllowFailure | Out-Null
        }
        "Snapshot" {
            Invoke-Vmrun -Arguments @("snapshot", $script:VmxPath, $SnapshotName) | Out-Null
        }
        "Stop" {
            Invoke-Vmrun -Arguments @("stop", $script:VmxPath, "soft") | Out-Null
        }
    }
}
