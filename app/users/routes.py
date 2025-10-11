from flask import Blueprint, render_template

users_bp = Blueprint('users', __name__)


@users_bp.route('/')
def list_users():
    """Placeholder users list page."""
    return render_template('users_list.html')
