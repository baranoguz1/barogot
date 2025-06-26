# data_fetchers/api_fetchers.py
"""
API'ler üzerinden veri çeken fonksiyonları içerir.
(OpenWeatherMap, TMDB, ExchangeRate, RSS, Spotify vb.)
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import feedparser
from bs4 import BeautifulSoup
import time

# Ana dizindeki config dosyasını import ediyoruz
import config

def get_hourly_weather(limit=8):
    """OpenWeatherMap API'den saatlik hava durumu tahminlerini çeker."""
    if not config.OPENWEATHER_API_KEY:
        print("⚠️ OpenWeatherMap API anahtarı bulunamadı.")
        return []

    print(f"ℹ️ {config.WEATHER_CITY} için hava durumu çekiliyor...")
    try:
        # URL ve diğer ayarlar config dosyasından alınır
        response = requests.get(config.OPENWEATHER_FORECAST_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "list" not in data:
            print(f"⚠️ Hava durumu verisi alınamadı (API yanıtı eksik): {data.get('message', 'Detay yok')}")
            return []

        hourly_forecast = []
        for forecast_item in data["list"]:
            if len(hourly_forecast) >= limit:
                break
            try:
                utc_dt = datetime.fromtimestamp(forecast_item["dt"], tz=timezone.utc)
                local_dt = utc_dt + timedelta(hours=config.TIME_OFFSET_HOURS)
                time_str = local_dt.strftime("%H:%M")
                temp = forecast_item["main"]["temp"]
                description = forecast_item["weather"][0]["description"].capitalize()
                icon_code = forecast_item["weather"][0].get("icon")
                icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else "https://via.placeholder.com/50"

                weather_class = "default-weather"
                desc_lower = description.lower()
                if any(s in desc_lower for s in ["açık", "güneşli", "clear"]): weather_class = "sunny"
                elif any(s in desc_lower for s in ["yağmur", "sağanak", "rain", "shower"]): weather_class = "rainy"
                elif any(s in desc_lower for s in ["kar", "snow"]): weather_class = "snowy"
                elif any(s in desc_lower for s in ["bulut", "kapalı", "cloud"]): weather_class = "cloudy"

                hourly_forecast.append((time_str, temp, description, icon_url, weather_class))
            except (KeyError, IndexError) as e_item:
                print(f"⚠️ Hava durumu tahmini öğesi ayrıştırılamadı: {e_item} - {forecast_item}")
                continue
        print(f"✅ {config.WEATHER_CITY} için {len(hourly_forecast)} saatlik hava durumu tahmini çekildi.")
        return hourly_forecast
    except requests.exceptions.RequestException as e:
        print(f"⚠️ OpenWeatherMap API Hatası: {e}")
        return []
    except (KeyError, TypeError):
        print("⚠️ OpenWeatherMap API yanıt formatı beklenmedik.")
        return []

def fetch_movies(limit=10):
    """TMDB API'den vizyondaki filmleri çeker."""
    if not config.TMDB_API_KEY:
        print("⚠️ TMDB API anahtarı bulunamadı.")
        return []
        
    print("ℹ️ Vizyondaki filmler (TMDB) çekiliyor...")
    try:
        response = requests.get(config.TMDB_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        movies = data.get("results", [])
        print(f"✅ TMDB'den {len(movies[:limit])} film çekildi.")
        return movies[:limit]
    except requests.exceptions.RequestException as e:
        print(f"⚠️ TMDB API isteği başarısız oldu: {e}")
        return []
    except KeyError:
        print("⚠️ TMDB API yanıt formatı beklenmedik.")
        return []

def get_exchange_rates():
    """USD bazlı temel döviz kurlarını çeker."""
    print("ℹ️ Döviz kurları çekiliyor...")
    try:
        response = requests.get(config.EXCHANGE_RATE_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        rates = data.get("rates", {})
        usd_to_try = rates.get("TRY")
        if not usd_to_try:
            print("⚠️ Döviz kuru verisi alınamadı veya TRY kuru eksik.")
            return {}

        eur_to_usd = rates.get("EUR", 0)
        gbp_to_usd = rates.get("GBP", 0)

        currency_rates = {
            "USDTRY": round(usd_to_try, 2),
            "EURTRY": round(usd_to_try / eur_to_usd, 2) if eur_to_usd else "N/A",
            "GBPTRY": round(usd_to_try / gbp_to_usd, 2) if gbp_to_usd else "N/A",
        }
        print(f"✅ Döviz kurları çekildi: {currency_rates}")
        return currency_rates
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Döviz kuru API hatası: {e}")
        return {}
    except (KeyError, TypeError):
        print("⚠️ Döviz kuru API yanıt formatı beklenmedik.")
        return {}

def fetch_rss_feed(url):
    """Verilen RSS URL'sinden haberleri çeker ve tarihleri parse eder."""
    try:
        print(f"📰 RSS okunuyor: {url}")
        feed = feedparser.parse(url)
        if feed.bozo:
            # bozo=1 ise feed düzgün parse edilememiştir.
            raise Exception(f"RSS formatı bozuk - {feed.bozo_exception}")

        source_name = feed.feed.title
        news_items = []
        for entry in feed.entries:
            # Tarih bilgisini parse etmeye çalış
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                # feedparser'ın parse ettiği time.struct_time'ı datetime nesnesine çevir
                parsed_date = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
            else:
                # Eğer tarih bilgisi yoksa, şu anki zamanı UTC olarak kullan
                parsed_date = datetime.now(timezone.utc)

            summary_soup = BeautifulSoup(entry.summary, 'html.parser')
            summary = summary_soup.get_text(separator=' ', strip=True)

            news_items.append({
                'source': source_name,
                'title': entry.title,
                'link': entry.link,
                'summary': summary,
                'pub_date': entry.get('published', 'Tarih yok'),
                'pub_date_parsed': parsed_date  # SIRALAMA İÇİN GEREKLİ ANAHTAR
            })
        return news_items
    except Exception as e:
        print(f"❌ RSS okuma hatası ({url}): {e}")
        return None

def get_spotify_token():
    """Spotify API için erişim token'ı alır veya yeniler."""
    if not all([config.SPOTIFY_CLIENT_ID, config.SPOTIFY_CLIENT_SECRET, config.SPOTIFY_REFRESH_TOKEN]):
        print("⚠️ Spotify API kimlik bilgileri (.env dosyasında) eksik.")
        return None

    try:
        response = requests.post(config.SPOTIFY_TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": config.SPOTIFY_REFRESH_TOKEN,
        }, auth=(config.SPOTIFY_CLIENT_ID, config.SPOTIFY_CLIENT_SECRET))

        response.raise_for_status()
        new_token = response.json()["access_token"]
        return new_token
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Spotify token yenileme hatası: {e}")
        return None
    except KeyError:
        print("⚠️ Spotify API yanıtında 'access_token' bulunamadı.")
        return None

def get_new_turkish_rap_tracks_embed(limit=10):
    """Belirli bir Spotify çalma listesinden parçaları çeker."""
    print("ℹ️ Spotify parça listesi çekiliyor...")
    token = get_spotify_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(config.SPOTIFY_PLAYLIST_TRACKS_URL, headers=headers)
        response.raise_for_status()
        items = response.json().get("items", [])

        rap_tracks = []
        for item in items:
            if len(rap_tracks) >= limit:
                break
            track = item.get("track")
            if not track or not track.get("id"):
                continue

            name = track.get("name", "Bilinmeyen Şarkı")
            artists = ", ".join([a.get("name", "Bilinmeyen Sanatçı") for a in track.get("artists", [])])
            track_id = track["id"]
            embed_url = f"https://open.spotify.com/embed/track/{track_id}"
            rap_tracks.append({"artist": artists, "title": name, "embed_url": embed_url})

        print(f"✅ Spotify'dan {len(rap_tracks)} parça çekildi.")
        return rap_tracks

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Spotify API parça çekme hatası: {e}")
        return []
    except KeyError:
        print("⚠️ Spotify API yanıt formatı beklenmedik.")
        return []
    

def fetch_ticketmaster_events(limit=20):
    """
    Ticketmaster API'sini kullanarak Türkiye'deki etkinlikleri çeker.
    """
    print("ℹ️ Ticketmaster etkinlikleri çekiliyor...")
    if not config.TICKETMASTER_API_KEY:
        print("⚠️ Ticketmaster API anahtarı bulunamadı.")
        return []

    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        'apikey': config.TICKETMASTER_API_KEY,
        'countryCode': 'TR',
        'size': limit,
        'sort': 'date,asc' # Etkinlikleri tarihe göre sırala
    }

    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "_embedded" not in data:
            print("✅ Ticketmaster: Yaklaşan etkinlik bulunamadı.")
            return []

        fetched_events = data["_embedded"]["events"]
        istanbul_events = []

        for event in fetched_events:
            # HTML şablonunuzun beklediği formata dönüştürüyoruz
            image_url = event['images'][0]['url'] if event.get('images') else 'https://via.placeholder.com/300x200.png?text=Etkinlik'
            venue_info = event.get('_embedded', {}).get('venues', [{}])[0]

            istanbul_events.append({
                'title': event.get('name', 'Başlık Yok'),
                'link': event.get('url', '#'),
                'image_url': image_url,
                'date_str': event.get('dates', {}).get('start', {}).get('localDate', 'Tarih Belirtilmemiş'),
                'venue': venue_info.get('name', 'Mekan Belirtilmemiş'),
                'location': venue_info.get('city', {}).get('name', 'Şehir Belirtilmemiş'),
                'category': event.get('classifications', [{}])[0].get('segment', {}).get('name', 'Genel')
            })

        print(f"✅ Ticketmaster'dan {len(istanbul_events)} etkinlik başarıyla çekildi.")
        return istanbul_events

    except requests.exceptions.RequestException as e:
        print(f"❌ Ticketmaster API isteği sırasında bir HATA oluştu: {e}")
        return []
    except KeyError as e:
        print(f"❌ Ticketmaster API yanıtı işlenirken bir HATA oluştu (beklenmeyen format): {e}")
        return []
