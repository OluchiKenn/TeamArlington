from flask import Blueprint, render_template

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login')
def login():
    """Placeholder login page."""
    return render_template('auth_login.html')
