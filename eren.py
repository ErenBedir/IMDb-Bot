import json
import time
from imdb import IMDb
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Giriş
ia = IMDb()
TOKEN = 'burayatoken' 

# Önbellek
CACHE_FILE = 'cache.json'
CACHE_EXPIRATION = 3600  # 1 saat (3600sn=1s)

# yasandıbittisaygısızca (bitmeseydi be)
def movie_to_dict(movie):
    return {
        'title': movie.get('title', 'Bilinmiyor'),
        'year': movie.get('year', 'Bilinmiyor'),
        'rating': movie.get('rating', 'Bilinmiyor'),
        'directors': [director['name'] for director in movie.get('directors', [])],
        'cast': [actor['name'] for actor in movie.get('cast', [])[:5]],  # Başrolleri al tanıdık cıkar ankaradan
        'kind': movie.get('kind', 'Bilinmiyor'),
        'movieID': movie.movieID,
        'full-size cover url': movie.get('full-size cover url', '')
    }

# Önbelleği yüklemek
def load_cache():
    try:
        with open(CACHE_FILE, 'r') as file:
            cache = json.load(file)
        return cache
    except (FileNotFoundError, json.JSONDecodeError):
        # Dosya bulunamazsa ya da JSON geçersizse boş bir önbellek döndür (anlayana)
        return {}

# Önbelleği kaydetmek
def save_cache(cache):
    with open(CACHE_FILE, 'w') as file:
        json.dump(cache, file)

# IMDb verisini önbellekten almak veya yenisini almak
def get_movie_from_cache_or_api(movie_name):
    cache = load_cache()
    current_time = time.time()
    
    # kocum almıs onbellege
    if movie_name in cache:
        cached_data = cache[movie_name]
        if current_time - cached_data['timestamp'] < CACHE_EXPIRATION:
            print("Önbellekten veri bakıyom..")
            return cached_data['data']
        else:
            print("Önbellek sogumus hoca ben sunu tazeliyim....")

    # yokmuş önbellekte napcaz
    print("IMDb API'den veri cekiyom...")
    results = ia.search_movie(movie_name)
    movie_data = results[0] if results else None

    # kafir jsonla ugrasıyorum
    if movie_data:
        movie_dict = movie_to_dict(movie_data)

        # önbellege KAYDET (emir)
        cache[movie_name] = {
            'timestamp': current_time,
            'data': movie_dict
        }
        save_cache(cache)
    
    return movie_dict

# Başlangıç mesajı askoooo
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 selamun aleykum.\n"
                                    "dizi film adı yaz neyi var yok dokeyim sana kardess. ")

# IMDb araması yapan mevzu
async def search_imdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    movie_data = get_movie_from_cache_or_api(query)
    
    # ne anlatıyon be abla diyen mesaj
    if not movie_data:
        await update.message.reply_text("❌ böyle bişi yok babba! belki yanlış yazmışındır.")
        return
    
    # pogaca var simit var neye bakıyon
    keyboard = [
        [InlineKeyboardButton(f"{movie_data['title']} ({movie_data.get('year', 'Bilinmiyor')})", callback_data=movie_data['movieID'])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔍 mite sordurdum bunlar var seç:", reply_markup=reply_markup)

# expertiz 
async def show_movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # dur isimi yapıyorum mesajı
    waiting_message = await query.message.reply_text("🔄 ankaradan bilgileri istedim geliyo...")

    # Seçilen film/dizi bilgilerini al
    movie_id = query.data
    movie = ia.get_movie(movie_id)
    
    # Bilgileri ayıkla
    movie_data = movie_to_dict(movie)
    title = movie_data['title']
    year = movie_data['year']
    rating = movie_data['rating']
    director = ', '.join(movie_data['directors'])
    cast = ', '.join(movie_data['cast'])
    imdb_url = f"https://www.imdb.com/title/tt{movie_id}/"
    poster_url = movie_data.get('full-size cover url')  # Poster görselinin URL'sini al (lazım)
    
    # Film/Dizi ek bilgileri
    kind = movie_data['kind']
    extra_info = ""
    if kind == "movie":  # Film ise süresini ekle (lütfen)
        duration = movie.get('runtimes', ['Bilinmiyor'])[0]
        extra_info = f"⏰ *Süre*: {duration} dakika"
    elif kind == "tv series":  # Dizi ise sezon, bölüm sayısı ve yılları ekle (güzel olur diye düşündüm)
        seasons = movie.get('seasons', [])
        seasons_count = len(seasons) if isinstance(seasons, list) else seasons
        episodes = movie.get('number of episodes', 'Bilinmiyor')
        extra_info = (f"📅 *Sezon*: {seasons_count}\n"
                      f"📺 *Bölüm Sayısı*: {episodes}\n"
                      f"🗓 *Yıllar*: {movie.get('series years', 'Bilinmiyor')}")

    # Emoji ile süslenmiş havalı çıktı
    details = (
        f"🎬 *Ad*: {title}\n"
        f"📅 *Yapım Yılı*: {year}\n"
        f"⭐️ *IMDb*: {rating}\n"
        f"🎥 *Yönetmen*: {director}\n"
        f"🌟 *Başroller*: {cast}\n"
        f"{extra_info}\n"
        f"🔗 [IMDb Sayfası]({imdb_url})\n\n"
        f"_github.com/erenbedir_"
    )
    
    # dur isimi yapayım mesajını sil (onun beni sildiği gibi)
    await waiting_message.delete()

    # Poster görselini ve bilgileri aynı mesajda gönder (estetik algılarım)
    if poster_url:
        await context.bot.send_photo(
            chat_id=query.message.chat_id, 
            photo=poster_url, 
            caption=details, 
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(details, parse_mode="Markdown")

# marş bas
def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    # olmazsan olmaz
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_imdb))
    application.add_handler(CallbackQueryHandler(show_movie_details))
    
    # bas gaza askımm
    application.run_polling()

if __name__ == '__main__':
    main()

# Bu kod github.com/erenbedir tarafından yazılmıs ve incelenmistir..
# Tamamen kafa dagıtmak icin yazdım beyler. hatası varsa affola.