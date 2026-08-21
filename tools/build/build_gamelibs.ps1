param(
    [string]$GameLibsRepo = "",
    [string]$BuildDir = "",
    [ValidateSet("plain", "debug", "debugoptimized", "release", "minsize", "custom")]
    [string]$BuildType = "",
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$openQ4Root = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))

if ([string]::IsNullOrWhiteSpace($GameLibsRepo)) {
    $GameLibsRepo = Join-Path $openQ4Root "..\openQ4-game"
}
if ([string]::IsNullOrWhiteSpace($BuildDir)) {
    $BuildDir = Join-Path $GameLibsRepo "builddir"
}
if ([string]::IsNullOrWhiteSpace($BuildType)) {
    $BuildType = if ([string]::IsNullOrWhiteSpace($env:OPENQ4_GAMELIBS_BUILDTYPE)) {
        "release"
    } else {
        $env:OPENQ4_GAMELIBS_BUILDTYPE.Trim()
    }
}
$allowedBuildTypes = @("plain", "debug", "debugoptimized", "release", "minsize", "custom")
if ($allowedBuildTypes -notcontains $BuildType) {
    throw "Invalid GameLibs build type '$BuildType'. Expected one of: $($allowedBuildTypes -join ', ')."
}

$gameLibsRoot = [System.IO.Path]::GetFullPath($GameLibsRepo)
$gameLibsBuildDir = [System.IO.Path]::GetFullPath($BuildDir)
$gameLibsMesonSetup = Join-Path $gameLibsRoot "tools\build\meson_setup.ps1"
$gameLibsCoreData = Join-Path $gameLibsBuildDir "meson-private\coredata.dat"
$gameLibsBuildNinja = Join-Path $gameLibsBuildDir "build.ninja"

if (-not (Test-Path $gameLibsRoot)) {
    throw "openQ4-game repository not found at '$gameLibsRoot'. Set OPENQ4_GAMELIBS_REPO or pass -GameLibsRepo."
}

if (-not (Test-Path $gameLibsMesonSetup)) {
    throw "openQ4-game Meson wrapper not found at '$gameLibsMesonSetup'."
}

Write-Host "Building openQ4 SDK game libraries from:"
Write-Host "  Repo: $gameLibsRoot"
Write-Host "  BuildDir: $gameLibsBuildDir"
Write-Host "  BuildType: $BuildType"

if ((Test-Path $gameLibsCoreData) -and (Test-Path $gameLibsBuildNinja)) {
    & $gameLibsMesonSetup setup --reconfigure $gameLibsBuildDir $gameLibsRoot --buildtype=$BuildType
} else {
    & $gameLibsMesonSetup setup --wipe $gameLibsBuildDir $gameLibsRoot --backend ninja --buildtype=$BuildType --vsenv
}
$setupExit = [int]$LASTEXITCODE
if ($setupExit -ne 0) {
    exit $setupExit
}

if ($SetupOnly) {
    exit 0
}

& $gameLibsMesonSetup compile -C $gameLibsBuildDir
$compileExit = [int]$LASTEXITCODE
if ($compileExit -ne 0) {
    exit $compileExit
}

Write-Host "openQ4-game build complete."
