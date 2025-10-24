from flask import Blueprint, render_template, redirect, request, session, url_for
from msal import ConfidentialClientApplication
import os
from sqlalchemy import func
from app.models import db, User

auth_bp = Blueprint('auth', __name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_PATH = "/auth/callback"
SCOPE = ["User.Read"]


def _build_msal_app(cache=None):
    return ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET, token_cache=cache
    )

@auth_bp.route("/login")
def login():
    """Redirects user to Microsoft login page."""
    msal_app = _build_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        SCOPE, redirect_uri=url_for("auth.authorized", _external=True)
    )
    print("Redirect URI used:", url_for("auth.authorized", _external=True))
    return redirect(auth_url)

@auth_bp.route("/callback")
def authorized():
    """Handles redirect from Microsoft after login."""
    code = request.args.get("code")
    if not code:
        return "Login failed or canceled."

    msal_app = _build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code, scopes=SCOPE, redirect_uri=url_for("auth.authorized", _external=True)
    )

    if "access_token" in result:
        claims = result["id_token_claims"]
        session["user"] = claims

        # Auto-provision or update DB user for current session user
        email = (claims.get("email") or claims.get("preferred_username") or "").strip()
        display_name = (claims.get("name") or email.split("@")[0] or "User").strip()
        if email:
            existing = User.query.filter(func.lower(User.email) == email.lower()).first()
            if not existing:
                u = User(name=display_name, email=email, role="basicuser", status="active")
                db.session.add(u)
                db.session.commit()
            else:
                # Optionally update the name if it changed
                if display_name and existing.name != display_name:
                    existing.name = display_name
                    db.session.commit()

        return redirect(url_for("auth.profile"))
    else:
        return f"Error: {result.get('error_description')}"

@auth_bp.route("/profile")
def profile():
    """Displays logged-in user's info."""
    if "user" not in session:
        return redirect(url_for("auth.login"))
    user = session["user"]
    print(session)
    return render_template("profile.html", user=user)
