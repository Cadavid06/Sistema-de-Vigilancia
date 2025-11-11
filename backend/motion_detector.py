import cv2
import time
import threading

class MotionDetector:
    def __init__(self, rtsp_url: str, config: dict = None, is_alarm_enabled_func=None):
        self.rtsp_url = rtsp_url
        self.config = config or {}
        self.is_alarm_enabled = is_alarm_enabled_func or (lambda: True)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.alarm_triggered = False  # Alarma activada (LED parpadeando)
        self.led_blink_thread = None
        self.thread = threading.Thread(target=self._capture_frames, daemon=True)
        self.thread.start()

    def _led_blink_loop(self, blink_interval=0.3):
        """Parpadeo continuo del LED rojo mientras la alarma está activa"""
        from gpio_control import encender_rojo, apagar_rojo
        while self.running and self.alarm_triggered and self.is_alarm_enabled():
            encender_rojo()
            time.sleep(blink_interval)
            apagar_rojo()
            time.sleep(blink_interval)
        # Al terminar, apagar LED
        apagar_rojo()

    def _buzzer_pulse(self, duration):
        """Activa el buzzer por un tiempo determinado"""
        from gpio_control import encender_buzzer, apagar_buzzer
        encender_buzzer()
        time.sleep(duration)
        apagar_buzzer()

    def reset_alarm(self):
        """Resetear estado de alarma (llamado desde web al desactivar)"""
        self.alarm_triggered = False
        from gpio_control import apagar_rojo, apagar_buzzer
        apagar_rojo()
        apagar_buzzer()

    def _capture_frames(self):
        # 📖 Leer configuración
        cam_config = self.config.get("camera", {})
        det_config = self.config.get("detection", {})
        hw_config = self.config.get("hardware", {})

        # Parámetros de cámara
        buffer_size = cam_config.get("buffer_size", 1)
        fps = cam_config.get("fps", 10)
        reconnect_delay = cam_config.get("reconnect_delay", 2)
        max_reconnect_attempts = cam_config.get("max_reconnect_attempts", 5)
        transport = cam_config.get("transport", "tcp")

        # 🌐 Configurar transporte RTSP (TCP más estable que UDP)
        import os
        if transport == "tcp":
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|rtsp_flags;prefer_tcp"

        # Parámetros de detección
        min_area = det_config.get("min_area", 5000)
        cooldown = det_config.get("cooldown_seconds", 10)
        motion_skip_frames = det_config.get("process_every_n_frames", 2)
        motion_print_cooldown = det_config.get("log_cooldown_seconds", 5)
        bg_history = det_config.get("background_history", 100)
        detect_shadows = det_config.get("detect_shadows", False)
        sensitivity = det_config.get("sensitivity", 25)

        # Parámetros de hardware
        buzzer_duration = hw_config.get("buzzer_duration", 60)
        led_blink_interval = hw_config.get("led_blink_interval", 0.3)

        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)

        # 🚀 OPTIMIZACIONES DE CAPTURA
        cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
        cap.set(cv2.CAP_PROP_FPS, fps)

        if not cap.isOpened():
            print("❌ Error: No se pudo abrir el stream de la cámara.")
            return

        # 🎯 Background Subtractor con parámetros configurables
        fgbg = cv2.createBackgroundSubtractorMOG2(
            history=bg_history,
            varThreshold=sensitivity,
            detectShadows=detect_shadows
        )

        last_alert = 0  # Para notificaciones de Telegram
        frame_count = 0
        last_motion_print = 0
        reconnect_attempts = 0

        print(
            f"📹 Cámara configurada: {fps} FPS, detección cada {motion_skip_frames + 1} frames, área mínima {min_area}px")
        print(f"🔔 Buzzer: {buzzer_duration}s por detección | Cooldown Telegram: {cooldown}s")

        while self.running:
            ret, frame = cap.read()

            if not ret:
                reconnect_attempts += 1
                if reconnect_attempts >= max_reconnect_attempts:
                    print(f"⚠️ Stream perdido ({reconnect_attempts} intentos). Esperando {reconnect_delay * 5}s...")
                    time.sleep(reconnect_delay * 5)
                    reconnect_attempts = 0
                else:
                    print("⚠️ Stream perdido. Reintentando...")
                    time.sleep(reconnect_delay)

                cap.release()
                cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
                cap.set(cv2.CAP_PROP_FPS, fps)
                continue

            reconnect_attempts = 0

            # 📉 REDUCIR RESOLUCIÓN para procesamiento
            height, width = frame.shape[:2]
            if width > 640:
                scale = 640 / width
                display_frame = frame.copy()
                frame = cv2.resize(frame, (640, int(height * scale)), interpolation=cv2.INTER_LINEAR)
            else:
                display_frame = frame.copy()

            # 🎯 DETECTAR MOVIMIENTO SOLO CADA N FRAMES
            motion = False
            if frame_count % (motion_skip_frames + 1) == 0:
                fgmask = fgbg.apply(frame)

                # Aplicar filtros para reducir ruido
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
                fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, kernel)

                contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area > min_area:
                        motion = True
                        x, y, w, h = cv2.boundingRect(cnt)

                        # Dibujar en el frame de display
                        if width > 640:
                            scale_back = width / 640
                            x = int(x * scale_back)
                            y = int(y * scale_back)
                            w = int(w * scale_back)
                            h = int(h * scale_back)

                        cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                        cv2.putText(display_frame, f"Area: {int(area)}", (x, y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            else:
                fgbg.apply(frame, learningRate=0.01)

            # ✅ LÓGICA DE ALARMA - Persistente hasta desactivación manual
            current_time = time.time()

            if motion and self.is_alarm_enabled():
                # Si es una nueva detección (después del cooldown)
                if (current_time - last_alert) > cooldown:
                    last_alert = current_time

                    # Si no había alarma activa, iniciar LED parpadeante
                    if not self.alarm_triggered:
                        self.alarm_triggered = True
                        print("🚨 ¡ALARMA ACTIVADA! LED parpadeando hasta desactivación manual")

                        # Iniciar parpadeo del LED en thread separado
                        self.led_blink_thread = threading.Thread(
                            target=self._led_blink_loop,
                            args=(led_blink_interval,),
                            daemon=True
                        )
                        self.led_blink_thread.start()
                    else:
                        print("🚨 Nueva detección de movimiento")

                    # Activar buzzer por 60 segundos (en thread separado)
                    threading.Thread(
                        target=self._buzzer_pulse,
                        args=(buzzer_duration,),
                        daemon=True
                    ).start()

                    def save_event():
                        try:
                            from models import get_session_maker, Event
                            db_path = self.config.get("database", {}).get("path", "events.db")
                            SessionLocal = get_session_maker(db_path)
                            db = SessionLocal()
                            evento = Event(
                                event_type = "movimiento_detectado",
                                info = "Movimiento detectado - Alarma activada"
                            )
                            db.add(evento)
                            db.commit()
                            db.close()
                            print("💾 Evento guardado")
                        except Exception as e:
                            print(f"Error guardando evento: {e}")

                    threading.Thread(target=save_event, daemon=True).start()

                    # 📲 Enviar notificación Telegram
                    telegram_config = self.config.get("telegram", {})
                    if telegram_config.get("enabled", False):
                        try:
                            from telegram_notifier import send_motion_alert
                            threading.Thread(
                                target=send_motion_alert,
                                args=(telegram_config,),
                                daemon=True
                            ).start()
                            print("📱 Notificación de Telegram enviada")
                        except ImportError:
                            pass

            elif motion and not self.is_alarm_enabled():
                # Alarma desactivada pero hay movimiento
                if current_time - last_motion_print > motion_print_cooldown:
                    print("👀 Movimiento detectado, pero alarma desactivada.")
                    last_motion_print = current_time

            # 🖼️ Actualizar frame para streaming
            with self.lock:
                self.frame = display_frame.copy()

            frame_count += 1
            time.sleep(0.03)

        cap.release()

    def get_frame(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        self.reset_alarm()
        if self.thread.is_alive():
            self.thread.join(timeout=5)