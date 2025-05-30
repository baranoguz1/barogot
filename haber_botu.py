# -*- coding: utf-8 -*-
import requests
import pandas as pd
import xml.etree.ElementTree as ET
import os
import time
import email.utils
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService # Yeniden adlandırma çakışmayı önler
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
import subprocess
# E-posta kütüphaneleri yorum satırı olarak bırakıldı, ihtiyaç halinde aktif edilebilir
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.base import MIMEBase
# from email import encoders
import sys
import contextlib

# 📌 .env Dosyasını Yükle (Proje kök dizininden)
# Betiğin bulunduğu dizindeki .env dosyasını yüklemeye çalışır.
# Eğer farklı bir yerde ise, dotenv_path'i uygun şekilde güncelleyebilirsiniz.
dotenv_path = Path(__file__).resolve().parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"⚠️ .env dosyası bulunamadı: {dotenv_path}")
    # API anahtarları doğrudan atanabilir veya program sonlandırılabilir.
    # Örnek: API_KEY = "YOUR_OPENWEATHER_API_KEY"

# 📌 OpenWeatherMap API Bilgileri
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY = "Istanbul"
UNITS = "metric"
LANG = "tr"

# ✅ TMDB API bilgileri
TMDB_API_KEY = os.getenv("TMDB_API_KEY") # .env dosyasından TMDB API anahtarını yükle
TMDB_API_URL = f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_API_KEY}&language=tr-TR&region=TR&page=1"

# 📌 Chrome için seçenekleri tanımla
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--log-level=3") # Sadece önemli hataları göster
chrome_options.add_argument("--disable-logging") # Selenium loglarını azaltır

# 📌 Dosyanın Kaydedileceği Yer (Masaüstü yerine betik dizininde bir alt klasör)
output_directory = Path(__file__).resolve().parent / "output"
output_directory.mkdir(parents=True, exist_ok=True) # Klasör yoksa oluştur
html_file_path = output_directory / "haberler.html"
debug_flashscore_path = output_directory / "debug_flashscore.html"
ratings_csv_path = output_directory / "gunluk_reytingler.csv"
ratings_excel_path = output_directory / "gunluk_reytingler.xlsx"


# 📌 Google Maps API anahtarını .env dosyasından al
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

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

@contextlib.contextmanager
def suppress_stderr():
    """Standart hata çıktısını geçici olarak bastırır."""
    # Bu, Selenium'un bazen ürettiği alakasız konsol mesajlarını gizlemek için kullanılabilir.
    # Ancak, hata ayıklama sırasında önemli mesajları da gizleyebileceğinden dikkatli kullanılmalıdır.
    null_fd = os.open(os.devnull, os.O_RDWR)
    save_stderr = os.dup(sys.stderr.fileno())
    os.dup2(null_fd, sys.stderr.fileno())
    try:
        yield
    finally:
        os.dup2(save_stderr, sys.stderr.fileno())
        os.close(null_fd)
        os.close(save_stderr)

# FUTBOL FİKSTÜR
def get_flashscore_fixtures(driver, flashscore_path_segment, league_name):
    """Verilen lig için Flashscore'dan fikstür bilgilerini çeker."""
    try:
        url = f"https://www.flashscore.com.tr/futbol/{flashscore_path_segment}/fikstur/"
        driver.get(url)

        # Çerez popup'ı (varsa)
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            print("🍪 Flashscore çerezleri kabul edildi.")
        except Exception: # TimeoutException, NoSuchElementException vb.
            print("ℹ️ Flashscore çerez popup'ı görünmedi veya tıklanamadı.")

        # Maçların yüklenmesini bekle
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[class*='event__match']"))
        )

        # Sayfa kaynağını debug için kaydet (isteğe bağlı)
        with open(debug_flashscore_path, "w", encoding="utf-8") as debug_file:
            debug_file.write(driver.page_source)

        # with suppress_stderr(): # Hata ayıklama sırasında stderr'i görmek faydalı olabilir
        matches = driver.find_elements(By.CSS_SELECTOR, "div[class^='event__match']")

        fixtures = []
        for match_element in matches:
            try:
                time_val = match_element.find_element(By.CLASS_NAME, "event__time").text.strip()
                home_team = match_element.find_element(By.CLASS_NAME, "event__homeParticipant").text.strip()
                away_team = match_element.find_element(By.CLASS_NAME, "event__awayParticipant").text.strip()
                
                # Bazen boş katılımcı isimleri gelebilir, bunları kontrol et
                if home_team and away_team:
                    fixtures.append(f"{time_val}: {home_team} - {away_team}")
                if len(fixtures) >= 10: # En fazla 10 maç al
                    break
            except Exception: # NoSuchElementException vb.
                # Belirli bir maç öğesi ayrıştırılamazsa devam et
                continue
        
        print(f"✅ {league_name}: {len(fixtures)} maç bulundu.")
        return league_name, fixtures

    except Exception as e:
        print(f"❌ {league_name} Flashscore verisi alınamadı: {e}")
        return league_name, []


# SPOTIFY
def get_spotify_token():
    """Spotify API için erişim token'ı alır veya yeniler."""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("⚠️ Spotify API kimlik bilgileri (.env dosyasında) eksik.")
        return None

    try:
        response = requests.post("https://accounts.spotify.com/api/token", data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }, auth=(client_id, client_secret)) 

        response.raise_for_status() 
        
        new_token = response.json()["access_token"]
        print("✅ Spotify erişim token'ı başarıyla alındı/yenilendi.")
        return new_token
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Spotify token yenileme hatası: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"⚠️ Spotify API Yanıtı: {e.response.text}")
        return None
    except KeyError:
        print("⚠️ Spotify API yanıtında 'access_token' bulunamadı.")
        return None


def get_new_turkish_rap_tracks_embed(limit=10):
    """Belirli bir Spotify çalma listesinden parçaları çeker."""
    token = get_spotify_token()
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}"
    }
    playlist_id = "42QvezcAoVfm9pdUQzM6xy"
    endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?market=from_token&limit=50"

    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        items = response.json().get("items", [])
        
        rap_tracks = []
        for item in items:
            track = item.get("track")
            if not track or not track.get("id"): 
                continue
            
            name = track.get("name", "Bilinmeyen Şarkı")
            artists = ", ".join([a.get("name", "Bilinmeyen Sanatçı") for a in track.get("artists", [])])
            track_id = track["id"]
            embed_url = f"https://open.spotify.com/embed/track/{track_id}"
            rap_tracks.append((artists, name, embed_url))

        print(f"✅ Spotify'dan {len(rap_tracks)} parça çekildi.")
        return rap_tracks

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Spotify API parça çekme hatası: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"⚠️ Spotify API Yanıtı: {e.response.text}")
        return []
    except KeyError:
        print("⚠️ Spotify API yanıt formatı beklenmedik.")
        return []


def get_trending_topics_trends24(city_slug="turkey/istanbul", limit=10):
    """
    trends24.in sitesinden belirtilen şehir için trend olan Twitter başlıklarını çeker.
    Sondaki birleşik sayısal ifadeleri (örn: 27K) temizlemek için regex güncellenmiştir.
    """
    url = f"https://trends24.in/{city_slug}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        
        trend_sections = soup.find_all("ol", class_="trend-card__list")

        if not trend_sections:
            print("⚠️ Trends24: Trend listesi ('ol.trend-card__list') bulunamadı.")
            return []
            
        trend_list_items = trend_sections[0].find_all("li")
        if not trend_list_items:
            print("⚠️ Trends24: Trend öğeleri (li) 'ol.trend-card__list' içinde bulunamadı.")
            return []

        trends = []
        for li in trend_list_items[:limit]:
            trend_text = li.get_text(strip=True) # Örn: "#KademeyiBeklemezsiniz27K"
            
            cleaned_trend = trend_text

            # 1. Baştaki sıralama numarasını kaldır (örn: "1. ", "2. ")
            cleaned_trend = re.sub(r"^\d+\.\s+", "", cleaned_trend).strip()
            
            # 2. Sondaki parantez içindeki tweet/paylaşım sayılarını kaldır (örn: "(15.3K Tweets)")
            cleaned_trend = re.sub(r"\s*\([\d.,]+[KMBkmb]?\s*(?:tweet|tweets|paylaşım|gönderi)\w*\s*\)$", "", cleaned_trend, flags=re.IGNORECASE).strip()
            
            # 3. Trend metninin sonundaki birleşik sayısal son ekleri (örn: "27K", "2K", "57K") kaldır.
            # Bu regex, bir veya daha fazla rakamın ardından K, M, veya B harfinin (büyük/küçük) geldiği
            # ve string'in sonunda bulunduğu durumu hedefler.
            cleaned_trend = re.sub(r"(\d+[KMB])$", "", cleaned_trend, flags=re.IGNORECASE).strip()
            # Örnekler:
            # "#KademeyiBeklemezsiniz27K" -> "#KademeyiBeklemezsiniz"
            # "#ALTINI2K" -> "#ALTINI"
            # "S.A.V57K" -> "S.A.V"

            if cleaned_trend:
                trends.append(cleaned_trend)
        
        if trends:
            print(f"✅ Trends24'ten {len(trends)} Twitter trendi (temizlenmiş) çekildi.")
        else:
            print("ℹ️ Trends24: Trendler ayrıştırıldı ancak temizlendikten sonra geçerli trend kalmadı veya hiç trend bulunamadı.")
        return trends

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Trends24 trend çekme hatası (RequestException): {e}")
        return []
    except Exception as e: 
        print(f"⚠️ Trends24 işlenirken genel hata: {e}")
        return []


import pandas as pd # Fonksiyon başında import edildiğinden emin olun
import numpy as np # NaN işlemleri için gerekebilir (genellikle pandas ile gelir)
# from pathlib import Path # output_directory için, ana betikte tanımlı olmalı

# output_directory değişkeninin fonksiyon içinde veya globalde erişilebilir olması gerekir.
# Örnek: output_directory = Path(__file__).resolve().parent / "output"

def get_daily_ratings(driver, limit=10):
    """TIAK üzerinden günlük TV reytinglerini çeker, tekrarları temizler ve doğru sıralar."""
    try:
        url = "https://tiak.com.tr/tablolar"
        driver.get(url)

        # Çalışan buton seçiciniz (veya daha stabil bir alternatif)
        gunluk_buton_xpath = "//div[contains(@id, 'gunluk-tablolar')]"
        try:
            gunluk_buton = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, gunluk_buton_xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", gunluk_buton)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", gunluk_buton)
            print("✅ TIAK Günlük Raporlar butonuna başarıyla tıklandı.")
        except Exception as e_button:
            print(f"⚠️ TIAK Günlük Raporlar butonu bulunamadı veya tıklanamadı: {e_button}")
            # ... (hata ayıklama için debug dosyası kaydetme) ...
            # Örnek:
            # debug_ratings_path = output_directory / "debug_tiak_button_error.html"
            # try:
            #     with open(debug_ratings_path, "w", encoding="utf-8") as f_debug: f_debug.write(driver.page_source)
            #     print(f"ℹ️ Hata anındaki TIAK sayfa kaynağı (buton) kaydedildi: {debug_ratings_path}")
            # except: pass
            return []

        table_container_class = "gunluktablo" # Bu class adının doğruluğu önemli
        try:
            WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.CLASS_NAME, table_container_class))
            )
            print(f"✅ TIAK Reyting tablo konteyneri (.{table_container_class}) yüklendi ve görünür.")
        except Exception as e_table_wait:
            print(f"⚠️ TIAK Reyting tablo konteyneri (.{table_container_class}) yüklenemedi veya görünür değil: {e_table_wait}")
            # ... (hata ayıklama için debug dosyası kaydetme) ...
            return []

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        
        table_container_div = soup.find("div", class_=table_container_class)
        if not table_container_div:
            print(f"⚠️ '{table_container_class}' class'ına sahip ana konteyner bulunamadı!")
            return []
        
        table = table_container_div.find("table")
        if not table:
            print(f"⚠️ Reyting tablosu ('{table_container_class}' konteyneri içinde) bulunamadı!")
            return []

        print("✅ Reyting tablosu bulundu!")
        rows = []
        for tr_idx, tr in enumerate(table.find_all("tr")):
            if tr_idx == 0:
                continue
            
            cols_td = tr.find_all("td")
            if len(cols_td) >= 7:
                row_data = [col.text.strip() for col in cols_td[:7]]
                rows.append(row_data)
            elif cols_td:
                print(f"ℹ️ TIAK Reyting satırında ({tr_idx}) 7'den az sütun ({len(cols_td)}) bulundu, bu satır atlanıyor.")

        if not rows:
            print("⚠️ TIAK Reyting verisi (satır) bulunamadı veya ayrıştırılamadı.")
            return []

        df_columns = ["Sıra", "Program", "Kanal", "Başlangıç Saati", "Bitiş Saati", "Rating %", "Share"]
        df = pd.DataFrame(rows, columns=df_columns)

        if df.empty:
            print("⚠️ DataFrame oluşturuldu ancak boş.")
            return []

        print("ℹ️ DataFrame oluşturuldu, tekrarlar ve sıralama düzenleniyor...")
        df['Rating_Numeric'] = pd.to_numeric(df['Rating %'].astype(str).str.replace(',', '.'), errors='coerce')
        
        df_sorted_by_rating = df.sort_values(['Program', 'Kanal', 'Rating_Numeric'], 
                                           ascending=[True, True, False], 
                                           na_position='last')
        
        df_cleaned_duplicates = df_sorted_by_rating.drop_duplicates(subset=['Program', 'Kanal'], keep='first')
        
        # "Sıra" sütununu sayısal yapıp ona göre sırala
        # .loc kullanarak SettingWithCopyWarning'den kaçının
        df_temp_for_final_sort = df_cleaned_duplicates.copy()
        df_temp_for_final_sort.loc[:, 'Sıra_Numeric'] = pd.to_numeric(df_temp_for_final_sort['Sıra'], errors='coerce')
        
        df_final_sorted = df_temp_for_final_sort.sort_values('Sıra_Numeric', na_position='last').drop(columns=['Rating_Numeric', 'Sıra_Numeric'])
        df_final_sorted = df_final_sorted.reset_index(drop=True)
        
        print(f"✅ Tekrarlar temizlendi ve Sıra'ya göre numerik sıralandı. Kalan satır sayısı: {len(df_final_sorted)}")

        try:
            # global output_directory # Eğer output_directory global ise veya Path ile tekrar tanımlayın
            # ratings_csv_path ve ratings_excel_path global değişkenlerini kullanın
            df_final_sorted.to_csv(ratings_csv_path, index=False, encoding="utf-8-sig")
            df_final_sorted.to_excel(ratings_excel_path, index=False)
            print(f"✅ Temizlenmiş ve sıralanmış günlük reyting verileri başarıyla kaydedildi.")
        except Exception as e_save:
            print(f"⚠️ Temizlenmiş ve sıralanmış reyting dosyaları kaydedilirken hata: {e_save}")
        
        if not df_final_sorted.empty:
            required_html_cols = ["Sıra", "Program", "Kanal", "Rating %"]
            # df_final_sorted DataFrame'inde bu sütunların olduğundan emin olalım.
            # 'Sıra' sütunu orijinal string haliyle kalmalı, sayısal sıralama için geçici sütun kullanıldı.
            final_df_for_html = df_final_sorted[required_html_cols]
            return final_df_for_html.head(limit).values.tolist()
        else:
            print("⚠️ Temizleme ve sıralama sonrası DataFrame boş kaldı.")
            return []

    except Exception as e: 
        print(f"⚠️ TIAK Reytingleri alınırken genel hata: {e}")
        # ... (hata ayıklama için debug dosyası kaydetme) ...
        # Örnek:
        # debug_ratings_path = output_directory / "debug_tiak_general_error.html"
        # try:
        #     with open(debug_ratings_path, "w", encoding="utf-8") as f_debug: f_debug.write(driver.page_source)
        #     print(f"ℹ️ Hata anındaki TIAK sayfa kaynağı (genel hata) kaydedildi: {debug_ratings_path}")
        # except: pass
        return []


def fetch_movies(limit=10):
    """TMDB API'den vizyondaki filmleri çeker ve liste olarak döndürür."""
    if not TMDB_API_KEY:
        print("⚠️ TMDB API anahtarı bulunamadı (.env dosyasını kontrol edin). Filmler alınamayacak.")
        return []
    try:
        response = requests.get(TMDB_API_URL, timeout=10)
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
    """USD bazlı temel döviz kurlarını (TRY, EUR, GBP) çeker."""
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "rates" not in data or "TRY" not in data["rates"]:
            print("⚠️ Döviz kuru verisi alınamadı veya TRY kuru eksik.")
            return {}
            
        usd_to_try = data["rates"]["TRY"]
        eur_to_usd = data["rates"].get("EUR", 0) 
        gbp_to_usd = data["rates"].get("GBP", 0)

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


def get_hourly_weather(city, api_key, units="metric", lang="tr", limit=8):
    """OpenWeatherMap API'den saatlik hava durumu tahminlerini çeker."""
    if not api_key:
        print("⚠️ OpenWeatherMap API anahtarı bulunamadı. Hava durumu alınamayacak.")
        return []
        
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units={units}&lang={lang}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "list" not in data:
            print(f"⚠️ Hava durumu verisi alınamadı (API yanıtı eksik): {data.get('message', 'Detay yok')}")
            return []

        hourly_forecast = []
        for forecast in data["list"][:limit]: 
            try:
                time_str = datetime.fromtimestamp(forecast["dt"]).strftime("%H:%M")
                temp = forecast["main"]["temp"]
                description = forecast["weather"][0]["description"].capitalize()
                icon_code = forecast["weather"][0].get("icon", None)
                
                icon_data_uri = "https://via.placeholder.com/50" 
                if icon_code:
                    icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
                    headers = {
                        "Referer": "https://openweathermap.org/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    try:
                        icon_response = requests.get(icon_url, headers=headers, timeout=5)
                        if icon_response.status_code == 200:
                            encoded_icon = base64.b64encode(icon_response.content).decode('utf-8')
                            content_type = icon_response.headers.get("Content-Type", "image/png")
                            icon_data_uri = f"data:{content_type};base64,{encoded_icon}"
                    except requests.exceptions.RequestException:
                        print(f"⚠️ Hava durumu ikonu ({icon_url}) çekilemedi.")
                
                weather_class = "default-weather"
                desc_lower = description.lower()
                if any(s in desc_lower for s in ["açık", "güneşli", "clear"]): weather_class = "sunny"
                elif any(s in desc_lower for s in ["yağmur", "sağanak", "rain", "shower"]): weather_class = "rainy"
                elif any(s in desc_lower for s in ["kar", "snow"]): weather_class = "snowy"
                elif any(s in desc_lower for s in ["bulut", "kapalı", "cloud"]): weather_class = "cloudy"
                
                hourly_forecast.append((time_str, temp, description, icon_data_uri, weather_class))
            except (KeyError, IndexError) as e_item:
                print(f"⚠️ Hava durumu tahmini öğesi ayrıştırılamadı: {e_item} - {forecast}")
                continue 

        print(f"✅ {city} için {len(hourly_forecast)} saatlik hava durumu tahmini çekildi.")
        return hourly_forecast
    except requests.exceptions.RequestException as e:
        print(f"⚠️ OpenWeatherMap API Hatası: {e}")
        return []
    except (KeyError, TypeError):
        print("⚠️ OpenWeatherMap API yanıt formatı beklenmedik.")
        return []


def fetch_rss_feed(url, timeout=15):
    """Verilen URL'den RSS akışını çeker ve haber öğelerini döndürür."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; HaberBotu/1.0; +http://example.com/bot)"} 
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e_parse:
            print(f"⚠️ XML Ayrıştırma Hatası ({url}): {e_parse}. İçerik:\n{response.text[:500]}...")
            return []

        news_items = []
        for item in root.findall(".//item"): 
            title = item.findtext("title", default="Başlık Yok").strip()
            link = item.findtext("link", default="#").strip()
            pub_date_raw = item.findtext("pubDate")
            
            pub_date_parsed = datetime.now() 
            if pub_date_raw:
                try:
                    pub_date_parsed = email.utils.parsedate_to_datetime(pub_date_raw)
                except (TypeError, ValueError):
                    try: 
                        pub_date_parsed = datetime.fromisoformat(pub_date_raw.replace("Z", "+00:00"))
                    except ValueError:
                        print(f"⚠️ Tarih formatı anlaşılamadı ({url}): {pub_date_raw}")
            
            news_items.append((title, link, pub_date_parsed))
        return news_items
    except requests.exceptions.RequestException as e:
        print(f"⚠️ RSS Çekme Hatası ({url}): {e}")
        return []
    except Exception as e_general: 
        print(f"⚠️ RSS İşleme Genel Hata ({url}): {e_general}")
        return []


def generate_html():
    """Tüm verileri toplayıp HTML dosyasını oluşturur."""
    try:
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome WebDriver başarıyla başlatıldı (webdriver_manager ile).")

    except Exception as e_driver:
        print(f"❌ Chrome WebDriver başlatılamadı: {e_driver}")
        print("ℹ️ ChromeDriver'ın doğru şekilde kurulduğundan ve PATH'de olduğundan emin olun,")
        print("ℹ️ veya webdriver_manager'ın internet erişimi olduğundan emin olun.")
        return 

    try:
        weather_results = get_hourly_weather(CITY, OPENWEATHER_API_KEY, UNITS, LANG)
        exchange_rates = get_exchange_rates()
        ratings = get_daily_ratings(driver)
        movies = fetch_movies()
        twitter_trends = get_trending_topics_trends24()
        spotify_tracks = get_new_turkish_rap_tracks_embed()

        leagues_config = [
            ("ingiltere/premier-league", "Premier League"),
            ("ispanya/laliga", "La Liga"),
            ("turkiye/super-lig", "Süper Lig"), 
            ("avrupa/sampiyonlar-ligi", "Şampiyonlar Ligi")
        ]
        fixtures_all = {}
        for path_segment, name in leagues_config:
            league_name_key, fixture_values = get_flashscore_fixtures(driver, path_segment, name)
            fixtures_all[league_name_key] = fixture_values
        
        news_results = {category: [] for category in RSS_FEEDS}
        with ThreadPoolExecutor(max_workers=10) as executor: 
            future_to_category_url = {}
            for category, urls in RSS_FEEDS.items():
                for url in urls:
                    future = executor.submit(fetch_rss_feed, url)
                    future_to_category_url[future] = (category, url)
            
            rss_fetch_count = 0
            for future in future_to_category_url:
                category, url_processed = future_to_category_url[future]
                try:
                    result = future.result() 
                    news_results[category].extend(result)
                    if result: 
                        rss_fetch_count += len(result)
                except Exception as e_rss_future:
                    print(f"⚠️ RSS ({url_processed}) işlenirken hata (ThreadPool): {e_rss_future}")
            print(f"✅ Toplam {rss_fetch_count} RSS haberi çekildi.")

    except Exception as e_data_fetch:
        print(f"❌ Veri çekme sırasında genel bir hata oluştu: {e_data_fetch}")
    finally:
        if 'driver' in locals() and driver:
            try:
                driver.quit()
                print("✅ Chrome WebDriver kapatıldı.")
            except Exception as e_quit:
                print(f"⚠️ Chrome WebDriver kapatılırken hata: {e_quit}")

    last_update = datetime.now().strftime("%d %B %Y, %H:%M:%S") 
    html_content = []
    
    html_content.append(f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <!-- PWA için manifest ve tema rengi (manifest.json dosyası gereklidir)
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#007bff">
    -->
    <title>Güncel Haberler, Hava Durumu ve Daha Fazlası</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
    :root {{
        --bg-color: #f4f6f8; --card-color: #ffffff; --text-color: #333;
        --primary-color: #0056b3; --primary-hover: #003c82; --accent-color: #4dabf7;
        --dark-bg: #1a1a1a; --dark-card: #2c2c2c; --dark-text: #eee;
        --border-color: #ddd; --dark-border-color: #444;
    }}
    html, body {{ margin: 0; padding: 0; overflow-x: hidden; font-family: 'Poppins', sans-serif; background-color: var(--bg-color); color: var(--text-color); text-align: center; width: 100%; transition: background-color 0.3s ease, color 0.3s ease; }}
    .page-wrapper {{ max-width: 1320px; margin: 0 auto; padding: 0 15px; box-sizing: border-box; padding-top: 70px; }}
    .container {{ display: flex; flex-wrap: wrap; justify-content: center; align-items: flex-start; gap: 20px; padding: 10px 0; width: 100%; box-sizing: border-box; }}
    .card {{ background: var(--card-color); width: 100%; max-width: 350px; box-sizing: border-box; padding: 15px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: left; transition: transform 0.2s ease, box-shadow 0.2s ease; border: 1px solid var(--border-color); }}
    .card:hover {{ transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.12); }}
    .card a {{ font-weight: 600; font-size: 1.05em; color: var(--primary-color); text-decoration: none; margin-bottom: 8px; display: block; }}
    .card a:hover {{ color: var(--primary-hover); }}
    .card p.date {{ font-size: 0.85em; color: #777; margin-top: 5px; }}
    .section-title {{ font-size: 1.8em; font-weight: 600; margin: 30px 0 15px; color: var(--text-color); scroll-margin-top: 80px; text-align: center; }}
    .sticky-nav {{ position: fixed; top: 0; left: 0; right: 0; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); padding: 12px 0; text-align: center; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; justify-content: center; flex-wrap: wrap; gap: 5px 15px; }}
    .sticky-nav a {{ white-space: nowrap; color: var(--primary-color); font-weight: 500; text-decoration: none; font-size: 0.95em; padding: 5px 10px; border-radius: 6px; transition: color 0.2s ease, background-color 0.2s ease; }}
    .sticky-nav a:hover {{ color: var(--primary-hover); background-color: rgba(0, 86, 179, 0.1);}}
    .toggle-button {{ position: fixed; top: 80px; right: 20px; background: var(--card-color); color: var(--text-color); padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 20px; cursor: pointer; font-size: 1.2em; z-index: 1001; transition: background-color 0.3s ease, color 0.3s ease, transform 0.2s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
    .toggle-button:hover {{ transform: scale(1.1); }}
    body.dark-mode {{ background-color: var(--dark-bg); color: var(--dark-text); }}
    body.dark-mode .card, body.dark-mode .weather-card, body.dark-mode .film-card, body.dark-mode .ratings-container {{ background: var(--dark-card); color: var(--dark-text); border-color: var(--dark-border-color); }}
    body.dark-mode .card a {{ color: var(--accent-color); }}
    body.dark-mode .card a:hover {{ color: #fff; }}
    body.dark-mode .card p.date {{ color: #aaa; }}
    body.dark-mode .sticky-nav {{ background: rgba(44, 44, 44, 0.9); box-shadow: 0 2px 8px rgba(0,0,0,0.3);}}
    body.dark-mode .sticky-nav a {{ color: var(--accent-color); }}
    body.dark-mode .sticky-nav a:hover {{ color: var(--dark-text); background-color: rgba(77, 171, 247, 0.2); }}
    body.dark-mode .section-title {{ color: var(--accent-color); }}
    body.dark-mode .toggle-button {{ background: var(--dark-card); color: var(--dark-text); border-color: var(--dark-border-color);}}
    body.dark-mode .exchange-card {{ background: linear-gradient(135deg, #2a3a5e, #1e2c4a); color: #ffc107; border-color: #405075; }}
    body.dark-mode table th {{ background-color: #3a3a3a; color: var(--accent-color); }}
    body.dark-mode table td {{ color: var(--dark-text); border-color: var(--dark-border-color); }}
    .weather-container {{ display: flex; flex-wrap: nowrap; overflow-x: auto; gap: 15px; padding: 15px 5px; width: 100%; box-sizing: border-box; -webkit-overflow-scrolling: touch; }}
    .weather-card {{ flex: 0 0 auto; width: 130px; padding: 15px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; color: #fff; transition: transform 0.2s ease; border: none; }}
    .weather-card:hover {{ transform: scale(1.03); }}
    .weather-card img {{ width: 50px; height: 50px; margin-bottom: 8px; }}
    .weather-card p {{ margin: 3px 0; font-size: 0.9em; }}
    .weather-card .temp {{ font-size: 1.3em; font-weight: 600; }}
    .weather-card.sunny   {{ background: linear-gradient(135deg,#ffda77,#ffb347); color:#543200;}}
    .weather-card.rainy   {{ background: linear-gradient(135deg,#6ca0dc,#4a7db5); }}
    .weather-card.snowy   {{ background: linear-gradient(135deg,#c4e0f9,#a3c2e0); color:#2e455c;}}
    .weather-card.cloudy  {{ background: linear-gradient(135deg,#a8b2c5,#8995ad); color:#2c333e;}}
    .weather-card.default-weather {{ background: linear-gradient(135deg,#868f96,#596164); }}
    .exchange-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; padding: 10px 0; }}
    .exchange-card {{ background: linear-gradient(135deg, #e9f0f8, #d9e2ec); color: #2c3e50; padding: 12px 18px; border-radius: 8px; box-shadow: 0 3px 8px rgba(0,0,0,0.07); font-size: 1em; font-weight: 500; transition: transform 0.2s ease; border: 1px solid #c8d territorio; }}
    .exchange-card:hover {{ transform: scale(1.03); }}
    .exchange-card strong {{ color: var(--primary-color); }}
    body.dark-mode .exchange-card strong {{ color: var(--accent-color); }}
    .film-container {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; padding: 10px 0; }}
    .film-card {{ background: var(--card-color); width: 220px; padding: 0; border-radius: 10px; text-decoration: none !important; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center; transition: transform 0.2s ease, box-shadow 0.2s ease; overflow: hidden; border: 1px solid var(--border-color);}}
    .film-card:hover {{ text-decoration: none !important; transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.12); }}
    .film-card img {{ width: 100%; height: 330px; object-fit: cover; display: block; }}
    .film-card-content {{ padding: 12px; }}
    .film-card h3 {{ margin: 0 0 8px; text-decoration: none !important; font-size: 1.1em; font-weight: 600; color: var(--text-color); }}
    .film-card p {{ font-size: 0.85em; text-decoration: none !important; color: #666; margin:0; max-height: 5.1em; overflow:hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;}}
    body.dark-mode .film-card h3 {{ text-decoration: none !important; color: var(--dark-text); }}
    body.dark-mode .film-card p {{ text-decoration: none !important; color: #bbb; }}
    .ratings-container {{ margin-top: 10px; padding: 15px; border: 1px solid var(--border-color); border-radius: 8px; background-color: var(--card-color); text-align: center; overflow-x: auto; max-width: 100%; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }}
    th, td {{ border: 1px solid var(--border-color); padding: 10px 12px; text-align: left; }}
    th {{ background-color: #e9ecef; font-weight: 600; color: var(--text-color);}}
    .spotify-container {{ max-height: 450px; overflow-y: auto; overflow-x: hidden; max-width: 100%; box-sizing: border-box; padding: 15px; border: 1px solid var(--border-color); border-radius: 8px; margin-top:10px; }}
    .spotify-item {{ margin-bottom: 15px; }}
    .spotify-item p {{ margin: 0 0 5px; font-weight: 500; }}
    .spotify-item iframe {{ border-radius:10px; width:100%; }}
    #map_canvas {{ width: 100%; height: 400px; border-radius: 8px; margin-bottom:15px; border: 1px solid var(--border-color); }}
    .route-controls {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:15px; align-items:center;}}
    .route-controls input[type='text'] {{ padding:10px; border:1px solid var(--border-color); border-radius:6px; flex-grow:1; min-width:150px;}}
    .route-controls button {{ padding:10px 15px; background-color:var(--primary-color); color:white; border:none; border-radius:6px; cursor:pointer; transition: background-color 0.2s ease;}}
    .route-controls button:hover {{ background-color:var(--primary-hover);}}
    body.dark-mode .route-controls input[type='text'] {{ background-color: var(--dark-card); border-color: var(--dark-border-color); color: var(--dark-text); }}
    body.dark-mode .route-controls button {{ background-color: var(--accent-color); color: var(--dark-bg); }}
    body.dark-mode .route-controls button:hover {{ background-color: #3fa1e6; }}
    #route-info {{ margin-top:10px; font-weight:500; color: var(--primary-color);}}
    body.dark-mode #route-info {{ color: var(--accent-color);}}
    @media (max-width: 768px) {{
        .page-wrapper {{ padding-top: 100px; }}
        .sticky-nav {{ padding: 8px 0; gap: 5px 8px; }}
        .sticky-nav a {{ font-size: 0.85em; padding: 4px 8px; }}
        .section-title {{ font-size: 1.5em; }}
        .card {{ max-width: 100%; }}
        .film-card {{ width: calc(50% - 10px); }}
        .weather-card {{ width: 120px; }}
        .toggle-button {{ top:28px; right:8px; font-size:1em; padding: 6px 10px;}}
    }}
    @media (max-width: 480px) {{
      .film-card {{ width: 100%; }}
    }}
    </style>
</head>
<body class=""> <nav class="sticky-nav">
        <a href="#hava">🌤️ Hava</a>
        <a href="#trafik">🚦 Trafik</a>
        <a href="#doviz">💱 Döviz</a>
        <a href="#fikstur">⚽ Fikstür</a>
        <a href="#reyting">📺 Reyting</a>
        <a href="#twitter">🔥 Gündem</a>
        <a href="#muzik">🎧 Müzik</a>
        <a href="#filmler">🎬 Filmler</a>
        <a href="#haberler">📰 Haberler</a>
    </nav>
    <button class="toggle-button" aria-label="Gece Modu Değiştir">🌙</button>
    <div class="page-wrapper">
        <p style="text-align:center; font-size:0.9em; color:#777; margin-bottom:20px;">Son Güncelleme: {last_update}</p>
""")

    # Hava Durumu
    html_content.append('<h2 id="hava" class="section-title">📍 İstanbul Saatlik Hava Durumu</h2><div class="weather-container">')
    if weather_results:
        for time_val, temp, description, icon_uri, weather_class in weather_results:
            html_content.append(f"""
            <div class="weather-card {weather_class}">
                <p><strong>{time_val}</strong></p>
                <img src="{icon_uri}" alt="{description}">
                <p>{description}</p>
                <p class="temp"><strong>{temp:.1f}°C</strong></p> </div>""")
    else:
        html_content.append('<p>⚠️ Hava durumu verisi alınamadı.</p>')
    html_content.append('</div>')

    # Trafik ve Navigasyon (Google Maps)
    if GOOGLE_MAPS_API_KEY:
        html_content.append(f"""
        <h2 id="trafik" class="section-title">🚦 İstanbul Trafik Durumu & Yol Tarifi</h2>
        <div id="map_canvas"></div> <div class="route-controls">
            <input id="start_location" type="text" placeholder="Başlangıç (örn: Kadıköy)">
            <button onclick="useCurrentLocation()" aria-label="Mevcut Konumumu Kullan">📍 Konumum</button>
            <input id="end_location" type="text" placeholder="Varış (örn: Beşiktaş)">
            <button onclick="calculateAndDisplayRoute()" aria-label="Yol Tarifi Göster">🧭 Tarifi Göster</button>
        </div>
        <div id="route-info"></div>
        <script>
            let map;
            let directionsService;
            let directionsRenderer;

            function initMap() {{
                const istanbul = {{ lat: 41.0082, lng: 28.9784 }};
                map = new google.maps.Map(document.getElementById("map_canvas"), {{ // ID güncellendi
                    zoom: 11, center: istanbul, mapTypeControl: false, streetViewControl: false
                }});
                new google.maps.TrafficLayer().setMap(map);
                directionsService = new google.maps.DirectionsService();
                directionsRenderer = new google.maps.DirectionsRenderer({{ map: map, suppressMarkers: false }});
                
                if (document.body.classList.contains('dark-mode')) {{
                    setDarkMapStyle();
                }}
            }}

            function useCurrentLocation() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(pos => {{
                        document.getElementById("start_location").value = `${{pos.coords.latitude}},${{pos.coords.longitude}}`;
                    }}, err => alert("Konum alınamadı: " + err.message));
                }} else {{ alert("Tarayıcınız konum servisini desteklemiyor."); }}
            }}

            function calculateAndDisplayRoute() {{
                const start = document.getElementById("start_location").value.trim();
                const end = document.getElementById("end_location").value.trim();
                if (!start || !end) {{ alert("Başlangıç ve varış noktalarını girin."); return; }}

                directionsService.route({{
                    origin: start, destination: end, travelMode: google.maps.TravelMode.DRIVING,
                    drivingOptions: {{ departureTime: new Date(), trafficModel: 'bestguess' }}
                }}, (response, status) => {{
                    if (status === "OK") {{
                        directionsRenderer.setDirections(response);
                        const leg = response.routes[0].legs[0];
                        let info = `Mesafe: ${{leg.distance.text}}, Süre: ${{leg.duration.text}}`;
                        if (leg.duration_in_traffic) {{ info += ` (Trafikle: ${{leg.duration_in_traffic.text}})`; }}
                        document.getElementById("route-info").innerHTML = info;
                    }} else {{ alert("Yol tarifi alınamadı: " + status); }}
                }});
            }}
            
            function setDarkMapStyle() {{
                if (map) {{ 
                    const darkStyle = [
                        {{ elementType: "geometry", stylers: [{{ color: "#242f3e" }}] }},
                        {{ elementType: "labels.text.stroke", stylers: [{{ color: "#242f3e" }}] }},
                        {{ elementType: "labels.text.fill", stylers: [{{ color: "#746855" }}] }},
                        {{ featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{{ color: "#d59563" }}] }},
                        {{ featureType: "poi", elementType: "labels.text.fill", stylers: [{{ color: "#d59563" }}] }},
                        {{ featureType: "poi.park", elementType: "geometry", stylers: [{{ color: "#263c3f" }}] }},
                        {{ featureType: "poi.park", elementType: "labels.text.fill", stylers: [{{ color: "#6b9a76" }}] }},
                        {{ featureType: "road", elementType: "geometry", stylers: [{{ color: "#38414e" }}] }},
                        {{ featureType: "road", elementType: "geometry.stroke", stylers: [{{ color: "#212a37" }}] }},
                        {{ featureType: "road", elementType: "labels.text.fill", stylers: [{{ color: "#9ca5b3" }}] }},
                        {{ featureType: "road.highway", elementType: "geometry", stylers: [{{ color: "#746855" }}] }},
                        {{ featureType: "road.highway", elementType: "geometry.stroke", stylers: [{{ color: "#1f2835" }}] }},
                        {{ featureType: "road.highway", elementType: "labels.text.fill", stylers: [{{ color: "#f3d19c" }}] }},
                        {{ featureType: "transit", elementType: "geometry", stylers: [{{ color: "#2f3948" }}] }},
                        {{ featureType: "transit.station", elementType: "labels.text.fill", stylers: [{{ color: "#d59563" }}] }},
                        {{ featureType: "water", elementType: "geometry", stylers: [{{ color: "#17263c" }}] }},
                        {{ featureType: "water", elementType: "labels.text.fill", stylers: [{{ color: "#515c6d" }}] }},
                        {{ featureType: "water", elementType: "labels.text.stroke", stylers: [{{ color: "#17263c" }}] }}
                    ];
                    map.setOptions({{ styles: darkStyle }});
                }}
            }}

            function setDefaultMapStyle() {{
                if (map) {{
                    map.setOptions({{ styles: null }});
                }}
            }}
        </script>
        <script async defer src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap&libraries=places&language=tr&region=TR"></script>
        """)
    else:
        html_content.append('<p>⚠️ Google Maps API anahtarı bulunamadığından trafik ve yol tarifi gösterilemiyor.</p>')

    # Döviz Kurları
    html_content.append('<h2 id="doviz" class="section-title">💱 Döviz Kurları</h2><div class="exchange-container">')
    if exchange_rates:
        for currency, rate in exchange_rates.items():
            html_content.append(f'<div class="exchange-card"><strong>{currency}:</strong> {rate} TRY</div>')
    else:
        html_content.append('<p>⚠️ Döviz kuru verisi alınamadı.</p>')
    html_content.append('</div>')

    # Futbol Fikstürü
    html_content.append('<h2 id="fikstur" class="section-title">⚽ Haftalık Fikstür</h2><div class="container">')
    if fixtures_all:
        for league, matches in fixtures_all.items():
            html_content.append(f"<div class='card'><h3>{league}</h3>")
            if matches:
                for match in matches:
                    html_content.append(f"<p>{match}</p>")
            else:
                html_content.append("<p>Bu lig için fikstür verisi bulunamadı.</p>")
            html_content.append("</div>")
    else:
        html_content.append('<p>⚠️ Fikstür verisi alınamadı.</p>')
    html_content.append('</div>')
    
    # Günlük Reytingler
    html_content.append('<h2 id="reyting" class="section-title">📺 Günlük Reytingler</h2>')
    if ratings: 
        html_content.append('<div class="ratings-container"><table><thead><tr><th>Sıra</th><th>Program</th><th>Kanal</th><th>Rating %</th></tr></thead><tbody>')
        for row in ratings[:10]: 
            if len(row) == 4: 
                 html_content.append(f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>")
        html_content.append('</tbody></table></div>')
    else:
        html_content.append('<p>⚠️ Günlük reyting verisi alınamadı.</p>')

    # Twitter Trendleri
    html_content.append('<h2 id="twitter" class="section-title">🔥 Türkiye Gündemi (Twitter)</h2><div class="container">')
    if twitter_trends:
        for trend in twitter_trends:
            query = trend.lstrip("#").replace(" ", "+")
            twitter_url = f"https://twitter.com/search?q=%23{query}&src=typed_query" 
            html_content.append(f"""
            <div class="card">
                <a href="{twitter_url}" target="_blank" rel="noopener noreferrer">{trend}</a>
            </div>""")
    else:
        html_content.append('<p>⚠️ Twitter gündem verisi alınamadı.</p>')
    html_content.append('</div>')

    # Spotify Müzik
    html_content.append('<h2 id="muzik" class="section-title">🎧 Yeni Çıkan Müzikler (Spotify)</h2><div class="card"><div class="spotify-container">')
    if spotify_tracks:
        for artist, title, embed_url in spotify_tracks: 
            html_content.append(f"""
            <div class="spotify-item">
                <p><strong>{artist}</strong> - {title}</p>
                <iframe title="{artist} - {title}" style="border-radius:12px"
                    src="{embed_url}"
                    width="100%" height="80" frameborder="0" allowfullscreen=""
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    loading="lazy">
                </iframe>
            </div>""")
    else:
        html_content.append('<p>⚠️ Spotify parça listesi alınamadı.</p>')
    html_content.append('</div></div>')

    # Vizyondaki Filmler
    html_content.append('<h2 id="filmler" class="section-title">🎬 Vizyondaki Filmler</h2><div class="film-container">')
    if movies:
        for film in movies:
            title = film.get("title", "Bilinmeyen Film")
            overview = film.get("overview", "Açıklama mevcut değil.")
            poster_path = film.get("poster_path")
            film_search_url = f"https://www.google.com/search?q={requests.utils.quote(title)}+film"

            poster_data_uri = "https://via.placeholder.com/220x330.png?text=Afiş+Yok" 
            if poster_path:
                tmdb_poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
                try:
                    img_response = requests.get(tmdb_poster_url, timeout=5, headers={"Referer": "https://www.themoviedb.org/"})
                    if img_response.status_code == 200:
                        encoded_img = base64.b64encode(img_response.content).decode('utf-8')
                        content_type = img_response.headers.get("Content-Type", "image/jpeg")
                        poster_data_uri = f"data:{content_type};base64,{encoded_img}"
                except requests.exceptions.RequestException:
                    print(f"⚠️ Film afişi ({tmdb_poster_url}) çekilemedi.")
            
            html_content.append(f"""
            <a href="{film_search_url}" target="_blank" rel="noopener noreferrer" class="film-card">
                <img src="{poster_data_uri}" alt="Afiş: {title}" loading="lazy">
                <div class="film-card-content">
                    <h3>{title}</h3>
                    <p>{overview}</p>
                </div>
            </a>""")
    else:
        html_content.append('<p>⚠️ Vizyondaki filmler verisi alınamadı.</p>')
    html_content.append('</div>')

    # RSS Haberleri
    html_content.append('<h2 id="haberler" class="section-title">📰 Haberler</h2>')
    for category, news_list in news_results.items():
        html_content.append(f'<h3>{category}</h3><div class="container">')
        if news_list:
            sorted_news = sorted(news_list, key=lambda x: x[2], reverse=True)[:10] 
            for title, link, pub_date in sorted_news:
                html_content.append(f"""
                <div class="card">
                    <a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>
                    <p class="date">{pub_date.strftime("%d %B %Y, %H:%M")}</p>
                </div>""")
        else:
            html_content.append(f'<p>Bu kategoride ({category}) haber bulunamadı.</p>')
        html_content.append('</div>')

    # HTML Sonu ve JavaScript
    html_content.append(f"""
    </div> <script>
        document.addEventListener("DOMContentLoaded", function () {{
            const toggleButton = document.querySelector(".toggle-button");
            const body = document.body;

            if (localStorage.getItem("darkMode") === "enabled") {{
                body.classList.add("dark-mode");
                toggleButton.textContent = "☀️";
                if (typeof setDarkMapStyle === 'function') setDarkMapStyle(); 
            }} else {{
                toggleButton.textContent = "�";
                if (typeof setDefaultMapStyle === 'function') setDefaultMapStyle();
            }}

            let busy = false; 
            function toggleDarkMode(event) {{
                event.preventDefault(); 
                if (busy) return;
                busy = true;

                body.classList.toggle("dark-mode");
                if (body.classList.contains("dark-mode")) {{
                    localStorage.setItem("darkMode", "enabled");
                    toggleButton.textContent = "☀️";
                    if (typeof setDarkMapStyle === 'function') setDarkMapStyle();
                }} else {{
                    localStorage.setItem("darkMode", "disabled");
                    toggleButton.textContent = "🌙";
                    if (typeof setDefaultMapStyle === 'function') setDefaultMapStyle();
                }}
                setTimeout(() => {{ busy = false; }}, 200); 
            }}
            toggleButton.addEventListener("click", toggleDarkMode);
            toggleButton.addEventListener("touchstart", toggleDarkMode, {{ passive: false }});
        }});
    </script>
</body>
</html>
""")
    
    # HTML dosyasını yaz
    try:
        with open(html_file_path, "w", encoding="utf-8") as file:
            file.write("".join(html_content))
        print(f"✅ HTML dosyası başarıyla oluşturuldu: {html_file_path}")
    except IOError as e_io:
        print(f"❌ HTML dosyası yazılamadı: {e_io}")
    except Exception as e_html_write:
        print(f"❌ HTML dosyası yazılırken beklenmedik bir hata oluştu: {e_html_write}")


if __name__ == "__main__":
    if not OPENWEATHER_API_KEY or not TMDB_API_KEY or not GOOGLE_MAPS_API_KEY or \
       not os.getenv("SPOTIFY_CLIENT_ID") or not os.getenv("SPOTIFY_CLIENT_SECRET") or \
       not os.getenv("SPOTIFY_REFRESH_TOKEN"):
        print("❌ Gerekli API anahtarlarından bazıları .env dosyasında eksik veya yüklenemedi.")
        print("ℹ️ Lütfen .env dosyasını kontrol edin: OPENWEATHER_API_KEY, TMDB_API_KEY, GOOGLE_MAPS_API_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN")
    else:
        generate_html()

    # E-posta gönderme kısmı yorum satırı olarak bırakıldı
    # def send_email_with_attachment(file_path_to_send):
    #     # ... (e-posta gönderme kodunuz)
    # pass
    # if html_file_path.exists():
    #    send_email_with_attachment(html_file_path)
