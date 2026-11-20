@echo off
REM Builds "Sikdar Consultancy.exe" (folder build) into dist\Sikdar Consultancy\
cd /d "%~dp0"
python -m pip install -r requirements.txt || goto :err
python make_icon.py || goto :err
python -m PyInstaller --noconfirm --clean --windowed --name "Sikdar Consultancy" ^
  --icon assets\app.ico ^
  --add-data "assets\logo.png;assets" ^
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtPdf --exclude-module tkinter ^
  main.py || goto :err
echo.
echo Done. Run:  dist\Sikdar Consultancy\Sikdar Consultancy.exe
exit /b 0
:err
echo Build failed.
exit /b 1
