"""
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from errors import ApiProblem

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db = SQLAlchemy(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email
        }

@app.errorhandler(ApiProblem)
def handle_api_problem(error):
    return ApiProblem._problem(
        error.status_code,
        error.title,
        error.detail,
        error.type.split("/")[-1] if error.type else None,
        **error.extra
    )

@app.get("/users/<int:uid>")
def get_user(uid):
    user = User.query.get(uid)
    if not user:
        raise ApiProblem(
            status_code=404,
            title="User not found",
            type_path="user-not-found",
            resource_id=uid,
        )
    return jsonify(user.to_dict())

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", port=5000, debug=True)
"""
from flask import Flask, jsonify, request, Response, make_response
import sqlite3
import hashlib
import base64
import json
app = Flask(__name__)
DB_NAME = "orders.db"
app.json.sort_keys = False
# Tham so phan trang
DEFAULT_SIZE, MAX_SIZE = 20, 100

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            customer_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            etag TEXT
        )
    """)

    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(orders)").fetchall()
    }

    if "customer_id" not in existing_columns:
        conn.execute("ALTER TABLE orders ADD COLUMN customer_id INTEGER")

    if "status" not in existing_columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'"
        )

    if "etag" not in existing_columns:
        conn.execute("ALTER TABLE orders ADD COLUMN etag TEXT")

    conn.commit()
    conn.close()

def compute_etag(title, author, isbn, price):
    content = f"{title}:{author}:{isbn}:{price}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def encode_cursor(sort_value, order_id):
    cursor_data = {
        "sort_value": sort_value,
        "id": order_id,
    }
    raw = json.dumps(cursor_data).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor):
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))

        if "sort_value" not in data or "id" not in data:
            raise ValueError("Cursor thieu du lieu")

        return data["sort_value"], int(data["id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise ValueError("cursor khong hop le")

@app.get("/orders")
def list_orders():
    try:
        limit = int(request.args.get("limit", DEFAULT_SIZE))
    except ValueError:
        return jsonify(error="limit phai la so nguyen"), 400

    if limit < 1 or limit > MAX_SIZE:
        return jsonify(
            error=f"limit phai nam trong khoang {MAX_SIZE}"
        ), 400
    
    allowed_sort_fields = {
        "id": "id",
        "price": "price",
        "quantity": "quantity",
        "customer_name": "customer_name",
    }
    sort_arg = request.args.get("sort", "id")
    descending = sort_arg.startswith("-")
    sort_name = sort_arg[1:] if descending else sort_arg

    if sort_name not in allowed_sort_fields:
        allowed = ", ".join(allowed_sort_fields)
        return jsonify(error=f"sort phai la 1 trong: {allowed}"), 400

    sort_column = allowed_sort_fields[sort_name]
    direction = "DESC" if descending else "ASC"
    comparison = "<" if descending else ">"
    where_clauses = []
    params = []
    status = request.args.get("status")
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    customer_id = request.args.get("customer_id")
    if customer_id is not None:
        try:
            customer_id = int(customer_id)
        except ValueError:
            return jsonify(error="customer_id phai la so nguyen"), 400
        where_clauses.append("customer_id = ?")
        params.append(customer_id)
    cursor_token = request.args.get("cursor")
    if cursor_token:
        try:
            last_sort_value, last_id = decode_cursor(cursor_token)
        except ValueError as error:
            return jsonify(error=str(error)), 400

        where_clauses.append(
            f"({sort_column} {comparison} ? "
            f"OR ({sort_column} = ? AND id {comparison} ?))"
        )
        params.extend([last_sort_value, last_sort_value, last_id])
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    allowed_fields = {
        "id",
        "customer_id",
        "customer_name",
        "product_name",
        "quantity",
        "price",
        "status",
        "etag",
    }
    fields_arg = request.args.get("fields")
    if fields_arg:
        fields = [field.strip() for field in fields_arg.split(",") if field.strip()]
        invalid_fields = set(fields) - allowed_fields
        if invalid_fields:
            return jsonify(
                error=f"field khong hop le: {', '.join(sorted(invalid_fields))}"
            ), 400

        if not fields:
            return jsonify(error="fields phai chua it nhat 1 field"), 400
        if "id" not in fields:
            fields.insert(0, "id")
    else:
        fields = [
            "id",
            "customer_id",
            "customer_name",
            "product_name",
            "quantity",
            "price",
            "status",
            "etag",
        ]
    select_sql = ", ".join(fields)
    conn = get_db()
    try:
        sql = f"""
            SELECT {select_sql}
            FROM orders
            {where_sql}
            ORDER BY {sort_column} {direction}, id {direction}
            LIMIT ?
        """
        rows = conn.execute(sql, params + [limit + 1]).fetchall()
    finally:
        conn.close()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [dict(row) for row in rows]
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = encode_cursor(last_row[sort_column], last_row["id"])
    return jsonify({
        "data": items,
        "page": {
            "limit": limit,
            "next_cursor": next_cursor,
        },
    }), 200

@app.get("/orders/<int:order_id>")
def get_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify(error="Khong tim thay order"), 404
    order = dict(row)
    resp = make_response(jsonify(order), 200)
    resp.headers["Cache-Control"] = "max-age=60"
    return resp

@app.post("/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    if not request.is_json:
        return jsonify(error="Request phai la JSON"), 415
    customer_name = data.get("customer_name", "")
    product_name = data.get("product_name", "")
    quantity = data.get("quantity", 0)
    price = data.get("price", 0.0)
    if not customer_name or not product_name or quantity <= 0 or price < 0:
        return jsonify(error="Phai co du cac field"), 422

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (customer_name, product_name, quantity, price) VALUES (?, ?, ?, ?)",
        (customer_name, product_name, quantity, price)
    )
    conn.commit()
    new_order_id = cursor.lastrowid
    cursor.execute("SELECT * FROM orders WHERE id = ?", new_order_id)
    new_order = dict(new_order_id)
    conn.close()
    resp = make_response(jsonify(new_order), 201)
    resp.headers["Location"] = f"/orders/{new_order_id}"
    return resp

@app.put("/orders/<int:oid>")
def update_order(oid):
    if not request.is_json:
        return jsonify(error = "Request phai la JSON"), 415
    data = request.get_json(silent = True) or {}
    customer_name = data.get("customer_name", "") 
    product_name = data.get("product_name", "")
    quantity =data.get("quantity")
    price = data.get("price")

    if not customer_name or not product_name or not quantity or not price or price < 0:
        return jsonify(error = "phai co du cac field"), 422

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM orders WHERE id=?", (oid,))
    if not cursor.fetchone():
        conn.close()
        return jsonify(error = "khong tim thay id"), 404
    cursor.execute("UPDATE orders SET cursor_name = ?, product_name = ?, quantity = ?, price = ? WHERE id = ?",
                   (customer_name, product_name, quantity, price, oid)
                   )
    conn.commit()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (oid,))
    updated_order = dict(cursor.fetchone())
    conn.close()
    return jsonify(updated_order), 200

@app.patch("/orders/<int:oid>")
def patch_order(oid):
    if not request.is_json:
        return jsonify(error = "request phai la JSON"), 415
    data = request.get_json(silent = True) or {}
    conn = get_db()
    cursor = conn.sursor()
    cursor.execute("SELECT * FROM orders WHERE id =?", (oid,))
    if not cursor.fetchone():
        conn.close()
        return jsonify(error = "khong tim thay id"), 404
    fields, params = [], []

    if "customer_name" in data:
        fields.append("customer_name = ?")
        params.append(str(data["customer_name"]).strip())
    if "product_name" in data:
        fields.append("product_name = ?")
        params.append(str(data["product_name"]).strip())
    if "quantity" in data:
        q_val = int(data["quantity"])
        if q_val <= 0:
            conn.close()
            return jsonify(error="Quantity phai > 0"), 422
        fields.append("quantity = ?")
        params.append(q_val)
    if "price" in data:
        p_val = float(data["price"])
        if p_val < 0:
            conn.close()
            return jsonify(error="Price phai >= 0"), 422
        fields.append("price = ?")
        params.append(p_val)

    if not fields:
        conn.close()
        return jsonify(error="Khong co field hop le de update"), 422

    params.append(oid)
    cursor.execute(f"UPDATE orders SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()

    cursor.execute("SELECT * FROM orders WHERE id = ?", (oid,))
    updated_order = dict(cursor.fetchone())
    conn.close()

    return jsonify(updated_order), 200
    
@app.delete("/orders/<int:oid>")
def delete_order(oid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id =?", (oid,))
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    if deleted_count == 0:
        return jsonify(error = "khong tim thay id"), 404
    return "", 204

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
