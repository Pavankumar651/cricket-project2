# reset_password.py (save in root of your project)
from backend.app import create_app, db
from backend.models.models import Admin
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    admin = Admin.query.filter_by(username='admin').first()
    if not admin:
        admin = Admin(username='admin', password_hash=generate_password_hash('admin123'))
        db.session.add(admin)
    else:
        admin.password_hash = generate_password_hash('admin123')
    db.session.commit()
    print("Done - Login: admin / admin123")