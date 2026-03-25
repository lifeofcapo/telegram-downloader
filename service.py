import os
import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import random

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("⚠️  Модуль qrcode не установлен. Установите: pip install qrcode[pil]")

load_dotenv()

API_ID = int(os.getenv('1API_ID', '0'))
API_HASH = os.getenv('1API_HASH', '')
BOT_USERNAME = os.getenv('BOT_USERNAME', '')  

BASE_DIR = Path(__file__).parent
QR_DIR = BASE_DIR / 'qr_codes'
SESSIONS_DIR = BASE_DIR / 'sessions'
QR_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)


class TelegramForwarder:
    def __init__(self, api_id, api_hash, bot_username, session_name='forwarder'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_username = bot_username.replace('@', '')
        self.session_name = session_name
        self.username = None
        
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
        
        # Настройки безопасной пересылки
        self.forward_delay_min = 2  # минимальная задержка между пересылками
        self.forward_delay_max = 5  # максимальная задержка
        self.batch_size = 20  # количество сообщений перед длинной паузой
        self.long_pause_min = 30  # длинная пауза после batch
        self.long_pause_max = 60
        self.forwarded_count = 0
    
    def _print_qr_code(self, url):
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
            print(f"⚠️  Не удалось отобразить QR-код: {e}")
            return False
    
    def _save_qr_image(self, url, filename=None):
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
    
    async def _safe_delay(self):
        """Умная задержка между пересылками"""
        self.forwarded_count += 1
        
        if self.forwarded_count % self.batch_size == 0:
            delay = random.uniform(self.long_pause_min, self.long_pause_max)
            print(f"  ⏸️  ДЛИННАЯ ПАУЗА ({int(delay)}с) после {self.batch_size} сообщений...")
            await asyncio.sleep(delay)
        else:
            delay = random.uniform(self.forward_delay_min, self.forward_delay_max)
            await asyncio.sleep(delay)
    
    async def _rename_session_folder(self):
        try:
            me = await self.client.get_me()
            if me and me.username:
                self.username = me.username
                new_session_name = f"@{me.username}_forwarder"
                new_session_path = SESSIONS_DIR / new_session_name
                
                if self.session_name == 'forwarder':
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
                    await self.client.disconnect()
                    return False
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ['password', 'two-step', '2fa', 'two_step']):
                        print("✓ QR-код отсканирован, обнаружена двухфакторная аутентификация")
                        print("\n🔒 Требуется пароль 2FA")
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
                        await self.client.disconnect()
                        return False
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
            
            me = await self.client.get_me()
            if me:
                print("\n" + "="*60)
                print("✅ УСПЕШНАЯ АВТОРИЗАЦИЯ")
                print("="*60)
                print(f"👤 Имя: {me.first_name} {me.last_name or ''}")
                print(f"🔖 Username: @{me.username if me.username else '[нет]'}")
                print(f"🆔 ID: {me.id}")
                
                await self._rename_session_folder()
                
                session_file = Path(str(self.session_path) + '.session')
                if session_file.exists():
                    print(f"💾 Сессия сохранена: {session_file}")
                
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
    
    async def forward_all_to_bot(self, channel_entity, limit=None):
        """Пересылка всех сообщений из канала боту"""
        
        if isinstance(channel_entity, str):
            try:
                entity = await self.client.get_entity(channel_entity)
            except Exception as e:
                print(f"✗ Ошибка получения канала: {e}")
                return
        else:
            entity = channel_entity
        
        # Получаем сущность бота
        try:
            bot_entity = await self.client.get_entity(self.bot_username)
            print(f"✓ Бот найден: @{self.bot_username}")
        except Exception as e:
            print(f"✗ Ошибка получения бота: {e}")
            print(f"💡 Убедитесь что бот @{self.bot_username} существует")
            print(f"💡 Напишите боту /start чтобы активировать его")
            return
        
        print(f"\n📤 Начинаю пересылку из: {entity.title}")
        print(f"📬 Получатель: @{self.bot_username}")
        print("🐢 БЕЗОПАСНЫЙ РЕЖИМ: паузы 2-5с между сообщениями")
        print(f"📦 BATCH: пауза 30-60с после каждых {self.batch_size} сообщений")
        
        if limit:
            print(f"⚠️  ЛИМИТ: будет переслано максимум {limit} сообщений")
        
        print("-" * 50)
        
        self.forwarded_count = 0
        total_messages = 0
        errors = 0
        
        try:
            # Отправляем боту сообщение о начале
            await self.client.send_message(
                bot_entity,
                f"🚀 **НАЧАЛО ПЕРЕСЫЛКИ**\n\n"
                f"📢 Канал: {entity.title}\n"
                f"🆔 ID: {entity.id}\n"
                f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            messages_to_forward = []
            
            async for message in self.client.iter_messages(entity, limit=limit):
                total_messages += 1
                
                # Собираем сообщения в пакет для пересылки
                messages_to_forward.append(message.id)
                
                # Пересылаем каждое сообщение отдельно
                if len(messages_to_forward) >= 1:
                    try:
                        # Задержка ПЕРЕД пересылкой
                        if self.forwarded_count > 0:
                            await self._safe_delay()
                        
                        # Пересылаем сообщение
                        await self.client.forward_messages(
                            bot_entity,
                            messages_to_forward,
                            entity
                        )
                        
                        self.forwarded_count += len(messages_to_forward)
                        
                        # Информация о прогрессе
                        msg_type = "📄"
                        if message.media:
                            if message.photo:
                                msg_type = "📷"
                            elif message.video:
                                msg_type = "🎥"
                            elif message.voice:
                                msg_type = "🎤"
                            elif message.document:
                                msg_type = "📎"
                        
                        print(f"  {msg_type} Переслано: {self.forwarded_count}/{total_messages} | ID: {message.id}")
                        
                        messages_to_forward = []
                        
                    except FloodWaitError as e:
                        wait_time = e.seconds + 5
                        print(f"  ⚠️  FloodWait! Ожидание {wait_time}с...")
                        await asyncio.sleep(wait_time)
                        errors += 1
                        
                    except Exception as e:
                        print(f"  ✗ Ошибка пересылки (ID {message.id}): {e}")
                        errors += 1
                        messages_to_forward = []
                
                # Показываем прогресс каждые 100 сообщений
                if total_messages % 100 == 0:
                    print(f"  ⏳ Обработано: {total_messages} | Переслано: {self.forwarded_count} | Ошибок: {errors}")
            
            # Пересылаем оставшиеся сообщения
            if messages_to_forward:
                try:
                    await self.client.forward_messages(
                        bot_entity,
                        messages_to_forward,
                        entity
                    )
                    self.forwarded_count += len(messages_to_forward)
                except Exception as e:
                    print(f"  ✗ Ошибка пересылки последних сообщений: {e}")
            
            # Отправляем боту сообщение о завершении
            await self.client.send_message(
                bot_entity,
                f"✅ **ПЕРЕСЫЛКА ЗАВЕРШЕНА**\n\n"
                f"📊 Статистика:\n"
                f"• Всего сообщений: {total_messages}\n"
                f"• Переслано: {self.forwarded_count}\n"
                f"• Ошибок: {errors}\n"
                f"📅 Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            print("\n" + "=" * 50)
            print("✅ ПЕРЕСЫЛКА ЗАВЕРШЕНА!")
            print(f"📊 Статистика:")
            print(f"  • Всего сообщений: {total_messages}")
            print(f"  • Переслано успешно: {self.forwarded_count}")
            print(f"  • Ошибок: {errors}")
            print("=" * 50)
            
        except Exception as e:
            print(f"✗ Критическая ошибка при пересылке: {e}")
            import traceback
            traceback.print_exc()


async def main():
    print("=" * 60)
    print("🤖 Telegram Message Forwarder (USERBOT)")
    print("📤 Пересылка сообщений боту")
    print("=" * 60)
    
    if not API_ID or not API_HASH:
        print("\n✗ ОШИБКА: API_ID и API_HASH не настроены!")
        print("📝 Создайте файл .env и добавьте:")
        print("   API_ID=ваш_api_id")
        print("   API_HASH=ваш_api_hash")
        print("\n💡 Получить можно на: https://my.telegram.org")
        return
    
    if not BOT_USERNAME:
        print("\n✗ ОШИБКА: BOT_USERNAME не настроен!")
        print("📝 Добавьте в файл .env:")
        print("   BOT_USERNAME=your_bot_username")
        print("\n💡 Без символа @")
        return
    
    forwarder = TelegramForwarder(API_ID, API_HASH, BOT_USERNAME, 'forwarder')
    
    if not await forwarder.start():
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
        async for dialog in forwarder.client.iter_dialogs():
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
            channel_entity = await forwarder.client.get_entity(int(channel_id))
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
            channel_entity = await forwarder.client.get_entity(channel_link)
            print(f"✓ Найдено: {channel_entity.title}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return
    
    # Спрашиваем про лимит
    print("\n" + "="*60)
    print("ЛИМИТ СООБЩЕНИЙ:")
    print("="*60)
    print("1. Переслать ВСЕ сообщения")
    print("2. Указать лимит (например, 100, 500, 1000)")
    print("="*60)
    
    limit_choice = input("\nВаш выбор (1/2): ").strip()
    limit = None
    
    if limit_choice == "2":
        try:
            limit = int(input("Введите количество сообщений: ").strip())
            print(f"✓ Установлен лимит: {limit} сообщений")
        except ValueError:
            print("⚠️  Неверный формат, будут пересланы ВСЕ сообщения")
    
    if channel_entity:
        print(f"\n⚠️  ВНИМАНИЕ! Перед запуском обязательно:")
        print(f"   1. Откройте бота @{BOT_USERNAME}")
        print(f"   2. Напишите ему /start")
        print(f"   3. Убедитесь что бот активен")
        
        confirm = input("\n✅ Бот активирован? Начать пересылку? (да/нет): ").strip().lower()
        
        if confirm in ['да', 'yes', 'y', 'д']:
            await forwarder.forward_all_to_bot(channel_entity, limit)
        else:
            print("❌ Отменено")
            return
    
    print("\n✅ Работа завершена! Сессия остаётся активной.")
    print(f"💾 Сессия: sessions/{forwarder.session_name}.session")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n✗ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()