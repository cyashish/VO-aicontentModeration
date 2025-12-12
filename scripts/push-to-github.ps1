# PowerShell script to push AI Moderation system to GitHub
# Usage: ./push-to-github.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "AI Moderation System - GitHub Push" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# Check if we're in a git repository
if (-not (Test-Path .git)) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    git branch -M main
    Write-Host "Git repository initialized with 'main' branch" -ForegroundColor Green
}

# Show current status
Write-Host ""
Write-Host "Current files to be committed:" -ForegroundColor Yellow
git status --short

Write-Host ""
$confirm = Read-Host "Do you want to commit these files? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Aborted by user" -ForegroundColor Red
    exit 0
}

# Add all files
Write-Host ""
Write-Host "Adding all files..." -ForegroundColor Yellow
git add .

# Commit
$commitMessage = Read-Host "Enter commit message (or press Enter for default)"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = "Add complete AI moderation system with Python, Flink, dbt, Grafana"
}

git commit -m "$commitMessage"

$currentBranch = git branch --show-current
if ([string]::IsNullOrWhiteSpace($currentBranch)) {
    Write-Host "Setting branch to 'main'..." -ForegroundColor Yellow
    git branch -M main
    $currentBranch = "main"
}

# Check for remote
$hasRemote = git remote | Select-String -Pattern "origin"
if (-not $hasRemote) {
    Write-Host ""
    Write-Host "No remote 'origin' found" -ForegroundColor Yellow
    $remoteUrl = Read-Host "Enter your GitHub repository URL (e.g., https://github.com/username/repo.git)"
    
    if ([string]::IsNullOrWhiteSpace($remoteUrl)) {
        Write-Host "ERROR: Remote URL is required" -ForegroundColor Red
        exit 1
    }
    
    git remote add origin $remoteUrl
    Write-Host "Remote 'origin' added" -ForegroundColor Green
}

# Push to GitHub
Write-Host ""
Write-Host "Pushing to GitHub on branch: $currentBranch..." -ForegroundColor Yellow

try {
    git push -u origin $currentBranch 2>&1 | Tee-Object -Variable pushOutput
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "First push failed, trying with --force (safe for new repos)..." -ForegroundColor Yellow
        git push -u origin $currentBranch --force
    }
} catch {
    Write-Host "Error during push: $_" -ForegroundColor Red
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. View your repo: https://github.com/YOUR_USERNAME/YOUR_REPO" -ForegroundColor White
    Write-Host "2. Follow DEPLOYMENT_GUIDE.md to run the system" -ForegroundColor White
    Write-Host "3. Check WINDOWS_SETUP.md for Windows-specific instructions" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host "Push failed - Troubleshooting:" -ForegroundColor Red
    Write-Host "=====================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "1. Authentication issue?" -ForegroundColor Yellow
    Write-Host "   - Use GitHub CLI: gh auth login" -ForegroundColor White
    Write-Host "   - Or Personal Access Token: https://github.com/settings/tokens" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Check remote URL is correct:" -ForegroundColor Yellow
    Write-Host "   git remote -v" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Try manual push:" -ForegroundColor Yellow
    Write-Host "   git push -u origin $currentBranch --force" -ForegroundColor White
}
