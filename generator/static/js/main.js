// Theme Management
document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle functionality
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            const icon = this.querySelector('i');
            icon.classList.toggle('fa-moon');
            icon.classList.toggle('fa-sun');
        });
    }

    // Theme option functionality
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach(option => {
        option.addEventListener('click', function() {
            const theme = this.getAttribute('onclick').match(/'([^']+)'/)[1];
            setTheme(theme);
        });
    });
});

function setTheme(theme) {
    document.body.className = theme;
    localStorage.setItem('selectedTheme', theme);
}

// Load saved theme
const savedTheme = localStorage.getItem('selectedTheme');
if (savedTheme) {
    document.body.className = savedTheme;
}

// Loading screen
window.addEventListener('load', function() {
    const loadingScreen = document.getElementById('loadingScreen');
    if (loadingScreen) {
        loadingScreen.style.opacity = '0';
        setTimeout(() => {
            loadingScreen.style.display = 'none';
        }, 500);
    }
});

// Enhanced Card Hover Effect
document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        card.style.transform = `perspective(1000px) rotateX(${(y - rect.height/2)/20}deg) rotateY(${-(x - rect.width/2)/20}deg) scale(1.02)`;
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
    });
}); 