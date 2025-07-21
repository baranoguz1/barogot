from sentence_transformers import SentenceTransformer, util
import numpy as np

# Bu dil modelini projenin başında bir kez yüklemek en verimli yöntemdir.
# Şimdilik bu dosya içinde tanımlayalım.
# Bu model, çok dilli metinleri anlayarak anlamsal benzerliklerini ölçer.
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"Dil modeli yüklenirken bir hata oluştu: {e}")
    print("Modelin indirilmesi için internet bağlantısı gerekebilir.")
    model = None

def group_similar_news(news_list, similarity_threshold=0.70):
    """
    Haber listesindeki başlıkları anlamsal benzerliklerine göre gruplar.

    Args:
        news_list (list): {'source': '...', 'title': '...'} formatında 
                          sözlükler içeren bir liste.
        similarity_threshold (float): İki başlığın aynı gruba girmesi için gereken 
                                      minimum benzerlik skoru (0 ile 1 arası).
                                      0.70-0.75 genellikle iyi bir başlangıç noktasıdır.

    Returns:
        list: Her biri benzer haberleri içeren bir liste (gruplar listesi).
              Örnek: [[haber1, haber2], [haber3], [haber4, haber5, haber6]]
    """
    # Model yüklenememişse veya haber listesi boşsa, boş liste döndür
    if model is None or not news_list:
        return []

    # Tüm başlıkları bir listeye alalım
    titles = [news['title'] for news in news_list]

    print("Haber başlıkları anlamsal vektörlere dönüştürülüyor...")
    # Başlıkları anlamsal vektörlere dönüştürüyoruz (Embedding).
    # Bu, her başlığın anlamsal bir sayısal temsilini oluşturur.
    embeddings = model.encode(titles, convert_to_tensor=True)

    # Vektörler arasındaki benzerliği hesaplıyoruz (Kosinüs Benzerliği).
    # Bu, bize tüm başlıkların birbiriyle olan anlamsal yakınlığını gösteren bir matris verir.
    cosine_scores = util.cos_sim(embeddings, embeddings)

    print("Benzer haberler gruplanıyor...")
    groups = []
    # İşlemden geçen haberlerin endekslerini takip etmek için bir set kullanıyoruz.
    processed_indices = set()

    for i in range(len(titles)):
        # Eğer bu haber zaten başka bir grubun parçasıysa atla
        if i in processed_indices:
            continue

        # i'inci haberin, diğer tüm haberlerle olan benzerlik skorlarını alıyoruz.
        # Skoru belirlediğimiz eşikten (similarity_threshold) yüksek olanları buluyoruz.
        similar_indices = np.where(cosine_scores[i] >= similarity_threshold)[0]
        
        current_group = []
        for index in similar_indices:
            # Bu haber daha önce bir gruba eklenmemişse, mevcut gruba ekle.
            if index not in processed_indices:
                current_group.append(news_list[index])
                processed_indices.add(index)
        
        # Eğer grup boş değilse, gruplar listesine ekle.
        if current_group:
            groups.append(current_group)
            
    print(f"Toplam {len(news_list)} haber, {len(groups)} gruba ayrıldı.")
    return groups