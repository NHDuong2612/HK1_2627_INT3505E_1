from contextlib import contextmanager
from sqlalchemy import event
from models import db, Product, Order, OrderItem

@contextmanager
def count_queries(db):
    """Đếm chính xác số lượng truy vấn SQL được thực thi trong khối code."""
    count = 0
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal count
        count += 1

    engine = db.engine
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield lambda: count
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

def test_create_product_success(client):
    payload = {
        "sku": "TEST-POST-01",
        "name": "Chuột không dây",
        "description": "Chuột máy tính Silent",
        "price_cents": 350000,
        "qty_in_stock": 15
    }
    
    response = client.post("/api/v1/products", json=payload)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["sku"] == "TEST-POST-01"
    assert data["name"] == "Chuột không dây"
    assert "id" in data

def test_list_orders_eager_loading(client, app):
    with app.app_context():
        p1 = Product(sku="P-TEST", name="Bàn phím Cơ", price_cents=500000, qty_in_stock=100)
        db.session.add(p1)
        db.session.commit()

        for _ in range(3):
            order = Order(status="created")
            db.session.add(order)
            db.session.flush()  # Lấy order.id
            
            item = OrderItem(order_id=order.id, product_id=p1.id, quantity=1, unit_price_cents=p1.price_cents)
            db.session.add(item)
        
        db.session.commit()

    with count_queries(db) as get_query_count:
        response = client.get("/api/v1/orders")

    assert response.status_code == 200
    orders = response.get_json()
    assert len(orders) == 3

    queries_executed = get_query_count()
    assert queries_executed == 2, f"Cảnh báo N+1 Query! Số query thực thi là {queries_executed} thay vì 2"
