document.addEventListener('DOMContentLoaded', () => {
    const sliders = document.querySelectorAll('.product-section');

    sliders.forEach((slider) => {
        const track = slider.querySelector('.product-track');
        const cards = track.querySelectorAll('.product-card');
        const nextBtn = slider.querySelector('.next-btn');
        const prevBtn = slider.querySelector('.prev-btn');

        let currentIndex = 0;
        const cardWidth = cards[0].offsetWidth + 20; // card width + margin
        const visibleCards = 4; // Number of cards visible at once

        function updateSlider() {
            track.style.transform = `translateX(-${currentIndex * cardWidth}px)`;
            updateButtonStates();
        }

        function updateButtonStates() {
            prevBtn.disabled = currentIndex === 0;
            nextBtn.disabled = currentIndex >= cards.length - visibleCards;
            prevBtn.style.opacity = prevBtn.disabled ? '0.5' : '1';
            nextBtn.style.opacity = nextBtn.disabled ? '0.5' : '1';
        }

        nextBtn.addEventListener('click', () => {
            if (currentIndex < cards.length - visibleCards) {
                currentIndex++;
                updateSlider();
            }
        });

        prevBtn.addEventListener('click', () => {
            if (currentIndex > 0) {
                currentIndex--;
                updateSlider();
            }
        });

        // Image rotation and zoom on hover
        cards.forEach(card => {
            const productImage = card.querySelector('.product-image');
            const images = card.querySelectorAll('.product-img');
            const dots = card.querySelectorAll('.dot');
            let currentImageIndex = 0;
            let interval;

            function rotateImage() {
                images[currentImageIndex].classList.remove('active');
                dots[currentImageIndex].classList.remove('active');
                currentImageIndex = (currentImageIndex + 1) % images.length;
                images[currentImageIndex].classList.add('active');
                dots[currentImageIndex].classList.add('active');
            }

            productImage.addEventListener('mouseenter', () => {
                interval = setInterval(rotateImage, 1200);
            });

            productImage.addEventListener('mouseleave', () => {
                clearInterval(interval);
                images.forEach((img, index) => {
                    img.classList.toggle('active', index === 0);
                });
                dots.forEach((dot, index) => {
                    dot.classList.toggle('active', index === 0);
                });
                currentImageIndex = 0;
            });
        });

        // Initial update
        updateButtonStates();
    });
});