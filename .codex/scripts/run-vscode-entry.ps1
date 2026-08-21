param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('task', 'launch')]
    [string]$Kind,

    [Parameter(Mandatory = $true, Position = 1)]
    [int]$Index
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$tasksPath = Join-Path $workspaceRoot '.vscode\tasks.json'
$launchPath = Join-Path $workspaceRoot '.vscode\launch.json'

function Resolve-WorkspaceToken([string]$Value) {
    if ($null -eq $Value) {
        return $null
    }

    return $Value.Replace('${workspaceFolder}', $workspaceRoot)
}

function Get-JsonFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required VS Code configuration file not found: $Path"
    }

    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Invoke-ConfiguredCommand(
    [string]$Label,
    [string]$Command,
    [object[]]$Arguments,
    [string]$WorkingDirectory
) {
    if ([string]::IsNullOrWhiteSpace($Command)) {
        return
    }

    $resolvedCommand = Resolve-WorkspaceToken $Command
    $resolvedArgs = @()
    $argumentList = @()

    if ($null -ne $Arguments) {
        $argumentList = @($Arguments)
    }

    foreach ($argument in $argumentList) {
        if ($null -eq $argument) {
            continue
        }

        $resolvedArgs += Resolve-WorkspaceToken ([string]$argument)
    }

    $resolvedWorkingDirectory = Resolve-WorkspaceToken $WorkingDirectory
    if ([string]::IsNullOrWhiteSpace($resolvedWorkingDirectory)) {
        $resolvedWorkingDirectory = $workspaceRoot
    }

    Write-Host "Running $Label"
    Push-Location -LiteralPath $resolvedWorkingDirectory
    try {
        & $resolvedCommand @resolvedArgs
        if ($LASTEXITCODE -ne $null) {
            exit $LASTEXITCODE
        }

        if (-not $?) {
            exit 1
        }
    }
    finally {
        Pop-Location
    }
}

$taskConfig = Get-JsonFile $tasksPath
$taskIndexByLabel = @{}
for ($i = 0; $i -lt $taskConfig.tasks.Count; $i++) {
    $taskIndexByLabel[$taskConfig.tasks[$i].label] = $i
}

$visitedTasks = New-Object System.Collections.Generic.HashSet[int]

function Invoke-TaskByIndex([int]$TaskIndex) {
    if ($TaskIndex -lt 0 -or $TaskIndex -ge $taskConfig.tasks.Count) {
        throw "Task index $TaskIndex is out of range."
    }

    if ($visitedTasks.Contains($TaskIndex)) {
        return
    }

    [void]$visitedTasks.Add($TaskIndex)
    $task = $taskConfig.tasks[$TaskIndex]
    $dependencies = @()

    if ($null -ne $task.dependsOn) {
        $dependencies = @($task.dependsOn)
    }

    foreach ($dependency in $dependencies) {
        if (-not $taskIndexByLabel.ContainsKey($dependency)) {
            throw "Task '$($task.label)' depends on unknown task '$dependency'."
        }

        Invoke-TaskByIndex ([int]$taskIndexByLabel[$dependency])
    }

    Invoke-ConfiguredCommand -Label $task.label -Command $task.command -Arguments $task.args -WorkingDirectory $task.options.cwd
}

function Invoke-LaunchByIndex([int]$LaunchIndex) {
    $launchConfig = Get-JsonFile $launchPath

    if ($LaunchIndex -lt 0 -or $LaunchIndex -ge $launchConfig.configurations.Count) {
        throw "Launch index $LaunchIndex is out of range."
    }

    $launch = $launchConfig.configurations[$LaunchIndex]

    if (-not [string]::IsNullOrWhiteSpace($launch.preLaunchTask)) {
        if (-not $taskIndexByLabel.ContainsKey($launch.preLaunchTask)) {
            throw "Launch '$($launch.name)' references unknown preLaunchTask '$($launch.preLaunchTask)'."
        }

        Invoke-TaskByIndex ([int]$taskIndexByLabel[$launch.preLaunchTask])
    }

    Invoke-ConfiguredCommand -Label $launch.name -Command $launch.program -Arguments $launch.args -WorkingDirectory $launch.cwd
}

switch ($Kind) {
    'task' {
        Invoke-TaskByIndex $Index
    }
    'launch' {
        Invoke-LaunchByIndex $Index
    }
}
