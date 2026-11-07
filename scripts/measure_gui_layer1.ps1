<#
.SYNOPSIS
  Measure Windows process CPU and memory during a controlled eMule GUI test.

.DESCRIPTION
  Read-only sampler: never touches Temp, .part or .part.met. Does NOT
  drive the GUI; perform the named scenario manually during capture.
  CPU is normalized by logical processor count (100% = all cores busy).
  This is not a substitute for a profiler or for Windows Event Viewer logs.

.EXAMPLE
  .\measure_gui_layer1.ps1 -ProcessName nuevo-emule -Variant portable -Scenario shift-arrow -Seconds 60 -OutputPath .\results\portable-selection.csv

.EXAMPLE
  .\measure_gui_layer1.ps1 -ProcessName emule -Variant original -Scenario idle -Seconds 60 -OutputPath .\results\original-idle.csv
#>
[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()][string]$ProcessName = 'nuevo-emule',
    [ValidateSet('original','portable')][string]$Variant = 'portable',
    [ValidateSet('idle','shift-arrow','categories','sources','scroll','startup')][string]$Scenario = 'idle',
    [ValidateRange(5,3600)][int]$Seconds = 60,
    [ValidateNotNullOrEmpty()][string]$OutputPath = '.\gui-layer1-metrics.csv'
)

$ErrorActionPreference = 'Stop'
$cores = [Math]::Max(1, [Environment]::ProcessorCount)
$name = [IO.Path]::GetFileNameWithoutExtension($ProcessName)
$instances = @(Get-Process -Name $name -ErrorAction SilentlyContinue)
if ($instances.Count -ne 1) {
    throw "Se esperaba exactamente un proceso '$name' y hay $($instances.Count). Cierra otras instancias antes de medir."
}

$proc = $instances[0]
$proc.Refresh()
if ($proc.HasExited) { throw 'El proceso ya ha terminado.' }

$fullOutput = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$directory = Split-Path -Parent $fullOutput
if (-not [IO.Directory]::Exists($directory)) {
    [void][IO.Directory]::CreateDirectory($directory)
}
if (Test-Path -LiteralPath $fullOutput) {
    throw "El CSV ya existe: $fullOutput. Elige otro OutputPath para no mezclar pruebas."
}

$start = [DateTime]::UtcNow
$prevTime = $start
$prevCpu = $proc.TotalProcessorTime.TotalSeconds
Write-Host "Midiendo $Variant/$Scenario: PID=$($proc.Id), $Seconds segundos, $cores procesadores logicos."
Write-Host 'Realiza la operacion de interfaz indicada. No cierres ni inicies el otro eMule.'

for ($i = 0; $i -lt $Seconds; ++$i) {
    Start-Sleep -Seconds 1
    try {
        $proc.Refresh()
        if ($proc.HasExited) {
            Write-Warning "El proceso termino durante la medicion (muestra $i)."
            break
        }

        $now = [DateTime]::UtcNow
        $cpu = $proc.TotalProcessorTime.TotalSeconds
        $elapsed = [Math]::Max(0.001, ($now - $prevTime).TotalSeconds)
        $cpuPercent = [Math]::Max(0.0, ($cpu - $prevCpu) * 100 / $elapsed / $cores)
        $sample = [pscustomobject]@{
            TimestampUtc        = $now.ToString('o')
            Variant             = $Variant
            Scenario            = $Scenario
            ProcessId           = $proc.Id
            ElapsedSeconds      = [Math]::Round(($now - $start).TotalSeconds, 3)
            CpuPercentAllCores  = [Math]::Round($cpuPercent, 2)
            WorkingSetMiB       = [Math]::Round($proc.WorkingSet64 / 1MB, 2)
            PrivateMiB          = [Math]::Round($proc.PrivateMemorySize64 / 1MB, 2)
            HandleCount         = $proc.HandleCount
            ThreadCount         = $proc.Threads.Count
            GuiResponding       = $proc.Responding
        }
        $sample | Export-Csv -Path $fullOutput -NoTypeInformation -Encoding UTF8 -Append
        $prevTime = $now
        $prevCpu = $cpu
    }
    catch {
        Write-Warning "Error de muestreo: $_. El proceso puede haber terminado."
        break
    }
}

Write-Host "CSV guardado en: $fullOutput"
Write-Host 'Anota aparte: numero de descargas, tiempo del cambio de categoria, bloqueos y pasos reproducibles.'
