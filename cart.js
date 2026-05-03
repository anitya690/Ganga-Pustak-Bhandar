const cartItems = document.querySelector("#cartItems");
const cartSummary = document.querySelector("#cartSummary");
const clearCart = document.querySelector("#clearCart");
const checkoutForm = document.querySelector("#cartCheckoutForm");
const cartMessage = document.querySelector("#cartMessage");

function formatMoney(amount) {
  return `Rs. ${amount}`;
}

function readCart() {
  return JSON.parse(localStorage.getItem("gpb_cart") || "[]");
}

function writeCart(cart) {
  localStorage.setItem("gpb_cart", JSON.stringify(cart));
  renderCart();
}

function cartTotal(cart) {
  return cart.reduce((sum, item) => sum + item.amount * item.quantity, 0);
}

function renderCart() {
  const cart = readCart();

  if (!cart.length) {
    cartItems.innerHTML = '<div class="empty-state"><h3>Cart empty hai</h3><p>Store page se books add kariye.</p><a class="btn primary" href="index.html#books">Browse Books</a></div>';
    cartSummary.innerHTML = '<div><span>Total</span><strong>Rs. 0</strong></div>';
    checkoutForm.hidden = true;
    return;
  }

  checkoutForm.hidden = false;
  cartItems.innerHTML = cart
    .map(
      (item, index) => `
        <article class="cart-item">
          <img src="${item.cover}" alt="${item.title} cover">
          <div>
            <h3>${item.title}</h3>
            <p>${item.author}</p>
            <span class="price">${item.price}</span>
            <span class="mrp">${item.mrp}</span>
          </div>
          <div class="qty-control">
            <button type="button" data-action="minus" data-index="${index}">-</button>
            <strong>${item.quantity}</strong>
            <button type="button" data-action="plus" data-index="${index}">+</button>
          </div>
          <button class="remove-btn" type="button" data-action="remove" data-index="${index}">Remove</button>
        </article>
      `
    )
    .join("");

  cartSummary.innerHTML = `
    <div><span>Items</span><strong>${cart.reduce((sum, item) => sum + item.quantity, 0)}</strong></div>
    <div><span>Total</span><strong>${formatMoney(cartTotal(cart))}</strong></div>
  `;
}

cartItems.addEventListener("click", (event) => {
  const action = event.target.dataset.action;
  if (!action) return;

  const cart = readCart();
  const index = Number(event.target.dataset.index);

  if (action === "plus") cart[index].quantity += 1;
  if (action === "minus") cart[index].quantity = Math.max(1, cart[index].quantity - 1);
  if (action === "remove") cart.splice(index, 1);

  writeCart(cart);
});

clearCart.addEventListener("click", () => writeCart([]));

checkoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const cart = readCart();
  if (!cart.length) return;

  const formData = new FormData(checkoutForm);
  const total = cartTotal(cart);
  const payload = {
    book_title: `Cart Order (${cart.length} items)`,
    book_author: cart.map((item) => item.title).join(", "),
    price: formatMoney(total),
    quantity: cart.reduce((sum, item) => sum + item.quantity, 0),
    total: formatMoney(total),
    items: cart.map((item) => ({
      title: item.title,
      author: item.author,
      quantity: item.quantity,
      price: item.price,
      total: formatMoney(item.amount * item.quantity),
    })),
    customer_name: formData.get("customer_name"),
    phone: formData.get("phone"),
    address: formData.get("address"),
    fulfillment_type: formData.get("fulfillment_type"),
    pickup_slot: formData.get("pickup_slot"),
    payment_method: formData.get("payment_method"),
  };

  cartMessage.textContent = "Cart order place ho raha hai...";

  try {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message);

    cartMessage.textContent = `Order placed. Order ID: #${result.order_id}`;
    writeCart([]);
    checkoutForm.reset();
  } catch (error) {
    cartMessage.textContent = "Order save nahi hua. Server check kariye.";
  }
});

renderCart();
