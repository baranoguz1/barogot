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
    Eğer yeniden çekme işlemi başarısız olursa (None dönerse), süresi dolmuş olsa bile
    önbellekteki son geçerli veriyi döndürür. Boş liste ([]) gibi sonuçları
    başarılı kabul eder ve önbelleğe kaydeder.
    """
    cache_path = os.path.join(CACHE_DIR, cache_file_name)
    stale_data = None 

    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            stale_data = cache_data.get('data')
            cached_time = datetime.fromisoformat(cache_data['timestamp'])

            if datetime.now() < cached_time + timedelta(minutes=expiry_minutes):
                print(f"✅ Önbellekten okundu: {cache_file_name} (Taze)")
                return stale_data
            else:
                print(f"⚠️ Önbellek bayatlamış: {cache_file_name}. Yeniden çekilecek.")
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"❌ Önbellek okuma hatası: {e}. Veri yeniden çekilecek.")
            stale_data = None

    print(f"🔄 Veri yeniden çekiliyor: {cache_file_name}...")
    new_data = fetch_function()

    # DÜZELTME: 'if new_data:' yerine 'if new_data is not None:' kullanılıyor.
    # Bu, boş liste [] veya boş string "" gibi sonuçların geçerli kabul edilmesini sağlar.
    if new_data is not None:
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
            return new_data
            
    if stale_data is not None:
        print(f"‼️ API/Çekme hatası! Bayatlamış önbellek kullanılıyor: {cache_file_name}")
        return stale_data

    print(f"❌ Veri çekilemedi ve önbellekte de veri yok: {cache_file_name}")
    return None