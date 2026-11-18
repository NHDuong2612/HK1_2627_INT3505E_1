from flask import Blueprint, current_app


bp = Blueprint("v2", __name__)


@bp.route("/<int:uid>")
def get(uid):
    user = current_app.config["USERS"].get(uid)
    if user is None:
        return {"error": "nf"}, 404

    return {
        "id": uid,
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email": user["email"],
    }
