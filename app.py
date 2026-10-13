
import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from config import Config
from services.email_service import init_email



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_email(app)
    os.makedirs(Config.MODEL_DIR, exist_ok=True)
    os.makedirs(Config.DATASET_DIR, exist_ok=True)
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

    from routes.alerts import alerts_bp
    from routes.assistant import assistant_bp
    from routes.auth import auth_bp
    from routes.branches import branches_bp
    from routes.customers import customers_bp
    from routes.dashboard import dashboard_bp
    from routes.dataset import dataset_bp
    from routes.models import models_bp
    from routes.reports import reports_bp
    from routes.segments import segments_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(branches_bp)
    app.register_blueprint(dataset_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(segments_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
