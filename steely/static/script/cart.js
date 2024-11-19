function updateQuantity(id, newQuantity) {
    fetch(`/cart/update/${id}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(), // Ensure CSRF token is included
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ quantity: newQuantity }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Find the item and update its quantity in the cart
            const item = cart.find(item => item.id === id);
            if (item) {
                item.quantity = data.quantity;
            }
            renderCart();
        } else {
            alert(data.message || 'Failed to update quantity.');
        }
    })
    .catch(error => console.error('Error:', error));
}


function removeItem(id) {
    fetch(`/cart/remove/${id}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(), // Ensure CSRF token is included
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove the item from the cart array and re-render
            cart = cart.filter(item => item.id !== id);
            renderCart();
        } else {
            alert(data.message || 'Failed to remove item.');
        }
    })
    .catch(error => console.error('Error:', error));
}


function renderCart() {
    const cartItemsContainer = document.getElementById('cart-items');
    cartItemsContainer.innerHTML = '';

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = '<p>Your cart is empty.</p>';
        updateOrderSummary();
        return;
    }

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
                <p class="item-meta">Color: ${item.color || 'N/A'} — Size: ${item.size || 'N/A'}</p>
                <div class="item-actions">
                    <div class="quantity-selector">
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity} - 1)">−</button>
                        <span class="quantity">${item.quantity}</span>
                        <button class="quantity-btn" onclick="updateQuantity(${item.id}, ${item.quantity} + 1)">+</button>
                    </div>
                    <button class="remove-btn" onclick="removeItem(${item.id})">×</button>
                </div>
            </div>
        `;
        cartItemsContainer.appendChild(itemElement);
    });

    updateOrderSummary();
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}



function updateOrderSummary() {
    const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const tax = subtotal * taxRate;
    const total = subtotal + tax;

    document.getElementById('subtotal').textContent = `$${subtotal.toFixed(2)}`;
    document.getElementById('tax').textContent = `$${tax.toFixed(2)}`;
    document.getElementById('total').textContent = `$${total.toFixed(2)}`;
}

document.addEventListener('DOMContentLoaded', function () {
    renderCart(); // Initial render of the cart
});