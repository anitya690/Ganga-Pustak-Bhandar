let books = [
  {
    title: "Godan",
    author: "Munshi Premchand",
    category: "hindi",
    mrp: 220,
    amount: 180,
    stock: "In stock",
    cover: "https://covers.openlibrary.org/b/isbn/9788126705035-L.jpg",
  },
  {
    title: "The Alchemist",
    author: "Paulo Coelho",
    category: "fiction",
    mrp: 399,
    amount: 299,
    stock: "In stock",
    cover: "https://covers.openlibrary.org/b/isbn/9780062315007-L.jpg",
  },
  {
    title: "CBSE Mathematics Class 10",
    author: "NCERT / CBSE",
    category: "school",
    mrp: 120,
    amount: 95,
    stock: "Limited",
    cover: "https://covers.openlibrary.org/b/isbn/8174506349-L.jpg",
  },
  {
    title: "ICSE English Literature Guide",
    author: "ICSE Board",
    category: "school",
    mrp: 340,
    amount: 260,
    stock: "In stock",
    cover: "https://covers.openlibrary.org/b/isbn/9780199450411-L.jpg",
  },
  {
    title: "MP Board Science Class 10",
    author: "MP Board",
    category: "school",
    mrp: 180,
    amount: 140,
    stock: "In stock",
    cover: "https://covers.openlibrary.org/b/isbn/9789352530141-L.jpg",
  },
  {
    title: "Indian Polity",
    author: "M. Laxmikanth",
    category: "competitive",
    mrp: 1099,
    amount: 940,
    stock: "In stock",
    cover: "https://covers.openlibrary.org/b/isbn/9789354600354-L.jpg",
  },
  {
    title: "Rich Dad Poor Dad",
    author: "Robert T. Kiyosaki",
    category: "fiction",
    mrp: 499,
    amount: 399,
    stock: "In stock",
    cover: "https://covers.openlibrary.org/b/isbn/9781612680194-L.jpg",
  },
  {
    title: "Samanya Gyan 2026",
    author: "Arihant Experts",
    category: "competitive",
    mrp: 280,
    amount: 210,
    stock: "New arrival",
    cover: "https://covers.openlibrary.org/b/isbn/9789327194347-L.jpg",
  },
  {
    title: "Rashmirathi",
    author: "Ramdhari Singh Dinkar",
    category: "hindi",
    mrp: 210,
    amount: 160,
    stock: "In stock",
    cover: "https://covers.openlibrary.org/b/isbn/9788126714983-L.jpg",
  },
  {
    title: "Premium Notebook Pack",
    author: "Stationery",
    category: "stationery",
    mrp: 310,
    amount: 240,
    stock: "In stock",
    cover:
      "https://images.unsplash.com/photo-1531346680769-a1d79b57de5c?auto=format&fit=crop&w=700&q=80",
  },
];

const categoryNames = {
  school: "School",
  competitive: "Competitive",
  hindi: "Hindi Literature",
  fiction: "Fiction",
  stationery: "Stationery",
};

const bookGrid = document.querySelector("#bookGrid");
const searchInput = document.querySelector("#searchInput");
const categoryFilter = document.querySelector("#categoryFilter");
const bookDialog = document.querySelector("#bookDialog");
const dialogBody = document.querySelector("#dialogBody");
const dialogClose = document.querySelector("#dialogClose");
const cartCount = document.querySelector("#cartCount");

function formatMoney(amount) {
  return `Rs. ${amount}`;
}

function normalizeProduct(product) {
  const price = Number(String(product.price || product.amount || 0).replace(/[^0-9]/g, ""));
  const mrp = Number(String(product.mrp || product.price || 0).replace(/[^0-9]/g, ""));
  return {
    title: product.title,
    author: product.author || "Ganga Pustak Bhandar",
    category: product.category || "school",
    mrp: mrp || price,
    amount: price,
    stock: Number(product.stock || 0) > 0 ? "In stock" : "Out of stock",
    cover:
      product.cover ||
      "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=700&q=80",
  };
}

async function loadCatalog() {
  try {
    const response = await fetch("/api/catalog");
    if (!response.ok) return;
    const data = await response.json();
    if (Array.isArray(data.products) && data.products.length) {
      books = data.products.map(normalizeProduct);
    }
  } catch (error) {
    // Static fallback books stay available if the local server is not running.
  }
}

function discountPercent(book) {
  return Math.round(((book.mrp - book.amount) / book.mrp) * 100);
}

function readCart() {
  return JSON.parse(localStorage.getItem("gpb_cart") || "[]");
}

function writeCart(cart) {
  localStorage.setItem("gpb_cart", JSON.stringify(cart));
  updateCartCount();
}

function updateCartCount() {
  if (!cartCount) return;
  const total = readCart().reduce((sum, item) => sum + item.quantity, 0);
  cartCount.textContent = total;
}

function addToCart(book, quantity = 1) {
  const cart = readCart();
  const existing = cart.find((item) => item.title === book.title);

  if (existing) {
    existing.quantity += quantity;
  } else {
    cart.push({
      title: book.title,
      author: book.author,
      cover: book.cover,
      price: formatMoney(book.amount),
      mrp: formatMoney(book.mrp),
      amount: book.amount,
      quantity,
    });
  }

  writeCart(cart);
}

function renderBooks() {
  const searchTerm = searchInput.value.trim().toLowerCase();
  const selectedCategory = categoryFilter.value;

  const filteredBooks = books.filter((book) => {
    const matchesCategory =
      selectedCategory === "all" || book.category === selectedCategory;
    const matchesSearch = [book.title, book.author, book.category]
      .join(" ")
      .toLowerCase()
      .includes(searchTerm);

    return matchesCategory && matchesSearch;
  });

  if (!filteredBooks.length) {
    bookGrid.innerHTML =
      '<div class="empty-state"><h3>No books found</h3><p>Try another title, author or exam category.</p></div>';
    return;
  }

  bookGrid.innerHTML = filteredBooks
    .map(
      (book) => `
        <article class="book-card" data-book-index="${books.indexOf(book)}" tabindex="0" role="button" aria-label="${book.title} details kholiye">
          <div class="discount-ribbon">${discountPercent(book)}% off</div>
          <div class="cover-wrap">
            <img src="${book.cover}" alt="${book.title} book cover" loading="lazy">
          </div>
          <div class="book-info">
            <span class="tag">${categoryNames[book.category]}</span>
            <h3>${book.title}</h3>
            <p>${book.author}</p>
            <div class="price-stack">
              <span class="price">${formatMoney(book.amount)}</span>
              <span class="mrp">${formatMoney(book.mrp)}</span>
              <span class="stock">${book.stock}</span>
            </div>
            <div class="card-actions">
              <button class="details-btn" type="button" data-action="details">Details</button>
              <button class="details-btn cart-btn" type="button" data-action="cart">Add Cart</button>
              <button class="details-btn buy-now-btn" type="button" data-action="buy">Buy Now</button>
            </div>
          </div>
        </article>
      `
    )
    .join("");
}

function openBookDetails(book) {
  dialogBody.innerHTML = `
    <div class="product-media">
      <img src="${book.cover}" alt="${book.title} book cover">
      <div class="secure-box">
        <strong>Store verified</strong>
        <span>Pickup from Near Star Automobiles, Satna</span>
      </div>
    </div>
    <div class="checkout-panel">
      <span class="tag">${categoryNames[book.category]}</span>
      <h2 id="dialogTitle">${book.title}</h2>
      <p class="product-author">by ${book.author}</p>
      <div class="rating-row" aria-label="Customer rating">
        <span>*****</span>
        <small>${discountPercent(book)}% discount for students</small>
      </div>
      <div class="buy-box">
        <div>
          <span class="price">${formatMoney(book.amount)}</span>
          <span class="mrp">${formatMoney(book.mrp)}</span>
          <p class="dialog-note">Final availability is confirmed by the store before dispatch or pickup.</p>
        </div>
        <strong class="stock">${book.stock}</strong>
      </div>

      <form class="order-form checkout-form" id="orderForm">
        <div class="checkout-steps">
          <span class="active">1 Book</span>
          <span>2 Pickup/Delivery</span>
          <span>3 Payment</span>
        </div>

        <label>
          Quantity
          <input id="quantityInput" name="quantity" type="number" min="1" max="10" value="1" required>
        </label>

        <div class="modal-actions">
          <button class="btn secondary" id="modalCartButton" type="button">Add to Cart</button>
          <a class="btn secondary" href="cart.html">Open Cart</a>
        </div>

        <fieldset class="choice-grid">
          <legend>Order type</legend>
          <label>
            <input type="radio" name="fulfillment_type" value="Pickup" checked>
            <span>
              <strong>Store Pickup</strong>
              <small>Near Star Automobiles, Satna</small>
            </span>
          </label>
          <label>
            <input type="radio" name="fulfillment_type" value="Delivery">
            <span>
              <strong>Home Delivery</strong>
              <small>Delivery will be confirmed by the store</small>
            </span>
          </label>
        </fieldset>

        <div class="customer-grid">
          <label>
            Name
            <input name="customer_name" type="text" placeholder="Customer name" required>
          </label>
          <label>
            Phone
            <input name="phone" type="tel" placeholder="Mobile number" required>
          </label>
        </div>

        <label>
          Delivery address / pickup note
          <textarea name="address" rows="3" placeholder="Delivery address or pickup note" required>Pickup from store</textarea>
        </label>

        <label>
          Pickup slot
          <select name="pickup_slot" required>
            <option value="Today, 4 PM - 8 PM">Today, 4 PM - 8 PM</option>
            <option value="Tomorrow, 10 AM - 1 PM">Tomorrow, 10 AM - 1 PM</option>
            <option value="Tomorrow, 4 PM - 8 PM">Tomorrow, 4 PM - 8 PM</option>
          </select>
        </label>

        <label>
          Payment
          <select name="payment_method" required>
            <option value="Cash on Pickup">Cash on Pickup</option>
            <option value="Cash on Delivery">Cash on Delivery</option>
            <option value="UPI on Confirmation">UPI on Confirmation</option>
          </select>
        </label>

        <div class="order-summary">
          <div><span>Item price</span><strong>${formatMoney(book.amount)}</strong></div>
          <div><span>MRP</span><strong>${formatMoney(book.mrp)}</strong></div>
          <div><span>Quantity</span><strong id="summaryQty">1</strong></div>
          <div><span>Total</span><strong id="summaryTotal">${formatMoney(book.amount)}</strong></div>
        </div>

        <button class="btn primary place-order" type="submit">Place Order</button>
        <p class="form-message" id="formMessage"></p>
      </form>
    </div>
  `;

  const orderForm = document.querySelector("#orderForm");
  const formMessage = document.querySelector("#formMessage");
  const quantityInput = document.querySelector("#quantityInput");
  const summaryQty = document.querySelector("#summaryQty");
  const summaryTotal = document.querySelector("#summaryTotal");
  const modalCartButton = document.querySelector("#modalCartButton");

  function updateSummary() {
    const quantity = Number(quantityInput.value || 1);
    summaryQty.textContent = quantity;
    summaryTotal.textContent = formatMoney(book.amount * quantity);
  }

  modalCartButton.addEventListener("click", () => {
    addToCart(book, Number(quantityInput.value || 1));
    formMessage.textContent = "Added to cart.";
  });

  quantityInput.addEventListener("input", updateSummary);

  orderForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(orderForm);
    const quantity = Number(formData.get("quantity"));
    const payload = {
      book_title: book.title,
      book_author: book.author,
      price: formatMoney(book.amount),
      quantity,
      total: formatMoney(book.amount * quantity),
      items: [
        {
          title: book.title,
          author: book.author,
          quantity,
          price: formatMoney(book.amount),
          total: formatMoney(book.amount * quantity),
        },
      ],
      customer_name: formData.get("customer_name"),
      phone: formData.get("phone"),
      address: formData.get("address"),
      fulfillment_type: formData.get("fulfillment_type"),
      pickup_slot: formData.get("pickup_slot"),
      payment_method: formData.get("payment_method"),
    };

    formMessage.textContent = "Placing order...";

    try {
      const response = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.message || "Order save nahi ho paya.");
      }

      formMessage.textContent = `Order placed. Order ID: #${result.order_id}. The store will call you for confirmation.`;
      orderForm.reset();
      quantityInput.value = 1;
      updateSummary();
    } catch (error) {
      formMessage.textContent =
        "Order could not be saved. Please make sure the local server is running.";
    }
  });

  bookDialog.showModal();
}

searchInput.addEventListener("input", renderBooks);
categoryFilter.addEventListener("change", renderBooks);

bookGrid.addEventListener("mousemove", (event) => {
  const card = event.target.closest(".book-card");
  if (!card) return;

  const rect = card.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width - 0.5) * 14;
  const y = ((event.clientY - rect.top) / rect.height - 0.5) * -14;
  card.style.setProperty("--tilt-x", `${y}deg`);
  card.style.setProperty("--tilt-y", `${x}deg`);
});

bookGrid.addEventListener("mouseleave", () => {
  document.querySelectorAll(".book-card").forEach((card) => {
    card.style.removeProperty("--tilt-x");
    card.style.removeProperty("--tilt-y");
  });
});

bookGrid.addEventListener("click", (event) => {
  const card = event.target.closest(".book-card");
  if (!card) return;

  const book = books[Number(card.dataset.bookIndex)];
  if (event.target.dataset.action === "cart") {
    event.stopPropagation();
    addToCart(book, 1);
    event.target.textContent = "Added";
    setTimeout(() => {
      event.target.textContent = "Add Cart";
    }, 900);
    return;
  }

  if (event.target.dataset.action === "buy") {
    event.stopPropagation();
    addToCart(book, 1);
    window.location.href = "cart.html";
    return;
  }

  openBookDetails(book);
});

bookGrid.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;

  const card = event.target.closest(".book-card");
  if (!card) return;

  event.preventDefault();
  openBookDetails(books[Number(card.dataset.bookIndex)]);
});

dialogClose.addEventListener("click", () => bookDialog.close());

loadCatalog().then(() => {
  renderBooks();
  updateCartCount();
});
