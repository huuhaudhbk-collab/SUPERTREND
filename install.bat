@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Candle Watch: cai dat lan dau ===
if not exist venv (
  python -m venv venv || (echo Khong tim thay Python 3.12. Cai tu python.org roi chay lai. & pause & exit /b 1)
)
call venv\Scripts\activate
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt || (echo Cai thu vien loi & pause & exit /b 1)
if not exist .env copy .env.example .env >nul
python -m pytest tests -q
echo.
echo Xong. run-daily-local.bat de chay thu job; python -m scripts.replay de do lai.
pause
