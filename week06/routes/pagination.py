import base64
import binascii
import json
import re

from flask import jsonify
from sqlalchemy import and_, or_
from models import Book

SORT = {"id": Book.id, "price": Book.price_vnd, "title": Book.title, "stock": Book.stock}
MAX_INT = 9223372036854775807


def parse_sort(raw):
    fields = []
    seen = set()
    for part in raw.split(","):
        desc = part.startswith("-")
        key = part[1:] if desc else part
        if key not in SORT or key in seen:
            raise ValueError("bad_sort")
        seen.add(key)
        fields.append((key, SORT[key], desc))
    # Neu client chua chi dinh id, them id cung chieu khoa dau tien.
    if "id" not in seen:
        fields.append(("id", Book.id, fields[0][2]))
    cols = [column.desc() if desc else column.asc() for _, column, desc in fields]
    return fields, cols


def apply_cursor(query, raw, sort, fields, category, genre):
    if raw is None:
        return query
    try:
        if len(raw) > 4096 or not re.fullmatch(r"[A-Za-z0-9_-]+", raw):
            raise ValueError
        padded = raw + "=" * (-len(raw) % 4)
        cursor = json.loads(base64.b64decode(padded, altchars=b"-_", validate=True))
        if not isinstance(cursor, dict):
            raise ValueError
        if not isinstance(cursor["s"], str) or not isinstance(cursor["v"], list):
            raise ValueError
        filters = cursor["f"]
        if not isinstance(filters, dict) or set(filters) != {"category", "genre"}:
            raise ValueError
        cat = filters["category"]
        if cat is not None and (type(cat) is not int or not 1 <= cat <= MAX_INT):
            raise ValueError
        g = filters["genre"]
        if g is not None and (not isinstance(g, str) or not g or len(g) > 100):
            raise ValueError
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, binascii.Error, RecursionError):
        raise ValueError("bad_cursor") from None
    if cursor["s"] != sort:
        raise ValueError("sort_chg")
    if filters != {"category": category, "genre": genre}:
        raise ValueError("filter_chg")

    values = cursor["v"]
    if len(values) != len(fields):
        raise ValueError("bad_cursor")
    conditions = []
    equal = []
    for (name, column, desc), value in zip(fields, values):
        if name == "title":
            if not isinstance(value, str) or len(value) > 200:
                raise ValueError("bad_cursor")
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("bad_cursor") from None
        elif type(value) is not int or not (1 if name == "id" else 0) <= value <= MAX_INT:
            raise ValueError("bad_cursor")
        # A < a OR (A = a AND B > b) ... cho tung khoa ASC/DESC.
        compare = column < value if desc else column > value
        conditions.append(and_(*equal, compare))
        equal.append(column == value)
    return query.where(or_(*conditions))


def build_response(items, sort, fields, more, category, genre):
    nxt = None
    if items and more:
        last = items[-1]
        values = [getattr(last, column.key) for _, column, _ in fields]
        state = {"s": sort, "v": values, "f": {"category": category, "genre": genre}}
        nxt = base64.urlsafe_b64encode(json.dumps(state).encode()).decode().rstrip("=")
    return jsonify({
        "data": [book.to_dict() for book in items],
        "page": {"next": nxt, "more": more}
    })
