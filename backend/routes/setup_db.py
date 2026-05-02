from backend.app import create_app, db
from backend.models.models import Admin, Player, PlayerCareerStats
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Create admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin created")
    
    # Create players if not exists
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
    print("All players created")
    print("Database setup complete!")