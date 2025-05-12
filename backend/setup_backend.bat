@echo off
REM Setup script for Concierge Platform backend

echo.
echo [1/5] Creating virtual environment...
python -m venv venv

echo.
echo [2/5] Activating virtual environment...
call venv\Scripts\activate

echo.
echo [3/5] Installing dependencies...
pip install --upgrade pip
pip install fastapi uvicorn openai twilio beautifulsoup4 requests

echo.
echo [4/5] Creating base Python files...
echo. > main.py
echo. > voicebot.py
echo. > website_parser.py
echo. > settings.py

echo.
echo [5/5] Setup complete. Virtual environment is activated.
echo You can now run your app using: uvicorn main:app --reload

cmd /k
