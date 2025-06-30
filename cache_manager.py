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

    :param cache_file_name: Verinin saklanacağı dosya adı (örn: "weather.json").
    :param fetch_function: Veri taze değilse çalıştırılacak olan API çekme fonksiyonu.
    :param expiry_minutes: Verinin kaç dakika "taze" sayılacağı.
    :return: Önbellekten veya API'den alınan veri.
    """
    cache_path = os.path.join(CACHE_DIR, cache_file_name)
    
    # 1. Önbellek dosyasını kontrol et
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            
            # 2. Veri taze mi diye kontrol et
            if datetime.now() < cached_time + timedelta(minutes=expiry_minutes):
                print(f"✅ Önbellekten okundu: {cache_file_name} (Taze)")
                return cache_data['data']
            else:
                print(f"⚠️ Önbellek bayatlamış: {cache_file_name}")
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"❌ Önbellek okuma hatası: {e}. Veri yeniden çekilecek.")

    # 3. Veri taze değilse veya önbellek yoksa, yeniden çek
    print(f"🔄 Veri yeniden çekiliyor: {cache_file_name}...")
    new_data = fetch_function()
    
    # 4. Yeni veriyi zaman damgasıyla birlikte önbelleğe kaydet
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            payload = {
                'timestamp': datetime.now().isoformat(),
                'data': new_data
            }
            json.dump(payload, f, ensure_ascii=False, indent=4)
        print(f"💾 Yeni veri önbelleğe kaydedildi: {cache_file_name}")
    except Exception as e:
        print(f"❌ Önbellek yazma hatası: {e}")

    return new_data