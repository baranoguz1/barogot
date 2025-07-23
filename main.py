# main.py (Sizin orijinal kodunuzun üzerine caching eklenmiş hali)

import time
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import undetected_chromedriver as uc
import hashlib # <- BURAYI EKLEDİK

# Proje modüllerini import et
import config
from analysis.news_analyzer import group_similar_news
from data_fetchers import api_fetchers, web_scrapers
from data_fetchers.web_scrapers import fetch_article_snippet
from analysis.summarizer import (
    generate_abstractive_summary,
    generate_weather_commentary,
    generate_daily_briefing,
    generate_dynamic_headline_for_trends,
    generate_comparative_news_analysis
)
from cache_manager import get_cached_data


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
        # GitHub Actions ortamında belirli bir sürüm belirtmek stabiliteyi artırabilir.
        # Eğer yerel makinede çalışıyorsanız bu satırı yorum satırı yapabilirsiniz.
        print("ℹ️ Tarayıcı sürümü 137 olarak ayarlanıyor.")
        driver = uc.Chrome(options=chrome_options, version_main=137)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
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
        # HTML dosyasının adını index.html olarak değiştiriyoruz
        env = Environment(loader=FileSystemLoader(root_dir / 'templates/'))
        template = env.get_template('haberler_template.html')
        html_output_path = output_dir / "index.html" # <- DEĞİŞİKLİK
        html_output = template.render(**context)
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_output)
        print(f"✅ HTML dosyası başarıyla oluşturuldu: {html_output_path}")

        # service-worker.js gibi PWA dosyalarını da kopyala
        static_files_to_copy = ["style.css", "script.js", "manifest.json", "service-worker.js"]
        for file_name in static_files_to_copy:
            source_path = root_dir / file_name
            if source_path.exists():
                shutil.copy(source_path, output_dir / file_name)
                print(f"✅ {file_name} dosyası output klasörüne kopyalandı.")
        print(f"\n✅ Çıktı klasörü başarıyla hazırlandı: {output_dir}")
    except Exception as e:
        print(f"❌ Çıktı dosyaları oluşturulurken hata oluştu: {e}")



def gather_all_data():
    """Tüm kaynaklardan verileri (önbelleği kontrol ederek) toplayan ana fonksiyon."""
    
    context = {}
    driver = setup_driver() # WebDriver'ı bir kere başlat
    if not driver:
        print("❌ WebDriver başlatılamadığı için program durduruluyor.")
        return None

    try:
        print("--- Veri Toplama İşlemi Başladı (Önbellek Kontrolü Aktif) ---")
        
        # --- Selenium ile çekilen ve önbelleğe alınan veriler ---
        books_fetcher = lambda: web_scrapers.fetch_books(driver)
        context['books'] = get_cached_data("books.json", books_fetcher, expiry_minutes=120) or []

        ratings_fetcher = lambda: web_scrapers.get_daily_ratings(driver)
        context['ratings'] = get_cached_data("ratings.json", ratings_fetcher, expiry_minutes=180) or []

        zorlu_events_fetcher = lambda: web_scrapers.fetch_istanbul_events(driver)
        zorlu_events = get_cached_data("zorlu_events.json", zorlu_events_fetcher, expiry_minutes=60) or []

        def fetch_all_fixtures():
            fixtures_all = {}
            for path, name in config.SPORT_LEAGUES_CONFIG:
                _, fixtures = web_scrapers.get_flashscore_sport_fixtures(driver, path, name)
                fixtures_all[name] = fixtures
            return fixtures_all
        context['fixtures'] = get_cached_data("fixtures.json", fetch_all_fixtures, expiry_minutes=120) or {}

        # --- API ve Diğer Veriler (Önbellekli) ---
        print("\n--- API ve Diğer Veriler Çekiliyor (Önbellek Kontrolü Aktif) ---")
        
        ticketmaster_fetcher = lambda: api_fetchers.fetch_ticketmaster_events(limit=10, city='Istanbul', get_popular_and_sort_by_date=True)
        ticketmaster_events = get_cached_data("ticketmaster_events.json", ticketmaster_fetcher, expiry_minutes=20) or []
        
        context['istanbul_events'] = zorlu_events + ticketmaster_events
        print(f"✅ Toplam {len(context['istanbul_events'])} adet etkinlik birleştirildi.")
        
        context['weather'] = get_cached_data("weather.json", api_fetchers.get_hourly_weather, expiry_minutes=15) or {}
        context['exchange_rates'] = get_cached_data("exchange_rates.json", api_fetchers.get_exchange_rates, expiry_minutes=30) or {}
        context['movies'] = get_cached_data("movies.json", api_fetchers.fetch_movies, expiry_minutes=60) or []
        context['spotify_tracks'] = get_cached_data("spotify.json", api_fetchers.get_new_turkish_rap_tracks_embed, expiry_minutes=60) or []
        context['twitter_trends'] = get_cached_data("trends.json", web_scrapers.get_trending_topics_trends24, expiry_minutes=10) or []

        # --- RSS Akışları (Genellikle önbelleksiz veya çok kısa süreli) ---
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
        
        # --- Yapay Zeka ile İçerik Üretimi (Önbellek Kontrolü Aktif) ---
        print("\n--- Yapay Zeka ile İçerik Üretimi Başladı ---")

        weather_commentary_fetcher = lambda: generate_weather_commentary(context.get('weather'))
        context['weather_commentary'] = get_cached_data("ai_weather_commentary.json", weather_commentary_fetcher, expiry_minutes=120) or "Hava durumu yorumu alınamadı."

        def fetch_daily_summary():
            all_news_flat = [item for sublist in news_results.values() for item in sublist]
            # En yeni 5 haberi al
            sorted_news = sorted(all_news_flat, key=lambda x: x['pub_date_parsed'], reverse=True)[:5]
            if not sorted_news: return None
            
            # Haber içeriklerini çekmek için string oluştur
            news_content_for_prompt = ""
            for news_item in sorted_news:
                # Başlık ve özet bilgisini birleştirerek prompt'a ekle
                news_content_for_prompt += f"Başlık: {news_item['title']}\nÖzet: {news_item['summary']}\n\n"
            
            if news_content_for_prompt:
                return generate_abstractive_summary(news_content_for_prompt)
            return None

        print("🔄 Günlük haber özeti (önemli başlıklar) oluşturuluyor...")
        summary_data = get_cached_data("ai_top_headlines.json", fetch_daily_summary, expiry_minutes=60)
        context['top_headlines'] = summary_data if summary_data else []
        if context['top_headlines']: print("✅ Günlük haber özeti başarıyla oluşturuldu.")
        else: print("⚠️ Günlük haber özeti oluşturulamadı veya veri bulunamadı.")

        print("🔄 Günlük brifing metni (günün özeti) oluşturuluyor...")
        context['daily_briefing'] = generate_daily_briefing(context)
        if context.get('daily_briefing') and "yeterli veri bulunamadı" not in context['daily_briefing']:
            print("✅ Günlük brifing metni başarıyla oluşturuldu.")
        else:
            print("⚠️ Günlük brifing için yeterli veri bulunamadı.")

        # =========================================================================
        # ===== KOTA SORUNUNU ÇÖZEN DÜZELTİLMİŞ ÖNBELLEKLEME (CACHING) BLOĞU =====
        # =========================================================================
        all_news_list = [item for category_news in context.get('news', {}).values() for item in category_news]
        context['haber_analizleri'] = [] 

        if all_news_list:
            print("\n--- Benzer Haberler Gruplanıyor ve Analiz Ediliyor (Önbellek Aktif) ---")
            
            haber_gruplari = group_similar_news(all_news_list)
            
            if haber_gruplari:
                cached_haber_analizleri = []
                
                for group in haber_gruplari:
                    if len(group) > 1:
                        # Önbellek anahtarı için haber başlıklarını kullanıyoruz
                        group_headlines = sorted([haber['title'] for haber in group])
                        headlines_str = "".join(group_headlines)
                        cache_key = f"analysis_{hashlib.md5(headlines_str.encode()).hexdigest()}.json"

                        # ÖNEMLİ DÜZELTME: Fonksiyona `group` değişkenini (haber nesnelerinin listesi)
                        # gönderdiğimizden emin oluyoruz, `group_headlines`'ı (metin listesi) değil.
                        analysis_result = get_cached_data(
                            cache_key,
                            lambda g=group: generate_comparative_news_analysis(g), # BU SATIRIN DOĞRULUĞU KRİTİK
                            expiry_minutes=180 
                        )
                        
                        if analysis_result:
                            # generate_comparative_news_analysis'ın döndürdüğü yapıya göre
                            # listeye ekleme yapıyoruz. Eğer fonksiyon tek bir analiz döndürüyorsa
                            # extend yerine append kullanmak daha güvenli olabilir.
                            # Şimdilik orijinal mantığı koruyalım:
                            cached_haber_analizleri.extend(analysis_result)

                context['haber_analizleri'] = cached_haber_analizleri
            
            if context['haber_analizleri']:
                print(f"✅ Toplam {len(context['haber_analizleri'])} adet olay analizi başarıyla oluşturuldu (önbellek kullanıldı).")
            else:
                print("⚠️ Analiz edilecek yeterli haber grubu bulunamadı veya analiz sırasında hata oluştu.")
        # =================== DEĞİŞİKLİĞİN SONU ===================

        # Son güncelleme zamanını ekle
        context['last_update'] = datetime.now(config.TZ).strftime('%d %B %Y, %H:%M:%S')

        print("--- Tüm Veri Toplama ve İşleme Adımları Tamamlandı ---")
        return context
    finally:
        if driver:
            driver.quit()
            print("✅ WebDriver kapatıldı.")


# --- DÜZELTİLMİŞ ANA ÇALIŞTIRMA BLOĞU ---
if __name__ == "__main__":
    start_time = time.time()
    try:
        print("🚀 Haber Botu ana betiği başlatıldı...")
        # Ana fonksiyonları burada çağırıyoruz
        context = gather_all_data()
        if context:
            generate_output_files(context)
            print("\n--- Tüm İşlemler Başarıyla Tamamlandı ---")
        else:
            print("\n❌ Veri toplama başarısız olduğu için dosya oluşturma işlemi atlandı.")

    except Exception as e:
        import traceback
        print("\n❌ PROGRAMIN ANA ÇALIŞMA AŞAMASINDA KRİTİK BİR HATA OLUŞTU:")
        traceback.print_exc()
    finally:
        end_time = time.time()
        print(f"\n⏱️  Toplam çalışma süresi: {end_time - start_time:.2f} saniye.")