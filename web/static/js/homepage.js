document.addEventListener('DOMContentLoaded', () => {
    const hero = document.querySelector('.hero-section');
    const enterBtn = document.querySelector('.enter-btn');

    // 鼠标跟随特效
    hero.addEventListener('mousemove', (e) => {
        const x = e.clientX / window.innerWidth;
        const y = e.clientY / window.innerHeight;
        
        const dx = (x - 0.5) * 20;
        const dy = (y - 0.5) * 20;
        document.querySelector('.logo-container').style.transform = 
            `translate(${dx}px, ${dy}px) rotate(${dx * 0.5}deg)`;
    });

    // 页面过渡效果
    enterBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const targetUrl = this.href;

        hero.classList.add('fade-out');

        setTimeout(() => {
            window.location.href = targetUrl;
        }, 1000);
    });
});