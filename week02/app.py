from flask import Flask, jsonify, request, Response, make_response
app = Flask(__name__)
BOOKS = []
_next_id = 1
# GET /books - list books
@app.get("/books")
def list_books():
    return jsonify({"data": BOOKS, "total": len(BOOKS)}), 200

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
