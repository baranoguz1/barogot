// Tema Değiştirme Mantığı
document.addEventListener("DOMContentLoaded", function () {
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
});

// --- "Yukarı Çık" Butonu Logiği ---

// Butonumuzu ID'si ile bulalım
const scrollToTopBtn = document.getElementById("scrollToTopBtn");

// Pencerenin kaydırma olayını dinle
window.onscroll = function() {
    scrollFunction();
};

function scrollFunction() {
    // Kullanıcı 100px'den fazla aşağı kaydırdığında butonu göster, aksi halde gizle
    if (scrollToTopBtn) {
        // DEĞİŞİKLİK: Eski yöntem yerine daha modern ve güvenilir olan window.scrollY kullanıldı.
        if (window.scrollY > 100) {
            scrollToTopBtn.style.display = "block";
        } else {
            scrollToTopBtn.style.display = "none";
        }
    }
}

// Butonun var olup olmadığını kontrol ederek tıklama olayını ekle
if (scrollToTopBtn) {
    scrollToTopBtn.addEventListener("click", function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth' // Yumuşak kaydırma efekti için
        });
    });
}