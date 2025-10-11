from flask import Flask, render_template
import os
from dotenv import load_dotenv
from app.auth.routes import auth_bp
from app.users.routes import users_bp
    

def create_app():
    """Application factory pattern for Flask app."""
    load_dotenv()
    app = Flask(__name__, 
                template_folder='ui/templates',
                static_folder='ui/css')
    
    app.config["SERVER_NAME"] = "localhost:5000"
    app.secret_key = os.getenv("FLASK_SECRET_KEY")
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(users_bp, url_prefix='/users')
    
    # Home page route
    @app.route('/')
    def index():
        return render_template('home.html')
    
    return app
