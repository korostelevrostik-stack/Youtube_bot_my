import telebot
from telebot import types
import yt_dlp
import os
import re
import time
import subprocess

# ===== ТОКЕН =====
TOKEN = '8707409862:AAFEfJxi8sXmCdg1Uy9Nb-R4qBMFSzl83Rw'
bot = telebot.TeleBot(TOKEN)

# Статистика пользователей
user_stats = {}

# Поддерживаемые сайты
SUPPORTED_SITES = r'(tiktok\.com|instagram\.com|vk\.com|twitter\.com|x\.com|facebook\.com|fb\.com|reddit\.com|dailymotion\.com|vimeo\.com|twitch\.tv|bilibili\.com|rutube\.ru|soundcloud\.com|bandcamp\.com)'
AUDIO_ONLY = r'(soundcloud\.com|bandcamp\.com)'

user_urls = {}
user_trims = {}

# ===== КОМАНДА /start =====
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📹 Видео"),
        types.KeyboardButton("🎵 MP3"),
        types.KeyboardButton("🖼 Превью"),
        types.KeyboardButton("✂️ Обрезать"),
        types.KeyboardButton("📂 Плейлист"),
        types.KeyboardButton("📊 Моя статистика"),
        types.KeyboardButton("❌ Отмена")
    )
    bot.send_message(
        chat_id,
        "🎬 **YouTube Downloader Bot**\n\n"
        "📌 **Поддерживает:**\n"
        "• TikTok • Instagram • VK • Twitter/X • Facebook\n"
        "• Reddit • Twitch • Bilibili • Rutube\n"
        "• Dailymotion • Vimeo\n"
        "• SoundCloud • Bandcamp (сразу MP3!)\n\n"
        "✂️ **Новая фича:**\n"
        "• Обрезай видео — укажи диапазон, например:\n"
        "  `00:30-01:20` или `1:30-2:45`\n\n"
        "🔥 **Как пользоваться:**\n"
        "1️⃣ Кинь ссылку\n"
        "2️⃣ Выбери действие\n"
        "3️⃣ Для обрезки введи время!",
        parse_mode='Markdown',
        reply_markup=markup
    )

# ===== ОБРАБОТЧИК КНОПОК =====
@bot.message_handler(func=lambda message: message.text in ['📹 Видео', '🎵 MP3', '🖼 Превью', '✂️ Обрезать', '📂 Плейлист', '📊 Моя статистика', '❌ Отмена'])
def buttons(message):
    chat_id = message.chat.id
    text = message.text

    if text == '❌ Отмена':
        if chat_id in user_urls:
            del user_urls[chat_id]
        if chat_id in user_trims:
            del user_trims[chat_id]
        markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "❌ Отменено!", reply_markup=markup)
        start(message)
        return

    if text == '📊 Моя статистика':
        show_stats(chat_id)
        return

    if chat_id not in user_urls:
        bot.send_message(chat_id, "❌ Сначала кинь ссылку!")
        return

    url = user_urls[chat_id]

    if text == '🎵 MP3':
        download_audio(chat_id, url)
        return

    if text == '🖼 Превью':
        download_thumbnail(chat_id, url)
        return

    if text == '✂️ Обрезать':
        bot.send_message(
            chat_id,
            "✂️ Введи **диапазон обрезки** в формате:\n"
            "`MM:SS-MM:SS` или `ЧЧ:MM:SS-ЧЧ:MM:SS`\n\n"
            "📌 **Примеры:**\n"
            "• `00:30-01:20` — с 30 секунд до 1 минуты 20 секунд\n"
            "• `1:30-2:45` — с 1:30 до 2:45\n"
            "• `00:00-00:15` — первые 15 секунд\n\n"
            "⏳ После ввода — бот скачает и обрежет видео.",
            parse_mode='Markdown'
        )
        user_trims[chat_id] = {'url': url}
        return

    if text == '📹 Видео':
        video_menu(chat_id, url)
        return

    if text == '📂 Плейлист':
        download_playlist(chat_id, url)
        return

# ===== ОБРАБОТЧИК ДИАПАЗОНА ОБРЕЗКИ =====
@bot.message_handler(func=lambda message: True)
def handle_trim_input(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id not in user_trims:
        return

    # Проверяем формат: MM:SS-MM:SS или HH:MM:SS-HH:MM:SS
    pattern = r'^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$'
    pattern_full = r'^(\d{1,2}):(\d{2}):(\d{2})-(\d{1,2}):(\d{2}):(\d{2})$'
    
    match = re.match(pattern, text)
    match_full = re.match(pattern_full, text)

    if not match and not match_full:
        bot.send_message(
            chat_id,
            "❌ Неверный формат!\n\n"
            "Используй: `MM:SS-MM:SS` или `HH:MM:SS-HH:MM:SS`\n"
            "📌 Пример: `00:30-01:20`",
            parse_mode='Markdown'
        )
        return

    if match:
        start_min, start_sec, end_min, end_sec = map(int, match.groups())
        start_time = start_min * 60 + start_sec
        end_time = end_min * 60 + end_sec
    else:
        h1, m1, s1, h2, m2, s2 = map(int, match_full.groups())
        start_time = h1 * 3600 + m1 * 60 + s1
        end_time = h2 * 3600 + m2 * 60 + s2

    if start_time >= end_time:
        bot.send_message(chat_id, "❌ Начало должно быть **меньше** конца!", parse_mode='Markdown')
        return

    url = user_trims[chat_id]['url']
    bot.send_message(chat_id, f"✂️ Обрезаю **{text}**... ⏳", parse_mode='Markdown')
    download_and_trim(chat_id, url, start_time, end_time)

# ===== ВИДЕО МЕНЮ =====
def video_menu(chat_id, url):
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("⚡ Лучшее (до 4K)"),
        types.KeyboardButton("720p"),
        types.KeyboardButton("1080p"),
        types.KeyboardButton("480p"),
        types.KeyboardButton("360p"),
        types.KeyboardButton("144p"),
        types.KeyboardButton("2K"),
        types.KeyboardButton("4K"),
        types.KeyboardButton("🔙 Назад")
    )
    bot.send_message(
        chat_id,
        "🎬 **Выбери качество:**",
        parse_mode='Markdown',
        reply_markup=markup
    )

# ===== ОБРАБОТЧИК КАЧЕСТВА =====
@bot.message_handler(func=lambda message: message.text in ['⚡ Лучшее (до 4K)', '720p', '1080p', '480p', '360p', '144p', '2K', '4K', '🔙 Назад'])
def quality_buttons(message):
    chat_id = message.chat.id
    text = message.text

    if text == '🔙 Назад':
        start(message)
        return

    if chat_id not in user_urls:
        bot.send_message(chat_id, "❌ Сначала кинь ссылку!")
        return

    url = user_urls[chat_id]

    quality_map = {
        '⚡ Лучшее (до 4K)': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '720p': 'best[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]',
        '1080p': 'best[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]',
        '480p': 'best[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]',
        '360p': 'best[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]',
        '144p': 'best[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[height<=144][ext=mp4]',
        '2K': 'best[height<=1440][ext=mp4]+bestaudio[ext=m4a]/best[height<=1440][ext=mp4]',
        '4K': 'best[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160][ext=mp4]',
    }

    bot.send_message(chat_id, f"⏳ Качаю **{text}**... ⏳", parse_mode='Markdown')
    download_video(chat_id, url, quality_map[text], text)

def download_video(chat_id, url, quality, quality_name):
    try:
        ydl_opts = {
            'format': quality,
            'merge_output_format': 'mp4',
            'outtmpl': f'video_{chat_id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            update_stats(chat_id, info.get('extractor', 'unknown'))

        filename = f'video_{chat_id}.mp4'
        if os.path.exists(filename):
            size = os.path.getsize(filename) / (1024 * 1024)
            with open(filename, 'rb') as f:
                bot.send_video(chat_id, f, caption=f"🎬 **{quality_name}** готово! ({size:.1f} МБ)", parse_mode='Markdown')
            os.remove(filename)
        else:
            bot.send_message(chat_id, "❌ Файл не найден")

        cleanup(chat_id)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)[:200]}")
        cleanup(chat_id)

# ===== СКАЧИВАНИЕ И ОБРЕЗКА =====
def download_and_trim(chat_id, url, start_time, end_time):
    try:
        # Скачиваем видео
        ydl_opts = {
            'format': 'best[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'merge_output_format': 'mp4',
            'outtmpl': f'trim_{chat_id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            update_stats(chat_id, info.get('extractor', 'unknown'))

        input_file = f'trim_{chat_id}.mp4'
        output_file = f'trimmed_{chat_id}.mp4'

        if not os.path.exists(input_file):
            bot.send_message(chat_id, "❌ Не удалось скачать видео.")
            return

        # Обрезаем через ffmpeg
        duration = end_time - start_time
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c', 'copy',
            output_file,
            '-y'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            size = os.path.getsize(output_file) / (1024 * 1024)
            with open(output_file, 'rb') as f:
                bot.send_video(
                    chat_id,
                    f,
                    caption=f"✂️ Обрезанное видео готово!\n"
                            f"⏱ {start_time//60}:{start_time%60:02d} → {end_time//60}:{end_time%60:02d}\n"
                            f"💾 {size:.1f} МБ",
                    parse_mode='Markdown'
                )
            os.remove(output_file)
        else:
            bot.send_message(chat_id, f"❌ Ошибка обрезки: {result.stderr[:200]}")

        os.remove(input_file)
        cleanup(chat_id)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)[:200]}")
        cleanup(chat_id)

# ===== СКАЧИВАНИЕ АУДИО =====
def download_audio(chat_id, url):
    bot.send_message(chat_id, "🎵 Скачиваю MP3... ⏳")
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'audio_{chat_id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            update_stats(chat_id, info.get('extractor', 'unknown'))

        filename = f'audio_{chat_id}.mp3'
        if os.path.exists(filename):
            size = os.path.getsize(filename) / (1024 * 1024)
            with open(filename, 'rb') as f:
                bot.send_audio(chat_id, f, caption=f"🎵 MP3 готов! ({size:.1f} МБ)")
            os.remove(filename)
        else:
            bot.send_message(chat_id, "❌ Файл не найден")

        cleanup(chat_id)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)[:200]}")
        cleanup(chat_id)

# ===== СКАЧИВАНИЕ ПРЕВЬЮ =====
def download_thumbnail(chat_id, url):
    bot.send_message(chat_id, "🖼 Получаю обложку... ⏳")
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumb = info.get('thumbnail')
            if thumb:
                bot.send_photo(chat_id, thumb, caption="🖼 Обложка видео!")
                update_stats(chat_id, info.get('extractor', 'unknown'))
            else:
                bot.send_message(chat_id, "❌ Обложка не найдена")
        cleanup(chat_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {str(e)[:200]}")
        cleanup(chat_id)

# ===== СКАЧИВАНИЕ ПЛЕЙЛИСТА =====
def download_playlist(chat_id, url):
    bot.send_message(chat_id, "📂 Скачиваю плейлист... ⏳")
    try:
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]',
            'merge_output_format': 'mp4',
            'outtmpl': f'playlist_{chat_id}_%(index)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get('entries', [])
            total = len(entries)
            site = info.get('extractor', 'unknown')

            for i in range(total):
                filename = f'playlist_{chat_id}_{i+1}.mp4'
                if os.path.exists(filename):
                    size = os.path.getsize(filename) / (1024 * 1024)
                    with open(filename, 'rb') as f:
                        bot.send_video(chat_id, f, caption=f"🎬 {i+1}/{total} ({size:.1f} МБ)")
                    os.remove(filename)
                    update_stats(chat_id, site)
                time.sleep(1)

        bot.send_message(chat_id, f"✅ Плейлист ({total} видео) скачан!")
        cleanup(chat_id)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка плейлиста: {str(e)[:200]}")
        cleanup(chat_id)

# ===== СТАТИСТИКА =====
def show_stats(chat_id):
    if chat_id not in user_stats:
        bot.send_message(chat_id, "📊 У тебя пока нет скачиваний.")
        return

    total = user_stats[chat_id].get('total', 0)
    sites = user_stats[chat_id].get('sites', {})

    if total == 0:
        bot.send_message(chat_id, "📊 Ты ещё ничего не скачал.")
        return

    top = sorted(sites.items(), key=lambda x: x[1], reverse=True)[:3]
    top_text = "\n".join([f"• {site}: {count}" for site, count in top])

    bot.send_message(
        chat_id,
        f"📊 **Твоя статистика:**\n\n"
        f"📥 Всего скачиваний: **{total}**\n"
        f"🏆 Топ сайтов:\n{top_text}",
        parse_mode='Markdown'
    )

def update_stats(chat_id, site):
    if chat_id not in user_stats:
        user_stats[chat_id] = {'total': 0, 'sites': {}}
    user_stats[chat_id]['total'] += 1
    user_stats[chat_id]['sites'][site] = user_stats[chat_id]['sites'].get(site, 0) + 1

# ===== ОБРАБОТЧИК ССЫЛОК =====
@bot.message_handler(func=lambda message: True)
def handle_url(message):
    chat_id = message.chat.id
    url = message.text.strip()

    if chat_id in user_trims:
        return  # Если ожидаем ввод диапазона обрезки

    if not re.search(SUPPORTED_SITES, url):
        bot.reply_to(
            message,
            "❌ Это не ссылка с поддерживаемого сайта!\n\n"
            "✅ **Поддерживаются:**\n"
            "• TikTok • Instagram • VK • Twitter/X • Facebook\n"
            "• Reddit • Twitch • Bilibili • Rutube\n"
            "• Dailymotion • Vimeo\n"
            "• SoundCloud • Bandcamp\n\n"
            "💡 Кинь ссылку и выбери действие из кнопок."
        )
        return

    if re.search(AUDIO_ONLY, url):
        download_audio(chat_id, url)
        return

    user_urls[chat_id] = url

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📹 Видео"),
        types.KeyboardButton("🎵 MP3"),
        types.KeyboardButton("🖼 Превью"),
        types.KeyboardButton("✂️ Обрезать"),
        types.KeyboardButton("📂 Плейлист"),
        types.KeyboardButton("📊 Моя статистика"),
        types.KeyboardButton("❌ Отмена")
    )

    bot.send_message(
        chat_id,
        "✅ **Ссылка сохранена!**\n\n"
        "📌 **Выбери действие:**",
        parse_mode='Markdown',
        reply_markup=markup
    )

# ===== ОЧИСТКА =====
def cleanup(chat_id):
    if chat_id in user_urls:
        del user_urls[chat_id]
    if chat_id in user_trims:
        del user_trims[chat_id]
    for f in os.listdir('.'):
        if f.startswith(f'video_{chat_id}') or f.startswith(f'audio_{chat_id}') or f.startswith(f'playlist_{chat_id}') or f.startswith(f'trim_{chat_id}') or f.startswith(f'trimmed_{chat_id}'):
            try:
                os.remove(f)
            except:
                pass

# ===== ЗАПУСК =====
print("🚀 БОТ ЗАПУЩЕН!")
print("📌 Поддерживает: TikTok, Instagram, VK, Twitter, Facebook, Reddit, Twitch, Bilibili, Rutube, Dailymotion, Vimeo")
print("✂️ Новая фича: ОБРЕЗКА ВИДЕО!")
print("🔥 Жду ссылки...")
bot.infinity_polling()
