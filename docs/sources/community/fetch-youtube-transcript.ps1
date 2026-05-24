# Fetch YouTube transcript via Transcript API and write transcript text to a file.
# Usage: set $env:TRANSCRIPT_API_KEY then run:
#   .\fetch-youtube-transcript.ps1 -VideoUrl "https://www.youtube.com/watch?v=Is5A47QQakI"
# Output: transcript JSON is saved to youtube-transcript-<videoId>.json; you can parse it and paste extracted content into youtube-dataset.md

param(
    [Parameter(Mandatory=$true)]
    [string]$VideoUrl,
    [string]$OutDir = "."
)

$apiKey = $env:TRANSCRIPT_API_KEY
if (-not $apiKey) {
    Write-Error "Set TRANSCRIPT_API_KEY environment variable (do not commit the key)."
    exit 1
}

$uri = "https://transcriptapi.com/api/v2/youtube/transcript?video_url=$([uri]::EscapeDataString($VideoUrl))&format=json"
$headers = @{ Authorization = "Bearer $apiKey" }

try {
    $response = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get
    $videoId = if ($VideoUrl -match "v=([^&]+)") { $Matches[1] } else { "unknown" }
    $outPath = Join-Path $OutDir "youtube-transcript-$videoId.json"
    $response | ConvertTo-Json -Depth 10 | Set-Content -Path $outPath -Encoding UTF8
    Write-Host "Saved transcript to $outPath"
} catch {
    Write-Error "Request failed: $_"
    exit 1
}
