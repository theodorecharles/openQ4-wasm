param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('setup', 'compile', 'install', 'fastbuild')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$mesonWrapper = Join-Path $workspaceRoot 'tools\build\meson_setup.ps1'
$buildDir = Join-Path $workspaceRoot 'builddir'
$installDir = Join-Path $workspaceRoot '.install'
$fastStageScript = Join-Path $workspaceRoot 'tools\build\stage_fast_install.py'
$checkStagedContentScript = Join-Path $workspaceRoot 'tools\build\check_staged_content_edits.py'

if (-not (Test-Path $mesonWrapper)) {
    throw "openQ4 Meson wrapper not found at '$mesonWrapper'."
}

function Invoke-openQ4Meson([string[]]$MesonArgs) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $mesonWrapper @MesonArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Invoke-PythonTool([string[]]$ToolArgs) {
    & python @ToolArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Test-MesonBuildDirectory([string]$Path) {
    $coreData = Join-Path $Path 'meson-private\coredata.dat'
    $ninjaFile = Join-Path $Path 'build.ninja'
    return (Test-Path $coreData) -and (Test-Path $ninjaFile)
}

switch ($Action) {
    'setup' {
        if (Test-MesonBuildDirectory $buildDir) {
            Invoke-openQ4Meson @(
                'setup',
                $buildDir,
                $workspaceRoot,
                '--reconfigure',
                '--backend',
                'ninja',
                '--buildtype',
                'debug',
                '--wrap-mode=forcefallback'
            )
        } else {
            Invoke-openQ4Meson @(
                'setup',
                '--wipe',
                $buildDir,
                $workspaceRoot,
                '--backend',
                'ninja',
                '--buildtype',
                'debug',
                '--wrap-mode=forcefallback'
            )
        }
    }
    'compile' {
        Invoke-openQ4Meson @(
            'compile',
            '-C',
            $buildDir
        )
    }
    'fastbuild' {
        if (-not (Test-Path $fastStageScript)) {
            throw "openQ4 fast staging script not found at '$fastStageScript'."
        }
        if (-not (Test-Path $checkStagedContentScript)) {
            throw "openQ4 staged content edit check script not found at '$checkStagedContentScript'."
        }

        Invoke-openQ4Meson @(
            'compile',
            '-C',
            $buildDir
        )
        Invoke-PythonTool @(
            $checkStagedContentScript,
            '--source-root',
            $workspaceRoot
        )
        Invoke-PythonTool @(
            $fastStageScript,
            '--source-root',
            $workspaceRoot,
            '--build-dir',
            $buildDir,
            '--install-dir',
            $installDir
        )
    }
    'install' {
        Invoke-openQ4Meson @(
            'install',
            '-C',
            $buildDir,
            '--no-rebuild',
            '--skip-subprojects'
        )
    }
}
