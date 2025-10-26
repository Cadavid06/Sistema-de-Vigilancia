from flask import Flask, render_template, jsonify, request, Response
import cv2
from models import get_session, Event
import yaml
import datetime
import os

# Cargar configuración YAML
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

app = Flask(__name__)
db = get_session(config["database"]["path"])

# ----------- VIDEO STREAM -----------
# Fuente de video: 0 para cámara local, o "video.mp4" para archivo
video_source = cv2.VideoCapture(0)


def generar_frames():
    """Genera frames JPEG continuos para enviar al navegador."""
    while True:
        success, frame = video_source.read()
        if not success:
            break  # si no hay frame, salimos del bucle
        ret, buffer = cv2.imencode(".jpg", frame)
        frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@app.route("/video_feed")
def video_feed():
    return Response(
        generar_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# -----------------------------------


@app.route("/")
def index():
    events = db.query(Event).order_by(Event.timestamp.desc()).limit(10).all()
    return render_template("index.html", events=events)


@app.route("/api/alarma/activar", methods=["POST"])
def activar_alarma():
    config["schedule"]["alarm_enabled"] = True
    evento = Event(event_type="alarma_activada", info="activada manualmente")
    db.add(evento)
    db.commit()
    return jsonify({"estado": "activada"})


@app.route("/api/alarma/desactivar", methods=["POST"])
def desactivar_alarma():
    config["schedule"]["alarm_enabled"] = False
    evento = Event(event_type="alarma_desactivada", info="desactivada manualmente")
    db.add(evento)
    db.commit()
    return jsonify({"estado": "desactivada"})


@app.route("/api/estado")
def estado():
    return jsonify(
        {
            "alarm_enabled": config["schedule"]["alarm_enabled"],
            "mensaje": (
                "Modo alarma" if config["schedule"]["alarm_enabled"] else "Modo normal"
            ),
        }
    )


if __name__ == "__main__":
    try:
        app.run(debug=True)
    finally:
        # liberar la cámara si el servidor se cierra
        video_source.release()
        print("✅ Cámara liberada correctamente.")

 