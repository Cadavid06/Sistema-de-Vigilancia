from flask import Flask, render_template, jsonify, Response
import cv2, yaml

# Importa la función modificada
from models import get_session_maker, Event
from motion_detector import MotionDetector
from gpio_control import encender_rojo, apagar_rojo, limpiar

# Cargar configuración
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

app = Flask(__name__)

# Creamos la CLASE Session globalmente (SessionLocal)
SessionLocal = get_session_maker(config["database"]["path"])

# INICIALIZAR DETECTOR GLOBALMENTE (Soluciona NameError)
detector = MotionDetector(config["camera"]["rtsp_url"])


@app.route("/")
def index():
    # Usar una sesión para esta ruta y cerrarla
    db = SessionLocal()

    events = db.query(Event).order_by(Event.timestamp.desc()).limit(10).all()

    db.close()
    return render_template("index.html", events=events)


@app.route("/api/alarma/activar", methods=["POST"])
def activar_alarma():
    db = SessionLocal()  # Nueva sesión por petición
    try:
        config["schedule"]["alarm_enabled"] = True
        encender_rojo()
        evento = Event(event_type="alarma_activada", info="activada manualmente")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "activada"})
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@app.route("/api/alarma/desactivar", methods=["POST"])
def desactivar_alarma():
    db = SessionLocal()  # Nueva sesión por petición
    try:
        config["schedule"]["alarm_enabled"] = False
        apagar_rojo()
        evento = Event(event_type="alarma_desactivada", info="desactivada manualmente")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "desactivada"})
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
            # Obtiene el último frame seguro del hilo del detector
            frame = detector.get_frame()

            if frame is None:
                continue

            _, buffer = cv2.imencode(".jpg", frame)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    # Intentamos asegurar la limpieza de GPIO al terminar
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    finally:
        # La función 'limpiar' ya está importada arriba
        limpiar()
