from flask import Flask, render_template, jsonify, Response
import cv2, yaml, os, time
from models import get_session_maker, Event
from motion_detector import MotionDetector
from gpio_control import encender_rojo, apagar_rojo, limpiar, encender_verde

# Cargar configuración
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# 🔴 ALARMA APAGADA AL INICIAR
config["schedule"]["alarm_enabled"] = False

encender_verde()
apagar_rojo()

# Inicializar GPIO si corresponde
if not os.getenv("SVP_SIMULATE", "0") == "1":
    try:
        from gpio_control import _init_gpio

        _init_gpio(config)
    except (ImportError, AttributeError):
        pass

app = Flask(__name__)
SessionLocal = get_session_maker(config["database"]["path"])


def is_alarm_active():
    return config["schedule"]["alarm_enabled"]


detector = MotionDetector(config["camera"]["rtsp_url"], config=config, is_alarm_enabled_func=is_alarm_active)


@app.route("/")
def index():
    db = SessionLocal()
    events = db.query(Event).order_by(Event.timestamp.desc()).limit(10).all()
    db.close()
    return render_template("index.html", events=events)


@app.route("/api/alarma/activar", methods=["POST"])
def activar_alarma():
    db = SessionLocal()
    try:
        config["schedule"]["alarm_enabled"] = True
        encender_rojo()
        print("🔴 Alarma ACTIVADA manualmente desde la web")
        evento = Event(event_type="alarma_activada", info="activada manualmente")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "activada", "alarm_enabled": True})
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@app.route("/api/alarma/desactivar", methods=["POST"])
def desactivar_alarma():
    db = SessionLocal()
    try:
        config["schedule"]["alarm_enabled"] = False

        # 🔕 Resetear completamente la alarma
        detector.reset_alarm()
        apagar_rojo()

        print("🟢 Alarma DESACTIVADA manualmente desde la web")
        evento = Event(event_type="alarma_desactivada", info="desactivada manualmente")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "desactivada", "alarm_enabled": False})
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@app.route("/api/alarma/estado", methods=["GET"])
def estado_alarma():
    """Endpoint para verificar el estado actual de la alarma"""
    return jsonify({
        "alarm_enabled": config["schedule"]["alarm_enabled"],
        "estado": "activada" if config["schedule"]["alarm_enabled"] else "desactivada"
    })


@app.route("/video_feed")
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
        app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
    finally:
        limpiar()