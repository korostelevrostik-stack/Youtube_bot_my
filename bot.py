import telebot
from telebot import types
import yt_dlp
import os
import re

TOKEN = '8707409862:AAFEfJxi8sXmCdg1Uy9Nb-R4qBMFSzl83Rw'  # ЗАМЕНИ НА СВОЙ ТОКЕН ОТ @BotFather

bot = telebot.TeleBot(TOKEN)

# Настройки для разных качеств
QUALITY_OPTS = {
    '144p': 'best[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[height<=144][ext=mp4]',
    '240p': 'best[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[height<=240][ext=mp4]',
    '360p': 'best[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]',
    '480p': 'best[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]',
    '720p': 'best[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]',
    '1080p': 'best[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]',
    '2K': 'best[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440][ext=mp4]',
    '4K': 'best[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]',
    '🎵 MP3': 'bestaudio/best',
    '🖼 Превью': 'thumbnail',
}

user_urls = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        "🎬 Привет! Я скачиваю видео с YouTube.\n\n"
        "1. Кинь мне ссылку на видео\n"
        "2. Выбери качество из кнопок\n"
        "3. Получи видео, звук или обложку!"
    )

@bot.message_handler(func=lambda message: True)
def handle_url(message):
    url = message.text.strip()
    
    if not re.search(r'(youtube\.com|youtu\.be)', url):
        bot.reply_to(message, "❌ Это не ссылка с YouTube! Попробуй ещё раз.")
        return
    
    user_urls[message.chat.id] = url
    
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    buttons = ['144p', '240p', '360p', '480p', '720p', '1080p', '2K', '4K', '🎵 MP3', '🖼 Превью']
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    
    bot.send_message(
        message.chat.id,
        "✅ Ссылка сохранена! Теперь выбери, что скачать:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text in QUALITY_OPTS)
def download_choice(message):
    chat_id = message.chat.id
    choice = message.text
    
    if chat_id not in user_urls:
        bot.send_message(chat_id, "❌ Сначала кинь ссылку на видео!")
        return
    
    url = user_urls[chat_id]
    bot.send_message(chat_id, f"⏳ Начинаю скачивание... Это может занять несколько секунд.")
    
    try:
        # Для превью используем отдельную логику
        if choice == '🖼 Превью':
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                thumbnail = info.get('thumbnail')
                if thumbnail:
                    bot.send_photo(chat_id, thumbnail, caption="🖼 Вот обложка видео!")
                else:
                    bot.send_message(chat_id, "❌ Не удалось найти обложку.")
            return
        
        # Для MP3
        if choice == '🎵 MP3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': f'video_{chat_id}.%(ext)s',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            
            filename = f'video_{chat_id}.mp3'
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    bot.send_audio(chat_id, f, caption="🎵 Держи звук в MP3!")
                os.remove(filename)
            return
        
        # Для видео
        ydl_opts = {
            'format': QUALITY_OPTS[choice],
            'merge_output_format': 'mp4',
            'outtmpl': f'video_{chat_id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        
        filename = f'video_{chat_id}.mp4'
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                bot.send_video(chat_id, f, caption=f"🎬 Видео {choice} готово!")
            os.remove(filename)
        else:
            bot.send_message(chat_id, "❌ Не удалось найти скачанный файл.")
        
        # Убираем клавиатуру и очищаем ссылку
        markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "✅ Готово! Можешь кинуть новую ссылку.", reply_markup=markup)
        del user_urls[chat_id]
        
    except Exception as e:
        error_msg = str(e)[:200]
        bot.send_message(chat_id, f"❌ Ошибка при скачивании: {error_msg}")
        # Чистим мусор
        for f in os.listdir('.'):
            if f.startswith(f'video_{chat_id}'):
                os.remove(f)

print("🚀 Бот запущен! Жду ссылки...")
bot.infinity_polling()
