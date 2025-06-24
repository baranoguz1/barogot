# main.py

import time
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import undetected_chromedriver as uc

# Proje modüllerini import et
import config
from data_fetchers import api_fetchers, web_scrapers
from data_fetchers.web_scrapers import fetch_article_snippet
from analysis.summarizer import (
    generate_abstractive_summary,
    generate_weather_commentary,
    generate_daily_briefing,
    generate_dynamic_headline_for_trends,
    generate_contextual_activity_suggestion
)


def setup_driver():
    """Paylaşılan ve tespit edilemeyen Selenium WebDriver'ı kurar."""
    print("ℹ️ Undetected Chrome WebDriver kuruluyor...")
    try:
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        driver = uc.Chrome(options=chrome_options)
        print("✅ Undetected Chrome WebDriver başarıyla başlatıldı.")
        return driver
    except Exception as e:
        import traceback
        print(f"❌ Undetected Chrome WebDriver başlatılamadı: {e}")
        traceback.print_exc()
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

        html_output = template.render(**context) # Anahtar-değer çiftleri olarak göndermek daha sağlıklıdır
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"✅ HTML dosyası başarıyla oluşturuldu: {html_output_path}")

        static_files_to_copy = ["style.css", "script.js", "manifest.json", "service-worker.js"]
        for file_name in static_files_to_copy:
            source_path = root_dir / file_name
            if source_path.exists():
                shutil.copy(source_path, output_dir / file_name)
                print(f"✅ {file_name} dosyası output klasörüne kopyalandı.")

        print(f"\n✅ Çıktı klasörü başarıyla hazırlandı: {output_dir}")

    except Exception as e:
        print(f"❌ Çıktı dosyaları oluşturulurken hata oluştu: {e}")

# ==============================================================================
# YENİ EKLENEN ANA VERİ TOPLAMA FONKSİYONU
# Bu fonksiyon, app.py tarafından da kullanılacak olan ana mantığı içerir.
# ==============================================================================
def gather_all_data():
    """Tüm kaynaklardan verileri toplayan ve tek bir context sözlüğü döndüren ana fonksiyon."""
    
    context = {}
    print("--- Veri Toplama İşlemi Başladı ---")
    
    driver = setup_driver()
    if driver:
        try:
            print("\n--- Selenium ile Veri Kazıma Başladı ---")
            context['ratings'] = web_scrapers.get_daily_ratings(driver)
            context['books'] = web_scrapers.fetch_books(driver)
            print("ℹ️ Etkinlikler çekiliyor (Zorlu PSM)...")
            zorlu_events = web_scrapers.fetch_istanbul_events(driver) or []
            
            print("ℹ️ Etkinlikler çekiliyor (Eventmag)...")
            eventmag_events = web_scrapers.fetch_eventmag_events(driver) or []
            all_events = zorlu_events + eventmag_events
            context['istanbul_events'] = all_events
            print(f"✅ Toplam {len(all_events)} adet etkinlik birleştirildi.")
            
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
    
    print("\n--- Yapay Zeka ile İçerik Üretimi Başladı ---")
    # Önce temel AI yorumlarını üretelim
    if context.get('weather'):
        context['weather_commentary'] = generate_weather_commentary(context['weather'])
    
    if context.get('twitter_trends'):
        context['twitter_headline'] = generate_dynamic_headline_for_trends(context.get('twitter_trends'))

    # Haber özetleme için içerikleri hazırla
    all_news_flat = [item for sublist in news_results.values() for item in sublist]
    sorted_news = sorted(all_news_flat, key=lambda x: x['pub_date_parsed'], reverse=True)[:20]

    news_for_summary = []
    print(f"Özetleme için en yeni {len(sorted_news)} haberin içeriği çekiliyor...")
    for news_item in sorted_news:
        snippet = fetch_article_snippet(news_item['link'])
        if snippet:
            news_for_summary.append({"title": news_item['title'], "content": snippet})

    if news_for_summary:
        summary_data = generate_abstractive_summary(news_for_summary)
        if summary_data:
            context['top_headlines'] = summary_data
            print(f"✅ Önemli olaylar başarıyla özetlendi: {len(context['top_headlines'])} başlık bulundu.")
        else:
            context['top_headlines'] = []
            print("⚠️ Özet verisi AI tarafından üretilemedi veya formatı bozuk.")
    else:
        context['top_headlines'] = []
        print("⚠️ Özetlenecek yeterli haber içeriği bulunamadı.")
    
    # Diğer AI fonksiyonlarını çağır
    context['contextual_suggestion'] = generate_contextual_activity_suggestion(context.get('weather_commentary'), context.get('istanbul_events'))
    context['daily_briefing'] = generate_daily_briefing(context)

    # Son güncelleme zamanını ekle
    context['last_update'] = datetime.now(config.TZ).strftime('%d %B %Y, %H:%M:%S')
    
    print("--- Tüm Veri Toplama ve İşleme Adımları Tamamlandı ---")
    return context


# ==============================================================================
# ANA ÇALIŞTIRMA BÖLÜMÜ
# `python main.py` komutu verildiğinde bu bölüm çalışır.
# ==============================================================================
if __name__ == "__main__":
    start_time = time.time()
    
    # 1. Tüm verileri topla
    final_context = gather_all_data()
    
    # 2. Toplanan verilerle statik HTML dosyasını oluştur
    generate_output_files(final_context)
    
    end_time = time.time()
    print(f"\n🎉 Tüm statik sayfa oluşturma işlemi {end_time - start_time:.2f} saniyede tamamlandı.")