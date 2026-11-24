from functools import wraps

from flask import Flask, jsonify, request

from blueprints.v1 import bp as v1_bp
from blueprints.v2 import bp as v2_bp
from gateway import dispatch


app = Flask(__name__)
app.config["USERS"] = {
    1: {"first_name": "Văn", "last_name": "Nguyễn", "email": "van.nguyen@example.com"},
}

app.register_blueprint(v1_bp, url_prefix="/api/v1/users")
app.register_blueprint(v2_bp, url_prefix="/api/v2/users")

LATEST = "2"
SUPPORTED = {"1", "2", "2024-06-20"}
USERS = {
    1: {"first_name": "Văn", "last_name": "Nguyễn", "email": "a@vnu.vn"},
}


def api_version(supported=SUPPORTED, default=LATEST):
    def decorate(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            version = request.headers.get("X-API-Version", default)
            if version not in supported:
                return jsonify(error="unsupported version"), 400

            response = jsonify(fn(version, *args, **kwargs))
            response.headers["X-API-Version-Served"] = version
            return response

        return wrapper

    return decorate


@app.route("/users/<int:uid>")
@api_version()
def get_user(version, uid):
    user = USERS.get(uid)
    if user is None:
        return {"error": "not found"}
    if version == "1":
        return {"id": uid, "full_name": f"{user['first_name']} {user['last_name']}"}
    return {"id": uid, **user}


@app.post("/orders")
def create_order():
    which, result = dispatch(request.get_json())
    response = jsonify(result)
    response.headers["X-Order-Handler"] = which
    return response, 201 if which == "v2" else 200
