from flask import session, redirect, url_for, request
from functools import wraps
from authlib.integrations.flask_client import OAuth
import oauth_config

def init_oauth(app):
    """Iniciar OAuth"""
    oauth = OAuth(app, cache=False)

    google = oauth.register(
        name="google",
        client_id = oauth_config.GOOGLE_CLIENT_ID,
        client_secret = oauth_config.GOOGLE_CLIENT_SECRET,
        server_metadata_url = oauth_config.CONF_URL,
        client_kwargs = {
            'scope': 'openid email profile'
        },
        userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
    )

    return oauth, google

def is_authorized_email(email):
    return email in oauth_config.AUTHORIZED_EMAILS

def login_required(f):
    """Decorador para proteger rutas que requieren login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    return session.get('user', None)

