from flask import Flask, jsonify, request   
from uuid import uuid4
app = Flask(__name__)
app.json.sort_keys = False
BOOKS = []
def find_by_id(book_id):
    return next((b for b in BOOKS if b["id"] == book_id), None)
@app.route("/books/<book_id>", methods=["GET"])
def get_book(book_id):
    book = find_by_id(book_id)
    if book is None:
        return jsonify({"error": "Book khong tim thay"}), 404
    return jsonify(book), 200
@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    return jsonify({"id": item_id}), 200
@app.route("/books", methods=["POST"])
def create_book():
    body = request.get_json(silent=True) or {}
    title = body.get("t", "")
    id = body.get("id", "")
    if not title or not id:
        return jsonify({"error": "Title va id la bat buoc"}), 400
    book = {"id": id, "t": title, "author":body.get("author","") }
    BOOKS.append(book)
    return jsonify({"id":book["id"], "t": book["t"], "author": book["author"]}), 201
@app.route("/books", methods=["GET"])
def list_books():
    limit=int(request.args.get("limit", 20))
    q=request.args.get("q","").strip().lower()
    items=[b for b in BOOKS if q in b["t"].lower()]
    return jsonify({"items": items}), 200
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
               