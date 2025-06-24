# data_fetchers/web_scrapers.py
"""
Selenium ve BeautifulSoup kullanarak web sitelerinden veri kazıyan (scraping)
fonksiyonları içerir.
"""
import time
import re
import traceback
from pathlib import Path
#import pandas as pd
import requests # get_trending_topics_trends24 için gerekli
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from datetime import datetime, timezone, timedelta



from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


# Ana dizindeki config dosyasını import ediyoruz
import config

def fetch_books(driver, limit=10):
    """İstanbul Kitapçısı'nın "Çok Satanlar" listesinden kitapları çeker."""
    url = config.ISTANBUL_KITAPCISI_URL
    books = []
    print(f"ℹ️ İstanbul Kitapçısı verileri çekiliyor: {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, config.KITAP_WAIT_SELECTOR))
        )
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        book_elements = soup.select(config.KITAP_WAIT_SELECTOR)

        if not book_elements:
            print("⚠️ Kitap elementleri bulunamadı.")
            return []

        for book_el in book_elements[:limit]:
            title_el = book_el.select_one(config.KITAP_TITLE_SELECTOR)
            author_el = book_el.select_one(config.KITAP_AUTHOR_SELECTOR)
            image_el = book_el.select_one(config.KITAP_IMAGE_SELECTOR)

            if title_el and image_el:
                book_link = title_el.get('href')
                if not book_link.startswith("http"):
                    book_link = "https://www.istanbulkitapcisi.com" + book_link

                books.append({
                    "title": title_el.get_text(strip=True),
                    "author": author_el.get_text(strip=True) if author_el else "Yazar Belirtilmemiş",
                    "image_url": image_el.get('data-src') or image_el.get('src'),
                    "link": book_link
                })
        print(f"✅ {len(books)} adet kitap bilgisi (İstanbul Kitapçısı) başarıyla çekildi.")
        return books
    except Exception as e:
        print(f"⚠️ İstanbul Kitapçısı'ndan veri çekilirken bir hata oluştu: {e}")
        return []

def _parse_zorlu_date_from_text(date_text):
    """Yardımcı fonksiyon: "04 HAZİRAN" gibi bir metinden gün ve ayı ayıklar."""
    if not date_text:
        return None, None
    match = re.match(r"(\d{2})\s*([A-ZĞÜŞİÖÇ]+)", date_text.strip(), re.IGNORECASE)
    if match:
        day = match.group(1)
        month = match.group(2).capitalize()
        return day, month
    return None, None

def fetch_istanbul_events(driver):
    """Zorlu PSM web sitesinden etkinlikleri çeker."""
    url = config.ZORLU_PSM_URL
    events = []
    print(f"ℹ️ Zorlu PSM etkinlikleri çekiliyor: {url}")
    try:
        driver.get(url)
        # Gerekirse çerez kabul etme ve sayfa kaydırma işlemleri buraya eklenebilir.
        # Örnek: time.sleep() yerine WebDriverWait kullanmak daha sağlıklıdır.
        time.sleep(2) # Sayfanın ilk yüklenmesi için kısa bir bekleme
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(1)

        WebDriverWait(driver, 30).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, config.ZORLU_EVENT_CARD_SELECTOR))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        event_elements = soup.select(config.ZORLU_EVENT_CARD_SELECTOR)

        if not event_elements:
            print(f"❌ KRİTİK HATA: Zorlu PSM sayfasında '{config.ZORLU_EVENT_CARD_SELECTOR}' ile eşleşen etkinlik bulunamadı.")
            return []

        print(f"✅ Zorlu PSM: {len(event_elements)} potansiyel etkinlik bulundu.")
        for event_element in event_elements:
            try:
                title_link_element = event_element.select_one(config.ZORLU_TITLE_LINK_SELECTOR)
                title = title_link_element.get_text(strip=True) if title_link_element else None
                if not title:
                    continue

                link_detail = title_link_element.get('href') if title_link_element else '#'
                final_link = f"https://www.zorlupsm.com{link_detail}" if link_detail and not link_detail.startswith('http') else link_detail

                image_el = event_element.select_one(config.ZORLU_IMAGE_SELECTOR)
                image_url_relative = image_el.get('src') or image_el.get('data-src') if image_el else ''
                image_url = f"https://www.zorlupsm.com{image_url_relative}" if image_url_relative and not image_url_relative.startswith('http') else image_url_relative

                date_el = event_element.select_one(config.ZORLU_DATE_SELECTOR)
                day, month = _parse_zorlu_date_from_text(date_el.text) if date_el else (None, None)
                
                time_el = event_element.select_one(config.ZORLU_TIME_SELECTOR)
                venue_el = event_element.select_one(config.ZORLU_VENUE_SELECTOR)
                category_el = event_element.select_one(config.ZORLU_CATEGORY_SELECTOR)

                events.append({
                    "title": title,
                    "date_str": f"{day} {month}" if day and month else "Belirtilmemiş",
                    "time_str": time_el.text.strip() if time_el else "",
                    "venue": venue_el.text.strip() if venue_el else "Zorlu PSM",
                    "link": final_link,
                    "image_url": image_url,
                    "category": category_el.get_text(strip=True) if category_el else "Genel"
                })
            except Exception as e_item:
                print(f"⚠️ Zorlu PSM'de bir etkinlik detayı işlenirken hata: {e_item}")
        print(f"✅ Toplam {len(events)} etkinlik Zorlu PSM'den başarıyla çekildi.")
        return events
    except Exception as e:
        print(f"❌ Zorlu PSM etkinlikleri çekilirken genel bir HATA OLUŞTU: {e}\n{traceback.format_exc()}")
        return []
    
# data_fetchers/web_scrapers.py dosyasında bu fonksiyonu güncelleyin

def fetch_bilet_events(driver, limit=20): # Limiti artırabilir veya kaldırabilirsiniz
    """
    Bubilet'in İstanbul etkinlikleri sayfasından etkinlikleri çeker.
    Sayfa aşağı kaydırıldıkça yeni etkinlikler yüklendiği için,
    önce sayfanın sonuna kadar kaydırma işlemi yapılır.
    """
    url = "https://www.bubilet.com.tr/istanbul"
    print(f"ℹ️ Bubilet etkinlikleri çekiliyor: {url}")
    events = []
    try:
        driver.get(url)

        try:
            cookie_accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Kabul Et')] | //div[contains(@class, 'cookie-accept')]"))
            )
            print("ℹ️ Bubilet: Çerez onayı pop-up'ı bulundu ve kapatılıyor.")
            cookie_accept_button.click()
            time.sleep(1)
        except Exception:
            print("ℹ️ Bubilet: Çerez onayı pop-up'ı bulunamadı veya zaten kapalı, devam ediliyor.")

        # Sayfanın en altına kadar kaydırma işlemi
        last_height = driver.execute_script("return document.body.scrollHeight")
        print("ℹ️ Bubilet: Tüm etkinlikleri yüklemek için sayfa aşağı kaydırılıyor...")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("✅ Bubilet: Sayfanın sonuna ulaşıldı.")
                break
            last_height = new_height

        print("ℹ️ Bubilet: Etkinliklerin HTML'de var olması bekleniyor...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.event-item"))
        )
        print("✅ Bubilet: Etkinlikler HTML'de bulundu.")
        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        event_cards = soup.find_all('div', class_='event-item')

        if not event_cards:
            print("⚠️ Bubilet: Etkinlik kartları bulunamadı.")
            return []

        # --- DÜZELTİLEN KISIM BAŞLANGICI ---
        for card in event_cards[:limit]:
            link_tag = card.find('a', class_='event-item-box-link')
            image_tag = card.find('img', class_='event-image')
            title_tag = card.find('h3', class_='event-title')
            category_tag = card.find('p', class_='event-category')
            location_tag = card.find('p', class_='event-location')
            date_tag = card.find('p', class_='event-date')

            if all([link_tag, image_tag, title_tag, location_tag, date_tag]):
                events.append({
                    'link': link_tag['href'],
                    'image': image_tag.get('data-src') or image_tag.get('src'),
                    'title': title_tag.get_text(strip=True),
                    'category': category_tag.get_text(strip=True) if category_tag else "Diğer",
                    'location': location_tag.get_text(strip=True),
                    'date': date_tag.get_text(strip=True)
                })
        # --- DÜZELTİLEN KISIM SONU ---
        
        print(f"✅ {len(events)} adet etkinlik (Bubilet) başarıyla çekildi.")
        return events

    except Exception as e:
        print(f"❌ Bubilet etkinlikleri çekilirken HATA oluştu: {e}")
        try:
            project_root = Path(__file__).resolve().parent.parent
            screenshot_path = project_root / "bubilet_debug_screenshot.png"
            page_source_path = project_root / "bubilet_debug_page.html"
            driver.save_screenshot(str(screenshot_path))
            with open(page_source_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"🐞 Hata ayıklama için ekran görüntüsü ve sayfa kaynağı kaydedildi.")
        except Exception as save_error:
            print(f"❌❌ DEBUG DOSYALARI KAYDEDİLİRKEN HATA OLUŞTU: {save_error}")
            traceback.print_exc()
        return []




def get_daily_ratings(driver, limit=10):
    """
    TIAK sitesinden reyting verilerini çeker. Bu versiyon pandas kütüphanesini kullanmaz.
    """
    url = config.TIAK_URL
    print(f"ℹ️ TIAK reytingleri çekiliyor: {url}")
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        print("... 'Günlük Raporlar' başlığı aranıyor ...")
        gunluk_raporlar_basligi = wait.until(
            EC.element_to_be_clickable((By.ID, "gunluk-tablolar"))
        )
        gunluk_raporlar_basligi.click()
        print("✅ 'Günlük Raporlar' başlığı tıklandı.")

        print("... Reyting tablosunun AJAX ile yüklenmesi bekleniyor ...")
        tablo_konteyneri = wait.until(
            EC.visibility_of_element_located((By.ID, "tablo"))
        )
        time.sleep(2)
        print("✅ Reyting tablosu yüklendi.")

        page_source = tablo_konteyneri.get_attribute('innerHTML')
        soup = BeautifulSoup(page_source, 'html.parser')

        final_list = []
        table_rows = soup.select('tbody tr')

        # DÜZELTME 1: Başlık satırını atlamak için döngüye ikinci satırdan başlıyoruz ([1:]).
        for row in table_rows[1:]:
            if len(final_list) >= limit:
                break
            
            cols = row.find_all('td')
            # DÜZELTME 2: Yeterli sütun olup olmadığını kontrol ediyoruz (en az 6).
            if len(cols) >= 6:
                try:
                    sira = int(cols[0].get_text(strip=True))
                    program = cols[1].get_text(strip=True)
                    kanal = cols[2].get_text(strip=True)
                    # DÜZELTME 3: Reytingi doğru sütundan alıyoruz (6. sütun, index 5).
                    rating_str = cols[5].get_text(strip=True).replace(',', '.')
                    rating_percent = float(rating_str)
                    
                    final_list.append([sira, program, kanal, rating_percent])
                except (ValueError, IndexError):
                    # Bir veri satırı hatalıysa görmezden gel ve devam et.
                    continue
        
        if not final_list:
            raise ValueError("HTML içeriği analiz edildi ama içinden geçerli veri satırı bulunamadı.")

        print("\n" + "="*40)
        print("--- BAŞARILI! Reyting Verileri ---")
        for item in final_list:
            print(item)
        print("="*40 + "\n")
        
        return final_list

    except Exception as e:
        print(f"❌ TIAK reytingleri çekilirken HATA oluştu: {e}")
        # Hatanın detayını görmek için bu satırı geçici olarak ekleyebilirsiniz:
        # traceback.print_exc() 
        return []


def get_trending_topics_trends24(limit=10):
    """trends24.in sitesinden trend olan Twitter başlıklarını çeker."""
    url = config.TRENDS24_URL
    print(f"ℹ️ Twitter trendleri çekiliyor: {url}")
    try:
        # Bu işlem için Selenium'a gerek yok, requests daha hızlıdır.
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        trend_list_items = soup.select("ol.trend-card__list li")
        if not trend_list_items:
            print("⚠️ Trends24: Trend listesi bulunamadı.")
            return []

        trends = []
        for li in trend_list_items[:limit]:
            trend_text = li.get_text(strip=True)
            # Çeşitli temizlik adımları
            cleaned_trend = re.sub(r"^\d+\.\s+", "", trend_text).strip() # "1. " gibi sıralamaları kaldır
            cleaned_trend = re.sub(r"\s*\([\d.,]+[KMBkmb]?\s*(?:tweet|paylaşım|gönderi)\w*\s*\)$", "", cleaned_trend, flags=re.IGNORECASE).strip() # "(15.3K Tweets)" gibi kısımları kaldır
            cleaned_trend = re.sub(r"(\d+[KMB])$", "", cleaned_trend, flags=re.IGNORECASE).strip() # "27K" gibi bitişikleri kaldır
            if cleaned_trend:
                trends.append(cleaned_trend)
        
        print(f"✅ {len(trends)} adet Twitter trendi (temizlenmiş) çekildi.")
        return trends
    except Exception as e:
        print(f"⚠️ Trends24 trend çekme hatası: {e}")
        return []

def get_flashscore_sport_fixtures(driver, combined_path, league_name, max_fixtures=7):
    """Flashscore'dan fikstür bilgilerini çeker."""
    path_parts = combined_path.split('/', 1)
    sport_path = path_parts[0].lower()
    league_path = path_parts[1]
    url = f"https://www.flashscore.com.tr/{sport_path}/{league_path}/fikstur/"
    
    print(f"ℹ️ {league_name} fikstürü çekiliyor...")
    try:
        driver.get(url)
        # Çerezleri kabul etme
        try:
            WebDriverWait(driver, 7).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            time.sleep(0.5)
        except Exception:
            pass # Popup çıkmazsa devam et

        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, config.FLASHSCORE_MATCH_ELEMENT_SELECTOR)))
        
        matches = driver.find_elements(By.CSS_SELECTOR, config.FLASHSCORE_MATCH_ELEMENT_SELECTOR)
        fixtures = []
        for match_element in matches:
            if len(fixtures) >= max_fixtures:
                break
            try:
                time_str_raw = match_element.find_element(By.CLASS_NAME, config.FLASHSCORE_TIME_CLASS).text.strip()
                converted_time_str = time_str_raw  # Hata durumunda orijinali kullan

                # Zamanı UTC+3'e dönüştürmeyi dene
                try:
                    # Durum 1: "DD.MM. HH:MM" formatı (örn: "18.06. 22:00")
                    if '.' in time_str_raw and ':' in time_str_raw:
                        parts = time_str_raw.split()
                        date_part = parts[0]
                        time_part = parts[1]
                        
                        current_year = datetime.now().year
                        full_date_str = f"{date_part}{current_year} {time_part}"
                        
                        utc_time = datetime.strptime(full_date_str, "%d.%m.%Y %H:%M")
                        local_time = utc_time + timedelta(hours=config.TIME_OFFSET_HOURS)
                        converted_time_str = local_time.strftime("%d.%m. %H:%M")

                    # Durum 2: "HH:MM" formatı (örn: "21:45")
                    elif ':' in time_str_raw and '.' not in time_str_raw:
                        hour, minute = map(int, time_str_raw.split(':'))
                        
                        now_utc = datetime.now(timezone.utc)
                        utc_time = now_utc.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        local_time = utc_time + timedelta(hours=config.TIME_OFFSET_HOURS)
                        converted_time_str = local_time.strftime("%H:%M")

                except (ValueError, IndexError) as e:
                    print(f"ℹ️ Flashscore zamanı ({time_str_raw}) dönüştürülemedi, orijinal kullanılıyor. Hata: {e}")
                    converted_time_str = time_str_raw

                if sport_path == "basketbol":
                    home_team_class = config.FLASHSCORE_BASKETBOL_HOME_TEAM_CLASS
                    away_team_class = config.FLASHSCORE_BASKETBOL_AWAY_TEAM_CLASS
                else:  # Varsayılan olarak futbol
                    home_team_class = config.FLASHSCORE_FUTBOL_HOME_TEAM_CLASS
                    away_team_class = config.FLASHSCORE_FUTBOL_AWAY_TEAM_CLASS

                home_team = match_element.find_element(By.CLASS_NAME, home_team_class).text.strip()
                away_team = match_element.find_element(By.CLASS_NAME, away_team_class).text.strip()
                
                if not home_team or not away_team:
                    continue

                fixtures.append(f"{converted_time_str}: {home_team} vs {away_team}")
            except Exception:
                continue  # Tek bir maçta hata olursa atla

        print(f"✅ {league_name}: {len(fixtures)} maç bulundu.")
        return league_name, fixtures
    except Exception as e:
        print(f"❌ {league_name} ({combined_path}) Flashscore verisi alınamadı: {e}")
        return league_name, []
    

def fetch_article_snippet(url, timeout=7):
    """Verilen URL'den makalenin meta açıklamasını veya ilk birkaç paragrafını çeker."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Strateji 1: Meta açıklamasını bul (genellikle en iyi özettir)
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content').strip()

        # Strateji 2: Meta açıklama yoksa, ilk birkaç anlamlı paragrafı bul
        paragraphs = soup.find_all('p')
        content = ". ".join(p.get_text(strip=True) for p in paragraphs[:3] if p.get_text(strip=True))
        return content if content else None

    except requests.exceptions.RequestException as e:
        print(f"⚠️ İçerik çekme hatası ({url}): {e}")
        return None