import json
from pathlib import Path
from flask import Blueprint, jsonify, request
from jsonschema import validate, ValidationError
from models import db, Book, Author, Category, User, Review

books = Blueprint("books", __name__)
with open(Path(__file__).resolve().parents[1] / "schemas/book.json", encoding="utf-8") as f:
    book_schema = json.load(f)


def check_book_data(data):
    try:
        validate(instance=data, schema=book_schema)
    except ValidationError as error:
        return error.message
    if db.session.get(Category, data["category_id"]) is None:
        return "Category khong ton tai"
    for author_id in data["author_ids"]:
        if db.session.get(Author, author_id) is None:
            return "Author khong ton tai"
    return None


@books.get("")
def get_books():
    return jsonify([book.to_dict() for book in Book.query.all()])


@books.get("/<int:book_id>")
def get_book(book_id):
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Khong tim thay sach"}), 404
    return jsonify(book.to_dict())


@books.post("")
def create_book():
    data = request.get_json()
    error = check_book_data(data)
    if error:
        return jsonify({"error": error}), 400
    if Book.query.filter_by(isbn=data["isbn"]).first():
        return jsonify({"error": "ISBN da ton tai"}), 409
    book = Book(title=data["title"], isbn=data["isbn"], price_vnd=data["price_vnd"],
                stock=data.get("stock", 0), category_id=data["category_id"])
    book.authors = [db.session.get(Author, author_id) for author_id in data["author_ids"]]
    db.session.add(book)
    db.session.commit()
    return jsonify(book.to_dict()), 201, {"Location": f"/api/v1/books/{book.id}"}


@books.put("/<int:book_id>")
def update_book(book_id):
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Khong tim thay sach"}), 404
    data = request.get_json()
    error = check_book_data(data)
    if error:
        return jsonify({"error": error}), 400
    other = Book.query.filter_by(isbn=data["isbn"]).first()
    if other and other.id != book_id:
        return jsonify({"error": "ISBN da ton tai"}), 409
    book.title = data["title"]
    book.isbn = data["isbn"]
    book.price_vnd = data["price_vnd"]
    book.stock = data.get("stock", 0)
    book.category_id = data["category_id"]
    book.authors = [db.session.get(Author, author_id) for author_id in data["author_ids"]]
    db.session.commit()
    return jsonify(book.to_dict())


@books.delete("/<int:book_id>")
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Khong tim thay sach"}), 404
    db.session.delete(book)
    db.session.commit()
    return "", 204


@books.get("/<int:book_id>/authors")
def get_book_authors(book_id):
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Khong tim thay sach"}), 404
    return jsonify([author.to_dict() for author in book.authors])


@books.get("/<int:book_id>/reviews")
def get_reviews(book_id):
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Khong tim thay sach"}), 404
    return jsonify([review.to_dict() for review in book.reviews])


@books.post("/<int:book_id>/reviews")
def create_review(book_id):
    book = db.session.get(Book, book_id)
    if book is None:
        return jsonify({"error": "Khong tim thay sach"}), 404
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Can gui JSON object"}), 400
    rating = data.get("rating")
    user_id = data.get("user_id")
    if type(rating) is not int or not 1 <= rating <= 5:
        return jsonify({"error": "Rating phai la so nguyen tu 1 den 5"}), 400
    if type(user_id) is not int or not 1 <= user_id <= 2147483647:
        return jsonify({"error": "User ID khong hop le"}), 400
    if db.session.get(User, user_id) is None:
        return jsonify({"error": "User khong ton tai"}), 400
    if not isinstance(data.get("comment", ""), str):
        return jsonify({"error": "Comment phai la chuoi"}), 400
    review = Review(rating=rating, comment=data.get("comment", ""), book_id=book_id, user_id=user_id)
    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201
