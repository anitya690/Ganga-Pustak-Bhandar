const loginPanel = document.querySelector("#loginPanel");
const loginForm = document.querySelector("#loginForm");
const loginMessage = document.querySelector("#loginMessage");
const adminHero = document.querySelector("#adminHero");
const ordersPanel = document.querySelector("#ordersPanel");
const logoutButton = document.querySelector("#logoutButton");
const ordersBody = document.querySelector("#ordersBody");
const orderCount = document.querySelector("#orderCount");
const refreshOrders = document.querySelector("#refreshOrders");

const statuses = ["New", "Confirmed", "Packed", "Completed", "Cancelled"];

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showDashboard() {
  loginPanel.hidden = true;
  adminHero.hidden = false;
  ordersPanel.hidden = false;
  logoutButton.hidden = false;
}

function showLogin() {
  loginPanel.hidden = false;
  adminHero.hidden = true;
  ordersPanel.hidden = true;
  logoutButton.hidden = true;
}

function renderOrderItems(order) {
  if (!Array.isArray(order.items) || !order.items.length) {
    return `${escapeHtml(order.book_author)} - ${escapeHtml(order.price)}`;
  }

  return order.items
    .map(
      (item) =>
        `${escapeHtml(item.title)} x ${escapeHtml(item.quantity)} (${escapeHtml(item.total)})`
    )
    .join("<br>");
}

async function checkSession() {
  const response = await fetch("/api/session");
  const data = await response.json();
  if (data.ok) {
    showDashboard();
    loadOrders();
  } else {
    showLogin();
  }
}

async function loadOrders() {
  ordersBody.innerHTML = '<tr><td colspan="9">Loading orders...</td></tr>';

  try {
    const response = await fetch("/api/orders");
    if (response.status === 401) {
      showLogin();
      return;
    }

    const data = await response.json();
    const orders = data.orders || [];

    orderCount.textContent = `${orders.length} orders`;

    if (!orders.length) {
      ordersBody.innerHTML =
        '<tr><td colspan="9">Abhi koi order nahi aaya hai.</td></tr>';
      return;
    }

    ordersBody.innerHTML = orders
      .map(
        (order) => `
          <tr>
            <td>#${order.id}</td>
            <td>
              <strong>${escapeHtml(order.book_title)}</strong>
              <small>${renderOrderItems(order)}</small>
            </td>
            <td>
              <strong>${escapeHtml(order.total || order.price)}</strong>
              <small>Qty: ${escapeHtml(order.quantity || 1)}</small>
            </td>
            <td>${escapeHtml(order.customer_name)}</td>
            <td><a href="tel:${escapeHtml(order.phone)}">${escapeHtml(order.phone)}</a></td>
            <td>
              <strong>${escapeHtml(order.fulfillment_type || "Pickup")}</strong>
              <small>${escapeHtml(order.pickup_slot || "")}</small>
              <small>${escapeHtml(order.address)}</small>
            </td>
            <td>${escapeHtml(order.payment_method)}</td>
            <td>
              <select class="status-select" data-order-id="${order.id}">
                ${statuses
                  .map(
                    (status) =>
                      `<option value="${status}" ${
                        status === order.status ? "selected" : ""
                      }>${status}</option>`
                  )
                  .join("")}
              </select>
            </td>
            <td>${escapeHtml(order.created_at)}</td>
          </tr>
        `
      )
      .join("");
  } catch (error) {
    ordersBody.innerHTML =
      '<tr><td colspan="9">Server nahi chal raha. Pehle python server.py run kariye.</td></tr>';
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginMessage.textContent = "Checking password...";
  const formData = new FormData(loginForm);

  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: formData.get("password") }),
  });

  if (!response.ok) {
    loginMessage.textContent = "Password galat hai.";
    return;
  }

  loginMessage.textContent = "";
  loginForm.reset();
  showDashboard();
  loadOrders();
});

logoutButton.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  showLogin();
});

ordersBody.addEventListener("change", async (event) => {
  if (!event.target.matches(".status-select")) return;

  const response = await fetch(`/api/orders/${event.target.dataset.orderId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: event.target.value }),
  });

  if (response.status === 401) {
    showLogin();
  }
});

refreshOrders.addEventListener("click", loadOrders);

checkSession();
