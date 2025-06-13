import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

def summarize_headlines(all_news, num_sentences=5):
    """
    Verilen haber listesindeki başlıklardan bir özet çıkarır.
    
    Args:
        all_news (list): {'title': '...', 'link': '...'} formatında sözlükler listesi.
        num_sentences (int): Döndürülecek en önemli başlık sayısı.

    Returns:
        list: En önemli başlıkları içeren string listesi.
    """
    if not all_news:
        return []

    # Tüm başlıkları tek bir metin bloğunda birleştir
    headlines_text = ". ".join([news['title'] for news in all_news if news.get('title')])
    
    # Metni sumy için ayrıştır
    parser = PlaintextParser.from_string(headlines_text, Tokenizer("turkish"))
    
    # LexRank algoritmasını kullanarak özetleyici oluştur
    summarizer = LexRankSummarizer()
    
    # Metni özetle ve belirtilen sayıda en önemli cümleyi al
    summary_sentences = summarizer(parser.document, num_sentences)
    
    # Cümleleri (yani başlıkları) string listesine çevir
    top_headlines = [str(sentence) for sentence in summary_sentences]
    
    return top_headlines