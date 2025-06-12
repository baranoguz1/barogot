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