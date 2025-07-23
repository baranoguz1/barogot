import os
import google.generativeai as genai
import logging
from dotenv import load_dotenv

# Temel yapılandırma
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Gemini API anahtarını al ve yapılandır
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logging.warning("GEMINI_API_KEY ortam değişkeni bulunamadı. Yapay zeka fonksiyonları çalışmayabilir.")

# Güvenlik ayarları - Daha az kısıtlayıcı
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

def get_gemini_model():
    """Gemini modelini döndürür, anahtar yoksa None döner."""
    if not GEMINI_API_KEY:
        return None
    return genai.GenerativeModel('gemini-1.5-flash-latest')

# ... (dosyanın geri kalan fonksiyonları aynı kalabilir)

def generate_abstractive_summary(news_content_for_prompt):
    model = get_gemini_model()
    if not model or not news_content_for_prompt:
        return None
    try:
        prompt = f"""Aşağıdaki haber başlıkları ve özetlerinden yola çıkarak, günün en önemli 5 olayını maddeler halinde (en önemliden başlayarak) ve her birinin altına tek cümlelik bir açıklama ekleyerek özetle. Cevabın sadece bu 5 maddeden oluşsun, başka hiçbir ek metin, başlık veya giriş cümlesi içermesin:

{news_content_for_prompt}
"""
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Soyut özet oluşturulurken hata: {e}")
        return None

def generate_weather_commentary(weather_data):
    model = get_gemini_model()
    if not model or not weather_data:
        return "Hava durumu verisi alınamadı."
    try:
        prompt = f"""Aşağıdaki saatlik hava durumu verilerine bakarak, bir spikerin sunacağı şekilde, sade ve anlaşılır bir dille önümüzdeki 8 saati özetleyen kısa (2-3 cümlelik) bir metin oluştur. Vurgulanması gerekenler: hissedilen sıcaklık, yağış ihtimali ve rüzgar durumu.
Veri: {weather_data}"""
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Hava durumu yorumu oluşturulurken hata: {e}")
        return "Hava durumu yorumu oluşturulurken bir sorun oluştu."

def generate_daily_briefing(context):
    model = get_gemini_model()
    if not model:
        return "Yapay zeka modeli başlatılamadığı için günlük brifing oluşturulamadı."
    
    weather_commentary = context.get('weather_commentary', 'bilgi yok')
    top_headlines = context.get('top_headlines', 'bilgi yok')
    exchange_rates = context.get('exchange_rates', {})
    
    # Sadece mevcut verilerle bir prompt oluştur
    prompt_parts = [
        "Bir radyo spikeri gibi, aşağıdaki bilgileri kullanarak akıcı ve enerjik bir "
        "dille gün başlangıcı için kısa bir anons metni hazırla. Her bölümü doğal geçişlerle birbirine bağla."
    ]
    if weather_commentary and weather_commentary != 'bilgi yok':
        prompt_parts.append(f"\n\nHava Durumu Bilgisi:\n{weather_commentary}")
    if top_headlines and top_headlines != 'bilgi yok':
        prompt_parts.append(f"\n\nGünün Öne Çıkan Gelişmeleri:\n{top_headlines}")
    if exchange_rates:
        rates_text = ", ".join([f"{k.replace('TRY','')} {v}" for k, v in exchange_rates.items()])
        prompt_parts.append(f"\n\Piyasalarda son durum:\n{rates_text}")
        
    if len(prompt_parts) <= 1:
        return "Günlük brifing için yeterli veri bulunamadı."
        
    prompt = "".join(prompt_parts)
    
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Günlük brifing oluşturulurken hata: {e}")
        return "Günlük brifing oluşturulurken bir hata meydana geldi."

def generate_comparative_news_analysis(group):
    """
    Benzer haber başlıklarını karşılaştırarak tek bir olay analizi metni oluşturur.
    """
    # =========================================================================
    # ===== HATAYI KAYNAĞINDA ENGELLEYEN YENİ GÜVENLİK KONTROLÜ =====
    # =========================================================================
    # Eğer 'group' boşsa veya grubun ilk elemanı bir metin (string) ise, bu, 
    # fonksiyonun yanlış veri ile çağrıldığı anlamına gelir. Hata vermeden boş dön.
    if not group or isinstance(group[0], str):
        logging.warning("generate_comparative_news_analysis, hatalı veri türüyle çağrıldı. İşlem atlanıyor.")
        return []
    # =================== GÜVENLİK KONTROLÜ SONU ===================

    model = get_gemini_model()
    if not model:
        return []

    logging.info(f"--- Karşılaştırmalı Haber Analizi Başladı ---")
    logging.info(f"Analiz edilecek {len(group)} adet haber grubu bulundu.")
    
    analysis_results = []

    try:
        # Gelen grubun, her bir haberin bir sözlük olduğu bir liste olduğunu varsayıyoruz.
        headlines_text = "\n".join([f"- {item.get('source') or item.get('feed_title', 'Bilinmeyen Kaynak')}: {item.get('title')}" for item in group])
        
        prompt = f"""Aşağıda aynı konu hakkında farklı kaynaklardan gelen haber başlıkları listelenmiştir. Bu başlıkları analiz ederek:
1. Bu olayın ne olduğunu tek ve kısa bir cümle ile özetle.
2. Olaydaki anahtar kişi, kurum veya konseptleri (en fazla 3 adet) virgülle ayırarak belirt.
3. Tüm başlıkları göz önünde bulundurarak, olayı en iyi yansıtan, dikkat çekici ve SEO uyumlu tek bir ana başlık oluştur.

Cevabını, aşağıdaki gibi '|||' ayıracını kullanarak formatla. Başka hiçbir açıklama ekleme.
Özet Cümle ||| Anahtar Kelimeler ||| SEO Uyumlu Başlık

Haber Başlıkları:
{headlines_text}
"""
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # Yanıtı işle ve sözlük olarak biçimlendir
        parts = response.text.strip().split('|||')
        if len(parts) == 3:
            analysis_results.append({
                'olay_ozeti': parts[0].strip(),
                'anahtar_kelimeler': [k.strip() for k in parts[1].split(',')],
                'seo_baslik': parts[2].strip(),
                'haberler': group
            })
        else:
            logging.warning(f"Model yanıtı beklenmedik formatta: {response.text.strip()}")

    except Exception as e:
        logging.error(f"Karşılaştırmalı analiz sırasında bir hata oluştu: {e}")

    return analysis_results

def generate_dynamic_headline_for_trends(trends_list):
    model = get_gemini_model()
    if not model or not trends_list:
        return "Gündem" # Varsayılan başlık
    try:
        trends_text = ", ".join(trends_list)
        prompt = f"""Aşağıdaki gündemdeki kelimelere bakarak, "İşte Gündemdeki En Çok Konuşulanlar" gibi genel bir ifade yerine, bu kelimelerin ortak temasını yansıtan daha yaratıcı ve ilgi çekici tek bir başlık cümlesi oluştur. Sadece başlığı yaz.

Kelimeler: {trends_text}"""
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip().replace('"', '')
    except Exception as e:
        logging.error(f"Trend başlığı oluşturulurken hata: {e}")
        return "Gündem"