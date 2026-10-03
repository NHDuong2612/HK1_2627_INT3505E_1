from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from errors import ApiProblem

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db = SQLAlchemy(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email
        }

@app.errorhandler(ApiProblem)
def handle_api_problem(error):
    return ApiProblem._problem(
        error.status_code,
        error.title,
        error.detail,
        error.type.split("/")[-1] if error.type else None,
        **error.extra
    )

@app.get("/users/<int:uid>")
def get_user(uid):
    user = User.query.get(uid)
    if not user:
        raise ApiProblem(
            status_code=404,
            title="User not found",
            type_path="user-not-found",
            resource_id=uid,
        )
    return jsonify(user.to_dict())

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", port=5000, debug=True)
