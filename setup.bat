@echo off
chcp 65001 > nul
echo.
echo ====================================================
echo   DSA RAG Chatbot - Cai dat tu dong (Windows)
echo ====================================================
echo.

:: Kiem tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Python chua duoc cai dat!
    echo      Tai tai: https://www.python.org/downloads/
    pause & exit /b 1
)
echo [OK] Python da co san

:: Tao virtual environment
if not exist ".venv" (
    echo [1/5] Tao virtual environment...
    python -m venv .venv
) else (
    echo [1/5] Virtual environment da ton tai
)

:: Kich hoat venv
echo [2/5] Kich hoat venv...
call .venv\Scripts\activate.bat

:: Nang cap pip
echo [3/5] Nang cap pip...
python -m pip install --upgrade pip -q

:: Cai thu vien
echo [4/5] Cai dat thu vien (co the mat 2-3 phut)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [LOI] Cai thu vien that bai!
    pause & exit /b 1
)
echo [OK] Thu vien da cai xong

:: Tao file .env
echo [5/5] Tao file .env...
if not exist ".env" (
    copy .env.example .env > nul
    echo [OK] Da tao file .env
    echo.
    echo >>> QUAN TRONG: Mo file .env va dien GEMINI_API_KEY cua ban <<<
) else (
    echo [OK] File .env da ton tai
)

:: Tao thu muc
if not exist "data" mkdir data
if not exist "chroma_db" mkdir chroma_db

echo.
echo ====================================================
echo   CAI DAT HOAN TAT!
echo ====================================================
echo.
echo Buoc tiep theo:
echo   1. Mo file .env
echo   2. Thay 'your_gemini_api_key_here' bang API key that
echo   3. Nap tai lieu: python ingest.py --file data\tailieu.pdf
echo   4. Chay chatbot: streamlit run app.py
echo.
pause
