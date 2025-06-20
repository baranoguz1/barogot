from flask import Flask, render_template, request, jsonify
import json
import os
from dotenv import load_dotenv

# .env dosyasını yükle
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print("✅ .env dosyası başarıyla yüklendi.")
else:
    print("⚠️ .env dosyası bulunamadı, ortam değişkenleri kullanılacak.")

import config
import google.generativeai as genai

# Yeniden kullanılabilir fonksiyonlarımızı import ediyoruz
from main import gather_all_data 
from analysis.summarizer import answer_user_query 

# Başlangıçta Gemini API'sini yapılandır
try:
    # API anahtarı yoksa, config dosyası zaten bir uyarı basacaktır.
    # Burada sadece yapılandırmayı deniyoruz.
    if config.GEMINI_API_KEY:
        genai.configure(api_key=config.GEMINI_API_KEY)
        print("✅ Gemini API başarıyla yapılandırıldı.")
    else:
        # Bu, sunucunun kapanmasını engeller ama loglarda görünür.
        print("❌ UYARI: GEMINI_API_KEY bulunamadığı için Gemini fonksiyonları çalışmayacak.")
except Exception as e:
    print(f"❌ UYARI: Gemini API yapılandırılırken bir hata oluştu: {e}")


app = Flask(__name__)

# Bütün veriyi sunucu başlarken bir kere çekip önbelleğe alalım.
print("⏳ Uygulama başlatılıyor, ilk veri seti çekiliyor... (Bu işlem biraz sürebilir)")
CACHED_CONTEXT = gather_all_data()
# Veri çekildikten sonra, olası eksik 'fixtures' anahtarı için varsayılan değer ekleyelim.
CACHED_CONTEXT.setdefault('fixtures', {})
print("✅ Veri seti başarıyla yüklendi ve önbelleğe alındı.")


@app.route('/')
def home():
    """Ana sayfayı, önbelleğe alınan gerçek verilerle gösterir."""
    return render_template('haberler_template.html', **CACHED_CONTEXT)

@app.route('/ask', methods=['POST'])
def ask():
    """Kullanıcının sorusunu alan ve AI'dan cevap üreten API."""
    user_question = request.json.get('question')
    if not user_question:
        return jsonify({'answer': 'Lütfen bir soru girin.'}), 400
    
    # Gerçek AI fonksiyonunu, önbellekteki context ile çağırıyoruz
    ai_answer = answer_user_query(CACHED_CONTEXT, user_question)
    
    return jsonify({'answer': ai_answer})

if __name__ == '__main__':
    # Bu blok sadece yerel makinede `python app.py` çalıştırıldığında kullanılır.
    # PythonAnywhere bu kısmı kullanmaz.
    app.run(host='0.0.0.0', port=5000, debug=True)