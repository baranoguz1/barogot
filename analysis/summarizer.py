import os
import google.generativeai as genai
import logging
import json
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

def generate_abstractive_summary(news_content_for_prompt):
    """
    Verilen haber içeriklerinden Gemini API kullanarak yapılandırılmış 
    bir JSON formatında günün önemli başlıklarını ve özetlerini oluşturur.
    """
    model = get_gemini_model()
    if not model or not news_content_for_prompt:
        return [] 

    prompt = f"""Aşağıdaki haber başlıkları ve özetlerinden yola çıkarak günün en önemli 5 olayını belirle.
Sonucu, başka hiçbir açıklama veya metin eklemeden, yalnızca ve yalnızca aşağıdaki JSON formatında bir liste olarak ver:
[
  {{
    "baslik": "Olayın Başlığı 1",
    "ozet": "Olayın tek cümlelik net özeti."
  }},
  {{
    "baslik": "Olayın Başlığı 2",
    "ozet": "Olayın tek cümlelik net özeti."
  }}
]

Haber İçerikleri:
{news_content_for_prompt}
"""
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, Exception) as e:
        logging.error(f"Soyut özet JSON'u işlenirken hata: {e}")
        return []

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
    # Bu fonksiyon doğru görünüyor, olduğu gibi bırakabiliriz.
    model = get_gemini_model()
    if not model: return "Yapay zeka modeli başlatılamadığı için günlük brifing oluşturulamadı."
    weather_commentary = context.get('weather_commentary', 'bilgi yok')
    top_headlines_data = context.get('top_headlines', [])
    exchange_rates = context.get('exchange_rates', {})
    
    # top_headlines bir liste olduğu için metne çeviriyoruz
    top_headlines_text = ""
    if top_headlines_data:
        top_headlines_text = "\n".join([f"- {h['baslik']}: {h['ozet']}" for h in top_headlines_data])

    prompt = f"""Bir radyo spikeri gibi, aşağıdaki bilgileri kullanarak akıcı ve enerjik bir dille gün başlangıcı için kısa bir anons metni hazırla. Her bölümü doğal geçişlerle birbirine bağla.

Hava Durumu Bilgisi:
{weather_commentary}

Günün Öne Çıkan Gelişmeleri:
{top_headlines_text}

Piyasalarda son durum:
{", ".join([f"{k.replace('TRY','')} {v}" for k, v in exchange_rates.items()])}
"""
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Günlük brifing oluşturulurken hata: {e}")
        return "Günlük brifing oluşturulurken bir hata meydana geldi."

def generate_comparative_news_analysis(group):
    """
    Benzer haber başlıklarını karşılaştırarak tek bir olay analizi metni oluşturur.
    Bu versiyon, daha esnek bir prompt ve daha sağlam bir ayrıştırma mantığı içerir.
    """
    if not group or isinstance(group[0], str):
        logging.warning("generate_comparative_news_analysis, hatalı veri türüyle çağrıldı. İşlem atlanıyor.")
        return []

    model = get_gemini_model()
    if not model:
        return []

    logging.info(f"--- Karşılaştırmalı Haber Analizi Başladı (Versiyon 2) ---")
    
    analysis_results = []

    try:
        headlines_text = "\n".join([f"- Başlık: {item.get('title')} (Kaynak: {item.get('source') or 'Bilinmiyor'})" for item in group])
        
        # Daha basit ve net bir prompt
        prompt = f"""Aşağıda aynı konu hakkında farklı kaynaklardan gelen haber başlıkları listelenmiştir:
{headlines_text}

Bu başlıklara dayanarak, olayı özetleyen SEO uyumlu bir başlık ve 2-3 cümlelik tarafsız bir analiz metni oluştur.
Cevabını formatlarken, ilk satıra SADECE başlığı yaz, ardından bir satır boşluk bırak ve sonraki satırlara analiz metnini yaz. Başka hiçbir şey ekleme.
"""
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # Daha esnek ayrıştırma mantığı
        response_text = response.text.strip()
        lines = response_text.split('\n')
        
        # Eğer cevap en az iki satırdan oluşuyorsa
        if len(lines) >= 2:
            seo_baslik = lines[0].strip()
            # Kalan tüm satırları analiz metni olarak birleştir
            olay_ozeti = "\n".join(lines[1:]).strip()
            
            # Eğer özet boşsa, tüm metni özet olarak al ve varsayılan bir başlık kullan
            if not olay_ozeti:
                olay_ozeti = seo_baslik
                seo_baslik = group[0].get('title', 'Haber Analizi')
        else: # Eğer cevap tek satırsa
            olay_ozeti = response_text
            seo_baslik = group[0].get('title', 'Haber Analizi')

        analysis_results.append({
            'seo_baslik': seo_baslik,
            'olay_ozeti': olay_ozeti,
            'haberler': group
        })

    except Exception as e:
        logging.error(f"Karşılaştırmalı analiz sırasında bir hata oluştu: {e}")

    return analysis_results

def generate_dynamic_headline_for_trends(trends_list):
    # Bu fonksiyon doğru görünüyor, olduğu gibi bırakabiliriz.
    model = get_gemini_model()
    if not model or not trends_list:
        return "Gündem" 
    try:
        trends_text = ", ".join(trends_list)
        prompt = f"""Aşağıdaki gündemdeki kelimelere bakarak, "İşte Gündemdeki En Çok Konuşulanlar" gibi genel bir ifade yerine, bu kelimelerin ortak temasını yansıtan daha yaratıcı ve ilgi çekici tek bir başlık cümlesi oluştur. Sadece başlığı yaz.

Kelimeler: {trends_text}"""
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip().replace('"', '')
    except Exception as e:
        logging.error(f"Trend başlığı oluşturulurken hata: {e}")
        return "Gündem"