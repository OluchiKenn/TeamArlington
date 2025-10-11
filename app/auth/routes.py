from flask import Blueprint, render_template, redirect, request, session, url_for
from msal import ConfidentialClientApplication
import os

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
        session["user"] = result["id_token_claims"]
        return redirect(url_for("auth.profile"))
    else:
        return f"Error: {result.get('error_description')}"

@auth_bp.route("/profile")
def profile():
    """Displays logged-in user's info."""
    if "user" not in session:
        return redirect(url_for("auth.login"))
    user = session["user"]
    return render_template("profile.html", user=user)
