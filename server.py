from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import base64
import os
import secrets
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ORDERS_PATH = DATA_DIR / "orders.jsonl"
STATUS_PATH = DATA_DIR / "status-events.jsonl"
PRODUCTS_PATH = DATA_DIR / "products.json"
ADMIN_PASSWORD = "admin123"
SESSIONS = set()


def use_postgres():
    return bool(os.environ.get("DATABASE_URL"))


def get_db():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


def init_storage():
    if use_postgres():
        init_postgres()
        return

    DATA_DIR.mkdir(exist_ok=True)
    ORDERS_PATH.touch(exist_ok=True)
    STATUS_PATH.touch(exist_ok=True)
    if not PRODUCTS_PATH.exists():
        save_products(seed_products())


def init_postgres():
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    sku TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT NOT NULL,
                    stock INTEGER NOT NULL DEFAULT 0,
                    rack TEXT NOT NULL DEFAULT '',
                    price INTEGER NOT NULL,
                    mrp INTEGER NOT NULL,
                    cover TEXT NOT NULL DEFAULT '',
                    worker_note TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    book_title TEXT NOT NULL,
                    book_author TEXT NOT NULL,
                    price TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    total TEXT NOT NULL,
                    items JSONB NOT NULL DEFAULT '[]'::jsonb,
                    customer_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL DEFAULT '',
                    fulfillment_type TEXT NOT NULL,
                    pickup_slot TEXT NOT NULL DEFAULT '',
                    payment_method TEXT NOT NULL,
                    payment_status TEXT NOT NULL DEFAULT 'Pending',
                    razorpay_payment_id TEXT NOT NULL DEFAULT '',
                    razorpay_order_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'New',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute("SELECT COUNT(*) AS count FROM products")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany(
                    """
                    INSERT INTO products (
                        sku, title, author, category, stock, rack,
                        price, mrp, cover, worker_note
                    )
                    VALUES (
                        %(sku)s, %(title)s, %(author)s, %(category)s, %(stock)s,
                        %(rack)s, %(price)s, %(mrp)s, %(cover)s, %(worker_note)s
                    )
                    """,
                    seed_products(),
                )


def seed_products():
    return [
        {"sku": "GPB-CBSE-10-MATH", "title": "CBSE Mathematics Class 10", "author": "NCERT / CBSE", "category": "school", "stock": 18, "rack": "A1", "price": 95, "mrp": 120, "cover": "https://covers.openlibrary.org/b/isbn/8174506349-L.jpg", "worker_note": "Keep with CBSE textbooks"},
        {"sku": "GPB-ICSE-ENG", "title": "ICSE English Literature Guide", "author": "ICSE Board", "category": "school", "stock": 12, "rack": "A2", "price": 260, "mrp": 340, "cover": "https://covers.openlibrary.org/b/isbn/9780199450411-L.jpg", "worker_note": "Check latest syllabus"},
        {"sku": "GPB-MP-SCI-10", "title": "MP Board Science Class 10", "author": "MP Board", "category": "school", "stock": 24, "rack": "A3", "price": 140, "mrp": 180, "cover": "https://covers.openlibrary.org/b/isbn/9789352530141-L.jpg", "worker_note": "Fast moving item"},
        {"sku": "GPB-POLITY-LAX", "title": "Indian Polity", "author": "M. Laxmikanth", "category": "competitive", "stock": 9, "rack": "C1", "price": 940, "mrp": 1099, "cover": "https://covers.openlibrary.org/b/isbn/9789354600354-L.jpg", "worker_note": "Keep near UPSC section"},
        {"sku": "GPB-GK-2026", "title": "Samanya Gyan 2026", "author": "Arihant Experts", "category": "competitive", "stock": 30, "rack": "C2", "price": 210, "mrp": 280, "cover": "https://covers.openlibrary.org/b/isbn/9789327194347-L.jpg", "worker_note": "Counter display"},
        {"sku": "GPB-NOTEBOOK-PACK", "title": "Premium Notebook Pack", "author": "Stationery", "category": "stationery", "stock": 40, "rack": "S1", "price": 240, "mrp": 310, "cover": "https://images.unsplash.com/photo-1531346680769-a1d79b57de5c?auto=format&fit=crop&w=700&q=80", "worker_note": "Bundle stock"},
    ]


def load_products():
    if use_postgres():
        init_storage()
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM products ORDER BY title")
                return [normalize_product(product) for product in cursor.fetchall()]

    init_storage()
    with PRODUCTS_PATH.open("r", encoding="utf-8") as file:
        products = json.load(file)

    migrated = [normalize_product(product) for product in products]
    if migrated != products:
        save_products(migrated)
    return migrated


def number_from_price(value, fallback=0):
    digits = "".join(character for character in str(value) if character.isdigit())
    return int(digits or fallback)


def category_slug(value):
    normalized = str(value or "school").strip().lower()
    if "competitive" in normalized or "exam" in normalized:
        return "competitive"
    if "hindi" in normalized:
        return "hindi"
    if "fiction" in normalized or "novel" in normalized:
        return "fiction"
    if "stationery" in normalized or "notebook" in normalized:
        return "stationery"
    return "school"


def normalize_product(product):
    price = number_from_price(product.get("price", product.get("amount", 0)))
    mrp = number_from_price(product.get("mrp", price), price)
    return {
        "sku": str(product.get("sku", "")).upper(),
        "title": str(product.get("title", "")),
        "author": str(product.get("author", "Ganga Pustak Bhandar")),
        "category": category_slug(product.get("category", "school")),
        "stock": int(product.get("stock", 0)),
        "rack": str(product.get("rack", "")),
        "price": price,
        "mrp": max(mrp, price),
        "cover": str(product.get("cover", "")) or "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=700&q=80",
        "worker_note": str(product.get("worker_note", "")),
    }


def save_products(products):
    if use_postgres():
        init_storage()
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM products")
                cursor.executemany(
                    """
                    INSERT INTO products (
                        sku, title, author, category, stock, rack,
                        price, mrp, cover, worker_note
                    )
                    VALUES (
                        %(sku)s, %(title)s, %(author)s, %(category)s, %(stock)s,
                        %(rack)s, %(price)s, %(mrp)s, %(cover)s, %(worker_note)s
                    )
                    """,
                    [normalize_product(product) for product in products],
                )
        return

    DATA_DIR.mkdir(exist_ok=True)
    with PRODUCTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(products, file, indent=2)


def read_jsonl(path):
    init_storage()
    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path, payload):
    init_storage()
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=True) + "\n")


def load_orders():
    if use_postgres():
        init_storage()
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id, book_title, book_author, price, quantity, total,
                        items, customer_name, phone, address, fulfillment_type,
                        pickup_slot, payment_method, payment_status,
                        razorpay_payment_id, razorpay_order_id, status,
                        TO_CHAR(created_at AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS created_at
                    FROM orders
                    ORDER BY id DESC
                    """
                )
                return cursor.fetchall()

    orders = read_jsonl(ORDERS_PATH)
    status_by_id = {
        event["id"]: event["status"] for event in read_jsonl(STATUS_PATH)
    }
    for order in orders:
        order["status"] = status_by_id.get(order["id"], order.get("status", "New"))
    return sorted(orders, key=lambda order: order["id"], reverse=True)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json_with_cookie(self, payload, cookie, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        return json.loads(raw_body or "{}")

    def is_admin(self):
        cookie_header = self.headers.get("Cookie", "")
        cookies = {}
        for item in cookie_header.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value
        return cookies.get("admin_session") in SESSIONS

    def require_admin(self):
        if self.is_admin():
            return True
        self.send_json({"ok": False, "message": "Admin login required."}, status=401)
        return False

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/session":
            self.send_json({"ok": self.is_admin()})
            return

        if path == "/api/orders":
            if not self.require_admin():
                return
            self.send_json({"orders": load_orders()})
            return

        if path == "/api/catalog":
            products = [product for product in load_products() if int(product.get("stock", 0)) > 0]
            self.send_json({"products": products})
            return

        if path == "/api/products":
            if not self.require_admin():
                return
            self.send_json({"products": load_products()})
            return

        if path == "/api/payments/config":
            key_id = os.environ.get("RAZORPAY_KEY_ID", "")
            self.send_json({"configured": bool(key_id), "key_id": key_id})
            return

        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/login":
            data = self.read_json()
            if data.get("password") != ADMIN_PASSWORD:
                self.send_json({"ok": False, "message": "Wrong password."}, status=401)
                return

            token = secrets.token_urlsafe(24)
            SESSIONS.add(token)
            self.send_json_with_cookie(
                {"ok": True, "message": "Logged in."},
                f"admin_session={token}; HttpOnly; SameSite=Strict; Path=/",
            )
            return

        if path == "/api/logout":
            self.send_json_with_cookie(
                {"ok": True, "message": "Logged out."},
                "admin_session=; Max-Age=0; SameSite=Strict; Path=/",
            )
            return

        if path == "/api/orders":
            try:
                data = self.read_json()
                required = [
                    "book_title",
                    "book_author",
                    "price",
                    "quantity",
                    "total",
                    "customer_name",
                    "phone",
                    "fulfillment_type",
                    "payment_method",
                ]
                missing = [
                    key for key in required if not str(data.get(key, "")).strip()
                ]
                if missing:
                    self.send_json(
                        {"ok": False, "message": "Please fill all order details."},
                        status=400,
                    )
                    return

                if use_postgres():
                    init_storage()
                    with get_db() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                """
                                INSERT INTO orders (
                                    book_title, book_author, price, quantity, total,
                                    items, customer_name, phone, address,
                                    fulfillment_type, pickup_slot, payment_method,
                                    payment_status, razorpay_payment_id,
                                    razorpay_order_id, status
                                )
                                VALUES (
                                    %(book_title)s, %(book_author)s, %(price)s,
                                    %(quantity)s, %(total)s, %(items)s::jsonb,
                                    %(customer_name)s, %(phone)s, %(address)s,
                                    %(fulfillment_type)s, %(pickup_slot)s,
                                    %(payment_method)s, %(payment_status)s,
                                    %(razorpay_payment_id)s, %(razorpay_order_id)s,
                                    'New'
                                )
                                RETURNING id
                                """,
                                {
                                    "book_title": data["book_title"],
                                    "book_author": data["book_author"],
                                    "price": data["price"],
                                    "quantity": int(data["quantity"]),
                                    "total": data["total"],
                                    "items": json.dumps(data.get("items", [])),
                                    "customer_name": data["customer_name"],
                                    "phone": data["phone"],
                                    "address": data.get("address", ""),
                                    "fulfillment_type": data["fulfillment_type"],
                                    "pickup_slot": data.get("pickup_slot", ""),
                                    "payment_method": data["payment_method"],
                                    "payment_status": data.get("payment_status", "Pending"),
                                    "razorpay_payment_id": data.get("razorpay_payment_id", ""),
                                    "razorpay_order_id": data.get("razorpay_order_id", ""),
                                },
                            )
                            order_id = cursor.fetchone()["id"]
                    self.send_json(
                        {
                            "ok": True,
                            "message": "Order placed successfully.",
                            "order_id": order_id,
                        },
                        status=201,
                    )
                    return

                existing_orders = read_jsonl(ORDERS_PATH)
                order_id = max([order["id"] for order in existing_orders], default=0) + 1
                append_jsonl(
                    ORDERS_PATH,
                    {
                        "id": order_id,
                        "book_title": data["book_title"],
                        "book_author": data["book_author"],
                        "price": data["price"],
                        "quantity": data["quantity"],
                        "total": data["total"],
                        "items": data.get("items", []),
                        "customer_name": data["customer_name"],
                        "phone": data["phone"],
                        "address": data.get("address", ""),
                        "fulfillment_type": data["fulfillment_type"],
                        "pickup_slot": data.get("pickup_slot", ""),
                        "payment_method": data["payment_method"],
                        "payment_status": data.get("payment_status", "Pending"),
                        "razorpay_payment_id": data.get("razorpay_payment_id", ""),
                        "razorpay_order_id": data.get("razorpay_order_id", ""),
                        "status": "New",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )

                self.send_json(
                    {
                        "ok": True,
                        "message": "Order placed successfully.",
                        "order_id": order_id,
                    },
                    status=201,
                )
            except json.JSONDecodeError:
                self.send_json({"ok": False, "message": "Invalid JSON."}, status=400)
            return

        if path == "/api/products":
            if not self.require_admin():
                return
            data = self.read_json()
            required = ["sku", "title", "author", "category", "stock", "rack", "price", "mrp"]
            missing = [key for key in required if not str(data.get(key, "")).strip()]
            if missing:
                self.send_json({"ok": False, "message": "Please fill all product fields."}, status=400)
                return

            products = load_products()
            sku = str(data["sku"]).strip().upper()
            if any(product["sku"] == sku for product in products):
                self.send_json({"ok": False, "message": "SKU already exists."}, status=409)
                return

            products.append(
                {
                    "sku": sku,
                    "title": str(data["title"]).strip(),
                    "author": str(data["author"]).strip(),
                    "category": str(data["category"]).strip(),
                    "stock": int(data["stock"]),
                    "rack": str(data["rack"]).strip(),
                    "price": int(data["price"]),
                    "mrp": int(data["mrp"]),
                    "cover": str(data.get("cover", "")).strip() or "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=700&q=80",
                    "worker_note": str(data.get("worker_note", "")).strip(),
                }
            )
            save_products(products)
            self.send_json({"ok": True, "message": "Product added."}, status=201)
            return

        if path == "/api/payments/create-order":
            data = self.read_json()
            key_id = os.environ.get("RAZORPAY_KEY_ID", "")
            key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
            if not key_id or not key_secret:
                self.send_json(
                    {
                        "ok": False,
                        "message": "Razorpay keys are not configured on the server.",
                    },
                    status=503,
                )
                return

            amount = int(data.get("amount", 0))
            if amount < 100:
                self.send_json({"ok": False, "message": "Invalid amount."}, status=400)
                return

            payload = json.dumps(
                {
                    "amount": amount,
                    "currency": "INR",
                    "receipt": f"gpb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "payment_capture": 1,
                }
            ).encode("utf-8")
            auth = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("utf-8")
            request = urllib.request.Request(
                "https://api.razorpay.com/v1/orders",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {auth}",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    self.send_json(json.loads(response.read().decode("utf-8")))
            except urllib.error.HTTPError as error:
                self.send_json(
                    {"ok": False, "message": error.read().decode("utf-8")},
                    status=error.code,
                )
            return

        self.send_json({"ok": False, "message": "Not found."}, status=404)

    def do_PATCH(self):
        path = urlparse(self.path).path
        if path.startswith("/api/orders/"):
            if not self.require_admin():
                return
            order_id = path.rsplit("/", 1)[-1]
            data = self.read_json()
            status = str(data.get("status", "")).strip()
            allowed = {"New", "Confirmed", "Packed", "Completed", "Cancelled"}
            if status not in allowed:
                self.send_json({"ok": False, "message": "Invalid status."}, status=400)
                return

            if use_postgres():
                init_storage()
                with get_db() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "UPDATE orders SET status = %s WHERE id = %s RETURNING id",
                            (status, int(order_id)),
                        )
                        updated = cursor.fetchone()
                if not updated:
                    self.send_json({"ok": False, "message": "Order not found."}, status=404)
                    return
                self.send_json({"ok": True, "message": "Status updated."})
                return

            numeric_order_id = int(order_id)
            order_exists = any(order["id"] == numeric_order_id for order in read_jsonl(ORDERS_PATH))

            if not order_exists:
                self.send_json({"ok": False, "message": "Order not found."}, status=404)
                return

            append_jsonl(
                STATUS_PATH,
                {
                    "id": numeric_order_id,
                    "status": status,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )

            self.send_json({"ok": True, "message": "Status updated."})
            return

        if path.startswith("/api/products/"):
            if not self.require_admin():
                return
            sku = path.rsplit("/", 1)[-1]
            data = self.read_json()
            products = load_products()
            for product in products:
                if product["sku"] == sku:
                    product["stock"] = int(data.get("stock", product["stock"]))
                    product["rack"] = str(data.get("rack", product["rack"]))
                    product["worker_note"] = str(data.get("worker_note", product["worker_note"]))
                    save_products(products)
                    self.send_json({"ok": True, "message": "Product updated."})
                    return

            self.send_json({"ok": False, "message": "Product not found."}, status=404)
            return

        self.send_json({"ok": False, "message": "Not found."}, status=404)


if __name__ == "__main__":
    init_storage()
    port = int(os.environ.get("PORT", "8000"))
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Ganga Pustak Bhandar running on http://{host}:{port}")
    print(f"Admin orders page: http://{host}:{port}/admin.html")
    server.serve_forever()
