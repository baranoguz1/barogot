import os
import openai

# OpenAI istemcisini API anahtarını ortam değişkeninden alarak başlatın
# GitHub Actions'da bu anahtar zaten ayarlı. Lokalde çalışmak için siz de ayarlamalısınız.
# Not: Ortam değişkeninin adı "OPENAI_API_KEY" olmalıdır.
try:
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except openai.OpenAIError as e:
    print(f"OpenAI istemcisi başlatılamadı. API anahtarınızı kontrol edin. Hata: {e}")
    client = None

def generate_abstractive_summary(news_items, num_events=5):
    """
    Verilen haber listesinden yola çıkarak günün önemli olaylarını OpenAI GPT ile özetler.
    'news_items' her biri 'title' ve 'snippet' içeren bir dictionary listesi olmalıdır.
    """
    if not client or not client.api_key:
        print("⚠️ OpenAI API anahtarı 'OPENAI_API_KEY' olarak ayarlanmamış veya istemci başlatılamadı.")
        return ["OpenAI API anahtarı yapılandırılmadığı için özet oluşturulamadı."]

    # Yapay zekaya gönderilecek metinleri hazırlayalım
    # Her haber için başlık ve kısa içerik birleştirilir
    texts_to_process = []
    for item in news_items:
        texts_to_process.append(f"Haber Başlığı: {item['title']}\nÖzet: {item['snippet']}")
    
    full_text = "\n\n---\n\n".join(texts_to_process)

    # API limitlerini aşmamak için metni güvenli bir uzunlukta tutalım (yaklaşık 3000 kelime)
    max_length = 15000 
    if len(full_text) > max_length:
        full_text = full_text[:max_length]

    # Modele gönderilecek talimat (prompt)
    system_prompt = f"""
Sen Türkiye gündemini analiz eden uzman bir haber editörüsün.
Sana sunulan haber başlıkları ve özetlerinden yola çıkarak, günün en önemli {num_events} olayını tespit et.
Her olayı, tek bir cümleyle, net, tarafsız ve bilgilendirici bir şekilde özetle.
Cevabını maddeleme veya numaralandırma olmadan, her bir olay ayrı bir satırda olacak şekilde ver.
Örnek:
Ekonomi bakanı yeni vergi düzenlemesi hakkında açıklamalarda bulundu.
Marmara Bölgesi'nde beklenen şiddetli yağış için uyarı yapıldı.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # En yeni ve yetenekli model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_text}
            ],
            max_tokens=300,  # Özetin toplam uzunluğu
            temperature=0.6,  # Dengeli ve tutarlı sonuçlar için
        )
        summary = response.choices[0].message.content.strip()
        # Cevabı satırlara bölerek temiz bir liste haline getir
        return [line.strip().lstrip('- ').strip() for line in summary.split('\n') if line.strip()]
    
    except Exception as e:
        print(f"❌ OpenAI API hatası: {e}")
        return [f"Yapay zeka ile özetleme sırasında bir hata oluştu: {e}"]