import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# config.py dosyasından TIAK_URL'yi çekmek için
import config

def setup_driver():
    """Selenium WebDriver'ı başlatan ve yapılandıran fonksiyon."""
    print("ℹ️ Selenium WebDriver kuruluyor...")
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("✅ Selenium WebDriver başarıyla başlatıldı.")
        return driver
    except Exception as e:
        print(f"❌ WebDriver başlatılırken KRİTİK HATA: {e}")
        return None

# --- Fonksiyonun adını 'get_daily_ratings' olarak düzelttik ---
def get_daily_ratings(driver, limit=10):
    """Sadece TİAK için izole edilmiş test fonksiyonu."""
    url = config.TIAK_URL
    print(f"ℹ️ TIAK reytingleri çekiliyor: {url}")
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # 1. Adım: Düğmenin sayfada var olmasını bekle.
        print("... 'Günlük Raporlar' sekmesi aranıyor ...")
        gunluk_raporlar_button = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='#gunluk']"))
        )
        print("✅ 'Günlük Raporlar' sekmesi bulundu.")

        # 2. Adım: JavaScript ile tıkla.
        print("... JavaScript ile 'Günlük Raporlar' sekmesine tıklanıyor ...")
        driver.execute_script("arguments[0].click();", gunluk_raporlar_button)
        print("✅ 'Günlük Raporlar' sekmesine başarıyla tıklandı.")

        # 3. Adım: Tablonun yüklenmesini bekle.
        print("... Günlük reyting tablosunun yüklenmesi bekleniyor ...")
        gunluk_tablosu = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div#gunluk table"))
        )
        print("✅ Günlük reyting tablosu başarıyla yüklendi.")

        page_source = gunluk_tablosu.get_attribute('outerHTML')
        ratings_df = pd.read_html(page_source, na_values=['-'])[0]
        
        # Gerekli yeniden adlandırma ve temizleme işlemleri...
        ratings_df.rename(columns={'SIRA': 'Sıra', 'PROGRAM': 'Program', 'KANAL': 'Kanal', 'RTG%': 'Rating %'}, inplace=True)
        required_cols = ['Sıra', 'Program', 'Kanal', 'Rating %']
        if not all(col in ratings_df.columns for col in required_cols):
            raise ValueError("Tablo bulundu ama beklenen sütunlar bulunamadı!")
        
        final_list = ratings_df[required_cols].head(limit).values.tolist()

        if not final_list:
            raise ValueError("Tüm adımlar tamamlandı ancak sonuç listesi boş.")

        print("\n--- BAŞARILI! TİAK VERİLERİ ---")
        for item in final_list:
            print(item)
        print("---------------------------------")
        return final_list

    except Exception as e:
        print("\n" + "="*50)
        print(f"❌ HATA YAKALANDI. HATA SEBEBİ: {e}")
        print("HATA AYIKLAMA DOSYALARI OLUŞTURULUYOR...")
        print("="*50 + "\n")
        
        try:
            debug_file_html = "DEBUG_TIAK_PAGE_SOURCE.html"
            debug_file_png = "DEBUG_TIAK_SCREENSHOT.png"
            
            with open(debug_file_html, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot(debug_file_png)
            print(f"✅ Hata ayıklama dosyaları başarıyla oluşturuldu: {debug_file_html}, {debug_file_png}")
            
        except Exception as debug_e:
            print(f"⚠️ Hata ayıklama dosyaları kaydedilirken ek bir hata oluştu: {debug_e}")
        
        raise e

if __name__ == "__main__":
    test_driver = setup_driver()
    if test_driver:
        try:
            # --- Fonksiyonu doğru adıyla ('get_daily_ratings') çağırıyoruz ---
            get_daily_ratings(test_driver)
        finally:
            print("ℹ️ Test bitti, WebDriver kapatılıyor.")
            test_driver.quit()