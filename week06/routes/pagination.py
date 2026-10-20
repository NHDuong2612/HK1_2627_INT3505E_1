import base64
import binascii
import json
import re

from flask import jsonify
from sqlalchemy import tuple_
from models import Book

SORT = {"id": Book.id, "price": Book.price_vnd}
MAX_INT = 9223372036854775807


def parse_sort(raw):
    desc = raw.startswith("-")
    key = raw[1:] if desc else raw
    if key not in SORT:
        raise ValueError("bad_sort")
    p = SORT[key]
    cols = [p.desc(), Book.id.desc()] if desc else [p.asc(), Book.id.asc()]
    return p, cols, desc


def apply_cursor(query, raw, sort, p, desc, category):
    if raw is None:
        return query
    try:
        if len(raw) > 1024 or not re.fullmatch(r"[A-Za-z0-9_-]+", raw):
            raise ValueError
        padded = raw + "=" * (-len(raw) % 4)
        cursor = json.loads(base64.b64decode(padded, altchars=b"-_", validate=True))
        if not isinstance(cursor, dict):
            raise ValueError
        value, book_id = cursor["v"], cursor["i"]
        if type(value) is not int or not 0 <= value <= MAX_INT:
            raise ValueError
        if type(book_id) is not int or not 1 <= book_id <= MAX_INT:
            raise ValueError
        if sort.lstrip("-") == "id" and value != book_id:
            raise ValueError
        cat = cursor.get("c")
        if cat is not None and (type(cat) is not int or not 1 <= cat <= MAX_INT):
            raise ValueError
        if not isinstance(cursor.get("s"), str):
            raise ValueError
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, binascii.Error):
        raise ValueError("bad_cursor") from None
    if cursor["s"] != sort:
        raise ValueError("sort_chg")
    if cat != category:
        raise ValueError("filter_chg")

    # Gia trung nhau thi so sanh them id de khong lap/bo sot sach.
    key = tuple_(p, Book.id)
    condition = key < (value, book_id) if desc else key > (value, book_id)
    return query.where(condition)


def build_response(items, sort, p, more, category):
    nxt = None
    if items and more:
        last = items[-1]
        state = {"s": sort, "v": getattr(last, p.key), "i": last.id, "c": category}
        nxt = base64.urlsafe_b64encode(json.dumps(state).encode()).decode().rstrip("=")
    return jsonify({
        "data": [book.to_dict() for book in items],
        "page": {"next": nxt, "more": more}
    })
