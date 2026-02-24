from app.extensions import db
from app.models import Admin


def create_admin_account(email, password, full_name):
    """Create an admin account for controlled bootstrap flows."""
    normalized_email = email.strip().lower()
    if Admin.query.filter_by(email=normalized_email).first():
        return None

    admin = Admin(full_name=full_name.strip(), email=normalized_email)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return admin
