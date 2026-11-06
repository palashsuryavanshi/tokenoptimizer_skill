[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    Write-Error "File not found: $Path"
    exit 1
}

$text = Get-Content -LiteralPath $Path -Raw
if ($null -eq $text) {
    $text = ''
}

$words = @($text -split '\s+' | Where-Object { $_ -ne '' }).Count
$chars = $text.Length

Write-Output "words=$words chars=$chars"
