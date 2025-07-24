document.addEventListener("DOMContentLoaded", function () {

    // --- TEMA DEĞİŞTİRME MANTIĞI ---
    const themeToggle = document.getElementById("theme-toggle");
    const currentTheme = localStorage.getItem("theme");

    if (currentTheme) {
        document.body.classList.add(currentTheme);
        if (currentTheme === "dark-mode") {
            themeToggle.textContent = "☀️";
        } else {
            themeToggle.textContent = "🌙";
        }
    }

    if(themeToggle) {
        themeToggle.addEventListener("click", () => {
            document.body.classList.toggle("dark-mode");
            let theme = "light-mode";
            let buttonText = "🌙";
            if (document.body.classList.contains("dark-mode")) {
                theme = "dark-mode";
                buttonText = "☀️";
            }
            localStorage.setItem("theme", theme);
            themeToggle.textContent = buttonText;
        });
    }


    // --- "YUKARI ÇIK" BUTONU LOGIĞI ---
    const scrollToTopBtn = document.getElementById("scrollToTopBtn");

    // Butonun HTML'de var olup olmadığını kontrol et
    if (scrollToTopBtn) {

        // Butonu gösterecek veya gizleyecek fonksiyon
        function handleScroll() {
            if (window.scrollY > 100) {
                scrollToTopBtn.style.display = "block";
            } else {
                scrollToTopBtn.style.display = "none";
            }
        }

        // Butona tıklandığında sayfanın en üstüne gitme fonksiyonu
        function scrollToTop() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth' // Yumuşak kaydırma efekti için
            });
        }

        // Gerekli olay dinleyicilerini ekle
        window.addEventListener('scroll', handleScroll);
        scrollToTopBtn.addEventListener('click', scrollToTop);
    }
});

/**
 * SCROLL SPY - KATEGORİ TAKİPÇİSİ
 * Sayfa kaydırıldığında, görünüm alanındaki (viewport) kategoriye göre
 * üst navigasyon çubuğundaki ilgili linki aktif hale getirir.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Navigasyon linklerini ve karşılık gelen kategori başlıklarını seç
    const navLinks = document.querySelectorAll('.kategori-link');
    const sections = document.querySelectorAll('.category-title');

    // Eğer sayfada kategori linki veya bölüm yoksa, fonksiyonu çalıştırma
    if (navLinks.length === 0 || sections.length === 0) {
        return;
    }

    // Ekranın üstünden ne kadar mesafede aktif olacağını belirler
    // Örneğin, başlık ekranın üstten 150 piksel altına geldiğinde aktif olur.
    const offset = 150; 

    function changeLinkState() {
        let currentSectionId = '';

        // Her bir bölümün pozisyonunu kontrol et
        sections.forEach(section => {
            const sectionTop = section.getBoundingClientRect().top;
            
            // Eğer bölümün üst kenarı, belirlediğimiz ofsetin altındaysa
            // ve hala ekranın içindeyse, onu 'aktif' bölüm olarak kabul et.
            if (sectionTop <= offset) {
                currentSectionId = section.getAttribute('id');
            }
        });

        // Tüm linklerden 'active' sınıfını kaldır
        navLinks.forEach(link => {
            link.classList.remove('active');
        });

        // Mevcut aktif bölüme karşılık gelen linki bul ve 'active' sınıfı ekle
        if (currentSectionId) {
            const activeLink = document.querySelector(`.kategori-link[href="#${currentSectionId}"]`);
            if (activeLink) {
                activeLink.classList.add('active');
            }
        }
    }

    // Sayfa her kaydırıldığında 'changeLinkState' fonksiyonunu çağır
    window.addEventListener('scroll', changeLinkState);

    // Sayfa ilk yüklendiğinde de bir kontrol yap
    changeLinkState();
});