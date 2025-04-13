import os
import telebot
import asyncio
from flask import Flask, request
from dotenv import load_dotenv
from shazamio import Shazam
import yt_dlp
import eyed3

# .env faylidan token olish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-app-name.onrender.com/bot

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

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

# YouTube-dan MP3 yuklab olish
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
            ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            return 'downloaded_song.mp3'
        except Exception as e:
            print("Yuklab olishda xatolik:", e)
            return None

# ID3 tag qo‘shish
def add_id3_tags(file_path, artist, title):
    audiofile = eyed3.load(file_path)
    if audiofile.tag is None:
        audiofile.initTag()
    audiofile.tag.artist = artist
    audiofile.tag.title = title
    audiofile.tag.save()

# Telegramga media kelganda
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

    # Musiqani aniqlash
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    query = loop.run_until_complete(recognize_song("temp_input.mp3"))

    if not query:
        bot.reply_to(message, "❌ Musiqa aniqlanmadi.")
        return

    bot.reply_to(message, f"🔍 Qidirilmoqda: {query}")

    # YouTube'dan yuklab olish
    mp3_file = download_mp3(query)

    if mp3_file and os.path.exists(mp3_file):
        add_id3_tags(mp3_file, query.split(' - ')[0], query.split(' - ')[1])

        with open(mp3_file, 'rb') as audio:
            bot.send_audio(message.chat.id, audio)

        os.remove(mp3_file)
    else:
        bot.send_message(message.chat.id, "❌ MP3 yuklab bo‘lmadi.")

    os.remove("temp_input.mp3")

# Flask uchun webhook endpoint
@app.route(f"/bot", methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200

# Flask ishga tushishi
@app.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti!"

# Webhookni o‘rnatish
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

