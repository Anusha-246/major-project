@echo off
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.initialize
echo.
echo Setup complete. Run run.bat or: python app.py
pause
