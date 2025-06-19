import time
import pandas as pd
from io import StringIO
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
    pandas'a doğru başlık satırını gösteren nihai ve kararlı sürüm.
    """
    url = config.TIAK_URL
    print(f"ℹ️ TIAK reytingleri çekiliyor: {url}")
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # 1. Adım: "Günlük Raporlar" başlığına tıkla.
        print("... 'Günlük Raporlar' başlığı aranıyor ...")
        gunluk_raporlar_basligi = wait.until(
            EC.element_to_be_clickable((By.ID, "gunluk-tablolar"))
        )
        gunluk_raporlar_basligi.click()
        print("✅ 'Günlük Raporlar' başlığı tıklandı.")
        
        # 2. Adım: AJAX'ın tabloyu doldurmasını bekle.
        print("... Reyting tablosunun AJAX ile yüklenmesi bekleniyor ...")
        tablo_konteyneri = wait.until(
            EC.visibility_of_element_located((By.ID, "tablo"))
        )
        time.sleep(2) # Tablo içeriğinin tam dolması için kritik ek bekleme
        print("✅ Reyting tablosu yüklendi.")

        # 3. Adım: Veriyi işle
        page_source = tablo_konteyneri.get_attribute('innerHTML')
        
        # Pandas'a tablonun ilk satırını başlık olarak kullanmasını söylüyoruz (header=0).
        # Hata mesajını engellemek için StringIO kullanıyoruz.
        ratings_df = pd.read_html(StringIO(page_source), header=0)[0]
        
        # Sütun isimlerindeki olası boşlukları temizle ve yeniden adlandır.
        ratings_df = ratings_df.rename(columns=lambda x: x.strip())
        ratings_df.rename(columns={'RATING %': 'Rating %'}, inplace=True, errors='ignore')

        required_cols = ['SIRA', 'PROGRAM', 'KANAL', 'Rating %']
        if not all(col in ratings_df.columns for col in required_cols):
            raise ValueError(f"Beklenen sütunlar tabloda bulunamadı! Bulunanlar: {ratings_df.columns.tolist()}")

        # Sütunları doğru isimleriyle seçelim
        df_cleaned = ratings_df[['SIRA', 'PROGRAM', 'KANAL', 'Rating %']].copy()
        df_cleaned.columns = ['Sıra', 'Program', 'Kanal', 'Rating %']

        df_cleaned['Rating %'] = pd.to_numeric(df_cleaned['Rating %'].astype(str).str.replace(',', '.'), errors='coerce')
        df_cleaned.dropna(subset=['Rating %'], inplace=True)
        final_list = df_cleaned.head(limit).values.tolist()

        if not final_list:
            raise ValueError("Tüm adımlar tamamlandı ancak sonuç listesi boş.")

        print("\n" + "="*40)
        print("--- BAŞARILI! İZOLE TEST SONUÇLARI ---")
        for item in final_list:
            print(item)
        print("="*40 + "\n")
        
        return final_list

    except Exception as e:
        print(f"❌ TIAK testi sırasında HATA oluştu: {e}")
        raise e

if __name__ == "__main__":
    test_driver = setup_driver()
    if test_driver:
        try:
            get_daily_ratings(test_driver)
        finally:
            print("ℹ️ İzole test bitti, WebDriver kapatılıyor.")
            test_driver.quit()