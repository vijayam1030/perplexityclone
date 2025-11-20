@echo off
echo ========================================
echo   AI Search Engine - Perplexity Clone
echo ========================================
echo.

REM Check if Ollama is running
echo Checking Ollama connection...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama doesn't seem to be running!
    echo Please start Ollama first: ollama serve
    echo.
    pause
    exit /b 1
)
echo [OK] Ollama is running
echo.

REM Check if required models are available
echo Checking Ollama models...
ollama list | findstr /C:"qwen2.5:7b" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] qwen2.5:7b not found!
    echo Downloading model... (this may take a while)
    ollama pull qwen2.5:7b
)

ollama list | findstr /C:"qwen2.5:14b" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] qwen2.5:14b not found!
    echo Downloading model... (this may take a while)
    ollama pull qwen2.5:14b
)
echo [OK] Models are ready
echo.

REM Check if Python dependencies are installed
echo Checking dependencies...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Dependencies not installed!
    echo Installing dependencies...
    pip install -r requirements.txt
)
echo [OK] Dependencies installed
echo.

REM Start the backend server
echo Starting backend server...
cd backend
start "AI Search Backend" cmd /k "python app.py"
cd ..

REM Wait for server to start
echo Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Open the frontend in default browser
echo Opening frontend in browser...
start http://localhost:8000
start index.html

echo.
echo ========================================
echo   Server is running!
echo   Backend: http://localhost:8000
echo   Frontend: Open index.html in browser
echo.
echo   Press Ctrl+C in the backend window to stop
echo ========================================
pause
