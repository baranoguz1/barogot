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
    # DEĞİŞİKLİK BURADA: 'title' yerine 'baslik' kullanıyoruz.
    main_headline = context['top_headlines'][0]['baslik'] if context.get('top_headlines') else "gündemde önemli bir gelişme yok."
    
    # Döviz kuru bilgisini alalım
    exchange_rate_info = ""
    rates = context.get('exchange_rates')
    if rates and 'USDTRY' in rates:
        usd_rate_value = rates['USDTRY']
        if usd_rate_value:
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

def generate_comparative_news_analysis(news_groups):
    """
    Gruplanmış haber listelerini alıp her bir grup için karşılaştırmalı 
    bir yapay zeka analizi üretir.

    Args:
        news_groups (list): İçinde haber listeleri olan bir liste 
                           (group_similar_news fonksiyonunun çıktısı).

    Returns:
        list: Her bir öğesi analiz edilmiş bir grup olan sözlük listesi.
              Örnek: [{'topic': 'Olayın konusu', 'analysis': 'Analiz metni...', 'original_news': [...]}]
    """
    # Gerekli kütüphaneyi fonksiyon içinde import ediyoruz
    import google.generativeai as genai 
    
    analysis_results = []
    print("\n--- Karşılaştırmalı Haber Analizi Başladı ---")
    
    # Sadece birden fazla haber içeren grupları analiz et
    groups_to_analyze = [g for g in news_groups if len(g) > 1]
    
    if not groups_to_analyze:
        print("⚠️ Analiz edilecek yeterli haber grubu bulunamadı.")
        print("--- Karşılaştırmalı Haber Analizi Tamamlandı ---")
        return []

    print(f"Analiz edilecek {len(groups_to_analyze)} adet haber grubu bulundu.")

    for i, group in enumerate(groups_to_analyze):
        headlines_text = "\n".join([f"- {item.get('source') or item.get('feed_title', 'Bilinmeyen Kaynak')}: {item.get('title')}" for item in group])
        
        prompt = f"""
        Sen bir uzman haber analistisin. Görevin, farklı haber kaynaklarından gelen ve aynı olayla ilgili görünen aşağıdaki haber başlıklarını analiz etmektir.

        İşte analiz etmen gereken başlıklar:
        {headlines_text}

        Bu başlıklara dayanarak senden istediğim analiz şu şekilde olmalı:
        1.  **Ana Konu:** Bu haberlerin ortak konusunu tek ve net bir cümleyle belirt.
        2.  **Karşılaştırmalı Analiz:** Kaynakların haberi sunuş biçimindeki olası farkları veya benzerlikleri vurgula. Örneğin, bir kaynak daha resmi bir dil kullanırken diğeri daha dikkat çekici bir başlık mı atmış? Vurgulanan farklı detaylar var mı?
        3.  **Genel Özet:** Tüm bu bilgileri birleştirerek olayı özetleyen, tarafsız ve bilgilendirici, 2-3 cümlelik bir paragraf yaz.

        Lütfen cevabını sadece ve sadece Markdown formatında, başlıkları kullanarak (`### Ana Konu`, `### Karşılaştırmalı Analiz`, `### Genel Özet`) yapılandır. Başka hiçbir ek açıklama yapma.
        """
        
        try:
            print(f"Grup {i+1}/{len(groups_to_analyze)} Gemini'ye analiz için gönderiliyor...")
            
            # --- DÜZELTME BURADA YAPILDI ---
            # Hatalı 'from config import model' satırı kaldırıldı.
            # Model, doğrudan burada, ihtiyaç anında tanımlanıyor.
            model = genai.GenerativeModel('gemini-1.5-flash-latest') 
            response = model.generate_content(prompt)
            analysis_text = response.text
            
            analysis_results.append({
                'analysis': analysis_text,
                'original_news': group
            })
            print(f"✅ Grup {i+1} analizi başarıyla tamamlandı.")

        except Exception as e:
            # Hata mesajını daha anlaşılır hale getiriyoruz
            print(f"❌ Grup {i+1} analizi sırasında bir hata oluştu: {e}")

    print("--- Karşılaştırmalı Haber Analizi Tamamlandı ---")
    return analysis_results