<# PowerShell example to set GitHub Actions secrets using gh CLI #>
$repo = "ok750927-byte/daily-trading-bot"  # replace with actual owner/repo

if (-not $env:NEW_KIS_KEY -or -not $env:NEW_KIS_SECRET) {
    Write-Host "Please set environment variables NEW_KIS_KEY and NEW_KIS_SECRET before running."
    return
}

gh secret set KIS_APP_KEY --body $env:NEW_KIS_KEY --repo $repo
gh secret set KIS_APP_SECRET --body $env:NEW_KIS_SECRET --repo $repo

if ($env:NEW_DISCORD_WEBHOOK) {
    gh secret set DISCORD_WEBHOOK_URL --body $env:NEW_DISCORD_WEBHOOK --repo $repo
}

Write-Host "Secrets updated. Trigger CI to validate."
