from datetime import datetime, timezone

from flask import Blueprint, current_app

from sunset import deprecate_at


bp = Blueprint("v1", __name__)
V1_SUNSET = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


@bp.route("/<int:uid>")
@deprecate_at(V1_SUNSET, replacement="/api/v2/users")
def get(uid):
    user = current_app.config["USERS"].get(uid)
    if user is None:
        return {"error": "nf"}, 404

    return {
        "id": uid,
        "full_name": f"{user['first_name']} {user['last_name']}",
        "email": user["email"],
    }
