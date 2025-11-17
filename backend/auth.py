from flask import session, redirect, url_for
from functools import wraps
from models import User
from datetime import datetime

def login_required(f):
    """Decorador para proteger rutas que requieren login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user(db):
    """Obtener usuario actual de la sesión"""
    user_id = session.get('user_id')
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user.to_dict()
    return None

