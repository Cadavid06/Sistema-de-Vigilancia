import cv2
import datetime
import threading
from gpio_control import encender_verde, apagar_verde


class MotionDetector:
    def __init__(self, source=0, min_area=2000):
        # 💡 NOTA: Usar el backend FFMPEG puede ayudar con streams RTSP
        self.capture = cv2.VideoCapture(source, cv2.CAP_FFMPEG)

        # Opcional: Reducir el buffer a 1 para menor latencia, pero puede ser inestable
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Verificar si la cámara se abrió correctamente
        if not self.capture.isOpened():
            print(f"Error: No se pudo abrir la fuente de video: {source}")
            # Considera usar 'return' en lugar de 'exit()' en entornos Flask
            exit()

        self.first_frame = None
        self.min_area = min_area

        # 🔒 Bloqueo para acceso seguro al frame entre hilos
        self.lock = threading.Lock()
        self.frame = None

        # 🏃 Hilo de ejecución en segundo plano
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        """Captura frames de la cámara en un hilo separado."""
        while True:
            success, frame = self.capture.read()

            if not success or frame is None:
                # Reintentar leer o reposicionar si falla
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            # Verificar si el frame tiene el tamaño correcto
            if frame.shape[0] == 0:
                continue

            processed_frame, _ = self._process_frame(frame)

            with self.lock:
                self.frame = processed_frame

    def _process_frame(self, frame):
        """Contiene toda la lógica de detección de movimiento."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.first_frame is None:
            # Captura el primer frame y sigue
            self.first_frame = gray
            return frame, False

        delta = cv2.absdiff(self.first_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) < self.min_area:
                continue
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            motion_detected = True

        if motion_detected:
            encender_verde()
            cv2.putText(
                frame,
                "Movimiento detectado",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
        else:
            apagar_verde()

        return frame, motion_detected

    def get_frame(self):
        """Devuelve el último frame capturado y procesado de forma segura."""
        with self.lock:
            return self.frame
