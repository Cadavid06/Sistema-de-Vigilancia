from flask import Flask, render_template, jsonify, Response, redirect, url_for, session, request
import cv2, yaml, os, time
from models import get_session_maker, Event
from motion_detector import MotionDetector
from gpio_control import encender_rojo, apagar_rojo, limpiar, encender_verde
from auth import init_oauth, login_required, is_authorized_email, get_current_user
import oauth_config

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

config["schedule"]["alarm_enabled"] = False

encender_verde()
apagar_rojo()

app = Flask(__name__)
app.secret_key = oauth_config.SECRET_KEY

@app.after_request
def add_no_cache_headers(response):
    # Si estamos en OAuth, NO desactivar la caché
    if request.path.startswith("/google-login") or request.path.startswith("/callback"):
        return response

    # Para todo lo demás sí bloquear cache
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


oauth, google = init_oauth(app)
SessionLocal = get_session_maker(config["database"]["path"])

def is_alarm_active():
    return config["schedule"]["alarm_enabled"]

detector = MotionDetector(config["camera"]["rtsp_url"], config=config, is_alarm_enabled_func=is_alarm_active)

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/google-login")
def google_login():
    redirect_uri = "http://localhost:5000/callback"
    return google.authorize_redirect(redirect_uri)


@app.route("/callback")
def authorize():
    """Callback de Google OAuth"""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            email = user_info.get('email')

            # Verificar si el email está autorizado
            if is_authorized_email(email):
                session['user'] = {
                    'email': email,
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture')
                }
                session.permanent = True  # Sesión persistente
                print(f"✅ Login exitoso: {email}")
                return redirect(url_for('index'))
            else:
                print(f"❌ Acceso denegado: {email}")
                return render_template("unauthorized.html", email=email)

        return redirect(url_for('login_page'))

    except Exception as e:
        print(f"❌ Error en autenticación: {e}")
        return redirect(url_for('login_page'))

@app.route("/logout")
def logout():
    email = session.get('user', {}).get('email', 'Usuario')
    session.clear()  # 👈 esto borra TODO, incluido el state
    print(f" Logout: {email}")
    return redirect(url_for('login_page'))

@app.route("/")
@login_required
def index():
    db = SessionLocal()
    events = db.query(Event).order_by(Event.timestamp.desc()).limit(10).all()
    user = get_current_user()
    db.close()
    return render_template("index.html", events=events, user=user)

@app.route("/api/alarma/activar", methods=["POST"])
@login_required
def activar_alarma():
    db = SessionLocal()
    try:
        config["schedule"]["alarm_enabled"] = True
        encender_rojo()
        user = get_current_user()
        print(f"🔴 Alarma ACTIVADA por {user.get('email')}")
        evento = Event(event_type="alarma_activada", info=f"activada por {user.get('email')}")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "activada", "alarm_enabled": True})
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@app.route("/api/alarma/desactivar", methods=["POST"])
@login_required
def desactivar_alarma():
    db = SessionLocal()
    try:
        config["schedule"]["alarm_enabled"] = False

        # 🔕 Resetear completamente la alarma
        detector.reset_alarm()
        apagar_rojo()
        user = get_current_user()
        print(f"🟢 Alarma DESACTIVADA por {user.get('email')}")
        evento = Event(event_type="alarma_desactivada", info=f"desactivada por {user.get('email')}")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "desactivada", "alarm_enabled": False})
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@app.route("/api/alarma/estado", methods=["GET"])
@login_required
def estado_alarma():
    """Endpoint para verificar el estado actual de la alarma"""
    return jsonify({
        "alarm_enabled": config["schedule"]["alarm_enabled"],
        "estado": "activada" if config["schedule"]["alarm_enabled"] else "desactivada"
    })


@app.route("/video_feed")
@login_required
def video_feed():
    def generate():
        # Parámetros desde config
        streaming_config = config.get("streaming", {})
        jpeg_quality = [int(cv2.IMWRITE_JPEG_QUALITY), streaming_config.get("jpeg_quality", 60)]
        target_fps = streaming_config.get("target_fps", 10)
        max_width = streaming_config.get("max_width", 640)
        frame_delay = 1.0 / target_fps
        last_frame_time = 0
        frame_skip_counter = 0

        while True:
            current_time = time.time()

            # Control de FPS - limitar a 10 FPS
            if current_time - last_frame_time < frame_delay:
                time.sleep(0.01)  # Pequeña pausa para no consumir CPU
                continue

            frame = detector.get_frame()
            if frame is None:
                frame_skip_counter += 1
                if frame_skip_counter > 50:  # Si falla mucho, pausa más
                    time.sleep(0.5)
                    frame_skip_counter = 0
                continue

            frame_skip_counter = 0

            # Reducir resolución si es muy grande (mejora performance)
            height, width = frame.shape[:2]
            if width > max_width:
                scale = max_width / width
                new_width = max_width
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

            # Codificar con calidad reducida para menos latencia
            success, buffer = cv2.imencode(".jpg", frame, jpeg_quality)

            if not success:
                continue

            last_frame_time = current_time

            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    finally:
        limpiar()