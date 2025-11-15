from flask import Flask, render_template, jsonify, Response, redirect, url_for, session, request
import cv2, yaml, os, time
from models import get_session_maker, Event
from motion_detector import MotionDetector
from gpio_control import encender_rojo, apagar_rojo, limpiar, encender_verde
from auth import init_oauth, login_required, is_authorized_email, get_current_user
from dotenv import load_dotenv
from scheduler import AlarmScheduler

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

config["schedule"]["alarm_enabled"] = False

encender_verde()
apagar_rojo()

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY")

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

# Funciones de callback para el scheduler
def auto_activate_alarm():
    """Activar alarma automáticamente"""
    config["schedule"]["alarm_enabled"] = True
    encender_rojo()
    db = SessionLocal()
    try:
        evento = Event(event_type="alarma_activada", info="activada automáticamente por programación")
        db.add(evento)
        db.commit()
    except:
        db.rollback()
    finally:
        db.close()

def auto_deactivate_alarm():
    """Desactivar alarma automáticamente"""
    config["schedule"]["alarm_enabled"] = False
    detector.reset_alarm()
    apagar_rojo()
    db = SessionLocal()
    try:
        evento = Event(event_type="alarma_desactivada", info="desactivada automáticamente por programación")
        db.add(evento)
        db.commit()
    except:
        db.rollback()
    finally:
        db.close()

# Inicializar programador
scheduler = AlarmScheduler(config, auto_activate_alarm, auto_deactivate_alarm)

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/google-login")
def google_login():
    redirect_uri = url_for('authorize', _external=True)
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
        scheduler.set_manual_override(True)
        encender_rojo()
        user = get_current_user()
        print(f"🔴 Alarma ACTIVADA por {user.get('email')}")
        evento = Event(event_type="alarma_activada", info=f"activada por {user.get('email')}")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "activada", "alarm_enabled": True, "manual_mode": True})
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
        scheduler.set_manual_override(True)
        detector.reset_alarm()
        apagar_rojo()
        user = get_current_user()
        print(f"🟢 Alarma DESACTIVADA por {user.get('email')}")
        evento = Event(event_type="alarma_desactivada", info=f"desactivada por {user.get('email')}")
        db.add(evento)
        db.commit()
        return jsonify({"estado": "desactivada", "alarm_enabled": False, "manual_mode": True})
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

@app.route("/api/alarma/auto", methods=["POST"])
@login_required
def modo_automatico():
    """Restaurar control automático según programación"""
    try:
        scheduler.set_manual_override(False)
        user = get_current_user()
        print(f"🤖 Modo automático restaurado por {user.get('email')}")

        # Verificar estado según programación
        should_be_active = scheduler.should_be_active()
        if should_be_active is not None:
            if should_be_active:
                auto_activate_alarm()
            else:
                auto_deactivate_alarm()

        return jsonify({
            "estado": "automatico",
            "alarm_enabled": config["schedule"]["alarm_enabled"],
            "manual_mode": False
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/schedules", methods=["GET"])
@login_required
def get_schedules():
    """Obtener horarios programados"""
    schedules = config.get("schedule", {}).get("schedules", [])
    auto_enabled = config.get("schedule", {}).get("auto_schedule", False)
    next_changes = scheduler.get_next_schedule()

    return jsonify({
        "schedules": schedules,
        "auto_schedule": auto_enabled,
        "manual_override": scheduler.manual_override,
        "next_changes": next_changes
    })


@app.route("/api/events", methods=["GET"])
@login_required
def get_events():
    """Obtener eventos con filtros"""
    db = SessionLocal()
    try:
        # Parámetros de filtro
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        event_type = request.args.get('event_type')
        search = request.args.get('search')
        limit = request.args.get('limit', 50, type=int)

        # Query base
        query = db.query(Event)

        # Filtro por fecha de inicio
        if start_date:
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Event.timestamp >= start_dt)
            except:
                pass

        # Filtro por fecha de fin
        if end_date:
            try:
                from datetime import datetime, timedelta
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Event.timestamp < end_dt)
            except:
                pass

        # Filtro por tipo de evento
        if event_type and event_type != 'all':
            query = query.filter(Event.event_type == event_type)

        # Búsqueda de texto
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Event.event_type.like(search_pattern)) |
                (Event.info.like(search_pattern))
            )

        # Ordenar y limitar
        events = query.order_by(Event.timestamp.desc()).limit(limit).all()

        # Convertir a diccionario
        events_list = [{
            'id': event.id,
            'event_type': event.event_type,
            'info': event.info,
            'timestamp': event.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for event in events]

        return jsonify({
            'events': events_list,
            'count': len(events_list)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route("/api/events/types", methods=["GET"])
@login_required
def get_event_types():
    """Obtener tipos de eventos únicos"""
    db = SessionLocal()
    try:
        from sqlalchemy import distinct
        event_types = db.query(distinct(Event.event_type)).all()
        types_list = [t[0] for t in event_types]

        return jsonify({
            'types': types_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route("/api/events/export", methods=["GET"])
@login_required
def export_events():
    """Exportar eventos a CSV"""
    db = SessionLocal()
    try:
        import io
        import csv
        from flask import make_response

        # Aplicar los mismos filtros que get_events
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        event_type = request.args.get('event_type')

        query = db.query(Event)

        if start_date:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Event.timestamp >= start_dt)

        if end_date:
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Event.timestamp < end_dt)

        if event_type and event_type != 'all':
            query = query.filter(Event.event_type == event_type)

        events = query.order_by(Event.timestamp.desc()).all()

        # Crear CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Headers
        writer.writerow(['ID', 'Tipo de Evento', 'Información', 'Fecha y Hora'])

        # Datos
        for event in events:
            writer.writerow([
                event.id,
                event.event_type,
                event.info,
                event.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            ])

        # Crear respuesta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=eventos.csv'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route("/api/events/stats", methods=["GET"])
@login_required
def get_event_stats():
    """Obtener estadísticas de eventos"""
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func

        # Eventos hoy
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        events_today = db.query(Event).filter(Event.timestamp >= today_start).count()

        # Eventos esta semana
        week_start = today - timedelta(days=today.weekday())
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        events_week = db.query(Event).filter(Event.timestamp >= week_start_dt).count()

        # Eventos este mes
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        events_month = db.query(Event).filter(Event.timestamp >= month_start_dt).count()

        # Total de eventos
        events_total = db.query(Event).count()

        # Eventos por tipo
        events_by_type = db.query(
            Event.event_type,
            func.count(Event.id)
        ).group_by(Event.event_type).all()

        return jsonify({
            'today': events_today,
            'week': events_week,
            'month': events_month,
            'total': events_total,
            'by_type': [{'type': t, 'count': c} for t, c in events_by_type]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# Limpiar al cerrar
import atexit
atexit.register(lambda: scheduler.stop())

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    finally:
        limpiar()