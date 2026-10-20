import base64
import json
import unittest

from flask import Flask
from models import db, Author, Book, Category
from routes.books import books


class PaginationTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(books, url_prefix="/api/v1/books")
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        tech = Category(name="Tech", slug="tech")
        fiction = Category(name="Fiction", slug="fiction")
        author = Author(name="Test author")
        db.session.add_all([tech, fiction, author])
        db.session.flush()
        # Ba sach trung gia, trong do co sach thuoc the loai khac.
        prices = [300000, 100000, 150000, 150000, 150000, 400000]
        for i, price in enumerate(prices, 1):
            db.session.add(Book(id=i, title=f"Book {i}", isbn=f"{i:013d}",
                                price_vnd=price, stock=1,
                                category=fiction if i == 5 else tech, authors=[author]))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()

    def page(self, **params):
        response = self.client.get("/api/v1/books", query_string=params)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_default_sort_and_last_page(self):
        body = self.page()
        self.assertEqual([book["id"] for book in body["data"]], [6, 5, 4, 3, 2, 1])
        self.assertEqual(body["page"], {"next": None, "more": False})

    def test_walk_all_sorts_with_duplicate_prices(self):
        expected = {
            "id": [1, 2, 3, 4, 5, 6], "-id": [6, 5, 4, 3, 2, 1],
            "price": [2, 3, 4, 5, 1, 6], "-price": [6, 1, 5, 4, 3, 2]
        }
        for sort, ids in expected.items():
            with self.subTest(sort=sort):
                found = []
                params = {"sort": sort, "limit": 2}
                for _ in range(4):
                    body = self.page(**params)
                    found.extend(book["id"] for book in body["data"])
                    if not body["page"]["more"]:
                        self.assertIsNone(body["page"]["next"])
                        break
                    self.assertIsNotNone(body["page"]["next"])
                    params["cursor"] = body["page"]["next"]
                self.assertEqual(found, ids)

    def test_category_is_applied_on_every_page(self):
        ids = []
        params = {"category": 1, "sort": "price", "limit": 2}
        for _ in range(4):
            body = self.page(**params)
            self.assertTrue(all(book["category"]["id"] == 1 for book in body["data"]))
            ids.extend(book["id"] for book in body["data"])
            if not body["page"]["more"]:
                break
            params["cursor"] = body["page"]["next"]
        self.assertEqual(ids, [2, 3, 4, 1, 6])
        self.assertEqual(self.page(category=999), {"data": [], "page": {"next": None, "more": False}})

    def test_bad_query_params(self):
        for sort in ["foo", "--id", "-price,title", "title", "", "id;DROP TABLE books"]:
            with self.subTest(sort=sort):
                response = self.client.get("/api/v1/books", query_string={"sort": sort})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json["error"], "bad_sort")
        for key, values in {"limit": ["0", "-1", "abc", "1.5", ""],
                            "category": ["0", "-1", "tech", "1.5", "", str(2**63)]}.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    response = self.client.get("/api/v1/books", query_string={key: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json["error"], f"bad_{key}")

    def test_default_limit_and_max_limit(self):
        for i in range(7, 108):
            db.session.add(Book(title=f"Extra {i}", isbn=f"{i:013d}", price_vnd=1,
                                stock=0, category_id=1))
        db.session.commit()
        self.assertEqual(len(self.page()["data"]), 20)
        body = self.page(limit=1000)
        self.assertEqual(len(body["data"]), 100)
        self.assertTrue(body["page"]["more"])
        end = self.page(limit=1000, cursor=body["page"]["next"])
        self.assertEqual(len(end["data"]), 7)
        self.assertFalse(end["page"]["more"])

    def test_malformed_cursor_returns_400(self):
        states = [[], {}, {"s": "-id", "v": 3, "i": True},
                  {"s": "-id", "v": "3", "i": 3}, {"s": "-id", "v": 4, "i": 3},
                  {"s": "-id", "v": 2**63, "i": 2**63},
                  {"s": "-id", "v": 3, "i": 3, "c": True}]
        tokens = ["", "not!base64", "a", "_w", "a" * 1025]
        for state in states:
            tokens.append(base64.urlsafe_b64encode(json.dumps(state).encode()).decode().rstrip("="))
        for token in tokens:
            with self.subTest(cursor=token):
                response = self.client.get("/api/v1/books", query_string={"cursor": token})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json["error"], "bad_cursor")

    def test_cursor_sort_and_category_cannot_change(self):
        cursor = self.page(limit=2, sort="price", category=1)["page"]["next"]
        for params, error in [({"sort": "-price", "category": 1}, "sort_chg"),
                              ({"sort": "price", "category": 2}, "filter_chg"),
                              ({"sort": "price"}, "filter_chg")]:
            response = self.client.get("/api/v1/books", query_string={**params, "cursor": cursor})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["error"], error)

    def test_cursor_still_works_after_anchor_book_is_deleted(self):
        cursor = self.page(limit=2, sort="price")["page"]["next"]
        response = self.client.delete("/api/v1/books/3")
        self.assertEqual(response.status_code, 204)
        body = self.page(limit=2, sort="price", cursor=cursor)
        self.assertEqual([book["id"] for book in body["data"]], [4, 5])

    def test_empty_collection(self):
        for book in Book.query.all():
            db.session.delete(book)
        db.session.commit()
        self.assertEqual(self.page(), {"data": [], "page": {"next": None, "more": False}})


if __name__ == "__main__":
    unittest.main()
