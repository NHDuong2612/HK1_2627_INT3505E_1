import json
from pathlib import Path
from flask import Blueprint, jsonify, request
from jsonschema import validate, ValidationError
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload
from models import db, Book, Author, Category, User, Review
from routes.pagination import parse_sort, apply_cursor, build_response, MAX_INT

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
    strategy = request.args.get("strategy", "cursor")
    if strategy not in ("offset", "cursor"):
        return jsonify({"error": "bad_strategy"}), 400
    if strategy == "offset" and "cursor" in request.args:
        return jsonify({"error": "cursor_with_offset"}), 400
    if strategy == "cursor" and "offset" in request.args:
        return jsonify({"error": "offset_with_cursor"}), 400

    try:
        limit = int(request.args.get("limit", "20"))
        if limit < 1:
            raise ValueError
        limit = min(limit, 100)
    except ValueError:
        return jsonify({"error": "bad_limit"}), 400

    category = request.args.get("category")
    if category is not None:
        try:
            category = int(category)
            if not 1 <= category <= MAX_INT:
                raise ValueError
        except ValueError:
            return jsonify({"error": "bad_category"}), 400

    genre = request.args.get("genre")
    if genre is not None and (not genre or genre != genre.strip() or len(genre) > 100):
        return jsonify({"error": "bad_genre"}), 400

    sort = request.args.get("sort", "-id")
    try:
        fields, cols = parse_sort(sort)
        query = select(Book)
        if category is not None:
            query = query.where(Book.category_id == category)
        if genre is not None:
            query = query.join(Category).where(Category.slug == genre)

        if strategy == "offset":
            try:
                offset = int(request.args.get("offset", "0"))
                if not 0 <= offset <= MAX_INT:
                    raise ValueError
            except ValueError:
                return jsonify({"error": "bad_offset"}), 400
            total = db.session.scalar(select(func.count()).select_from(query.subquery()))
            rows = db.session.scalars(
                query.options(joinedload(Book.category), selectinload(Book.authors))
                .order_by(*cols).offset(offset).limit(limit)
            ).all()
            return jsonify({
                "data": [book.to_dict() for book in rows],
                "pagination": {"offset": offset, "limit": limit, "total": total,
                               "has_next": offset + limit < total}
            })

        query = apply_cursor(query, request.args.get("cursor"), sort, fields, category, genre)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    # Lay du 1 sach de biet con trang sau hay khong.
    rows = db.session.scalars(
        query.options(joinedload(Book.category), selectinload(Book.authors))
        .order_by(*cols).limit(limit + 1)
    ).all()
    return build_response(rows[:limit], sort, fields, len(rows) > limit, category, genre)


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
