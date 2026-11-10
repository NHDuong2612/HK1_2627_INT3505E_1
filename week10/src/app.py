from flask import Flask
from flask_migrate import Migrate
from models import db
from routes import products_bp
from routes_orders import orders_bp
from routes_health import health_bp

def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(health_bp)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)