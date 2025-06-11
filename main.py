# main.py (Final Hali)
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader # Jinja2 importu eklendi

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

import config
from data_fetchers import api_fetchers, web_scrapers


def setup_driver():
    """Paylaşılan Selenium WebDriver'ı kurar ve döndürür."""
    print("ℹ️ Chrome WebDriver kuruluyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    try:
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome WebDriver başarıyla başlatıldı.")
        return driver
    except Exception as e:
        print(f"❌ Chrome WebDriver başlatılamadı: {e}")
        return None

def generate_html_from_template(context):
    """
    Toplanan verileri (context) kullanarak Jinja2 şablonundan nihai HTML'i üretir.
    """
    try:
        # Jinja2 ortamını kur ve şablonların olduğu klasörü belirt
        env = Environment(loader=FileSystemLoader('templates/'))
        template = env.get_template('haberler_template.html')

        # Şablonu context verileriyle "render" et (doldur)
        html_output = template.render(context)

        # Çıktı klasörünün var olduğundan emin ol
        config.OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        
        # Nihai HTML dosyasını yaz
        with open(config.HTML_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(html_output)
        
        print(f"\n✅ Nihai HTML dosyası şablondan başarıyla oluşturuldu: {config.HTML_FILE_PATH}")

    except Exception as e:
        print(f"❌ HTML dosyası şablondan oluşturulurken hata oluştu: {e}")

def main():
    """Ana iş akışını yönetir."""
    start_time = time.time()
    
    context = {}
    
    # API Anahtarını context'e ekle, böylece şablon içinde kullanılabilir
    context['GOOGLE_MAPS_APİ_KEY'] = config.GOOGLE_MAPS_API_KEY
    
    driver = setup_driver()
    if driver:
        try:
            print("\n--- Selenium ile Veri Kazıma Başladı ---")
            context['ratings'] = web_scrapers.get_daily_ratings(driver)
            context['books'] = web_scrapers.fetch_books(driver)
            context['istanbul_events'] = web_scrapers.fetch_istanbul_events(driver)
            
            fixtures_all = {}
            for path, name in config.SPORT_LEAGUES_CONFIG:
                _, fixtures = web_scrapers.get_flashscore_sport_fixtures(driver, path, name)
                fixtures_all[name] = fixtures
            context['fixtures'] = fixtures_all
        finally:
            driver.quit()
            print("✅ Chrome WebDriver kapatıldı.")
    else:
        print("⚠️ Selenium işlemleri atlandı.")

    print("\n--- API ve Diğer Veriler Çekiliyor ---")
    context['weather'] = api_fetchers.get_hourly_weather()
    context['exchange_rates'] = api_fetchers.get_exchange_rates()
    context['movies'] = api_fetchers.fetch_movies()
    context['spotify_tracks'] = api_fetchers.get_new_turkish_rap_tracks_embed()
    context['twitter_trends'] = web_scrapers.get_trending_topics_trends24()

    print("\n--- RSS Akışları Paralel Olarak Çekiliyor ---")
    news_results = {category: [] for category in config.RSS_FEEDS}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(api_fetchers.fetch_rss_feed, url): category for category, urls in config.RSS_FEEDS.items() for url in urls}
        for future in future_to_url:
            category = future_to_url[future]
            try:
                result = future.result()
                if result: news_results[category].extend(result)
            except Exception as e:
                print(f"⚠️ RSS görevi hatası: {e}")
    context['news'] = news_results
    
    local_now = datetime.now(timezone.utc) + timedelta(hours=config.TIME_OFFSET_HOURS)
    context['last_update'] = local_now.strftime("%d %B %Y, %H:%M:%S")

    # Toplanan tüm verilerle HTML'i şablondan oluştur
    generate_html_from_template(context)

    end_time = time.time()
    print(f"\n🎉 Tüm işlemler {end_time - start_time:.2f} saniyede tamamlandı.")

if __name__ == "__main__":
    if not all([config.OPENWEATHER_API_KEY, config.TMDB_API_KEY, config.SPOTIFY_CLIENT_ID]):
        print("❌ Gerekli API anahtarları eksik. .env dosyasını kontrol edin.")
    else:
        main()