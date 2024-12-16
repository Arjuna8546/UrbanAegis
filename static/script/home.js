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
        document.querySelectorAll('.product-card').forEach(card => {
    const productImageContainer = card.querySelector('.product-image');
    const images = [...card.querySelectorAll('.product-img')];
    const dots = [...card.querySelectorAll('.dot')];
    let currentIndex = 0;
    let rotationInterval;

    function updateImage(index) {
        // Reset active state for images and dots
        images.forEach((img, i) => img.classList.toggle('active', i === index));
        dots.forEach((dot, i) => dot.classList.toggle('active', i === index));
    }

    function startImageRotation() {
        rotationInterval = setInterval(() => {
            currentIndex = (currentIndex + 1) % images.length;
            updateImage(currentIndex);
        }, 1200);
    }

    function stopImageRotation() {
        clearInterval(rotationInterval);
        currentIndex = 0;
        updateImage(currentIndex);
    }

    // Event listeners
    productImageContainer.addEventListener('mouseenter', startImageRotation);
    productImageContainer.addEventListener('mouseleave', stopImageRotation);
});


        // Initial update
        updateButtonStates();
    });
});
function toggleWishlist(event,productId) {
    const btn = event.currentTarget;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const formData = new FormData();
    console.log(productId);

    formData.append('product_id', productId);

    fetch('/wishlist/toggle/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            btn.classList.toggle('active');
            // Optional: Show a success message
            // console.log(data.message);
            Toastify({
                text: data.message, // Display the message from the response
                duration: 3000, // Show for 3 seconds
                close: true, // Add a close button
                gravity: "top", // Show the toast at the top
                position: "center", // Align toast to the right
                style: {
                    background: "linear-gradient(to right, #28a745, #5cd85d)", // Success style
                    color: "#fff", // White text
                    borderRadius: "8px", // Rounded corners
                    boxShadow: "0px 4px 6px rgba(0, 0, 0, 0.1)" // Subtle shadow
                },
            }).showToast();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Optional: Show an error message to the user
        Toastify({
            text: "Please login and try again.",
            duration: 3000,
            close: true,
            gravity: "top",
            position: "right",
            style: {
                background: "linear-gradient(to right, #dc3545, #ff6b6b)", // Error style
                color: "#fff",
                borderRadius: "8px",
                boxShadow: "0px 4px 6px rgba(0, 0, 0, 0.1)"
            },
        }).showToast();
    });
}


