import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import json
import re

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', '0'))  # Ваш Telegram ID (опционально)

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / 'bot_downloads'
DOWNLOADS_DIR.mkdir(exist_ok=True)


class TelegramReceiverBot:
    def __init__(self, token):
        self.token = token
        self.app = Application.builder().token(token).build()
        self.stats = {
            'total_messages': 0,
            'photos': 0,
            'videos': 0,
            'documents': 0,
            'voices': 0,
            'audios': 0,
            'stickers': 0,
            'animations': 0,
            'texts': 0,
            'links': []
        }
        self.current_channel = None
        self.current_channel_path = None
        self.messages_data = []
        
        # Регистрируем обработчики
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        self.app.add_handler(CommandHandler("reset", self.reset_command))
        self.app.add_handler(MessageHandler(filters.ALL, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        
        welcome_text = (
            f"👋 **Привет, {user.first_name}!**\n\n"
            f"🤖 Я бот-приёмник для сохранения сообщений.\n\n"
            f"📋 **Как использовать:**\n"
            f"1. Запустите userbot скрипт\n"
            f"2. Выберите канал для пересылки\n"
            f"3. Я автоматически сохраню все файлы\n\n"
            f"📊 **Команды:**\n"
            f"/stats - статистика сохранённых файлов\n"
            f"/reset - сбросить статистику\n\n"
            f"🆔 **Ваш ID:** `{user.id}`\n"
            f"💾 **Папка сохранения:** `{DOWNLOADS_DIR}`\n\n"
            f"✅ Бот готов к работе!"
        )
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        print(f"✓ Пользователь {user.first_name} (@{user.username}) активировал бота")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - показать статистику"""
        stats_text = (
            f"📊 **СТАТИСТИКА СОХРАНЕНИЯ**\n\n"
            f"📨 Всего сообщений: {self.stats['total_messages']}\n"
            f"📷 Фотографий: {self.stats['photos']}\n"
            f"🎥 Видео: {self.stats['videos']}\n"
            f"📄 Документов: {self.stats['documents']}\n"
            f"🎤 Голосовых: {self.stats['voices']}\n"
            f"🎵 Аудио: {self.stats['audios']}\n"
            f"🎭 Стикеров: {self.stats['stickers']}\n"
            f"🎬 Анимаций: {self.stats['animations']}\n"
            f"💬 Текстовых: {self.stats['texts']}\n"
            f"🔗 Ссылок найдено: {len(set(self.stats['links']))}\n\n"
        )
        
        if self.current_channel:
            stats_text += f"📢 Текущий канал: {self.current_channel}\n"
            stats_text += f"📁 Путь: `{self.current_channel_path}`"
        else:
            stats_text += "⚠️ Нет активной пересылки"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /reset - сбросить статистику"""
        self.stats = {
            'total_messages': 0,
            'photos': 0,
            'videos': 0,
            'documents': 0,
            'voices': 0,
            'audios': 0,
            'stickers': 0,
            'animations': 0,
            'texts': 0,
            'links': []
        }
        self.current_channel = None
        self.current_channel_path = None
        self.messages_data = []
        
        await update.message.reply_text("✅ Статистика сброшена!")
    
    def _extract_channel_info(self, text):
        """Извлечение информации о канале из сообщения"""
        if "НАЧАЛО ПЕРЕСЫЛКИ" in text or "🚀" in text:
            # Ищем название канала
            lines = text.split('\n')
            for line in lines:
                if "Канал:" in line:
                    channel_name = line.split("Канал:")[-1].strip()
                    return channel_name
        return None
    
    def _create_channel_folder(self, channel_name):
        """Создание папки для канала"""
        safe_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_'))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder_name = f"{safe_name}_{timestamp}"
        
        channel_path = DOWNLOADS_DIR / folder_name
        channel_path.mkdir(exist_ok=True)
        
        # Создаём подпапки
        (channel_path / 'photos').mkdir(exist_ok=True)
        (channel_path / 'videos').mkdir(exist_ok=True)
        (channel_path / 'documents').mkdir(exist_ok=True)
        (channel_path / 'voices').mkdir(exist_ok=True)
        (channel_path / 'audios').mkdir(exist_ok=True)
        (channel_path / 'stickers').mkdir(exist_ok=True)
        (channel_path / 'animations').mkdir(exist_ok=True)
        
        return channel_path
    
    async def _save_metadata(self):
        """Сохранение метаданных"""
        if not self.current_channel_path:
            return
        
        metadata = {
            'channel': self.current_channel,
            'download_date': datetime.now().isoformat(),
            'stats': self.stats,
            'messages': self.messages_data
        }
        
        metadata_file = self.current_channel_path / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Сохранение всех текстов
        if self.messages_data:
            texts_file = self.current_channel_path / 'all_texts.txt'
            with open(texts_file, 'w', encoding='utf-8') as f:
                for msg in self.messages_data:
                    if msg.get('text'):
                        f.write(f"--- Сообщение | Дата: {msg.get('date', 'N/A')} ---\n")
                        f.write(msg['text'] + '\n\n')
        
        # Сохранение ссылок
        if self.stats['links']:
            unique_links = list(set(self.stats['links']))
            links_file = self.current_channel_path / 'links.txt'
            with open(links_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(unique_links))
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка всех входящих сообщений"""
        message = update.effective_message
        user = update.effective_user
        
        # Проверка авторизации (опционально)
        if AUTHORIZED_USER_ID and user.id != AUTHORIZED_USER_ID:
            await message.reply_text("⛔ У вас нет доступа к этому боту")
            return
        
        self.stats['total_messages'] += 1
        
        message_info = {
            'date': message.date.isoformat() if message.date else None,
            'text': message.text or message.caption or '',
        }
        
        # Проверяем на начало пересылки
        if message.text:
            channel_name = self._extract_channel_info(message.text)
            if channel_name:
                self.current_channel = channel_name
                self.current_channel_path = self._create_channel_folder(channel_name)
                print(f"\n🚀 НАЧАЛО ПЕРЕСЫЛКИ из канала: {channel_name}")
                print(f"📁 Папка создана: {self.current_channel_path}")
                await message.reply_text(
                    f"✅ Начата пересылка!\n"
                    f"📢 Канал: {channel_name}\n"
                    f"📁 Путь: `{self.current_channel_path}`",
                    parse_mode='Markdown'
                )
                return
            
            # Проверяем на завершение пересылки
            if "ПЕРЕСЫЛКА ЗАВЕРШЕНА" in message.text or "✅" in message.text:
                await self._save_metadata()
                print(f"\n✅ ПЕРЕСЫЛКА ЗАВЕРШЕНА!")
                print(f"📊 Статистика сохранена в: {self.current_channel_path / 'metadata.json'}")
                await message.reply_text(
                    f"✅ **Пересылка завершена!**\n\n"
                    f"📊 **Статистика:**\n"
                    f"📨 Сообщений: {self.stats['total_messages']}\n"
                    f"📷 Фото: {self.stats['photos']}\n"
                    f"🎥 Видео: {self.stats['videos']}\n"
                    f"📄 Документов: {self.stats['documents']}\n"
                    f"🎤 Голосовых: {self.stats['voices']}\n\n"
                    f"📁 Путь: `{self.current_channel_path}`",
                    parse_mode='Markdown'
                )
                return
        
        # Извлечение ссылок из текста
        if message.text or message.caption:
            text = message.text or message.caption
            urls = re.findall(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                text
            )
            if urls:
                self.stats['links'].extend(urls)
                message_info['links'] = urls
        
        # Если нет активной папки канала, создаём временную
        if not self.current_channel_path:
            self.current_channel_path = self._create_channel_folder("Unknown_Channel")
            self.current_channel = "Unknown Channel"
            print(f"⚠️  Создана временная папка: {self.current_channel_path}")
        
        # Обработка медиа
        try:
            if message.photo:
                # Фото
                file = await message.photo[-1].get_file()
                filename = f"photo_{message.date.strftime('%Y%m%d_%H%M%S')}_{file.file_unique_id}.jpg"
                filepath = self.current_channel_path / 'photos' / filename
                
                await file.download_to_drive(str(filepath))
                self.stats['photos'] += 1
                message_info['media'] = {'type': 'photo', 'file': filename}
                print(f"  📷 Фото сохранено: {filename}")
            
            elif message.video:
                # Видео
                file = await message.video.get_file()
                ext = '.mp4'
                if message.video.mime_type:
                    ext = '.' + message.video.mime_type.split('/')[-1]
                filename = f"video_{message.date.strftime('%Y%m%d_%H%M%S')}_{file.file_unique_id}{ext}"
                filepath = self.current_channel_path / 'videos' / filename
                
                await file.download_to_drive(str(filepath))
                self.stats['videos'] += 1
                message_info['media'] = {'type': 'video', 'file': filename}
                print(f"  🎥 Видео сохранено: {filename}")
            
            elif message.document:
                # Документ
                file = await message.document.get_file()
                filename = message.document.file_name or f"document_{file.file_unique_id}"
                filepath = self.current_channel_path / 'documents' / filename
                
                await file.download_to_drive(str(filepath))
                self.stats['documents'] += 1
                message_info['media'] = {
                    'type': 'document',
                    'file': filename,
                    'mime': message.document.mime_type,
                    'size': message.document.file_size
                }
                print(f"  📄 Документ сохранён: {filename}")
            
            elif message.voice:
                # Голосовое
                file = await message.voice.get_file()
                filename = f"voice_{message.date.strftime('%Y%m%d_%H%M%S')}_{file.file_unique_id}.ogg"
                filepath = self.current_channel_path / 'voices' / filename
                
                await file.download_to_drive(str(filepath))
                self.stats['voices'] += 1
                message_info['media'] = {
                    'type': 'voice',
                    'file': filename,
                    'duration': message.voice.duration
                }
                print(f"  🎤 Голосовое сохранено: {filename}")
            
            elif message.audio:
                # Аудио
                file = await message.audio.get_file()
                filename = message.audio.file_name or f"audio_{file.file_unique_id}.mp3"
                filepath = self.current_channel_path / 'audios' / filename
                
                await file.download_to_drive(str(filepath))
                self.stats['audios'] += 1
                message_info['media'] = {
                    'type': 'audio',
                    'file': filename,
                    'duration': message.audio.duration,
                    'performer': message.audio.performer,
                    'title': message.audio.title
                }
                print(f"  🎵 Аудио сохранено: {filename}")
            
            elif message.sticker:
                # Стикер
                file = await message.sticker.get_file()
                ext = '.webp' if message.sticker.is_animated else '.webp'
                filename = f"sticker_{file.file_unique_id}{ext}"
                filepath = self.current_channel_path / 'stickers' / filename
                
                await file.download_to_drive(str(filepath))
                self.stats['stickers'] += 1
                message_info['media'] = {'type': 'sticker', 'file': filename}
                print(f"  🎭 Стикер сохранён: {filename}")
            
            elif message.animation:
                # GIF/анимация
                file = await message.animation.get_file()
                filename = message.animation.file_name or f"animation_{file.file_unique_id}.mp4"
                filepath = self.current_channel_path / 'animations' / filename
                
                await file.download_to_drive(str(filepath))
                self.stats['animations'] += 1
                message_info['media'] = {'type': 'animation', 'file': filename}
                print(f"  🎬 Анимация сохранена: {filename}")
            
            elif message.text:
                # Текстовое сообщение
                self.stats['texts'] += 1
            
        except Exception as e:
            print(f"  ✗ Ошибка сохранения медиа: {e}")
            message_info['download_error'] = str(e)
        
        self.messages_data.append(message_info)
        
        # Автосохранение метаданных каждые 50 сообщений
        if self.stats['total_messages'] % 50 == 0:
            await self._save_metadata()
            print(f"  💾 Автосохранение метаданных (обработано {self.stats['total_messages']} сообщений)")
    
    def run(self):
        """Запуск бота"""
        print("=" * 60)
        print("🤖 Telegram Receiver Bot")
        print("📥 Приём и сохранение файлов")
        print("=" * 60)
        print(f"💾 Папка сохранения: {DOWNLOADS_DIR}")
        print("✅ Бот запущен и ожидает сообщений...")
        print("=" * 60)
        
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    if not BOT_TOKEN:
        print("\n✗ ОШИБКА: BOT_TOKEN не настроен!")
        print("📝 Добавьте в файл .env:")
        print("   BOT_TOKEN=ваш_токен_от_BotFather")
        exit(1)
    
    bot = TelegramReceiverBot(BOT_TOKEN)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()