from flask import Flask, jsonify, request, Response, make_response
import sqlite3
import hashlib
app = Flask(__name__)
DB_NAME = "books.db"
app.json.sort_keys = False
# Tham so phan trang
DEFAULT_SIZE, MAX_SIZE = 20, 100

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    isbn TEXT NOT NULL,
                    price REAL NOT NULL,
                    etag TEXT
                    )
                """)
    conn.commit()
    conn.close()

def compute_etag(title, author, isbn, price):
    content = f"{title}:{author}:{isbn}:{price}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


#  filter + pagination + links
@app.get("/books")
def list_books():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", DEFAULT_SIZE))
    except ValueError:
        return jsonify (error = "page va size phai la so nguyen"), 400
    page = max(page, 1)
    size = max(min(size, MAX_SIZE), 1)

    where_clauses = []
    params = []

    author = request.get("author")
    if author:
        where_clauses.append("author = ?")
        params.append(author)

    q = request.get("q")
    if q:
        where_clauses.append("LOWER(title) LIKE ?")
        params.append(f"%{q.lower()}%")

    where_str = f"WHERE {' AND'.join(where_clauses)}" if where_clauses else ""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM books {where_str}", params)
    total = cursor.fetchone()[0]

    offset = (page - 1) * size
    cursor.execute(f"SELECT * FROM books {where_str} LIMIT ? OFFSET?", params + [size, offset])
    rows = cursor.fetchall()
    items = [dict(row) for row in rows]
    conn.close()
    total_pages = (total + size -1) // size

    def u(p):
        return f"/books?page={p}&size={size}"
    links = {"self": {"href": u(page)}, "first": {"href": u(1)}, "last": {"href": u(max(1,total_pages))}}
    if page > 1:
        links["prev"] = {"href": u(page - 1)}
    if page < total_pages and total > 0:
        links["next"] = {"href": u(page + 1)}

    body = {
        "data": items,
        "pagination": {"page": page, "size": size, "total": total, "total_pages": total_pages},
        "_links": links
    }

    resp = make_response(jsonify(body), 200)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp

# GET /books/<book_id> - cache 60s
@app.get("/books/<int:book_id>")
def get_book(book_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify(error = "khong tim thay book"), 404
    book = dict(row)
    etag = book.pop("etag", None)
    if not etag:
        etag = compute_etag(book["title"], book["author"], book["isbn"], book["price"])
    if_none_match = request.headers.get("If_None_Match")
    if if_none_match and if_none_match.strip('"') == etag:
        resp = make_response("", 304)
        resp.headers["ETag"] = f'"{etag}"'
        return resp
    resp = make_response(jsonify(book), 200)
    resp.headers["Cache-Control"] = "max-age=60"
    resp.headers["ETag"] = f'"{etag}"'
    return resp

# PUT /books/<book_id> - update toan bo field
@app.put("/books/<int:book_id>")
def update_book(book_id):
    if not request.is_json:
        return jsonify(error="Request phai la JSON"), 415

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    author = str(data.get("author", "")).strip()
    isbn = str(data.get("isbn", "")).strip()
    price = data.get("price")

    if not title or not author or not isbn or price is None or price < 0:
        return jsonify(error="Phai co du cac field hop le"), 422

    etag = compute_etag(title, author, isbn, price)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM books WHERE id = ?", (book_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify(error="Khong tim thay book"), 404

    cursor.execute(
        "UPDATE books SET title = ?, author = ?, isbn = ?, price = ?, etag = ? WHERE id = ?",
        (title, author, isbn, price, etag, book_id),
    )
    conn.commit()

    cursor.execute(
        "SELECT id, title, author, isbn, price FROM books WHERE id = ?",
        (book_id,),
    )
    updated_book = dict(cursor.fetchone())
    conn.close()

    return jsonify(updated_book), 200
# PATCH /books/<book_id> - update 1 so field
@app.patch("/books/<int:book_id>")
def patch_book(book_id):
    if not request.is_json:
        return jsonify(error="Request phai la JSON"), 415

    data = request.get_json(silent=True) or {}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, author, isbn, price FROM books WHERE id = ?", (book_id,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify(error="Khong tim thay book"), 404

    current_book = dict(row)
    fields, params = [], []

    if "title" in data:
        fields.append("title = ?")
        params.append(str(data["title"]).strip())
        current_book["title"] = str(data["title"]).strip()

    if "author" in data:
        fields.append("author = ?")
        params.append(str(data["author"]).strip())
        current_book["author"] = str(data["author"]).strip()

    if "isbn" in data:
        fields.append("isbn = ?")
        params.append(str(data["isbn"]).strip())
        current_book["isbn"] = str(data["isbn"]).strip()

    if "price" in data:
        try:
            p_val = float(data["price"])
            if p_val < 0:
                conn.close()
                return jsonify(error="Price phai >= 0"), 422
            fields.append("price = ?")
            params.append(p_val)
            current_book["price"] = p_val
        except ValueError:
            conn.close()
            return jsonify(error="Price phai la so"), 422

    if not fields:
        conn.close()
        return jsonify(error="Khong co field hop le de update"), 422

    # Tính toán lại ETag mới
    new_etag = compute_etag(
        current_book["title"],
        current_book["author"],
        current_book["isbn"],
        current_book["price"],
    )
    fields.append("etag = ?")
    params.append(new_etag)

    params.append(book_id)
    cursor.execute(f"UPDATE books SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()

    cursor.execute(
        "SELECT id, title, author, isbn, price FROM books WHERE id = ?",
        (book_id,),
    )
    updated_book = dict(cursor.fetchone())
    conn.close()

    return jsonify(updated_book), 200

# DELETE /books/<book_id> - delete book
@app.delete("/books/<int:book_id>")
def delete_book(book_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()

    if deleted_count == 0:
        return jsonify(error="Khong tim thay book"), 404

    return "", 204

# POST /books - create a new book
@app.post("/books")
def create_book():
    data = request.get_json(silent=True) or {}
    if not request.is_json:
        return jsonify(error = "Request phai la JSON"), 415
    title = data.get("title")
    author = data.get("author")
    isbn = data.get("isbn")
    price = data.get("price")

    if not title or not author:
        return jsonify(error = "title va author la bat buoc"), 422
    etag = compute_etag(title, author, isbn, price)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO books (title, author, isbn, price, etag) VALUES (?, ?, ?, ?, ?)",
                   (title, author, isbn, price, etag),)
    conn.commit()
    new_book_id = cursor.lastrowid

    cursor.execute("SELECT * FROM books WHERE id = ?", (new_book_id,),)
    new_book = dict(cursor.fetchone())
    conn.close()
    resp = make_response(jsonify(new_book), 201)
    resp.headers["Location"] = f"/books/{new_book_id}"
    return resp




"""
@app.get("/orders")
def list_orders():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", DEFAULT_SIZE))
    except ValueError:
        return jsonify(error = "page va size phai la so nguyen"), 400
    
    page = max(page, 1)
    size = max(min(size, MAX_SIZE), 1)

    customer_name = request.args.get("customer_name")
    q = request.args.get("q")

    where_clauses = []
    params = []
    if customer_name:
        where_clauses.append("customer_name = ?")
        params.append(customer_name)
    if q:
        where_clauses.append("product_name LIKE ? OR customer_name LIKE ?")
        params.append([f"%{q}%", f"%{q}%"])
    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM orders {where_str}", params)
    total = cursor.fetchone()[0]

    offset = (page - 1) * size
    cursor.execute(f"SELECT * FROM orders {where_str} LIMIT ? OFFSET ?", params + [size, offset])
    rows = cursor.fetchall()
    items = [dict(row) for row in rows]
    conn.close()
    total_pages = (total + size - 1) // size

    def u(p):
        return f"/orders?page={p}&size={size}"
    links = {"self": {"href": u(page)}, "first": {"href": u(1)}, "last": {"href": u(max(1, total_pages))}}
    if page > 1:
        links["prev"] = {"href": u(page - 1)}
    if page < total_pages and total > 0:
        links["next"] = {"href": u(page + 1)}

    body = {
        "data": items,
        "pagination": {"page": page, "size": size, "total": total, "total_pages": total_pages},
        "_links": links
    }
    resp = make_response(jsonify(body), 200)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp

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

"""

if __name__ == "__main__":
    init_db()
    run = app.run(host="127.0.0.1", port = 5000, debug = True)