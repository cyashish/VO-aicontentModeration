@echo off
REM Batch script to push AI Moderation system to GitHub
REM Usage: push-to-github.bat

echo =====================================
echo AI Moderation System - GitHub Push
echo =====================================
echo.

REM Check if git is installed
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from: https://git-scm.com/download/win
    exit /b 1
)

REM Check if we're in a git repository
if not exist .git (
    echo Initializing Git repository...
    git init
    REM Set default branch to main
    git branch -M main
    echo Git repository initialized with 'main' branch
)

REM Show current status
echo.
echo Current files to be committed:
git status --short

echo.
set /p CONFIRM="Do you want to commit these files? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Aborted by user
    exit /b 0
)

REM Add all files
echo.
echo Adding all files...
git add .

REM Commit
echo.
set /p COMMIT_MSG="Enter commit message (or press Enter for default): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Add complete AI moderation system with Python, Flink, dbt, Grafana
git commit -m "%COMMIT_MSG%"

REM Ensure we're on main branch
for /f "tokens=*" %%i in ('git branch --show-current') do set BRANCH=%%i
if "%BRANCH%"=="" (
    echo Setting branch to 'main'...
    git branch -M main
    set BRANCH=main
)

REM Check for remote
git remote | findstr "origin" >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo No remote 'origin' found
    set /p REMOTE_URL="Enter your GitHub repository URL: "
    
    if "%REMOTE_URL%"=="" (
        echo ERROR: Remote URL is required
        exit /b 1
    )
    
    git remote add origin %REMOTE_URL%
    echo Remote 'origin' added
)

REM Push to GitHub
echo.
echo Pushing to GitHub on branch: %BRANCH%...
git push -u origin %BRANCH%

REM If push fails, try with force flag for initial push
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo First push failed, trying with --force (safe for new repos)...
    git push -u origin %BRANCH% --force
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =====================================
    echo Successfully pushed to GitHub!
    echo =====================================
    echo.
    echo Next steps:
    echo 1. View your repo: https://github.com/YOUR_USERNAME/YOUR_REPO
    echo 2. Follow DEPLOYMENT_GUIDE.md to run the system
    echo 3. Check WINDOWS_SETUP.md for Windows-specific instructions
) else (
    echo.
    echo =====================================
    echo Push failed - Troubleshooting:
    echo =====================================
    echo.
    echo 1. Authentication issue?
    echo    - Use GitHub CLI: gh auth login
    echo    - Or Personal Access Token: https://github.com/settings/tokens
    echo.
    echo 2. Check remote URL is correct:
    echo    git remote -v
    echo.
    echo 3. Try manual push:
    echo    git push -u origin %BRANCH% --force
)

pause
