# main.py (Önbellekleme Mantığı Eklenmiş Son Hali)

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
# YENİ: Önbellek yöneticisini import ediyoruz
from cache_manager import get_cached_data


def setup_driver():
    """Paylaşılan ve tespit edilemeyen Selenium WebDriver'ı kurar."""
    # ... (Bu fonksiyonun içeriği aynı kalıyor, değişiklik yok)
    print("ℹ️ Undetected Chrome WebDriver kuruluyor...")
    try:
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
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
    # ... (Bu fonksiyonun içeriği aynı kalıyor, değişiklik yok)
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
        html_output = template.render(**context)
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



def gather_all_data():
    """Tüm kaynaklardan verileri (önbelleği kontrol ederek) toplayan ana fonksiyon."""
    
    context = {}
    print("--- Veri Toplama İşlemi Başladı (Önbellek Kontrolü Aktif) ---")
    
    # ... (Selenium ve API veri toplama işlemleri aynı kalıyor)

    # --- RSS Akışları (Genellikle önbelleksiz veya çok kısa süreli) ---
    print("\n--- RSS Akışları Paralel Olarak Çekiliyor ---")
    # Bu bölümü önbelleksiz bırakarak her zaman en taze haberlerin gelmesini sağlıyoruz.
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

    # Hava durumu yorumu: 120 dakika (2 saat) önbellek
    weather_commentary_fetcher = lambda: generate_weather_commentary(context.get('weather'))
    context['weather_commentary'] = get_cached_data("ai_weather_commentary.json", weather_commentary_fetcher, expiry_minutes=120)

    # Twitter başlığı: 60 dakika önbellek
    twitter_headline_fetcher = lambda: generate_dynamic_headline_for_trends(context.get('twitter_trends'))
    context['twitter_headline'] = get_cached_data("ai_twitter_headline.json", twitter_headline_fetcher, expiry_minutes=60)

    # Aktivite Önerisi: 120 dakika önbellek
    activity_suggestion_fetcher = lambda: generate_contextual_activity_suggestion(context.get('weather_commentary'), context.get('istanbul_events'))
    context['contextual_suggestion'] = get_cached_data("ai_activity_suggestion.json", activity_suggestion_fetcher, expiry_minutes=120)

    # Günlük Haber Özeti için yardımcı fonksiyon tanımı
    def fetch_daily_summary():
        """Haber içeriklerini çekip özetleyen ve sadece sonucu döndüren yardımcı fonksiyon."""
        all_news_flat = [item for sublist in news_results.values() for item in sublist]
        sorted_news = sorted(all_news_flat, key=lambda x: x['pub_date_parsed'], reverse=True)[:5]
        
        news_for_summary = []
        print(f"Özetleme için en yeni {len(sorted_news)} haberin içeriği çekiliyor...")
        for news_item in sorted_news:
            snippet = fetch_article_snippet(news_item['link'])
            if snippet:
                news_for_summary.append({"title": news_item['title'], "content": snippet})
                
        if news_for_summary:
            summary_data = generate_abstractive_summary(news_for_summary)
            return summary_data
        return None

    # --- DEĞİŞİKLİK BURADA BAŞLIYOR ---

    # Günlük Haber Özeti (ÖNBELLEKSİZ)
    # Bu fonksiyon her zaman en güncel haber akışından (RSS) beslendiği için
    # tutarlılığı sağlamak amacıyla önbellek kullanılmamalıdır.
    print("🔄 Günlük haber özeti (önemli başlıklar) oluşturuluyor...")
    summary_data = fetch_daily_summary()
    context['top_headlines'] = summary_data if summary_data else []
    if context['top_headlines']:
        print("✅ Günlük haber özeti başarıyla oluşturuldu.")
    else:
        print("⚠️ Günlük haber özeti oluşturulamadı veya veri bulunamadı.")


    # Günlük Brifing (ÖNBELLEKSİZ)
    # Bu fonksiyon, 'top_headlines' gibi anlık oluşturulan verilere dayandığı için
    # her seferinde yeniden oluşturulmalıdır.
    print("🔄 Günlük brifing metni (günün özeti) oluşturuluyor...")
    context['daily_briefing'] = generate_daily_briefing(context)
    if context.get('daily_briefing') and "yeterli veri bulunamadı" not in context['daily_briefing']:
         print("✅ Günlük brifing metni başarıyla oluşturuldu.")
    else:
        print("⚠️ Günlük brifing için yeterli veri bulunamadı.")

    # --- DEĞİŞİKLİK BURADA BİTİYOR ---

    # Son güncelleme zamanını ekle
    context['last_update'] = datetime.now(config.TZ).strftime('%d %B %Y, %H:%M:%S')

    print("--- Tüm Veri Toplama ve İşleme Adımları Tamamlandı ---")
    return context


# ANA ÇALIŞTIRMA BÖLÜMÜ (Bu bölüm değişmedi)
if __name__ == "__main__":
    start_time = time.time()
    try:
        final_context = gather_all_data()
        generate_output_files(final_context)
        end_time = time.time()
        print(f"\n🎉 Tüm statik sayfa oluşturma işlemi {end_time - start_time:.2f} saniyede tamamlandı.")
    except Exception as e:
        print("\n❌ PROGRAM ÇALIŞIRKEN KRİTİK BİR HATA OLUŞTU!")
        import traceback
        traceback.print_exc()
        exit(1)


