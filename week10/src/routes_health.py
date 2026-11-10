from flask import Blueprint, jsonify
from sqlalchemy import text
from models import db

health_bp = Blueprint("health", __name__)

# 1. Liveness Probe: Kiểm tra tiến trình Flask còn sống (không kết nối DB)
@health_bp.get("/healthz")
def liveness():
    return jsonify({"status": "ok"}), 200

# 2. Readiness Probe: Kiểm tra kết nối DB đã sẵn sàng nhận traffic chưa
@health_bp.get("/ready")
def readiness():
    checks = {}
    try:
        db.session.execute(text("SELECT 1"))
        checks["db"] = "ok"
        return jsonify({"status": "ok", "checks": checks}), 200
    except Exception:
        checks["db"] = "err"
        return jsonify({"status": "degraded", "checks": checks}), 503