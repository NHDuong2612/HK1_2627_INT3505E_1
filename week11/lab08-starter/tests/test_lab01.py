"""LAB 1 - add your five tests here. Do not delete the smoke tests.

A. GET /books, empty database -> HTTP 200 and []
B. GET /books/9999 -> HTTP 404, JSON code == NOT_FOUND
C. POST /books with only author -> HTTP 400, errors contains title
D. POST valid book, DELETE it, GET same id -> HTTP 404
BONUS. Validate a Book response using JSON Schema; add an unknown
       field to a *copy* of the response and assert ValidationError.

Useful imports:
    from jsonschema import validate, ValidationError
    import pytest
    from tools import get_book_schema

Do not depend on test execution order. Fixtures: client, app, sample_book.
"""

import pytest
from jsonschema import ValidationError, validate

from tools import get_book_schema


def test_list_books_returns_empty_array(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_missing_book_returns_not_found(client):
    response = client.get("/books/9999")
    assert response.status_code == 404
    assert response.get_json()["code"] == "NOT_FOUND"


def test_create_book_without_title_returns_validation_error(client):
    response = client.post("/books", json={"author": "J.J. Geewax"})
    assert response.status_code == 400
    assert any(error["field"] == "title" for error in response.get_json()["errors"])


def test_get_deleted_book_returns_not_found(client):
    created = client.post("/books", json={"title": "API Design Patterns", "author": "J.J. Geewax"})
    assert created.status_code == 201
    book_path = f"/books/{created.get_json()['id']}"

    assert client.delete(book_path).status_code == 204
    assert client.get(book_path).status_code == 404


def test_response_extra_field_blocked(client, sample_book):
    response = client.get(f"/books/{sample_book}")
    assert response.status_code == 200
    book = response.get_json()
    schema = get_book_schema()
    validate(book, schema)

    with pytest.raises(ValidationError) as error:
        validate({**book, "password_hash": "fake-hash"}, schema)
    assert error.value.validator == "additionalProperties"
