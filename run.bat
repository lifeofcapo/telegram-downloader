@echo off
chcp 65001 >nul

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    python telegram_downloader.py
) else (
    echo ❌ Виртуальное окружение не найдено!
    echo 📝 Сначала запустите: setup.bat
    pause
)