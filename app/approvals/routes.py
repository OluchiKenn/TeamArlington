# app/approvals/routes.py
import os
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
)
from werkzeug.utils import secure_filename
from app.models import db, Signature
from app.users.routes import require_login, current_db_user

approvals_bp = Blueprint("approvals_bp", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_MIMETYPES = {"image/png", "image/jpeg"}
MAX_BYTES = 2 * 1024 * 1024  # 2MB


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@approvals_bp.get("/signature")
@require_login
def signature_upload_get():
    me = current_db_user()
    sig = Signature.query.filter_by(user_id=me.id).first() if me else None
    image_url = None
    if sig and sig.image_path:
        filename = os.path.basename(sig.image_path)
        image_url = url_for("approvals_bp.serve_signature", filename=filename)
    return render_template("signature_upload.html", signature=sig, image_url=image_url)


@approvals_bp.post("/signature")
@require_login
def signature_upload_post():
    me = current_db_user()
    if not me:
        flash("You must be logged in.", "error")
        return redirect(url_for("approvals_bp.signature_upload_get"))

    file = request.files.get("signature")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("approvals_bp.signature_upload_get"))

    if not allowed_file(file.filename):
        flash("Invalid file type. Please upload a PNG or JPEG image.", "error")
        return redirect(url_for("approvals_bp.signature_upload_get"))

    # Validate mimetype
    if file.mimetype not in ALLOWED_MIMETYPES:
        flash("Invalid file type. Please upload a PNG or JPEG image.", "error")
        return redirect(url_for("approvals_bp.signature_upload_get"))

    # Validate size (up to 2MB)
    pos = file.stream.tell()
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(pos)
    if size > MAX_BYTES:
        flash("File too large. Maximum size is 2MB.", "error")
        return redirect(url_for("approvals_bp.signature_upload_get"))

    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads/signatures")
    # Ensure absolute filesystem path for saving
    base_dir = os.path.abspath(os.path.join(current_app.root_path, os.pardir, upload_folder))
    os.makedirs(base_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = secure_filename(f"{me.id}_{ts}.{ext}")
    abs_path = os.path.join(base_dir, filename)

    # Save file
    file.save(abs_path)

    # Store relative path in DB (relative to project root)
    relative_path = os.path.join(upload_folder, filename).replace("\\", "/")

    sig = Signature.query.filter_by(user_id=me.id).first()
    if sig:
        sig.image_path = relative_path
        sig.uploaded_at = datetime.utcnow()
    else:
        sig = Signature(user_id=me.id, image_path=relative_path)
        db.session.add(sig)

    db.session.commit()

    flash("Signature uploaded successfully", "success")
    return redirect(url_for("approvals_bp.signature_upload_get"))


@approvals_bp.get("/uploads/signatures/<path:filename>")
@require_login
def serve_signature(filename):
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads/signatures")
    base_dir = os.path.abspath(os.path.join(current_app.root_path, os.pardir, upload_folder))
    return send_from_directory(base_dir, filename)
