from flask import Flask, jsonify, request, Response, make_response
app = Flask(__name__)
app.json.sort_keys = False
# Tham so phan trang
DEFAULT_SIZE, MAX_SIZE = 20, 100
BOOKS = []
_next_id = 1
# list + filter + pagination + links
@app.get("/books")
def list_books():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", DEFAULT_SIZE))
    except ValueError:
        return jsonify (error = "page va size phai la so nguyen"), 400
    page = max(page, 1)
    size = max(min(size, MAX_SIZE), 1)

    # filter: author chinh xac, q trong title
    fil = BOOKS
    author = request.args.get("author")
    if author:
        fil = [b for b in fil if b["author"] == author]
    q = request.args.get("q")
    if q:
        fil = [b for b in fil if q.lower() in b["title"].lower()]

    #pagination
    total = len(fil)
    start = (page - 1) * size
    end = start + size
    items = fil[start:end]
    last = (total + size - 1) // size

    #HATEOAS links
    def u(p):
        return f"/books?page={p}&size={size}"
    links = {"self": {"href": u(page)}, "first": {"href": u(1)}, "last": {"href": u(max(1, last))}}
    if page > 1:
        links["prev"] = {"href": u(page - 1)}
    if end < total:
        links["next"] = {"href" : u(page + 1)}
    body = {"data": items,
             "pagination": {"page": page, "size": size, "total": total, "total_pages": last},
               "_links": links}
    resp = make_response(jsonify(body), 200)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp

# GET /books/<book_id> - cache 60s
@app.get("/books/<int:book_id>")
def get_book(book_id):
    book = next((b for b in BOOKS if b["id"] == book_id), None)
    if not book:
        return jsonify(error = "Khong tim thay book"), 404
    resp = make_response(jsonify(book), 200)
    resp.headers["Cache=Control"] = "max-age=60"
    return resp

# PUT /books/<book_id> - update toan bo field
@app.put("/books/<int:book_id>")
def put(book_id):
    book = next((b for b in BOOKS if b["id"] == book_id), None)
    if not book:
        return jsonify(error = "Khong tim thay book"), 404
    data = request.get_json(silent = True) or {}
    if not request.is_json:
        return jsonify(error = "Request phai la JSON"), 415
    title = data.get("title", "")
    author = data.get("author", "")
    isbn = data.get("isbn", "")
    price = data.get("price", 0)
    if not title or not author or not isbn or price < 0:
        return jsonify(error = "Phai co du cac field"), 422
    book.update(data or {})
    return jsonify(book), 200

# PATCH /books/<book_id> - update 1 so field
@app.patch("/books/<int:book_id>")
def patch(book_id):
    book = next((b for b in BOOKS if b["id"] == book_id), None)
    if not book:
        return jsonify(error = "Khong tim thay book"), 404
    data = request.get_json(silent = True) or {}
    if not request.is_json:
        return jsonify(error = "Request phai la JSON"), 415
    if data.get("price", 0) < 0:
        return jsonify(error = "Price phai >= 0"), 422
    book.update(data or {})
    return jsonify(book), 200

# DELETE /books/<book_id> - delete book
@app.delete("/books/<int:book_id>")
def delete(book_id):
    book = next((b for b in BOOKS if b["id"] == book_id), None)
    if not book:
        return jsonify(error = "Khong tim thay book"), 404
    BOOKS.remove(book)
    return "", 204

# POST /books - create a new book
@app.post("/books")
def create_book():
    global _next_id
    data = request.get_json(silent = True) or {}
    if not request.is_json:
        return jsonify(error = "Request phai la JSON"), 415
    title = data.get("title", "")
    author = data.get("author", "")
    isbn = data.get("isbn", "")
    price = data.get("price", 0)
    if price < 0:
        return jsonify(error = "Price phai >= 0"), 422
    if not title or not author or not isbn:
        return jsonify(error = "Phai co du cac field"), 422
    book = {"id": _next_id, "title": title, "author": author, "isbn": isbn, "price": price}
    BOOKS.append(book)
    _next_id += 1
    resp = make_response(jsonify(book), 201)
    resp.headers["Location"] = f"/books/{book['id']}"
    return resp
if __name__ == "__main__":
    run = app.run(host="127.0.0.1", port = 5000, debug = True)
