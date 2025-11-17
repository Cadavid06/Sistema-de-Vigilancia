from models import get_session_maker, User
import yaml

# Cargar configuración
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

SessionLocal = get_session_maker(config["database"]["path"])


def create_user(username, password, name):
    """Crear nuevo usuario"""
    db = SessionLocal()
    try:
        # Verificar si el usuario ya existe
        existing_user = db.query(User).filter(
            (User.username == username)
        ).first()

        if existing_user:
            print(f"❌ El usuario ya existe")
            return False

        # Crear nuevo usuario
        user = User(
            username=username,
            name=name
        )
        user.set_password(password)

        db.add(user)
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()


def list_users():
    """Listar todos los usuarios"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("No hay usuarios registrados.")
            return

        print("\n=== Usuarios Registrados ===")
        for user in users:
            status = "✅ Activo" if user.is_active else "❌ Inactivo"
            print(f"\nID: {user.id}")
            print(f"Usuario: {user.username}")
            print(f"Nombre: {user.name}")

    finally:
        db.close()


def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_users()
        return

    print("=== Crear Nuevo Usuario ===")
    username = input("Usuario: ").strip()
    password = input("Contraseña: ").strip()
    name = input("Nombre completo: ").strip()

    if not all([username, password, name]):
        print("❌ Todos los campos son obligatorios")
        return

    create_user(username, password, name)


if __name__ == "__main__":
    main()