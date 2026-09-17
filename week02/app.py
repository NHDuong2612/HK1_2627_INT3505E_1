from flask import Flask, jsonify, request, Response, make_response
app = Flask(__name__)
BOOKS = []
_next_id = 1
# GET /books - list books
@app.get("/books")
def list_books():
    return jsonify({"data": BOOKS, "total": len(BOOKS)}), 200

# POST /books - create a new book
@app.post("/books")
def create_book():
    global _next_id
    data = request.get_json(silent = True) or {}
    if not request.is_json:
        return jsonify(error = "Request phai la JSON"), 415
    title = data.get("title", "")
    author = data.get("author", "")
    if not title or not author:
        return jsonify(error = "Phai co title va author"), 422
    book = {"id": _next_id, "title": title, "author": author}
    BOOKS.append(book)
    _next_id += 1
    resp = make_response(jsonify(book), 201)
    resp.headers["Location"] = f"/books/{book['id']}"
    return resp
if __name__ == "__main__":
    run = app.run(host="127.0.0.1", port = 5000, debug = True)
