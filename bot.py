import os
import asyncio
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument, 
    MessageMediaWebPage, Channel, Chat,
    DocumentAttributeAudio, DocumentAttributeVideo, DocumentAttributeFilename
)
from telethon.errors import SessionPasswordNeededError
from datetime import datetime
import json
import re
from pathlib import Path
from dotenv import load_dotenv

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("⚠️  Модуль qrcode не установлен. Установите: pip install qrcode[pil]")


load_dotenv()

API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
BASE_DIR = Path(__file__).parent
QR_DIR = BASE_DIR / 'qr_codes'
SESSIONS_DIR = BASE_DIR / 'sessions'
DOWNLOADS_DIR = BASE_DIR / 'downloads'
QR_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)


class TelegramDownloader:
    def __init__(self, api_id, api_hash, session_name='default'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.username = None
        
        # Путь к файлу сессии
        self.session_path = SESSIONS_DIR / session_name
        
        self.client = TelegramClient(
            str(self.session_path),
            api_id,
            api_hash,
            device_model="iPhone 13",
            system_version="iOS 15.4",
            app_version="8.4",
            lang_code="en",
            system_lang_code="en-US"
        )
        
        self.download_path = DOWNLOADS_DIR
    
    def _print_qr_code(self, url):
        """Печать QR-кода в терминале"""
        if not QR_AVAILABLE:
            return False
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            print("\n" + "="*60)
            print("📱 ОТСКАНИРУЙТЕ ЭТОТ QR-КОД:")
            print("="*60)
            qr.print_ascii(invert=True)
            print("="*60)
            return True
        except Exception as e:
            print(f"⚠️  Не удалось отобразить QR-код в терминале: {e}")
            return False
    
    def _save_qr_image(self, url, filename=None):
        """Сохранение QR-кода как изображение"""
        if not QR_AVAILABLE:
            return False
        
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'qr_{timestamp}.png'
            
            filepath = QR_DIR / filename
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(str(filepath))
            print(f"💾 QR-код сохранен: {filepath}")
            return True
        except Exception as e:
            print(f"⚠️  Не удалось сохранить QR-код: {e}")
            return False
    
    async def _rename_session_folder(self):
        """Переименование папки сессии после успешной авторизации"""
        try:
            me = await self.client.get_me()
            if me and me.username:
                self.username = me.username
                new_session_name = f"@{me.username}"
                new_session_path = SESSIONS_DIR / new_session_name
                
                if self.session_name == 'default':
                    await self.client.disconnect()
                    
                    old_file = Path(str(self.session_path) + '.session')
                    new_file = Path(str(new_session_path) + '.session')
                    
                    if old_file.exists() and not new_file.exists():
                        old_file.rename(new_file)
                        print(f"📁 Сессия переименована: {new_session_name}")
                    
                    self.session_path = new_session_path
                    self.session_name = new_session_name
                    
                    self.client = TelegramClient(
                        str(self.session_path),
                        self.api_id,
                        self.api_hash,
                        device_model="iPhone 13",
                        system_version="iOS 15.4",
                        app_version="8.4",
                        lang_code="en",
                        system_lang_code="en-US"
                    )
                    await self.client.connect()
        except Exception as e:
            print(f"⚠️  Не удалось переименовать сессию: {e}")
    
    async def start(self):
        """Запуск клиента и авторизация"""
        print("\n📱 Подключение к Telegram...")
        
        try:
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                self.username = me.username
                print("✓ Используется сохраненная сессия")
                print(f"👤 Имя: {me.first_name} {me.last_name or ''}")
                print(f"🔖 Username: @{me.username if me.username else '[нет]'}")
                return True
            
            print("✗ Авторизация не найдена, требуется вход")
            
            print("\n" + "="*60)
            print("ВЫБЕРИТЕ СПОСОБ ВХОДА:")
            print("="*60)
            print("1. QR-код (РЕКОМЕНДУЕТСЯ)")
            print("2. Код из SMS/Telegram")
            print("="*60)
            
            choice = input("\nВаш выбор (1/2): ").strip()
            
            # QR
            if choice == "1":
                print("\n🔄 Генерирую QR-код...")
                qr_login = await self.client.qr_login()
                
                print("\n" + "="*60)
                print("📱 QR-код для входа")
                print("="*60)
                print(f"\n🔗 Ссылка: {qr_login.url}")
                qr_printed = self._print_qr_code(qr_login.url)
                qr_saved = self._save_qr_image(qr_login.url)
                print("\n📋 Инструкция:")
                print("1. Откройте Telegram на телефоне")
                print("2. Настройки → Устройства → Подключить устройство")
                
                if qr_printed:
                    print("3. Отсканируйте QR-код ВЫШЕ ↑↑↑")
                elif qr_saved:
                    print("3. Откройте файл в папке qr_codes/ и отсканируйте")
                else:
                    print("3. Скопируйте ссылку выше и откройте в браузере")
                
                print("4. Подтвердите вход")
                print("\n⏳ Ожидаю сканирования (10 минут)...")
                print("="*60)
                
                try:
                    await asyncio.wait_for(qr_login.wait(), timeout=600)
                    print("✓ QR-код успешно отсканирован!")
                    
                except asyncio.TimeoutError:
                    print("\n✗ Время ожидания вышло (10 минут)")
                    print("💡 Попробуйте еще раз или используйте вход по коду")
                    await self.client.disconnect()
                    return False
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    # 2FA errors check
                    if any(keyword in error_msg for keyword in ['password', 'two-step', '2fa', 'two_step']):
                        print("✓ QR-код отсканирован, обнаружена двухфакторная аутентификация")
                        print("\n🔒 Требуется пароль 2FA")
                        print("="*60)
                        password = input("🔑 Введите пароль: ").strip()
                        
                        try:
                            await self.client.sign_in(password=password)
                            print("✓ Вход с 2FA успешен!")
                        except Exception as pwd_error:
                            print(f"✗ Ошибка при вводе пароля: {pwd_error}")
                            await self.client.disconnect()
                            return False
                    else:
                        print(f"⚠️  Произошла ошибка при входе: {e}")
                        print("💡 Попробуйте перезапустить скрипт")
                        await self.client.disconnect()
                        return False
            
            # SMS CODE
            else:
                phone = input("\n📱 Введите номер телефона (+79123456789): ").strip()
                
                print("\n" + "="*60)
                print("⚠️  ВАЖНО:")
                print("="*60)
                print("1. НЕ копируйте код в буфер обмена")
                print("2. Вводите код ВРУЧНУЮ")
                print("="*60)
                
                sent_code = await self.client.send_code_request(phone)
                print(f"\n✓ Код отправлен: {sent_code.type}")
                
                code = input("\n✏️  Введите код ВРУЧНУЮ: ").strip()
                
                try:
                    await self.client.sign_in(
                        phone=phone,
                        code=code,
                        phone_code_hash=sent_code.phone_code_hash
                    )
                    print("✓ Код принят!")
                    
                except SessionPasswordNeededError:
                    print("\n🔒 Требуется пароль 2FA")
                    password = input("🔑 Введите пароль: ").strip()
                    await self.client.sign_in(password=password)
                    print("✓ Вход с 2FA успешен!")
                except Exception as e:
                    print(f"✗ Ошибка: {e}")
                    await self.client.disconnect()
                    return False
            
            # CHECKING AUTH
            me = await self.client.get_me()
            if me:
                print("\n" + "="*60)
                print("✅ УСПЕШНАЯ АВТОРИЗАЦИЯ")
                print("="*60)
                print(f"👤 Имя: {me.first_name} {me.last_name or ''}")
                print(f"🔖 Username: @{me.username if me.username else '[нет]'}")
                print(f"🆔 ID: {me.id}")
                
                # NAMING SESSION BY USERNAME
                await self._rename_session_folder()
                
                session_file = Path(str(self.session_path) + '.session')
                if session_file.exists():
                    print(f"💾 Сессия сохранена: {session_file}")
                else:
                    print(f"⚠️  Файл сессии не найден")
                
                print("="*60 + "\n")
                return True
            else:
                print("✗ Не удалось получить данные пользователя")
                await self.client.disconnect()
                return False
            
        except Exception as e:
            print(f"\n✗ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            await self.client.disconnect()
            return False
    
    async def get_entity_info(self, channel_link):
        """Получение информации о канале/группе"""
        try:
            entity = await self.client.get_entity(channel_link)
            if isinstance(entity, (Channel, Chat)):
                print(f"✓ Найден: {entity.title}")
                return entity
            return None
        except Exception as e:
            print(f"✗ Ошибка получения канала: {e}")
            return None
    
    def _get_document_filename(self, document, message_id, message_date, default_ext='bin'):
        """Получение имени файла для документа"""
        filename = None
        
        for attr in document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
                break
        
        if not filename:
            date_str = message_date.strftime('%Y%m%d_%H%M%S') if message_date else datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if document.mime_type:
                ext = document.mime_type.split('/')[-1]
            else:
                ext = default_ext
            
            for attr in document.attributes:
                if isinstance(attr, DocumentAttributeAudio):
                    if attr.voice:
                        filename = f"voice_{message_id}_{date_str}.ogg"
                        break
                    else:
                        filename = f"audio_{message_id}_{date_str}.{ext}"
                        break
            
            if not filename:
                for attr in document.attributes:
                    if isinstance(attr, DocumentAttributeVideo):
                        filename = f"video_{message_id}_{date_str}.{ext}"
                        break
            
            if not filename:
                filename = f"document_{message_id}_{date_str}.{ext}"
        
        return filename
    
    async def download_all_content(self, channel_entity):
        """Скачивание всего контента из канала/группы"""
        if isinstance(channel_entity, str):
            entity = await self.get_entity_info(channel_entity)
            if not entity:
                return
        else:
            entity = channel_entity
        
        safe_name = "".join(c for c in entity.title if c.isalnum() or c in (' ', '-', '_'))
        channel_path = self.download_path / safe_name
        channel_path.mkdir(exist_ok=True)
        
        stats = {
            'photos': 0,
            'videos': 0,
            'documents': 0,
            'voices': 0,
            'messages': 0,
            'links': []
        }
        
        messages_data = []
        
        print(f"\n📥 Начинаю скачивание из: {entity.title}")
        print("-" * 50)
        
        try:
            async for message in self.client.iter_messages(entity):
                stats['messages'] += 1
                
                message_info = {
                    'id': message.id,
                    'date': message.date.isoformat() if message.date else None,
                    'text': message.text or '',
                    'views': message.views,
                    'forwards': message.forwards
                }
                
                if message.text:
                    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 
                                    message.text)
                    if urls:
                        stats['links'].extend(urls)
                        message_info['links'] = urls
                
                if message.media:
                    try:
                        if isinstance(message.media, MessageMediaPhoto):
                            filename = f"photo_{message.id}_{message.date.strftime('%Y%m%d_%H%M%S')}.jpg"
                            filepath = channel_path / 'photos' / filename
                            filepath.parent.mkdir(exist_ok=True)
                            
                            await self.client.download_media(message.media, str(filepath))
                            stats['photos'] += 1
                            message_info['media'] = {'type': 'photo', 'file': filename}
                            print(f"  📷 Фото: {filename}")
                            
                        elif isinstance(message.media, MessageMediaDocument):
                            doc = message.media.document
                            
                            is_voice = False
                            for attr in doc.attributes:
                                if isinstance(attr, DocumentAttributeAudio) and attr.voice:
                                    is_voice = True
                                    break
                            
                            if is_voice:
                                folder = 'voices'
                                stats['voices'] += 1
                                emoji = "🎤"
                            elif 'video' in doc.mime_type:
                                folder = 'videos'
                                stats['videos'] += 1
                                emoji = "🎥"
                            else:
                                folder = 'documents'
                                stats['documents'] += 1
                                emoji = "📄"
                            
                            filename = self._get_document_filename(doc, message.id, message.date)
                            
                            filepath = channel_path / folder / filename
                            filepath.parent.mkdir(exist_ok=True)
                            
                            await self.client.download_media(message.media, str(filepath))
                            
                            message_info['media'] = {
                                'type': folder,
                                'file': filename,
                                'mime': doc.mime_type,
                                'size': doc.size
                            }
                            
                            if is_voice:
                                for attr in doc.attributes:
                                    if isinstance(attr, DocumentAttributeAudio):
                                        message_info['media']['duration'] = attr.duration
                                        break
                            
                            print(f"  {emoji} {folder.capitalize()}: {filename}")
                            
                        elif isinstance(message.media, MessageMediaWebPage):
                            if message.media.webpage.url:
                                stats['links'].append(message.media.webpage.url)
                                message_info['webpage'] = message.media.webpage.url
                                
                    except Exception as e:
                        print(f"  ✗ Ошибка скачивания медиа (ID {message.id}): {e}")
                        message_info['download_error'] = str(e)
                
                messages_data.append(message_info)
                
                if stats['messages'] % 100 == 0:
                    print(f"  ⏳ Обработано сообщений: {stats['messages']}")
                    
        except Exception as e:
            print(f"✗ Ошибка при получении сообщений: {e}")
        
        metadata = {
            'channel': entity.title,
            'channel_id': entity.id,
            'download_date': datetime.now().isoformat(),
            'stats': stats,
            'messages': messages_data
        }
        
        metadata_file = channel_path / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        if stats['links']:
            unique_links = list(set(stats['links']))
            with open(channel_path / 'links.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(unique_links))
        
        texts_file = channel_path / 'all_texts.txt'
        with open(texts_file, 'w', encoding='utf-8') as f:
            for msg in messages_data:
                if msg.get('text'):
                    f.write(f"--- Сообщение ID: {msg['id']} | Дата: {msg.get('date', 'N/A')} ---\n")
                    f.write(msg['text'] + '\n\n')
        
        print("\n" + "=" * 50)
        print("✓ Скачивание завершено!")
        print(f"📊 Статистика:")
        print(f"  • Всего сообщений: {stats['messages']}")
        print(f"  • Фотографий: {stats['photos']}")
        print(f"  • Видео: {stats['videos']}")
        print(f"  • Голосовых сообщений: {stats['voices']}")
        print(f"  • Документов: {stats['documents']}")
        print(f"  • Ссылок найдено: {len(set(stats['links']))}")
        print(f"📁 Путь: {channel_path}")
        print("=" * 50)


async def main():
    print("=" * 50)
    print("🤖 Telegram Content Downloader")
    print("=" * 50)
    
    if not API_ID or not API_HASH:
        print("\n✗ ОШИБКА: API_ID и API_HASH не настроены!")
        print("📝 Создайте файл .env и добавьте:")
        print("   API_ID=ваш_api_id")
        print("   API_HASH=ваш_api_hash")
        print("\n💡 Получить можно на: https://my.telegram.org")
        return
    
    downloader = TelegramDownloader(API_ID, API_HASH, 'default')
    
    if not await downloader.start():
        print("\n✗ Не удалось авторизоваться")
        return
    
    print("\n" + "="*60)
    print("ВЫБЕРИТЕ СПОСОБ ДОСТУПА К КАНАЛУ/ГРУППЕ:")
    print("="*60)
    print("1. Ввести ссылку или @username")
    print("2. Выбрать из списка моих диалогов")
    print("3. Ввести ID группы/канала напрямую")
    print("="*60)
    
    choice = input("\nВаш выбор (1/2/3): ").strip()
    
    channel_entity = None
    
    if choice == "2":
        print("\n📋 Загружаю список ваших диалогов...")
        dialogs = []
        async for dialog in downloader.client.iter_dialogs():
            dialogs.append(dialog)
        
        print("\n" + "="*60)
        print("ВАШИ ГРУППЫ И КАНАЛЫ:")
        print("="*60)
        
        groups_channels = []
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                groups_channels.append(dialog)
                entity_type = "📢 Канал" if dialog.is_channel else "👥 Группа"
                members = f"({dialog.entity.participants_count} участников)" if hasattr(dialog.entity, 'participants_count') else ""
                print(f"{len(groups_channels)}. {entity_type} | {dialog.name} {members}")
        
        if not groups_channels:
            print("✗ У вас нет групп или каналов")
            return
        
        print("="*60)
        choice_num = input(f"\nВведите номер (1-{len(groups_channels)}): ").strip()
        
        try:
            idx = int(choice_num) - 1
            if 0 <= idx < len(groups_channels):
                channel_entity = groups_channels[idx].entity
                print(f"✓ Выбрано: {groups_channels[idx].name}")
            else:
                print("✗ Неверный номер")
                return
        except ValueError:
            print("✗ Введите число")
            return
    
    elif choice == "3":
        print("\n📝 Введите ID группы/канала (например: -1001234567890)")
        channel_id = input("   ID: ").strip()
        
        try:
            channel_entity = await downloader.client.get_entity(int(channel_id))
            print(f"✓ Найдено: {channel_entity.title}")
        except Exception as e:
            print(f"✗ Ошибка получения группы по ID: {e}")
            return
    
    else:
        print("\n📝 Введите ссылку на канал или группу:")
        print("   Примеры: @channelname, https://t.me/channelname")
        channel_link = input("   Ссылка: ").strip()
        
        if not channel_link:
            print("✗ Ссылка не указана")
            return
        
        try:
            channel_entity = await downloader.client.get_entity(channel_link)
            print(f"✓ Найдено: {channel_entity.title}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return
    
    if channel_entity:
        await downloader.download_all_content(channel_entity)
    
    print("\n💾 Отключаюсь от Telegram...")
    
    if downloader.client.is_connected():
        await downloader.client.disconnect()
    
    print("👋 Работа завершена!")
    print(f"💡 Сессия сохранена: sessions/{downloader.session_name}.session")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n✗ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()