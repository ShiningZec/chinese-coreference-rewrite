$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Node = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
if (-not (Test-Path $Node)) {
    $Node = "node"
}

$Script = Join-Path $PSScriptRoot "build_presentation.mjs"
$OutputDir = Join-Path $Root "outputs"

# Artifact-tool can leave a non-zero native exit code on Windows after writing files.
& $Node $Script

$LatestPptx = Get-ChildItem -LiteralPath $OutputDir -Filter "*.pptx" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($LatestPptx) {
    Write-Output "PPT generated: $($LatestPptx.FullName)"
    exit 0
}

Write-Error "PPT was not generated."
exit 1
