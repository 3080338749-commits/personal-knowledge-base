param([switch]$Embed, [switch]$Cpu)
$ErrorActionPreference = 'Stop'
$vaultRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\..')).Path
$qmdCommand = (Get-Command qmd.cmd -ErrorAction Stop).Source
$savedEnvironment = @{}
foreach ($key in @('QMD_FORCE_CPU','QMD_LLAMA_GPU','QMD_EMBED_PARALLELISM','QMD_EMBED_CONTEXT_SIZE')) {
    $savedEnvironment[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
}
Push-Location -LiteralPath $vaultRoot
try {
    & $qmdCommand --index personal-kb update
    if ($LASTEXITCODE -ne 0) { throw "QMD update failed: $LASTEXITCODE" }
    if ($Embed) {
        $env:QMD_EMBED_PARALLELISM = '1'
        $env:QMD_EMBED_CONTEXT_SIZE = '1024'
        if ($Cpu) {
            $env:QMD_FORCE_CPU = '1'
            Remove-Item Env:QMD_LLAMA_GPU -ErrorAction SilentlyContinue
        } else {
            Remove-Item Env:QMD_FORCE_CPU -ErrorAction SilentlyContinue
            $env:QMD_LLAMA_GPU = 'vulkan'
        }
        & $qmdCommand --index personal-kb embed --max-docs-per-batch 1 --max-batch-mb 2
        if ($LASTEXITCODE -ne 0) { throw "QMD embed failed: $LASTEXITCODE" }
    }
} finally {
    foreach ($key in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($key, $savedEnvironment[$key], 'Process')
    }
    Pop-Location
}
