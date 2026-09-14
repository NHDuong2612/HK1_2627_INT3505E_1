from flask import Flask, jsonify, request   
from uuid import uuid4
app = Flask(__name__)
app.json.sort_keys = False
_next = 1
BOOKS = [{"id":1,"title":"Clean Code","author":"R. Martin","year":2008}]
def find_by_id(book_id):
    return next((b for b in BOOKS if b["id"] == book_id), None)

# LIST - GET /books
@app.route("/books", methods=["GET"])
def list_books():
    limit=int(request.args.get("limit", 100))
    q = request.args.get("q")
    sort = request.args.get("sort")
    if q:
        result = [book for book in BOOKS if q.lower() in book["title"].lower()]
    else:
        result = BOOKS
    if sort == "title":
        result = sorted(result, key=lambda book: book["title"])
    return jsonify(result), 200

# DETAIL - GET /books/<book_id>
@app.route("/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    book = find_by_id(book_id)
    if book is None:
        return jsonify({"error": "Book khong tim thay"}), 404
    return jsonify(book), 200
@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    return jsonify({"id": item_id}), 200

# CREATE - POST /books
@app.route("/books", methods=["POST"])
def create_book():
    global _next
    body = request.get_json(silent=True) or {}
    title = body.get("title", "")
    author = body.get("author", "")
    year = body.get("year","")
    if not title or not author or not year:
        return jsonify({"error": "Title, author va year la bat buoc"}), 400
    if year < 1900:
        return jsonify({"error":"year phai >=1900"})
    _next+=1
    book = {"id": _next, "title": title, "author":body.get("author",""),"year":body.get("year", 2023)}
    BOOKS.append(book)
    return jsonify(book), 201, {"Location": f"/books/{book['id']}"}

# UPDATE - PUT /books/<book_id>
@app.route("/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    book = find_by_id(book_id)
    if not book:
        return jsonify({"error": "not fount"}), 404
    data = request.get_json(silent=True) or {}
    book.update(data or {})
    return jsonify(book), 200

# DELETE - DELETE /books/<book_id>
@app.route("/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    book = find_by_id(book_id)
    if not book:
        return jsonify({"error": "not fount"}), 404
    BOOKS.remove(book)
    return "", 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


               