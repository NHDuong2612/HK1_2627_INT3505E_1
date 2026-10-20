from app import app, init_db
from models import db, Author, Book, Category


with app.app_context():
    init_db()
    tech = Category.query.filter_by(slug="tech").first()
    if tech is None:
        tech = Category(name="Technology", slug="tech")
        db.session.add(tech)
    fiction = Category.query.filter_by(slug="fiction").first()
    if fiction is None:
        fiction = Category(name="Fiction", slug="fiction")
        db.session.add(fiction)
    author = Author.query.order_by(Author.id).first()
    if author is None:
        author = Author(name="Lab Author", bio="Sample author")
        db.session.add(author)

    samples = [
        ("9780000000101", "Flask Basics", 100000, tech),
        ("9780000000102", "REST API", 150000, tech),
        ("9780000000103", "SQLAlchemy Basics", 150000, tech),
        ("9780000000104", "Data Modeling", 300000, tech),
        ("9780000000105", "A Short Story", 150000, fiction),
    ]
    for isbn, title, price, category in samples:
        if Book.query.filter_by(isbn=isbn).first() is None:
            db.session.add(Book(title=title, isbn=isbn, price_vnd=price, stock=5,
                                category=category, authors=[author]))
    db.session.commit()
    print("Du lieu Lab 2 da san sang.")
    print(f"Technology category ID: {tech.id}")
    print(f"Fiction category ID: {fiction.id}")
