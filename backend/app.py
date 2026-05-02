# backend/app.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
import os

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__,
                template_folder='../frontend/templates',
                static_folder='../frontend/static')

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cricket-secret-key-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/cricket_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    CORS(app)

    from backend.routes.auth import auth_bp
    from backend.routes.players import players_bp
    from backend.routes.matches import matches_bp
    from backend.routes.scoring import scoring_bp
    from backend.routes.analytics import analytics_bp
    from backend.routes.admin import admin_bp
    from backend.routes.main import main_bp          # ← separate file now

    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(players_bp,   url_prefix='/api/players')
    app.register_blueprint(matches_bp,   url_prefix='/api/matches')
    app.register_blueprint(scoring_bp,   url_prefix='/api/scoring')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(main_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)