# main.py (Son Düzeltme)
import time
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader

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

def generate_output_files(context):
    """Toplanan verileri ve statik dosyaları kullanarak 'output' klasörünü oluşturur."""
    print("\n--- Çıktı Dosyaları Oluşturuluyor ---")
    try:
        root_dir = Path(__file__).resolve().parent
        output_dir = config.OUTPUT_DIRECTORY
        
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        env = Environment(loader=FileSystemLoader(root_dir / 'templates/'))
        template = env.get_template('haberler_template.html')
        html_output_path = output_dir / "index.html"
        
        html_output = template.render(context)
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"✅ {html_output_path.name} dosyası başarıyla oluşturuldu.")

        static_files = ["style.css", "script.js", "manifest.json", "service-worker.js"]
        for file_name in static_files:
            source_path = root_dir / file_name
            if source_path.exists():
                shutil.copy(source_path, output_dir / file_name)
                print(f"✅ {file_name} dosyası output klasörüne kopyalandı.")
        
        print(f"\n✅ Çıktı klasörü başarıyla hazırlandı: {output_dir}")

    except Exception as e:
        print(f"❌ Çıktı dosyaları oluşturulurken veya kopyalanırken hata oluştu: {e}")

def main():
    """Ana iş akışını yönetir."""
    start_time = time.time()
    
    context = {'GOOGLE_MAPS_API_KEY': config.GOOGLE_MAPS_API_KEY}
    
    driver = setup_driver()
    if driver:
        # HATA BU BLOKTAYDI. ŞİMDİ DOLDURULDU.
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
            print("✅ Selenium işlemleri bitti, WebDriver kapatılıyor.")
            driver.quit()
    else:
        print("⚠️ Selenium işlemleri atlandı (WebDriver başlatılamadı).")

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

    generate_output_files(context)

    end_time = time.time()
    print(f"\n🎉 Tüm işlemler {end_time - start_time:.2f} saniyede tamamlandı.")

if __name__ == "__main__":
    main()