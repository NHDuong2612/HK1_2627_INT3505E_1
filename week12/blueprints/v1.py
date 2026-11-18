from flask import Blueprint, current_app


bp = Blueprint("v1", __name__)


@bp.route("/<int:uid>")
def get(uid):
    user = current_app.config["USERS"].get(uid)
    if user is None:
        return {"error": "nf"}, 404

    return {
        "id": uid,
        "full_name": f"{user['first_name']} {user['last_name']}",
        "email": user["email"],
    }
