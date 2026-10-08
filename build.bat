@echo off
rem Rebuild BehindTheFrame-UA-Install.exe from these sources.
rem
rem The --collect-all switches are not optional: UnityPy pulls its typetree
rem data, the FMOD dll, the texture codecs and archspec's CPU tables in at
rem runtime, so PyInstaller's static analysis never sees them and the build
rem dies partway through an install.
rem
rem private\ holds the translation and artwork, kept outside this repository.
rem Link it once:  mklink /J private <folder with translation\ and art\>
rem Only the CSV and the artwork go into the installer, not the review sheet.

setlocal
cd /d "%~dp0"

echo Installing build dependencies...
python -m pip install --quiet UnityPy pillow openpyxl pyinstaller || goto :fail

echo.
echo Building...
python -m PyInstaller --onefile --clean --noconfirm ^
  --name "BehindTheFrame-UA-Install" ^
  --add-data "data;data" --add-data "reference;reference" ^
  --add-data "private\translation\Ukrainian.csv;private\translation" ^
  --add-data "private\art;private\art" ^
  --collect-all UnityPy --collect-all tpk_ar --collect-all fmod_toolkit ^
  --collect-all texture2ddecoder --collect-all etcpak --collect-all astc_encoder_py ^
  --collect-all archspec ^
  --hidden-import verify ^
  --exclude-module tkinter --exclude-module matplotlib --exclude-module numpy ^
  installer.py || goto :fail

echo.
echo Done: dist\BehindTheFrame-UA-Install.exe
certutil -hashfile "dist\BehindTheFrame-UA-Install.exe" SHA256
goto :eof

:fail
echo.
echo Build failed.
exit /b 1
