@echo off
chcp 65001 >nul
setlocal
set "CSDK=C:\Users\Alexd\Downloads\Reduced_CSDK_12\Reduced_CSDK_12"
set "SRC=%CSDK%\content\citadel_addons\solomonreminder"
set "RC=%CSDK%\game\bin_cs2\win64\resourcecompiler.exe"
cd /d "%~dp0"
if not exist build mkdir build
echo. > build\compile_log.txt

echo [0/4] tests
python tests\test_logic.py || goto :fail
echo [1/4] HUD: stage
python solomon_reminder.py stage || goto :fail
echo [2/4] piece colors: stage
python piece_colors.py stage || goto :fail
echo [2b/4] ground neon: stage
python ground_neon.py stage || goto :fail
echo [3/4] compile (xml + js + css + vmat + vpcf)
for %%F in ("panorama\layout\hud_ability_icon.xml" "panorama\scripts\solomon_reminder.js" "panorama\styles\solomon_reminder.css") do (
    echo ===================== %%~F ===================== >> build\compile_log.txt
    "%RC%" -i "%SRC%\%%~F" -f -v >> build\compile_log.txt 2>&1
)
if exist "%SRC%\materials\particle\projected\*.vmat" (
    for %%F in ("%SRC%\materials\particle\projected\*.vmat") do (
        echo ===================== %%~nxF ===================== >> build\compile_log.txt
        "%RC%" -i "%%~F" -f >> build\compile_log.txt 2>&1
    )
)
if exist "%SRC%\particles\abilities\chessmaster\*.vpcf" (
    for %%F in ("%SRC%\particles\abilities\chessmaster\*.vpcf") do (
        echo ===================== %%~nxF ===================== >> build\compile_log.txt
        "%RC%" -i "%%~F" -f >> build\compile_log.txt 2>&1
    )
)
echo [4/4] pack + install
python solomon_reminder.py pack || goto :fail
python solomon_reminder.py install || goto :fail

echo.
echo GOTOVO: build\solomon\pak03_dir.vpk ustanovlen v addons. Perezapusti Deadlock.
if /i not "%1"=="-q" pause
exit /b 0

:fail
echo.
echo OSHIBKA - smotri build\compile_log.txt
if /i not "%1"=="-q" pause
exit /b 1

