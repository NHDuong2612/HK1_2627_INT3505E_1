from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Bang trung gian cho quan he nhieu - nhieu.
class BookAuthor(db.Model):
    __tablename__ = "book_authors"
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), primary_key=True)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    books = db.relationship("Book", back_populates="category")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "slug": self.slug}


class Author(db.Model):
    __tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, default="")
    books = db.relationship("Book", secondary="book_authors", back_populates="authors")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "bio": self.bio}


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    price_vnd = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    category = db.relationship("Category", back_populates="books")
    authors = db.relationship("Author", secondary="book_authors", back_populates="books")
    reviews = db.relationship("Review", back_populates="book", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "isbn": self.isbn,
            "price_vnd": self.price_vnd, "stock": self.stock,
            "category": self.category.to_dict(),
            "authors": [{"id": author.id, "name": author.name} for author in self.authors]
        }


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    reviews = db.relationship("Review", back_populates="user")

    def to_dict(self):
        return {"id": self.id, "email": self.email, "display_name": self.display_name}


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, default="")
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    book = db.relationship("Book", back_populates="reviews")
    user = db.relationship("User", back_populates="reviews")

    def to_dict(self):
        return {"id": self.id, "rating": self.rating, "comment": self.comment,
                "book_id": self.book_id, "user": self.user.to_dict()}
