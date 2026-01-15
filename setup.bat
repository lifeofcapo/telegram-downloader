@echo off
chcp 65001 >nul
echo 🚀 Настройка Telegram Content Downloader
echo ==========================================
echo.

REM Создание виртуального окружения
echo 📦 Создаю виртуальное окружение...
python -m venv venv

REM Активация виртуального окружения
echo 🔄 Активирую виртуальное окружение...
call venv\Scripts\activate.bat

REM Обновление pip
echo ⬆️  Обновляю pip...
python -m pip install --upgrade pip

REM Установка зависимостей
echo 📥 Устанавливаю зависимости...
pip install -r requirements.txt

REM Создание структуры папок
echo 📁 Создаю структуру папок...
if not exist downloads mkdir downloads
if not exist sessions mkdir sessions
if not exist qr_codes mkdir qr_codes

REM Создание .env файла из примера
if not exist .env (
    echo 📝 Создаю файл .env...
    copy .env.example .env
    echo.
    echo ⚠️  ВАЖНО: Отредактируйте файл .env и добавьте ваши API credentials!
    echo    Получить их можно на: https://my.telegram.org/auth
) else (
    echo ✓ Файл .env уже существует
)

echo.
echo ✅ Установка завершена!
echo.
echo 📋 Следующие шаги:
echo 1. Отредактируйте .env и добавьте API_ID и API_HASH
echo 2. Активируйте окружение: venv\Scripts\activate.bat
echo 3. Запустите скрипт: python telegram_downloader.py
echo.
echo 💡 Получить API credentials: https://my.telegram.org/auth
echo.
pause