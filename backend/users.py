from werkzeug.security import generate_password_hash, check_password_hash
import json
import os


class UserManager:
    def __init__(self, users_file="users.json"):
        self.users_file = users_file
        self.users = self._load_users()

    def _load_users(self):
        """Cargar usuarios desde archivo JSON"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_users(self):
        """Guardar usuarios en archivo JSON"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=4)

    def add_user(self, username, password, name, email):
        """Agregar nuevo usuario"""
        if username in self.users:
            return False

        self.users[username] = {
            'password': generate_password_hash(password),
            'name': name,
            'email': email
        }
        self._save_users()
        return True

    def verify_user(self, username, password):
        """Verificar credenciales de usuario"""
        if username not in self.users:
            return False

        return check_password_hash(self.users[username]['password'], password)

    def get_user_info(self, username):
        """Obtener información del usuario"""
        if username in self.users:
            user_data = self.users[username].copy()
            user_data.pop('password', None)  # No devolver contraseña
            user_data['username'] = username
            return user_data
        return None

    def change_password(self, username, old_password, new_password):
        """Cambiar contraseña de usuario"""
        if not self.verify_user(username, old_password):
            return False

        self.users[username]['password'] = generate_password_hash(new_password)
        self._save_users()
        return True

    def delete_user(self, username):
        """Eliminar usuario"""
        if username in self.users:
            del self.users[username]
            self._save_users()
            return True
        return False