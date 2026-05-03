from backend.app import create_app, db
from backend.models.models import Admin, Player, PlayerCareerStats
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()

    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin created")

    players = [
        'Pavankumar', 'Veeresh', 'Darshan', 'Sukin', 'Yashwanth',
        'Santhosh', 'Pramod', 'Rakesh', 'Sachin', 'Nishanth',
        'Neeraj', 'Putraju', 'Shivu', 'Prashant', 'Praveen'
    ]

    for name in players:
        if not Player.query.filter_by(name=name).first():
            p = Player(name=name, role='All Rounder')
            db.session.add(p)
            db.session.flush()
            cs = PlayerCareerStats(player_id=p.id)
            db.session.add(cs)

    db.session.commit()
    print("Setup complete!")