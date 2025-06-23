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