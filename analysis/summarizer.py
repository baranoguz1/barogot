import os
import json
from datetime import datetime
import google.generativeai as genai
import config

def get_summarization_prompt(all_news):
    """Haber içeriklerinden Gemini için bir prompt oluşturur."""
    prompt_header = """
Aşağıda çeşitli haber kaynaklarından alınmış haber başlıkları ve içerikleri bulunmaktadır. 
Bu haberleri analiz ederek günün en önemli 5 olayını belirle. 
Analizini yaparken şu adımları izle:
1.  Birbiriyle ilişkili haberleri grupla.
2.  Her önemli olay için Türkçe, dikkat çekici ve SEO uyumlu bir başlık oluştur. Başlıklar tırnak içinde olmalı.
3.  Her başlık için, olayın en önemli detaylarını içeren, 30-50 kelimelik kısa bir özet metni yaz.
4.  Her olayın ne zaman gerçekleştiğini veya ne zaman haber yapıldığını belirterek bir zaman bilgisi ekle.
5.  Sonucunu, yalnızca aşağıdaki JSON formatında, başka hiçbir ek metin olmadan ver:
    {
      "gunun_ozeti": [
        {
          "baslik": "Örnek Başlık 1",
          "ozet": "Bu bölümde olayın kısa ve özeti yer alacak.",
          "zaman": "YYYY-MM-DDTHH:MM:SS"
        },
        {
          "baslik": "Örnek Başlık 2",
          "ozet": "Bu bölümde diğer önemli olayın özeti yer alacak.",
          "zaman": "YYYY-MM-DDTHH:MM:SS"
        }
      ]
    }

İşte analiz edilecek haberler:
"""
    haber_metinleri = "\n\n".join(
        [f"Haber Başlığı: {haber.get('title', 'Başlık Yok')}\nİçerik: {haber.get('content', 'İçerik Yok')}" for haber in all_news]
    )
    return prompt_header + haber_metinleri

def generate_abstractive_summary(all_news, num_events=5):
    """Verilen haberleri Google Gemini kullanarak özetler."""
    print("📰 Günün önemli olayları yapay zeka ile özetleniyor...")
    
    # Varsayılan hata durumu yanıtı
    default_error_response = {
        "gunun_ozeti": [{
            "baslik": "Günün Özeti Alınamadı",
            "ozet": "Haberler özetlenirken bir sorun oluştu. API limitleri veya bağlantı sorunları olabilir.",
            "zaman": datetime.now(config.TZ) # Çökmeyi engellemek için datetime nesnesi olarak bırakılır
        }]
    }

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ Gemini API anahtarı (GEMINI_API_KEY) bulunamadı.")
            return default_error_response

        genai.configure(api_key=api_key)
        
        print("Özetleme için en yeni 20 haberin içeriği çekiliyor...")
        haber_icerikleri = [haber for haber in all_news if haber.get('content')]
        
        if not haber_icerikleri:
            print("⚠️ Özetlenecek yeterli haber içeriği bulunamadı.")
            return default_error_response

        prompt = get_summarization_prompt(haber_icerikleri[:20]) # İlk 20 haberi kullan
        
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        
        # Yanıtın JSON formatında olduğundan emin ol ve temizle
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "")
        summary_data = json.loads(cleaned_response_text)
        
        # API'den gelen zaman bilgisini datetime nesnesine çevir
        for item in summary_data.get("gunun_ozeti", []):
            if isinstance(item.get("zaman"), str):
                item["zaman"] = datetime.fromisoformat(item["zaman"])

        print(f"✅ Önemli olaylar başarıyla özetlendi: {len(summary_data.get('gunun_ozeti', []))} başlık bulundu.")
        return summary_data

    except Exception as e:
        print(f"❌ Gemini API hatası veya JSON parse hatası: {e}")
        return default_error_response
    

def generate_weather_commentary(hourly_forecast):
    """Saatlik hava durumu verilerinden Gemini kullanarak bir yorum oluşturur."""
    print("🌤️ Hava durumu yapay zeka ile yorumlanıyor...")
    
    # Gemini'ye gönderilecek talimatı (prompt) hazırlama
    prompt_header = """
    Aşağıda İstanbul için saatlik hava durumu verileri bulunmaktadır. Bu verilere dayanarak, kullanıcıya hitap eden, samimi ve kısa bir hava durumu yorumu yaz. 
    - Genel durumdan bahset (örn: "Bugün hava genel olarak güneşli olacak...").
    - Akşama doğru bir değişiklik varsa belirt (örn: "...ancak akşama doğru hava serinliyor.").
    - Giyilebilecek kıyafetler hakkında kısa bir tavsiye ver.
    - Yorumun 30-40 kelimeyi geçmesin ve tek bir paragraf olsun.

    İşte veriler:
    """
    
    # Hava durumu verilerini okunabilir bir metne dönüştürme
    forecast_text = "\n".join(
        [f"- Saat {item[0]}: Sıcaklık {item[1]:.0f}°C, Durum: {item[2]}" for item in hourly_forecast]
    )
    
    full_prompt = prompt_header + forecast_text
    
    try:
        # Bu kısım generate_abstractive_summary fonksiyonundakine benzer şekilde
        # Gemini API anahtarını kullanarak API'yi çağırır.
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Hava durumu yorumu için API anahtarı bulunamadı."

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(full_prompt)
        
        print("✅ Hava durumu yorumu başarıyla oluşturuldu.")
        return response.text.strip()

    except Exception as e:
        print(f"❌ Hava durumu yorumu oluşturulurken hata: {e}")
        return "Şu an için hava durumu yorumu yapılamıyor."
    

# analysis/summarizer.py içine eklenecek yeni fonksiyon

def generate_daily_briefing(context):
    """Tüm verileri kullanarak güne dair genel bir özet oluşturur."""
    print("📰 Günlük özet raporu oluşturuluyor...")
    try:
        # Gemini'ye gönderilecek verileri hazırlama
        weather_info = context.get('weather_commentary', 'Hava durumu verisi yok.')
        headlines = context.get('top_headlines', [])
        headline_titles = [h['baslik'] for h in headlines]
        dolar_rate = context.get('exchange_rates', {}).get('USD', 'bilinmiyor')

        prompt = f"""
        Aşağıdaki verileri kullanarak, bir haber spikeri gibi samimi ve bilgilendirici bir tonda "Günün Özeti" raporu oluştur. 
        Rapor kısa ve ilgi çekici olsun. İşte bugünün verileri:
        - Hava Durumu Yorumu: "{weather_info}"
        - Önemli Haber Başlıkları: {', '.join(headline_titles)}
        - Dolar Kuru: {dolar_rate} TRY

        Bu bilgilere dayanarak 2-3 cümlelik bir açılış paragrafı yaz.
        """
        
        # Gemini API çağrısı (generate_weather_commentary fonksiyonundakine benzer)
        # ... (API anahtarını alıp modeli çağırma kısmı) ...
        # response = model.generate_content(prompt)
        # return response.text.strip()
        
        # Örnek statik cevap (API entegrasyonu yapılana kadar)
        # Bu kısmı kendi Gemini API çağrınızla değiştirin.
        return (f"Günaydın! Bugün hava {weather_info.lower().split(' ')[-1]} görünüyor. "
                f"Piyasalarda Dolar/TL kuru {dolar_rate} seviyesinde güne başlarken, "
                f"gündemin en önemli başlığı '{headline_titles[0]}' olarak öne çıkıyor. İşte günün detayları...")

    except Exception as e:
        print(f"❌ Günlük özet oluşturulurken hata: {e}")
        return None