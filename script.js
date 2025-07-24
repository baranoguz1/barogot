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

    if (scrollToTopBtn) {
        function handleScroll() {
            if (window.scrollY > 100) {
                scrollToTopBtn.style.display = "block";
            } else {
                scrollToTopBtn.style.display = "none";
            }
        }
        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        window.addEventListener('scroll', handleScroll);
        scrollToTopBtn.addEventListener('click', scrollToTop);
    }
    
    // --- SCROLL SPY - KATEGORİ TAKİPÇİSİ (DÜZELTİLMİŞ VERSİYON) ---
    const navLinks = document.querySelectorAll('nav.sticky-nav a');
    const sections = document.querySelectorAll('.section-title[id]');

    if (navLinks.length === 0 || sections.length === 0) {
        return;
    }

    const offset = 150; 

    function changeLinkState() {
        let currentSectionId = '';
        const pageTop = window.scrollY;

        sections.forEach(section => {
            if (section.offsetTop <= pageTop + offset) {
                currentSectionId = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${currentSectionId}`) {
                link.classList.add('active');
                
                // Aktif linki görünüme kaydır
                link.scrollIntoView({
                    behavior: 'smooth',
                    inline: 'center',
                    block: 'nearest'
                });
            }
        });
    }

    window.addEventListener('scroll', changeLinkState);
    changeLinkState();
});