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
        for sort in ["foo", "--id", "price,price", "id,-id", "price,", "", "id;DROP TABLE books"]:
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
        filters = {"category": None, "genre": None}
        states = [[], {}, {"s": "-id", "v": 3, "f": filters},
                  {"s": "-id", "v": [True], "f": filters},
                  {"s": "-id", "v": ["3"], "f": filters},
                  {"s": "-id", "v": [2**63], "f": filters},
                  {"s": "-id", "v": [0], "f": filters},
                  {"s": "-id", "v": [3, 4], "f": filters},
                  {"s": "-id", "v": [3], "f": {"category": True, "genre": None}}]
        tokens = ["", "not!base64", "a", "_w", "a" * 1025]
        nested = "[" * 1100 + "0" + "]" * 1100
        tokens.append(base64.urlsafe_b64encode(nested.encode()).decode().rstrip("="))
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

    def walk_cursor(self, **params):
        ids = []
        for _ in range(10):
            body = self.page(strategy="cursor", limit=2, **params)
            ids.extend(book["id"] for book in body["data"])
            if not body["page"]["more"]:
                self.assertIsNone(body["page"]["next"])
                self.assertEqual(len(ids), len(set(ids)))
                return ids
            params["cursor"] = body["page"]["next"]
        self.fail("Cursor khong ket thuc")

    def test_multi_sort_with_mixed_directions_and_ties(self):
        for book_id, title in [(3, "Zebra"), (4, "Alpha"), (5, "Alpha")]:
            db.session.get(Book, book_id).title = title
        db.session.commit()
        orders = {
            "price,title": [2, 4, 5, 3, 1, 6],
            "-price,title": [6, 1, 5, 4, 3, 2],
            "price,-title,-id": [2, 3, 5, 4, 1, 6],
            "title,-id,price": [5, 4, 1, 2, 6, 3]
        }
        for sort, expected in orders.items():
            with self.subTest(sort=sort):
                self.assertEqual(self.walk_cursor(sort=sort), expected)
                offset_ids = []
                for offset in [0, 2, 4]:
                    body = self.page(strategy="offset", sort=sort, offset=offset, limit=2)
                    offset_ids.extend(book["id"] for book in body["data"])
                    self.assertEqual(body["pagination"]["total"], 6)
                self.assertEqual(offset_ids, expected)

    def test_genre_filter_for_both_strategies(self):
        for strategy in ["cursor", "offset"]:
            with self.subTest(strategy=strategy):
                body = self.page(strategy=strategy, genre="fiction", sort="price,title")
                self.assertEqual([book["id"] for book in body["data"]], [5])
                body = self.page(strategy=strategy, genre="fiction", category=1)
                self.assertEqual(body["data"], [])
                body = self.page(strategy=strategy, genre="not-found")
                self.assertEqual(body["data"], [])
        self.assertEqual(self.walk_cursor(genre="tech", sort="price,title"), [2, 3, 4, 1, 6])

    def test_offset_metadata_and_out_of_range(self):
        body = self.page(strategy="offset", genre="tech", sort="id", limit=2)
        self.assertEqual([book["id"] for book in body["data"]], [1, 2])
        self.assertEqual(body["pagination"], {"offset": 0, "limit": 2, "total": 5, "has_next": True})
        body = self.page(strategy="offset", genre="tech", sort="id", offset=4, limit=2)
        self.assertEqual([book["id"] for book in body["data"]], [6])
        self.assertFalse(body["pagination"]["has_next"])
        body = self.page(strategy="offset", genre="tech", offset=100, limit=2)
        self.assertEqual(body["data"], [])
        self.assertEqual(body["pagination"]["total"], 5)
        self.assertFalse(body["pagination"]["has_next"])
        body = self.page(strategy="offset", genre="not-found")
        self.assertEqual(body["pagination"], {"offset": 0, "limit": 20, "total": 0, "has_next": False})

    def test_homework_bad_params(self):
        cases = [({"strategy": "foo"}, "bad_strategy"),
                 ({"strategy": "offset", "cursor": "abc"}, "cursor_with_offset"),
                 ({"offset": 0}, "offset_with_cursor")]
        for value in ["-1", "abc", "1.5", "", str(2**63)]:
            cases.append(({"strategy": "offset", "offset": value}, "bad_offset"))
        for genre in ["", " ", "tech ", "x" * 101]:
            cases.append(({"genre": genre}, "bad_genre"))
        for params, error in cases:
            with self.subTest(params=params):
                response = self.client.get("/api/v1/books", query_string=params)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json["error"], error)

    def test_cursor_bound_to_genre_and_full_sort(self):
        cursor = self.page(genre="tech", sort="-price,title", limit=2)["page"]["next"]
        for params, error in [({"genre": "fiction", "sort": "-price,title"}, "filter_chg"),
                              ({"genre": "tech", "sort": "-price,-title"}, "sort_chg")]:
            response = self.client.get("/api/v1/books", query_string={**params, "cursor": cursor})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["error"], error)
        # Doi limit duoc phep; trang sau van tiep tuc dung vi tri.
        body = self.page(genre="tech", sort="-price,title", cursor=cursor, limit=1)
        self.assertEqual([book["id"] for book in body["data"]], [3])

    def test_stock_and_unicode_title_sort(self):
        db.session.get(Book, 3).title = "Tiếng Việt"
        db.session.get(Book, 4).title = "Tiếng Việt"
        db.session.get(Book, 2).stock = 0
        db.session.commit()
        for sort in ["stock,-title", "-title,price", "price,stock,-title,id"]:
            with self.subTest(sort=sort):
                all_books = self.page(strategy="offset", sort=sort)["data"]
                self.assertEqual(self.walk_cursor(sort=sort), [book["id"] for book in all_books])

    def test_offset_limit_defaults_and_cap(self):
        body = self.page(strategy="offset")
        self.assertEqual(body["pagination"]["limit"], 20)
        body = self.page(strategy="offset", limit=999)
        self.assertEqual(body["pagination"]["limit"], 100)

    def test_cursor_rejects_wrong_multi_sort_value_types(self):
        for values in [[100000, 42, 2], [100000, "Alpha"],
                       [True, "Alpha", 2], [100000, "Alpha", -1],
                       [100000, "\ud800", 2]]:
            state = {"s": "price,title", "v": values,
                     "f": {"category": None, "genre": None}}
            token = base64.urlsafe_b64encode(json.dumps(state).encode()).decode().rstrip("=")
            response = self.client.get("/api/v1/books", query_string={"sort": "price,title", "cursor": token})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json["error"], "bad_cursor")


if __name__ == "__main__":
    unittest.main()
