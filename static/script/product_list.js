const productGrid = document.getElementById('productGrid');
const filterBtn = document.getElementById('filterBtn');
const filterOptions = document.getElementById('filterOptions');
const searchQuery = document.getElementById('searchInput').value.trim();

// Toggle filter options
filterBtn.addEventListener('click', () => {
    filterOptions.style.display = filterOptions.style.display === 'none' ? 'block' : 'none';
});

// Fetch and render products
function fetchAndRenderProducts() {
    fetch('/product/list/')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch products');
            }
            return response.json();
        })
        .then(products => {
            renderProducts(products);
        })
        .catch(error => {
            console.error(error.message);
        });
}

function renderProducts(products) {
    productGrid.innerHTML = '';
    products.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'product-card';

        productCard.onclick = () => {
            window.location.href = `/product/${product.id}`; // Adjust the URL pattern as per your Django app
        };
        productCard.innerHTML = `
    <div class="product-image">
        <img src="${product.images[0]}" alt="${product.name}">
    </div>
    <div class="product-info">
        <div class="product-info-header">
            <div class="product-name">${product.name}</div>
            <button class="wishlist-btn ${product.in_wishlist ? 'active' : ''}" 
                    onclick="toggleWishlist(event, ${product.id})" 
                    type="button" 
                    title="${product.in_wishlist ? 'Remove from Wishlist' : 'Add to Wishlist'}">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="${product.in_wishlist ? 'red' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                </svg>
            </button>
        </div>
        <div class="variant-price" style="color: red;">
        ${product.variants[0].is_offer 
            ? `<span style="text-decoration: line-through; color: gray;">${product.variants[0].price}</span> 
               <span>${product.variants[0].discounted_price}</span>
               <div style="display: inline-block; background-color: red; color: white; padding: 2px 6px; margin-left: 10px; border-radius: 4px; font-size: .9em;">
                   Save ${product.variants[0].offer_discount}
               </div>` 
            : `${product.variants[0].price}`}
        </div>
        <div class="product-variants">
            <div class="available-colors">
                <div class="color-boxes">
                    ${[...new Set(product.variants.map(variant => variant.color))]
                        .map(color => `<span class="color-box" style="background-color: ${getColorCode(color)};" title="${color}"></span>`)
                        .join('')}
                </div>
            </div>
            <div class="available-sizes">
                <div class="size-boxes">
                    ${[...new Set(product.variants.map(variant => variant.size))]
                        .map(size => `<span class="size-box">${size}</span>`)
                        .join('')}
                </div>
            </div>
        </div>
    </div>`;
        function getColorCode(color) {
            const colorMap = {
                gold: '#FFD700',
                silver: '#C0C0C0',
                pearl: '#FFFFFF',
            };
            return colorMap[color.toLowerCase()] || '#000'; // Default to black if the color is not in the map
        }

        let currentImageIndex = 0;
        let intervalId;
        
        // Preload images
        const preloadedImages = product.images.map(imageUrl => {
            const img = new Image();
            img.src = imageUrl; // This will preload the image
            return img;
        });
        
        // Event listener for mouse enter
        productCard.addEventListener('mouseenter', () => {
            intervalId = setInterval(() => {
                currentImageIndex = (currentImageIndex + 1) % product.images.length;
                productCard.querySelector('img').src = product.images[currentImageIndex];
            }, 1200);
        });
        
        // Event listener for mouse leave
        productCard.addEventListener('mouseleave', () => {
            clearInterval(intervalId);
            currentImageIndex = 0;
            productCard.querySelector('img').src = product.images[0]; // Reset to the first image
        });
        
        productGrid.appendChild(productCard);
    });
}

// Initial fetch and render
fetchAndRenderProducts();

document.querySelectorAll('.color-circle').forEach(circle => {
    circle.addEventListener('click', () => {
        document.querySelectorAll('.color-circle').forEach(c => c.classList.remove('active'));
        circle.classList.add('active');
    });
});

document.querySelectorAll('.size-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    });
});

const priceSlider = document.getElementById('priceSlider');
const priceDisplay = document.getElementById('priceDisplay');
priceSlider.addEventListener('input', () => {
    priceDisplay.textContent = `$${priceSlider.value}.00`;
});


function getFilterData() {
    const categories = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
        .map(checkbox => checkbox.value);

    const colors = Array.from(document.querySelectorAll('.color-circle.active'))
        .map(circle => circle.getAttribute('data-color'));

    const sizes = Array.from(document.querySelectorAll('.size-btn.active'))
        .map(btn => btn.getAttribute('data-size'));

    const price = document.getElementById('priceSlider').value;

    const searchQuery = document.getElementById('searchInput').value.trim(); // Retrieve search input value

    // Return the filter data as an object
    return {
        categories: categories.join(','), // Join multiple values with a comma
        colors: colors.join(','),
        sizes: sizes.join(','),
        price: price,
        search: searchQuery,
    };
}
function fetchAndRenderFilteredProducts(filterData) {
    // Construct the query parameters from filterData
    const queryParams = new URLSearchParams(filterData).toString();

    // Fetch filtered products
    fetch(`/product/list/filter?${queryParams}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch filtered products');
            }
            return response.json();
        })
        .then(products => {
            renderProducts(products); // Use the existing renderProducts function
        })
        .catch(error => {
            console.error('Error:', error.message);
        });
}

document.querySelector('.filter-btn1').addEventListener('click', () => {
    const filterData = getFilterData(); // Collect filter data
    fetchAndRenderFilteredProducts(filterData); // Fetch and render filtered products
});

document.getElementById('filterBtn2').addEventListener('click', () => {
    const filters =getFilterData();
    const queryParams = new URLSearchParams(filters).toString();

    fetch(`/product/list/filter?${queryParams}`)
        .then(response => response.json())
        .then(products => {
            renderProducts(products);
        })
        .catch(error => console.error('Error fetching filtered products:', error));
});
function toggleWishlist(event, productId) {
    event.preventDefault();
    event.stopPropagation();
    
    
    const btn = event.currentTarget;
    const heartIcon = btn.querySelector('svg');
    const formData = new FormData();
    formData.append('product_id', productId);

    fetch('/wishlist/toggle/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': CSRF_TOKEN,
            'X-Requested-With': 'XMLHttpRequest'
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
            btn.classList.toggle('active', data.in_wishlist);
            heartIcon.setAttribute('fill', data.in_wishlist ? 'red' : 'none');
            
            // Update the button title
            btn.setAttribute('title', data.in_wishlist ? 'Remove from Wishlist' : 'Add to Wishlist');
            
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}
function showToast(message) {
    // Create toast element if it doesn't exist
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        document.body.appendChild(toast);
    }
    
    // Set message and show toast
    toast.textContent = message;
    toast.classList.add('show');
    
    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}