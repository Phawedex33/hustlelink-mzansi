from app.extensions import db
from app.models import Profile, User


def create_admin_account(email, password, full_name):
    """Create an admin account for controlled bootstrap flows."""
    normalized_email = email.strip().lower()
    if User.query.filter_by(email=normalized_email).first():
        return None

    # For admins, we use a basic user with is_admin=True and is_verified=True
    admin = User(
        phone_number=f"admin-{normalized_email}",  # Placeholder for phone-based auth system
        email=normalized_email,
        is_admin=True,
        is_verified=True,
    )
    admin.set_password(password)

    # Parse full name into first and last for the profile
    name_parts = full_name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    profile = Profile(user=admin, first_name=first_name, last_name=last_name)

    db.session.add(admin)
    db.session.add(profile)
    db.session.commit()
    return admin
