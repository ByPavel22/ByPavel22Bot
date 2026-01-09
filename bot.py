import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from database import init_database, get_or_create_user, User, Message, db

# Загрузка конфигурации
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
init_database()

# ========== КОМАНДЫ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_data = update.effective_user
    user, created = get_or_create_user(user_data)
    
    welcome_text = f"""
👋 Привет, {user_data.first_name}!

Я бот-помощник. Все ваши сообщения будут переправлены администратору.

📋 Доступные команды:
/start - Начальное сообщение
/help - Помощь и информация
/feedback - Оставить отзыв
/about - О боте

Просто напишите сообщение, и я передам его!
    """
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📚 Помощь по боту:

• Просто напишите любое сообщение, и оно будет отправлено администратору
• Администратор может ответить на ваше сообщение
• Вы можете использовать команды для навигации

🛠 Команды:
/start - Начало работы
/help - Эта справка
/feedback - Оставить отзыв о работе бота
/about - Информация о боте

📨 Все сообщения сохраняются для истории
    """
    await update.message.reply_text(help_text)

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для оставления отзыва"""
    keyboard = [
        [InlineKeyboardButton("👍 Хорошо", callback_data='feedback_good')],
        [InlineKeyboardButton("👎 Плохо", callback_data='feedback_bad')],
        [InlineKeyboardButton("💡 Предложение", callback_data='feedback_suggest')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Пожалуйста, выберите тип отзыва:",
        reply_markup=reply_markup
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о боте"""
    about_text = """
🤖 Бот для связи с администратором

Версия: 2.0
Разработчик: @ByPavel22

📊 Функции:
• Пересылка сообщений администратору
• Ответы на сообщения пользователей
• Система отзывов
• Статистика использования
• История всех сообщений

🔒 Ваши данные защищены и не передаются третьим лицам
    """
    await update.message.reply_text(about_text)

# ========== ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ ==========

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений от пользователей"""
    user_data = update.effective_user
    message_text = update.message.text
    
    # Сохраняем пользователя в БД
    user, created = get_or_create_user(user_data)
    
    # Сохраняем сообщение в БД
    db.connect()
    User.update(messages_count=User.messages_count + 1).where(User.id == user.id).execute()
    
    message = Message.create(
        user=user,
        text=message_text,
        direction='incoming'
    )
    db.close()
    
    # Формируем сообщение для админа
    user_info = f"👤 Пользователь: {user_data.first_name}"
    if user_data.username:
        user_info += f" (@{user_data.username})"
    
    admin_message = f"""
{user_info}
🆔 ID: {user_data.id}
📊 Сообщений всего: {user.messages_count + 1}
➖➖➖➖➖➖➖➖➖➖
📨 Сообщение:
{message_text}
➖➖➖➖➖➖➖➖➖➖
💬 Ответить: /reply_{user_data.id}
    """
    
    # Отправляем админу
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode='HTML'
        )
        await update.message.reply_text("✅ Ваше сообщение доставлено администратору!")
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")
        await update.message.reply_text("❌ Ошибка отправки. Попробуйте позже.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото"""
    user_data = update.effective_user
    photo = update.message.photo[-1]
    caption = update.message.caption or "Без описания"
    
    user_info = f"👤 {user_data.first_name}"
    if user_data.username:
        user_info += f" (@{user_data.username})"
    
    admin_message = f"""
{user_info}
🆔 ID: {user_data.id}
📸 Прислал фото
➖➖➖➖➖➖➖➖➖➖
📝 Описание: {caption}
💬 Ответить: /reply_{user_data.id}
    """
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=admin_message
    )
    await update.message.reply_text("✅ Фото доставлено!")

# ========== АДМИН-КОМАНДЫ ==========

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика бота (только для админа)"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Эта команда только для администратора")
        return
    
    db.connect()
    total_users = User.select().count()
    total_messages = Message.select().count()
    
    recent_users = User.select().order_by(User.created_at.desc()).limit(5)
    
    stats_text = f"""
📊 <b>Статистика бота</b>

👥 Пользователей: <b>{total_users}</b>
💬 Сообщений: <b>{total_messages}</b>
➖➖➖➖➖➖➖➖➖➖
<b>Послед