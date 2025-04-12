import os
import telebot
import asyncio
from dotenv import load_dotenv
from shazamio import Shazam
import yt_dlp
import eyed3

# .env faylidan bot tokenini yuklab olish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Shazam orqali musiqa aniqlash
async def recognize_song(file_path):
    shazam = Shazam()
    result = await shazam.recognize_song(file_path)
    try:
        track = result['track']
        title = track['title']
        artist = track['subtitle']
        return f"{artist} - {title}"
    except:
        return None

# YouTube-dan MP3 formatida musiqa yuklab olish
def download_mp3(search_query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'outtmpl': 'downloaded_song.%(ext)s',
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            return 'downloaded_song.mp3'
        except Exception as e:
            print("Yuklab olishda xatolik:", e)
            return None

# MP3 faylga ID3 taglarini qo‘shish (musiqa nomi va ijrochi)
def add_id3_tags(file_path, artist, title):
    audiofile = eyed3.load(file_path)
    audiofile.tag.artist = artist
    audiofile.tag.title = title
    audiofile.tag.save()

# Media fayllarni qabul qilish va qayta ishlash
@bot.message_handler(content_types=['audio', 'voice', 'video'])
def handle_media(message):
    file_id = (
        message.audio.file_id if message.content_type == 'audio' else
        message.voice.file_id if message.content_type == 'voice' else
        message.video.file_id
    )

    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with open("temp_input.mp3", 'wb') as f:
        f.write(downloaded_file)

    # Asinxron tarzda musiqani aniqlash
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    query = loop.run_until_complete(recognize_song("temp_input.mp3"))

    if not query:
        bot.reply_to(message, "❌ Musiqa aniqlanmadi.")
        return

    bot.reply_to(message, f"🔍 Qidirilmoqda: {query}")

    # Musiqani yuklab olish
    mp3_file = download_mp3(query)

    if mp3_file and os.path.exists(mp3_file):
        # ID3 taglarini qo‘shish
        add_id3_tags(mp3_file, query.split(' - ')[0], query.split(' - ')[1])

        # Faylni yuborish
        with open(mp3_file, 'rb') as audio:
            bot.send_audio(message.chat.id, audio)

        # Yuklab olingan faylni o‘chirish
        os.remove(mp3_file)
    else:
        bot.send_message(message.chat.id, "❌ MP3 yuklab bo‘lmadi.")

    # Xatolikdan so‘ng vaqtinchalik faylni o‘chirish
    os.remove("temp_input.mp3")

# Botni ishga tushurish
bot.infinity_polling()
