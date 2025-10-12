from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    oid = db.Column(db.String(100), unique=True, nullable=True)  # optional (for O365)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    role = db.Column(db.String(40), nullable=False, default="basicuser")  # 'basicuser' | 
    'admin'
    status = db.Column(db.String(40), nullable=False, default="active")   # 'active' | 
    'deactivated'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "oid": self.oid,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }

