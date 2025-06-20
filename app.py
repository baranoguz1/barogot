from flask import Flask, render_template, request, jsonify
import config
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# .env dosyasını yükle
# Bu satırlar, .env dosyasındaki değişkenleri okuyup sisteme yükler.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print("✅ .env dosyası yüklendi.")
else:
    print("⚠️ .env dosyası bulunamadı, ortam değişkenleri kullanılacak.")

# main.py'den yeniden kullanılabilir veri toplama fonksiyonumuzu import ediyoruz
from main import gather_all_data 
# summarizer.py'den yeni chatbot AI fonksiyonumuzu import ediyoruz
from analysis.summarizer import answer_user_query 

# Başlangıçta Gemini API'sini yapılandır
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
except AttributeError as e:
    print(f"❌ HATA: config.py dosyasında GEMINI_API_KEY bulunamadı. Lütfen kontrol edin.")
    exit()


app = Flask(__name__)

# Bütün veriyi her istekte çekmek çok yavaş olur. 
# Bu yüzden sunucu başlarken veriyi bir kere çekip bir değişkende (önbellekte) tutalım.
print("🚀 Uygulama başlatılıyor, ilk veri seti çekiliyor... (Bu işlem biraz sürebilir)")
CACHED_CONTEXT = gather_all_data()
print("✅ Veri seti başarıyla yüklendi ve önbelleğe alındı.")


@app.route('/')
def home():
    """
    Ana sayfayı, uygulama başlarken toplanan gerçek verilerle gösterir.
    """
    return render_template('haberler_template.html', **CACHED_CONTEXT)

@app.route('/ask', methods=['POST'])
def ask():
    """
    Kullanıcının sorusunu alan ve önbellekteki veriyi kullanarak AI'dan cevap üreten API.
    """
    user_question = request.json.get('question')
    if not user_question:
        return jsonify({'answer': 'Lütfen bir soru girin.'}), 400
    
    # Gerçek AI fonksiyonunu, önbellekteki context ve kullanıcı sorusu ile çağırıyoruz
    ai_answer = answer_user_query(CACHED_CONTEXT, user_question)
    
    return jsonify({'answer': ai_answer})

if __name__ == '__main__':
    # debug=True, yaptığınız değişikliklerin anında yansımasını sağlar.
    app.run(host='0.0.0.0', port=5000, debug=True)