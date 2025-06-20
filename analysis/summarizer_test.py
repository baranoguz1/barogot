import google.generativeai as genai
import json
import logging

# Hataları loglamak için temel yapılandırma
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_abstractive_summary(news_content):
    """
    Verilen haber içeriklerinden Gemini API kullanarak özet bir JSON çıktısı oluşturur.
    Özet, günün en önemli olaylarını içerir.
    """
    if not news_content:
        logging.warning("Özetlenecek haber içeriği bulunamadı.")
        return None

    prompt = f"""
    Aşağıdaki haber içeriklerini analiz et. Bu içeriklerden günün en önemli 5 olayını belirle.
    Her olay için bir başlık (baslik), olayın kısa bir özeti (ozet) ve olayın geçtiği zaman dilimini (zaman, örneğin 'Sabah', 'Öğle', 'Akşam' veya 'Günün Gelişmesi') belirle.
    Sonucu, yalnızca ve yalnızca aşağıdaki JSON formatında bir liste olarak ver. Başka hiçbir metin ekleme.

    Format:
    [
      {{
        "baslik": "Örnek Başlık 1",
        "ozet": "Örnek özet 1",
        "zaman": "Örnek Zaman Dilimi 1"
      }},
      {{
        "baslik": "Örnek Başlık 2",
        "ozet": "Örnek özet 2",
        "zaman": "Örnek Zaman Dilimi 2"
      }}
    ]

    Haber İçerikleri:
    {news_content}
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        # Bazen model, JSON'u markdown kod bloğu içinde döndürebilir, bunu temizleyelim.
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_response)
    except Exception as e:
        logging.error(f"Gemini API ile özet oluşturulurken hata oluştu: {e}")
        return None

def generate_weather_commentary(hourly_data):
    """
    Saatlik hava durumu verilerinden yola çıkarak gün için kısa, sohbet havasında bir yorum oluşturur.
    """
    if not hourly_data:
        return "Hava durumu verileri alınamadı."

    prompt = f"""
    Aşağıdaki saatlik hava durumu verilerine bakarak gün için kısa, samimi ve bilgilendirici bir hava durumu yorumu yap.
    Sıcaklık, hissedilen sıcaklık ve hava durumunu (örneğin, 'Parçalı Bulutlu') dikkate al.
    Örnek: 'Bugün hava parçalı bulutlu ve sıcaklıklar 25°C civarında seyredecek. Akşama doğru serinleyebilir, yanınıza bir hırka almayı unutmayın!'
    
    Veriler:
    {json.dumps(hourly_data, indent=2, ensure_ascii=False)}
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini API ile hava durumu yorumu oluşturulurken hata oluştu: {e}")
        return "Bugün için hava durumu yorumu yapılamadı."

def generate_daily_briefing(context):
    """
    Günün ana bağlamını (hava durumu, ana haber, döviz) kullanarak spiker tadında bir açılış metni oluşturur.
    """
    if not context.get('weather_commentary') or not context.get('top_headlines'):
        return "Günün özeti için yeterli veri bulunamadı."

    weather = context.get('weather_commentary', 'Hava durumu bilgisi yok.')
    main_headline = context['top_headlines'][0]['title'] if context.get('top_headlines') else "gündemde önemli bir gelişme yok."
    
    # Döviz kuru bilgisini alalım (DÜZELTİLMİŞ BÖLÜM)
    exchange_rate_info = ""
    rates = context.get('exchange_rates')
    if rates and 'USDTRY' in rates:
        usd_rate_value = rates['USDTRY']
        if usd_rate_value:
             # Değeri formatlayarak string'e ekleyelim
             exchange_rate_info = f"dolar kuru {usd_rate_value:.2f} seviyelerinden işlem görüyor."

    prompt = f"""
    Aşağıdaki bilgileri kullanarak bir haber bülteni sunucusu gibi güne başlangıç için kısa ve etkileyici bir açılış paragrafı oluştur.
    - Hava Durumu Yorumu: "{weather}"
    - Günün Ana Başlığı: "{main_headline}"
    - Döviz Bilgisi: "{exchange_rate_info}"
    
    Paragraf bilgilendirici ve akıcı olsun.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini API ile günlük brifing oluşturulurken hata: {e}")
        return "Günün özetini hazırlarken bir sorun oluştu."


def generate_dynamic_headline_for_trends(trends):
    """
    Twitter trend listesinden en baskın temayı bularak dinamik bir başlık oluşturur.
    """
    if not trends:
        return "🔥 Türkiye Gündemi"

    # Hatalı satırı kaldırıyoruz ve 'trends' değişkenini doğrudan kullanıyoruz.
    
    prompt = f"""
    Aşağıdaki Twitter trend listesini analiz et. Bu listeyi özetleyen, emoji içeren, merak uyandırıcı ve kısa tek bir başlık oluştur.
    Örnek: 'Gündem siyaset ve spor arasında gidip geliyor ⚽🗳️'
    
    Trendler:
    {', '.join(trends)} 
    """ # <--- DEĞİŞİKLİK BURADA
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini API ile trend başlığı oluşturulurken hata: {e}")
        return "🔥 Türkiye Gündemi"

def generate_contextual_activity_suggestion(weather_commentary, events):
    """
    Hava durumuna ve mevcut etkinliklere göre kişisel bir aktivite önerisi sunar.
    """
    if not weather_commentary or not events:
        return "" # Eğer veri yoksa bu bölümü boş bırakmak daha iyi olabilir.

    event_list = [f"'{event['title']}' ({event.get('type', 'Etkinlik')})" for event in events[:3]] # İlk 3 etkinlik yeterli

    prompt = f"""
    Bir kullanıcıya gün için aktivite önereceksin. Aşağıdaki bilgileri kullan:
    - Güncel Hava Durumu Yorumu: "{weather_commentary}"
    - Şehirdeki Bazı Etkinlikler: {', '.join(event_list)}

    Bu bilgilere dayanarak, hava durumuyla etkinlikleri mantıklı bir şekilde birleştiren samimi bir öneri cümlesi yaz.
    Örnek: 'Hava bugün güneşli görünüyor, bu fırsatı değerlendirip 'Açık Hava Konseri' gibi bir etkinliğe katılmaya ne dersin?'
    ya da 'Yağmurlu bir gün kapıda, belki de 'Sanat Galerisi' gezmek için harika bir zamandır.'
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini API ile aktivite önerisi oluşturulurken hata: {e}")
        return "Günün keyfini çıkarın!"