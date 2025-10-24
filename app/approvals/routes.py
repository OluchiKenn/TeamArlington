# app/approvals/routes.py
import os
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, session
)
from werkzeug.utils import secure_filename
from app.models import db, User, Signature, Request, FormTemplate
from app.users.routes import require_login, current_db_user
from datetime import datetime
import json

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


@approvals_bp.route("/new", methods=["GET", "POST"])
def new_request():
    templates = FormTemplate.query.all()

    if request.method == "POST":
        form_template_id = request.form["form_template_id"]
        data = dict(request.form)
        data.pop("form_template_id")

        new_req = Request(
            user_id=current_user.id,
            form_template_id=form_template_id,
            data_json=data,
            status="draft"   # first state
        )
        db.session.add(new_req)
        db.session.commit()
        return redirect(url_for("approvals.view_request", request_id=new_req.id))

    return render_template("approvals/new_request.html", templates=templates)


@approvals_bp.route("/submit/<form_code>", methods=["POST"])
def submit_request(form_code):
    form_template = FormTemplate.query.filter_by(form_code=form_code).first_or_404()

    
    user_info = session.get("user")
    user_email = user_info.get("preferred_username") if user_info else None
    user_name = user_info.get("name") if user_info else "Unknown User"

    user = User.query.filter_by(email=user_email).first()

    
    if not user and user_email:
        user = User(
            name=user_name,
            email=user_email,
            role="basicuser"
        )
        db.session.add(user)
        db.session.commit()



    
    form_data = {}
    for key in request.form:
        form_data[key] = request.form.getlist(key) if len(request.form.getlist(key)) > 1 else request.form.get(key)

    action = request.form.get("action")  

    new_request = Request(
        form_template_id=form_template.id,
        requester_id=user.id,
        form_data_json=form_data,
        status="draft" if action == "draft" else "pending",
    )

    db.session.add(new_request)
    db.session.commit()

    flash("Form saved as draft!" if action == "draft" else "Form submitted for approval!", "success")
    return redirect(url_for("approvals_bp.list_forms"))


@approvals_bp.route("/forms")
def list_forms():
    forms = FormTemplate.query.all()
    return render_template("forms_list.html", forms=forms)

@approvals_bp.route("/forms/<form_code>", methods=["GET", "POST"])
def fill_form(form_code):
    """Display and handle form creation."""
    form_template = FormTemplate.query.filter_by(form_code=form_code).first_or_404()

    user = session.get("user")
    if not user:
        flash("You must be logged in to submit a form.", "warning")
        return redirect(url_for("auth.login"))

    
    db_user = User.query.filter_by(email=user["preferred_username"]).first()
    if not db_user:
        flash("User not found in database.", "danger")
        return redirect(url_for("auth.login"))

    requester_id = db_user.id

    if request.method == "POST":
        form_data = {}

        for key, field_type in form_template.fields_json.items():
            if isinstance(field_type, dict) and field_type.get("type") == "select":
                form_data[key] = request.form.get(key)
            elif isinstance(field_type, list):
                form_data[key] = request.form.getlist(key)
            elif field_type == "file":
                file = request.files.get(key)
                form_data[key] = file.filename if file else None
            elif field_type == "auto_date":
                form_data[key] = datetime.utcnow().strftime("%Y-%m-%d")
            else:
                form_data[key] = request.form.get(key)

        if request.form.get("action") == "draft":
            status = "draft"
            message = "Saved as draft!"
        else:
            status = "pending"
            message = "Form submitted for approval!"

        new_request = Request(
            form_template_id=form_template.id,
            requester_id=requester_id,
            form_data_json=form_data,
            status=status,
            submitted_at=datetime.utcnow() if status == "pending" else None
        )

        db.session.add(new_request)
        db.session.commit()

        flash(message, "success")
        return redirect(url_for("approvals_bp.list_my_requests"))

    return render_template(
        "form_fill.html",
        form_template=form_template,
        current_date=datetime.utcnow().strftime("%Y-%m-%d")
    )



@approvals_bp.route("/request/<int:request_id>/edit", methods=["GET", "POST"])
def edit_request(request_id):
    """Edit a draft request using the same fill form template."""
    req = Request.query.get_or_404(request_id)

    user = session.get("user")
    if not user:
        flash("You must be logged in to edit requests.", "warning")
        return redirect(url_for("auth.login"))

    db_user = User.query.filter_by(email=user["preferred_username"]).first()
    if not db_user:
        flash("User not found in database.", "danger")
        return redirect(url_for("auth.login"))

    requester_id = db_user.id


    if req.requester_id != requester_id:
        flash("You cannot edit someone else's request.", "warning")
        return redirect(url_for("approvals_bp.list_my_requests"))

    if req.status != "draft":
        flash("Only drafts can be edited.", "warning")
        return redirect(url_for("approvals_bp.list_my_requests"))

    form_template = req.form_template

    if request.method == "POST":
        updated_data = {}

        for key, field_type in form_template.fields_json.items():
            if isinstance(field_type, dict) and field_type.get("type") == "select":
                updated_data[key] = request.form.get(key)
            elif isinstance(field_type, list):
                updated_data[key] = request.form.getlist(key)
            elif field_type == "file":
                file = request.files.get(key)
                updated_data[key] = file.filename if file else req.form_data_json.get(key)
            elif field_type == "auto_date":
                updated_data[key] = datetime.utcnow().strftime("%Y-%m-%d")
            else:
                updated_data[key] = request.form.get(key)

        req.form_data_json = updated_data

        if request.form.get("action") == "draft":
            req.status = "draft"
            req.submitted_at = None
            flash("Draft updated!", "success")
        else:
            req.status = "pending"
            req.submitted_at = datetime.utcnow()
            flash("Form submitted for approval!", "success")

        db.session.commit()
        return redirect(url_for("approvals_bp.list_my_requests"))

    return render_template(
        "form_fill.html",
        form_template=form_template,
        current_data=req.form_data_json,
        current_date=datetime.utcnow().strftime("%Y-%m-%d"),
        req=req
    )



@approvals_bp.route("/my_requests")
def list_my_requests():
    user = session.get("user")
    if not user:
        flash("You must be logged in to view your requests.", "warning")
        return redirect(url_for("auth.login"))

    db_user = User.query.filter_by(email=user["preferred_username"]).first()
    if not db_user:
        flash("User not found in database.", "danger")
        return redirect(url_for("auth.login"))

    requester_id = db_user.id

    requests = Request.query.filter_by(requester_id=requester_id).order_by(Request.created_at.desc()).all()

    return render_template("my_requests.html", requests=requests)