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


def get_daily_ratings(driver, limit=10):
    """
    TIAK sitesinin otomasyon ortamlarına gönderdiği eski yapıyla başa çıkabilen,
    nihai ve kararlı sürüm.
    """
    url = config.TIAK_URL
    print(f"ℹ️ TIAK reytingleri çekiliyor: {url}")
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # 1. Adım: "Günlük Raporlar" başlığına tıkla. Bu bir <a> değil, <div>.
        # ID'si "gunluk-tablolar" olan div'i arıyoruz.
        print("... 'Günlük Raporlar' başlığı aranıyor ...")
        gunluk_raporlar_basligi = wait.until(
            EC.element_to_be_clickable((By.ID, "gunluk-tablolar"))
        )
        print("✅ 'Günlük Raporlar' başlığı bulundu ve tıklandı.")
        gunluk_raporlar_basligi.click()
        
        # 2. Adım: Tıkladıktan sonra AJAX'ın tabloyu doldurması için bekle.
        # Tablo, id'si "tablo" olan div'in içinde oluşur.
        print("... Reyting tablosunun AJAX ile yüklenmesi bekleniyor ...")
        wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div#tablo table"))
        )
        # Tablonun içeriğinin tam dolması için kısa bir ek bekleme
        time.sleep(2)
        print("✅ Reyting tablosu başarıyla yüklendi.")

        # 3. Adım: Veriyi işle
        tablo_elementi = driver.find_element(By.CSS_SELECTOR, "div#tablo table")
        page_source = tablo_elementi.get_attribute('outerHTML')
        ratings_df = pd.read_html(page_source, na_values=['-'])[0]
        
        # Bu eski yapıda sütun isimleri zaten doğru geliyor.
        ratings_df.rename(columns={'SIRA': 'Sıra', 'PROGRAM': 'Program', 'KANAL': 'Kanal', 'RATING %': 'Rating %'}, inplace=True)
        
        required_cols = ['Sıra', 'Program', 'Kanal', 'Rating %']
        if not all(col in ratings_df.columns for col in required_cols):
            raise ValueError(f"Beklenen sütunlar tabloda bulunamadı! Bulunanlar: {ratings_df.columns.tolist()}")

        df_cleaned = ratings_df[required_cols].copy()
        df_cleaned['Rating %'] = pd.to_numeric(df_cleaned['Rating %'].astype(str).str.replace(',', '.'), errors='coerce')
        df_cleaned.dropna(subset=['Rating %'], inplace=True)
        final_list = df_cleaned.head(limit).values.tolist()

        print(f"✅ TIAK günlük program reytingleri başarıyla çekildi ve {len(final_list)} program işlendi.")
        return final_list

    except Exception as e:
        print(f"❌ TIAK reytingleri alınırken genel bir HATA oluştu: {e}")
        # Hata anında yine de debug dosyalarını oluşturmaya çalışalım
        try:
            with open("DEBUG_FINAL_ERROR.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("DEBUG_FINAL_ERROR.png")
            print("ℹ️ Hata ayıklama için sayfanın son hali kaydedildi.")
        except Exception as debug_e:
            print(f"⚠️ Hata ayıklama dosyaları kaydedilemedi: {debug_e}")
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