from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from models import db, Product
from schemas import ProductOut, ProductIn, ProductPatch, ReserveIn

products_bp = Blueprint("products", __name__, url_prefix="/api/v1/products")

@products_bp.get("")
def list_products():
    page = max(1, int(request.args.get("page", 1)))
    size = min(100, max(1, int(request.args.get("size", 20))))

    stmt = db.select(Product).where(Product.archived == False).order_by(Product.id).offset((page - 1) * size).limit(size)
    rows = db.session.execute(stmt).scalars().all()

    total_stmt = db.select(db.func.count()).select_from(Product).where(Product.archived == False)
    total = db.session.scalar(total_stmt)

    return jsonify({
        "items": [ProductOut().dump(p) for p in rows],
        "page": page,
        "size": size,
        "total": total
    }), 200

@products_bp.get("/<int:id>")
def get_product(id):
    p = db.session.scalar(db.select(Product).where(Product.id == id, Product.archived == False))
    if not p:
        return jsonify({"error": "Not Found", "detail": "Không tìm thấy sản phẩm"}), 404
    return jsonify(ProductOut().dump(p)), 200

@products_bp.post("")
def create_product():
    try:
        data = ProductIn().load(request.json)
    except Exception as err:
        return jsonify({"error": "Validation Error", "detail": err.messages}), 422

    p = Product(**data)
    db.session.add(p)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Conflict", "detail": "Mã SKU này đã tồn tại"}), 409

    return jsonify(ProductOut().dump(p)), 201

@products_bp.post("/<int:id>/reserve")
def reserve_product(id):
    try:
        data = ReserveIn().load(request.json)
    except Exception as err:
        return jsonify({"error": "Validation Error", "detail": err.messages}), 422

    p = db.session.scalar(db.select(Product).where(Product.id == id, Product.archived == False))
    if not p:
        return jsonify({"error": "Not Found", "detail": "Không tìm thấy sản phẩm"}), 404

    if p.qty_in_stock < data["qty"]:
        return jsonify({"error": "Conflict", "detail": "Số lượng hàng trong kho không đủ"}), 409

    p.qty_in_stock -= data["qty"]
    db.session.commit()
    return jsonify(ProductOut().dump(p)), 200

@products_bp.patch("/<int:id>")
def patch_product(id):
    try:
        data = ProductPatch().load(request.json, partial=True)
    except Exception as err:
        return jsonify({"error": "Validation Error", "detail": err.messages}), 422

    p = db.session.scalar(db.select(Product).where(Product.id == id, Product.archived == False))
    if not p:
        return jsonify({"error": "Not Found", "detail": "Không tìm thấy sản phẩm"}), 404

    for key, val in data.items():
        setattr(p, key, val)

    db.session.commit()
    return jsonify(ProductOut().dump(p)), 200

@products_bp.delete("/<int:id>")
def delete_product(id):
    p = db.session.scalar(db.select(Product).where(Product.id == id, Product.archived == False))
    if not p:
        return jsonify({"error": "Not Found", "detail": "Không tìm thấy sản phẩm"}), 404

    p.archived = True  
    db.session.commit()
    return "", 204