// Sample cart data
let cart = [
    { id: 1, name: "Snake Chain", price: 75.00, color: "Silver", size: "M", quantity: 1, image: "/placeholder.svg" },
    { id: 2, name: "Essential Chain", price: 22.00, color: "Silver", size: "M", quantity: 1, image: "/placeholder.svg" }
];

// Tax rate
const taxRate = 0.05;

// Function to render cart items
function renderCart() {
    const cartItemsContainer = document.getElementById('cart-items');
    cartItemsContainer.innerHTML = '';

    cart.forEach(item => {
        const itemElement = document.createElement('div');
        itemElement.className = 'cart-item';
        itemElement.innerHTML = `
            <img src="${item.image}" alt="${item.name}" class="item-image">
            <div class="item-details">
                <div class="item-header">
                    <h2>${item.name}</h2>
                    <span class="item-price">$${item.price.toFixed(2)}</span>
                </div>
                <p class="item-meta">Color: ${item.color} — Size: ${item.size}</p>
                <div class="item-actions">
                    <div class="quantity-selector">
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, -1)">−</button>
                        <span class="quantity">${item.quantity}</span>
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                    </div>
                    <button class="remove-btn" onclick="removeItem(${item.id})">×</button>
                </div>
            </div>
        `;
        cartItemsContainer.appendChild(itemElement);
    });

    updateOrderSummary();
}

// Function to update item quantity
function updateQuantity(id, change) {
    const item = cart.find(item => item.id === id);
    if (item) {
        item.quantity = Math.max(1, item.quantity + change);
        renderCart();
    }
}

// Function to remove item from cart
function removeItem(id) {
    cart = cart.filter(item => item.id !== id);
    renderCart();
}

// Function to update order summary
function updateOrderSummary() {
    const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const tax = subtotal * taxRate;
    const total = subtotal + tax;

    document.getElementById('subtotal').textContent = `$${subtotal.toFixed(2)}`;
    document.getElementById('tax').textContent = `$${tax.toFixed(2)}`;
    document.getElementById('total').textContent = `$${total.toFixed(2)}`;
}

// Function to handle checkout
function checkout() {
    alert('Proceeding to checkout...');
    // Add your checkout logic here
}

// Function to handle continue shopping
function continueShopping(event) {
    event.preventDefault();
    alert('Continuing shopping...');
    // Add your continue shopping logic here
}

// Initial render
renderCart();