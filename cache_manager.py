# cache_manager.py

import json
import os
from datetime import datetime, timedelta

CACHE_DIR = "cache" # Önbellek dosyalarını saklamak için bir klasör

# Cache klasörünün var olduğundan emin ol
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cached_data(cache_file_name, fetch_function, expiry_minutes=15):
    """
    Veriyi önbellekten alır veya gerekirse yeniden çeker.
    Eğer yeniden çekme işlemi başarısız olursa, süresi dolmuş olsa bile
    önbellekteki son geçerli veriyi döndürür.

    :param cache_file_name: Verinin saklanacağı dosya adı (örn: "weather.json").
    :param fetch_function: Veri taze değilse çalıştırılacak olan API çekme fonksiyonu.
    :param expiry_minutes: Verinin kaç dakika "taze" sayılacağı.
    :return: Önbellekten veya API'den alınan veri.
    """
    cache_path = os.path.join(CACHE_DIR, cache_file_name)
    stale_data = None # Eski veriyi tutmak için bir değişken

    # 1. Önbellek dosyasını her zaman kontrol et ve eski veriyi sakla
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            stale_data = cache_data.get('data') # Eski veriyi al
            cached_time = datetime.fromisoformat(cache_data['timestamp'])

            # 2. Veri taze mi diye kontrol et
            if datetime.now() < cached_time + timedelta(minutes=expiry_minutes):
                print(f"✅ Önbellekten okundu: {cache_file_name} (Taze)")
                return stale_data # Taze veri varsa döndür
            else:
                print(f"⚠️ Önbellek bayatlamış: {cache_file_name}. Yeniden çekilecek.")
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"❌ Önbellek okuma hatası: {e}. Veri yeniden çekilecek.")
            stale_data = None # Hatalı dosyayı geçerli sayma

    # 3. Veri taze değilse veya önbellek yoksa, yeniden çek
    print(f"🔄 Veri yeniden çekiliyor: {cache_file_name}...")
    new_data = fetch_function()

    # 4. Yeni veri başarıyla çekildiyse kaydet ve döndür
    #    (None, False, [], {} gibi 'boş' değerler başarıSız kabul edilir)
    if new_data:
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                payload = {
                    'timestamp': datetime.now().isoformat(),
                    'data': new_data
                }
                json.dump(payload, f, ensure_ascii=False, indent=4)
            print(f"💾 Yeni veri önbelleğe kaydedildi: {cache_file_name}")
            return new_data
        except Exception as e:
            print(f"❌ Önbellek yazma hatası: {e}")
            # Yazma hatası olsa bile yeni çekilen veriyi döndür
            return new_data
            
    # 5. Yeni veri çekilemediyse ve elimizde eski veri varsa, onu kullan
    if stale_data:
        print(f"‼️ API/Çekme hatası! Bayatlamış önbellek kullanılıyor: {cache_file_name}")
        return stale_data

    # 6. Hiçbir veri yoksa (ilk çalıştırma ve hata) None döndür
    print(f"❌ Veri çekilemedi ve önbellekte de veri yok: {cache_file_name}")
    return None