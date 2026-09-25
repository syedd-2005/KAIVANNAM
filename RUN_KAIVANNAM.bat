@echo off
cd /d "%~dp0"
echo ========================================
echo       KAIVANNAM - KAI VANNAM
echo      Presentation Ready Launcher
echo ========================================
echo.
py -m streamlit run app.py
if errorlevel 1 (
  echo.
  echo Streamlit did not start. Run: py -m pip install -r requirements.txt
  pause
)
