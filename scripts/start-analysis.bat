@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%start-analysis.ps1"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

if not exist "%PS_SCRIPT%" (
  echo Could not find "%PS_SCRIPT%"
  exit /b 1
)

set "INPUT_VIDEO=%~1"
set "SESSION_NAME=%~2"
set "ACTION_TYPE=%~3"
set "ATHLETE_NAME=%~4"
set "ATHLETE_ID=%~5"
set "DATE_VALUE=%~6"
set "PROVIDER=%~7"
set "HANDEDNESS=%~8"
set "SAMPLE_EVERY=%~9"

shift
shift
shift
shift
shift
shift
shift
shift
shift

set "SERVE_PRE_SECONDS=%~1"
set "SERVE_POST_SECONDS=%~2"
set "MODEL_ASSET_PATH=%~3"

set "INTERACTIVE_MODE=0"
if "%INPUT_VIDEO%"=="" set "INTERACTIVE_MODE=1"

if "%INPUT_VIDEO%"=="" set /p INPUT_VIDEO=Input video path: 
if "%SESSION_NAME%"=="" set /p SESSION_NAME=Session name: 
if "%ACTION_TYPE%"=="" set /p ACTION_TYPE=Action type: 
if "%ATHLETE_NAME%"=="" set /p ATHLETE_NAME=Athlete name: 
if "%ATHLETE_ID%"=="" set /p ATHLETE_ID=Athlete id: 
if "%INTERACTIVE_MODE%"=="1" if "%DATE_VALUE%"=="" set /p DATE_VALUE=Date [optional]: 
if "%INTERACTIVE_MODE%"=="1" if "%PROVIDER%"=="" set /p PROVIDER=Provider [optional]: 
if "%INTERACTIVE_MODE%"=="1" if "%HANDEDNESS%"=="" set /p HANDEDNESS=Handedness [optional]: 
if "%INTERACTIVE_MODE%"=="1" if "%SAMPLE_EVERY%"=="" set /p SAMPLE_EVERY=Sample every [optional]: 
if "%INTERACTIVE_MODE%"=="1" if "%SERVE_PRE_SECONDS%"=="" set /p SERVE_PRE_SECONDS=Serve pre seconds [optional]: 
if "%INTERACTIVE_MODE%"=="1" if "%SERVE_POST_SECONDS%"=="" set /p SERVE_POST_SECONDS=Serve post seconds [optional]: 
if "%INTERACTIVE_MODE%"=="1" if "%MODEL_ASSET_PATH%"=="" set /p MODEL_ASSET_PATH=Model asset path [optional]: 

set "TA_INPUT_VIDEO=%INPUT_VIDEO%"
set "TA_SESSION_NAME=%SESSION_NAME%"
set "TA_ACTION_TYPE=%ACTION_TYPE%"
set "TA_ATHLETE_NAME=%ATHLETE_NAME%"
set "TA_ATHLETE_ID=%ATHLETE_ID%"
set "TA_DATE=%DATE_VALUE%"
set "TA_PROVIDER=%PROVIDER%"
set "TA_HANDEDNESS=%HANDEDNESS%"
set "TA_SAMPLE_EVERY=%SAMPLE_EVERY%"
set "TA_SERVE_PRE_SECONDS=%SERVE_PRE_SECONDS%"
set "TA_SERVE_POST_SECONDS=%SERVE_POST_SECONDS%"
set "TA_MODEL_ASSET_PATH=%MODEL_ASSET_PATH%"

echo.
echo Running analysis...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$params = @{ InputVideo = $env:TA_INPUT_VIDEO; SessionName = $env:TA_SESSION_NAME; ActionType = $env:TA_ACTION_TYPE; AthleteName = $env:TA_ATHLETE_NAME; AthleteId = $env:TA_ATHLETE_ID };" ^
  "if ($env:TA_DATE) { $params.Date = $env:TA_DATE };" ^
  "if ($env:TA_PROVIDER) { $params.Provider = $env:TA_PROVIDER };" ^
  "if ($env:TA_HANDEDNESS) { $params.Handedness = $env:TA_HANDEDNESS };" ^
  "if ($env:TA_SAMPLE_EVERY) { $params.SampleEvery = [int]$env:TA_SAMPLE_EVERY };" ^
  "if ($env:TA_SERVE_PRE_SECONDS) { $params.ServePreSeconds = [double]::Parse($env:TA_SERVE_PRE_SECONDS, [System.Globalization.CultureInfo]::InvariantCulture) };" ^
  "if ($env:TA_SERVE_POST_SECONDS) { $params.ServePostSeconds = [double]::Parse($env:TA_SERVE_POST_SECONDS, [System.Globalization.CultureInfo]::InvariantCulture) };" ^
  "if ($env:TA_MODEL_ASSET_PATH) { $params.ModelAssetPath = $env:TA_MODEL_ASSET_PATH };" ^
  "& '%PS_SCRIPT%' @params"

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
  echo Analysis completed.
) else (
  echo Analysis failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%

:help
echo Usage:
echo   start-analysis.bat INPUT_VIDEO SESSION_NAME ACTION_TYPE ATHLETE_NAME ATHLETE_ID [DATE] [PROVIDER] [HANDEDNESS] [SAMPLE_EVERY] [SERVE_PRE_SECONDS] [SERVE_POST_SECONDS] [MODEL_ASSET_PATH]
echo.
echo Example:
echo   start-analysis.bat "D:\videos\serve-1.mp4" "basket-serve" "serve" "Simon" "simon" "2026-03-27" "mediapipe" "right" "2" "1.4" "1.5" "assets\models\pose_landmarker.task"
exit /b 0
