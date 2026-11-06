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

$text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
if ($null -eq $text) {
    $text = ''
}

$words = @($text -split '\s+' | Where-Object { $_ -ne '' }).Count
# chars counts UTF-16 code units after UTF-8 decoding, so astral characters (surrogate pairs) count as 2.
$chars = $text.Length

Write-Output "words=$words chars=$chars"
