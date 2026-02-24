from app import create_app
from app.extensions import db
from app.models.user import Provider, Admin

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("Tables created successfully!")

    # Test creating a provider
    provider = Provider(
        full_name="Test Provider",
        email="test@provider.com",
        phone_number="1234567890"
    )
    provider.set_password("password123")
    db.session.add(provider)

    # Test creating an admin
    admin = Admin(
        full_name="Test Admin",
        email="admin@test.com"
    )
    admin.set_password("adminpass")
    db.session.add(admin)

    db.session.commit()
    print("Test entries added successfully!")
