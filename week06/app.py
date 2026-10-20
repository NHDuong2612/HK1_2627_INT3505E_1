from flask import Flask, jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException
from models import db, Book, Author, Category, User
from routes.books import books

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lab1.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.sort_keys = False
db.init_app(app)
app.register_blueprint(books, url_prefix="/api/v1/books")


@app.get("/api/v1/authors")
def get_authors():
    return jsonify([author.to_dict() for author in Author.query.all()])


@app.get("/api/v1/categories")
def get_categories():
    return jsonify([category.to_dict() for category in Category.query.all()])


@app.get("/api/v1/users")
def get_users():
    return jsonify([user.to_dict() for user in User.query.all()])


@app.get("/api/v1/authors/<int:author_id>/books")
def get_author_books(author_id):
    author = db.session.get(Author, author_id)
    if author is None:
        return jsonify({"error": "Khong tim thay tac gia"}), 404
    return jsonify([book.to_dict() for book in author.books])


@app.errorhandler(IntegrityError)
def database_error(error):
    db.session.rollback()
    return jsonify({"error": "Du lieu bi trung hoac khong hop le"}), 409


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify({"error": error.description}), error.code


def init_db():
    db.create_all()
    # Them du lieu mau de chay thu lan dau.
    if Category.query.count() == 0:
        category = Category(name="Technology", slug="tech")
        author = Author(name="Robert C. Martin", bio="Software developer")
        user = User(email="an@example.com", display_name="An")
        book = Book(title="Clean Code", isbn="9780132350884",
                    price_vnd=450000, stock=10, category=category,
                    authors=[author])
        db.session.add_all([category, author, user, book])
        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
