from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ORDERS_PATH = DATA_DIR / "orders.jsonl"
STATUS_PATH = DATA_DIR / "status-events.jsonl"
ADMIN_PASSWORD = "admin123"
SESSIONS = set()


def init_storage():
    DATA_DIR.mkdir(exist_ok=True)
    ORDERS_PATH.touch(exist_ok=True)
    STATUS_PATH.touch(exist_ok=True)


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

        self.send_json({"ok": False, "message": "Not found."}, status=404)


if __name__ == "__main__":
    init_storage()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Ganga Pustak Bhandar running at http://127.0.0.1:8000")
    print("Admin orders page: http://127.0.0.1:8000/admin.html")
    server.serve_forever()
