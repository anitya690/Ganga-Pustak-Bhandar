const inventoryBody = document.querySelector("#inventoryBody");
const inventorySearch = document.querySelector("#inventorySearch");
const inventoryMessage = document.querySelector("#inventoryMessage");
const addProductForm = document.querySelector("#addProductForm");
const addProductMessage = document.querySelector("#addProductMessage");
let products = [];

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadInventory() {
  const response = await fetch("/api/products");
  if (response.status === 401) {
    inventoryBody.innerHTML =
      '<tr><td colspan="7">Please login on the admin page first.</td></tr>';
    return;
  }
  const data = await response.json();
  products = data.products || [];
  renderInventory();
}

function renderInventory() {
  const query = inventorySearch.value.trim().toLowerCase();
  const filtered = products.filter((product) =>
    [product.sku, product.title, product.category, product.rack]
      .join(" ")
      .toLowerCase()
      .includes(query)
  );

  inventoryBody.innerHTML = filtered
    .map(
      (product) => `
        <tr data-sku="${escapeHtml(product.sku)}">
          <td>${escapeHtml(product.sku)}</td>
          <td><strong>${escapeHtml(product.title)}</strong><small>Rs. ${escapeHtml(product.price)} / MRP Rs. ${escapeHtml(product.mrp)}</small></td>
          <td>${escapeHtml(product.category)}</td>
          <td><input class="stock-input" type="number" min="0" value="${escapeHtml(product.stock)}"></td>
          <td><input class="rack-input" type="text" value="${escapeHtml(product.rack)}"></td>
          <td><input class="note-input" type="text" value="${escapeHtml(product.worker_note)}"></td>
          <td><button class="btn secondary save-product" type="button">Save</button></td>
        </tr>
      `
    )
    .join("");
}

inventorySearch.addEventListener("input", renderInventory);

addProductForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(addProductForm);
  const payload = Object.fromEntries(formData.entries());

  addProductMessage.textContent = "Adding book...";
  const response = await fetch("/api/products", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();

  if (!response.ok) {
    addProductMessage.textContent = result.message || "Could not add book.";
    return;
  }

  addProductMessage.textContent = "Book added to inventory and store.";
  addProductForm.reset();
  await loadInventory();
});

inventoryBody.addEventListener("click", async (event) => {
  if (!event.target.matches(".save-product")) return;
  const row = event.target.closest("tr");
  const sku = row.dataset.sku;
  const payload = {
    stock: row.querySelector(".stock-input").value,
    rack: row.querySelector(".rack-input").value,
    worker_note: row.querySelector(".note-input").value,
  };

  const response = await fetch(`/api/products/${sku}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  inventoryMessage.textContent = response.ok
    ? "Inventory updated."
    : "Could not update inventory.";
  await loadInventory();
});

loadInventory();
