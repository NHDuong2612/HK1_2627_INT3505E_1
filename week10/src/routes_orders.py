from flask import Blueprint, request, jsonify
from sqlalchemy.orm import selectinload
from models import db, Order, OrderItem, Product

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")

@orders_bp.post("")
def create_order():
    data = request.json or {}
    items_data = data.get("items", [])
    if not items_data:
        return jsonify({"error": "Bad Request", "detail": "Danh sách items không được rỗng"}), 400

    order = Order(status="created")
    db.session.add(order)
    db.session.flush()

    for item in items_data:
        p = db.session.get(Product, item["product_id"])
        if not p or p.archived:
            db.session.rollback()
            return jsonify({"error": "Not Found", "detail": f"Product {item['product_id']} không tồn tại"}), 404
        
        if p.qty_in_stock < item["quantity"]:
            db.session.rollback()
            return jsonify({"error": "Conflict", "detail": f"Product {p.id} không đủ kho"}), 409

        p.qty_in_stock -= item["quantity"]
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=p.id,
            quantity=item["quantity"],
            unit_price_cents=p.price_cents
        ))

    db.session.commit()
    return jsonify({
        "id": order.id,
        "status": order.status,
        "items": [{"product_id": i.product_id, "quantity": i.quantity, "unit_price_cents": i.unit_price_cents} for i in order.items]
    }), 201

@orders_bp.get("")
def list_orders():
    # Sử dụng selectinload để Eager Loading các OrderItem, tránh lỗi N+1 Query
    stmt = db.select(Order).options(selectinload(Order.items))
    orders = db.session.execute(stmt).scalars().all()

    return jsonify([{
        "id": o.id,
        "status": o.status,
        "items": [{"product_id": i.product_id, "quantity": i.quantity, "unit_price_cents": i.unit_price_cents} for i in o.items]
    } for o in orders]), 200