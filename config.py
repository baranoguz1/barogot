# config.py
import os
from dotenv import load_dotenv
from pathlib import Path


# 📌 .env Dosyasını Yükle (Proje kök dizininden)
# Betiğin bulunduğu dizindeki .env dosyasını yüklemeye çalışır.
# Eğer farklı bir yerde ise, dotenv_path'i uygun şekilde güncelleyebilirsiniz.
dotenv_path = Path(__file__).resolve().parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"⚠️ .env dosyası bulunamadı: {dotenv_path}")


# --- DOSYA YOLLARI ---
# Projenin kök dizinini temel alan çıktı klasörü
OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "output"
HTML_FILE_PATH = OUTPUT_DIRECTORY / "haberler.html"
RATINGS_CSV_PATH = OUTPUT_DIRECTORY / "gunluk_reytingler.csv"
RATINGS_EXCEL_PATH = OUTPUT_DIRECTORY / "gunluk_reytingler.xlsx"
# Gerekirse hata ayıklama dosyaları için yollar:
# DEBUG_FLASHSCORE_PATH = OUTPUT_DIRECTORY / "debug_flashscore.html"


# --- API BİLGİLERİ ---
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")


# --- GENEL AYARLAR ---
CITY = "Istanbul"
UNITS = "metric"
LANG = "tr"
TIME_OFFSET_HOURS = 3
OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "output"


# --- API ve HİZMET URL'leri ---
TMDB_API_URL = f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_API_KEY}&language=tr-TR&region=TR&page=1"
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
OPENWEATHER_FORECAST_URL = f"https://api.openweathermap.org/data/2.5/forecast?q={WEATHER_CITY}&appid={OPENWEATHER_API_KEY}&units={WEATHER_UNITS}&lang={WEATHER_LANG}"
TRENDS24_URL = "https://trends24.in/turkey/istanbul/"
TIAK_URL = "https://tiak.com.tr/tablolar"
ISTANBUL_KITAPCISI_URL = "https://www.istanbulkitapcisi.com/cok-satan-kitaplar"
ZORLU_PSM_URL = "https://www.zorlupsm.com/etkinlikler"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_PLAYLIST_ID = "42QvezcAoVfm9pdUQzM6xy" # Yeni Türkçe Rap
SPOTIFY_PLAYLIST_TRACKS_URL = f"https://api.spotify.com/v1/playlists/{SPOTIFY_PLAYLIST_ID}/tracks?market=from_token&limit=50"


# 📌 KATEGORİLERE GÖRE RSS ADRESLERİ
RSS_FEEDS = {
    "Gündem": [
        "https://www.cnnturk.com/feed/rss/turkiye/news",
        "https://www.ntv.com.tr/turkiye.rss",
        "http://www.hurriyet.com.tr/rss/gundem",
    ],
    "Yabancı Kaynak": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.theguardian.com/world/rss"
    ],
    "Dünya": [
        "https://www.cnnturk.com/feed/rss/dunya/news",
        "https://www.ntv.com.tr/dunya.rss",
        "http://feeds.bbci.co.uk/turkce/rss.xml",
        "https://tr.sputniknews.com/export/rss2/archive/index.xml"
    ],
    "Ekonomi": [
        "https://www.cnnturk.com/feed/rss/ekonomi/news",
    ],
    "Magazin": [
        "https://www.cnnturk.com/feed/rss/magazin/news",
        "https://www.magazinsortie.com/rss/tum-mansetler"
    ],
    "Spor": [
        "https://www.cnnturk.com/feed/rss/spor/news",
        "https://www.ntv.com.tr/spor.rss"
    ],
    "Sanat": [
        "https://www.sanattanyansimalar.com/rss.xml"
    ]
}


# --- SPOR FİKSTÜRÜ AYARLARI ---
SPORT_LEAGUES_CONFIG = [
    ("futbol/ingiltere/premier-league", "Premier League"),
    ("futbol/ispanya/laliga", "La Liga"),
    ("futbol/turkiye/super-lig", "Süper Lig"),
    ("futbol/avrupa/sampiyonlar-ligi", "Şampiyonlar Ligi"),
    ("basketbol/turkiye/super-lig", "Süper Lig (Basketbol)")
    ]


# --- WEB SCRAPING SEÇİCİLERİ (SELECTORS) ---

# İstanbul Kitapçısı
KITAP_WAIT_SELECTOR = "div.product-item"
KITAP_TITLE_SELECTOR = "a.product-title"
KITAP_AUTHOR_SELECTOR = "a.model-title"
KITAP_IMAGE_SELECTOR = "a.image-wrapper img"


# Zorlu PSM Etkinlikleri
ZORLU_EVENT_CARD_SELECTOR = "div.event-list-card-wrapper-link"
ZORLU_TITLE_LINK_SELECTOR = "a.event-list-card-item-detail-text"
ZORLU_IMAGE_SELECTOR = "div.event-list-card-content > a > img"
ZORLU_DATE_SELECTOR = "div.location.col-location p.date"
ZORLU_TIME_SELECTOR = "div.location.col-location b.hour"
ZORLU_VENUE_SELECTOR = "div.location.place p"
ZORLU_CATEGORY_SELECTOR = "div.event-list-card-item-header"


# TIAK Reytingleri
TIAK_GUNLUK_BUTON_XPATH = "//div[contains(@id, 'gunluk-tablolar')]"
TIAK_TABLE_CONTAINER_CLASS = "gunluktablo"


# Flashscore
# Not: Flashscore seçicileri spor türüne göre dinamik olarak belirlendiği için,
# ana class'ları buraya ekleyebiliriz.
FLASHSCORE_MATCH_ELEMENT_SELECTOR = "div[class*='event__match']"
FLASHSCORE_TIME_CLASS = "event__time"
# Futbol Takımları
FLASHSCORE_FUTBOL_HOME_TEAM_CLASS = "event__homeParticipant"
FLASHSCORE_FUTBOL_AWAY_TEAM_CLASS = "event__awayParticipant"
# Basketbol Takımları
FLASHSCORE_BASKETBOL_HOME_TEAM_CLASS = "event__participant--home"
FLASHSCORE_BASKETBOL_AWAY_TEAM_CLASS = "event__participant--away"