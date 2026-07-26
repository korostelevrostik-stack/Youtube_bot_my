import telebot
from telebot import types
import yt_dlp
import os
import re

TOKEN = '8707409862:AAFEfJxi8sXmCdg1Uy9Nb-R4qBMFSzl83Rw'  # ЗАМЕНИ НА СВОЙ

bot = telebot.TeleBot(TOKEN)

# Настройки качества
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
        "🎬 YouTube Downloader Bot\n\n"
        "1. Кинь ссылку на видео\n"
        "2. Выбери качество\n"
        "3. Получи видео, звук или обложку!"
    )

# ===== ОБРАБОТЧИК КНОПОК (ВЫБОР КАЧЕСТВА) =====
@bot.message_handler(func=lambda message: message.text in QUALITY_OPTS)
def download_choice(message):
    chat_id = message.chat.id
    choice = message.text
    
    if chat_id not in user_urls:
        bot.send_message(chat_id, "❌ Сначала кинь ссылку на видео!")
        return
    
    url = user_urls[chat_id]
    bot.send_message(chat_id, f"⏳ Качаю {choice}... Подожди немного ⏳")
    
    try:
        # ===== Превью =====
        if choice == '🖼 Превью':
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                thumb = info.get('thumbnail')
                if thumb:
                    bot.send_photo(chat_id, thumb, caption="🖼 Обложка видео!")
                else:
                    bot.send_message(chat_id, "❌ Обложка не найдена")
            cleanup(chat_id)
            return
        
        # ===== MP3 =====
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
                    bot.send_audio(chat_id, f, caption="🎵 MP3 готов!")
                os.remove(filename)
            cleanup(chat_id)
            return
        
        # ===== Видео =====
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
                bot.send_video(chat_id, f, caption=f"🎬 {choice} готово!")
            os.remove(filename)
        else:
            bot.send_message(chat_id, "❌ Файл не найден")
        
        cleanup(chat_id)
        
    except Exception as e:
        error_msg = str(e)[:200]
        bot.send_message(chat_id, f"❌ Ошибка: {error_msg}")
        cleanup(chat_id)

# ===== ОБРАБОТЧИК ССЫЛОК =====
@bot.message_handler(func=lambda message: True)
def handle_url(message):
    chat_id = message.chat.id
    url = message.text.strip()
    
    # Проверяем, что это ссылка
    if not re.search(r'(youtube\.com|youtu\.be)', url):
        bot.reply_to(message, "❌ Это не ссылка с YouTube! Попробуй ещё раз.")
        return
    
    user_urls[chat_id] = url
    
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    buttons = ['144p', '240p', '360p', '480p', '720p', '1080p', '2K', '4K', '🎵 MP3', '🖼 Превью']
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    
    bot.send_message(
        chat_id,
        "✅ Ссылка сохранена! Теперь выбери, что скачать:",
        reply_markup=markup
    )

def cleanup(chat_id):
    """Удаляет временные файлы и очищает сессию"""
    markup = types.ReplyKeyboardRemove()
    bot.send_message(chat_id, "✅ Готово! Кинь новую ссылку.", reply_markup=markup)
    if chat_id in user_urls:
        del user_urls[chat_id]
    for f in os.listdir('.'):
        if f.startswith(f'video_{chat_id}'):
            try:
                os.remove(f)
            except:
                pass

print("🚀 БОТ ЗАПУЩЕН! Жду ссылки...")
bot.infinity_polling()
