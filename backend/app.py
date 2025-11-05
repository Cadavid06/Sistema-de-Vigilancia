from flask import Flask, render_template, jsonify, Response
import cv2, yaml
from models import get_session, Event
from motion_detector import MotionDetector
from gpio_control import encender_rojo, apagar_rojo

# Cargar configuración
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

app = Flask(__name__)
db = get_session(config["database"]["path"])

# Inicializar detector
detector = MotionDetector(config["camera"]["rtsp_url"])


@app.route("/")
def index():
    events = db.query(Event).order_by(Event.timestamp.desc()).limit(10).all()
    return render_template("index.html", events=events)


@app.route("/api/alarma/activar", methods=["POST"])
def activar_alarma():
    config["schedule"]["alarm_enabled"] = True
    encender_rojo()  # 🔴 LED rojo encendido = alarma activa
    evento = Event(event_type="alarma_activada", info="activada manualmente")
    db.add(evento)
    db.commit()
    return jsonify({"estado": "activada"})


@app.route("/api/alarma/desactivar", methods=["POST"])
def desactivar_alarma():
    config["schedule"]["alarm_enabled"] = False
    apagar_rojo()  # 🔴 LED rojo apagado = alarma desactivada
    evento = Event(event_type="alarma_desactivada", info="desactivada manualmente")
    db.add(evento)
    db.commit()
    return jsonify({"estado": "desactivada"})


@app.route("/video_feed")
def video_feed():
    def generate():
        while True:
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
    app.run(host="0.0.0.0", port=5000, debug=True)
