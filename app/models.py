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
    # Relationships
    signatures = db.relationship('Signature', back_populates='user', cascade='all, delete-orphan')
    requests = db.relationship('Request', back_populates='requester', cascade='all, delete-orphan')
    approval_steps = db.relationship('ApprovalStep', back_populates='approver', cascade='all, delete-orphan')

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

class Signature(db.Model):
    __tablename__ = "signatures"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='signatures')

    def as_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "image_path": self.image_path,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class FormTemplate(db.Model):
    __tablename__ = "form_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    form_code = db.Column(db.String(50), unique=True, nullable=False)
    latex_template_path = db.Column(db.String(255), nullable=False)
    fields_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    requests = db.relationship('Request', back_populates='form_template', cascade='all, delete-orphan')

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "form_code": self.form_code,
            "latex_template_path": self.latex_template_path,
            "fields_json": self.fields_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Request(db.Model):
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    form_template_id = db.Column(db.Integer, db.ForeignKey('form_templates.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum('draft', 'pending', 'returned', 'approved', 'rejected', name='request_status'), nullable=False, default='draft')
    form_data_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)

    form_template = db.relationship('FormTemplate', back_populates='requests')
    requester = db.relationship('User', back_populates='requests')
    approval_steps = db.relationship('ApprovalStep', back_populates='request', order_by='ApprovalStep.sequence', cascade='all, delete-orphan')

    def as_dict(self):
        return {
            "id": self.id,
            "form_template_id": self.form_template_id,
            "requester_id": self.requester_id,
            "status": self.status,
            "form_data_json": self.form_data_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }


class ApprovalStep(db.Model):
    __tablename__ = "approval_steps"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', 'returned', name='approval_step_status'), nullable=False, default='pending')
    comments = db.Column(db.Text, nullable=True)
    signed_pdf_path = db.Column(db.String(255), nullable=True)
    actioned_at = db.Column(db.DateTime, nullable=True)

    request = db.relationship('Request', back_populates='approval_steps')
    approver = db.relationship('User', back_populates='approval_steps')

    def as_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "approver_id": self.approver_id,
            "sequence": self.sequence,
            "status": self.status,
            "comments": self.comments,
            "signed_pdf_path": self.signed_pdf_path,
            "actioned_at": self.actioned_at.isoformat() if self.actioned_at else None,
        }
