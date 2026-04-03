@echo off
echo === Building AirTap standalone .exe ===
echo.

cd /d "%~dp0airtap"

pip install pyinstaller --quiet
pyinstaller airtap.spec --noconfirm

echo.
if exist "dist\AirTap\AirTap.exe" (
    echo Build successful! Output: airtap\dist\AirTap\AirTap.exe
) else (
    echo Build FAILED. Check output above for errors.
)
pause
