from flask import Flask, render_template
import os
from app.auth.routes import auth_bp
from app.users.routes import users_bp
    

def create_app():
    """Application factory pattern for Flask app."""
    app = Flask(__name__, 
                template_folder='ui/templates',
                static_folder='ui/css')
    
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    
    # Home page route
    @app.route('/')
    def index():
        return render_template('home.html')
    
    return app
