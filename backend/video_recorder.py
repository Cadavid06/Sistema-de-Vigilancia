import cv2
import threading
import time
import os
from datetime import datetime


class VideoRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_seconds = 15  # Buffer de 15 segundos
        self.fps = 10
        self.max_frames = self.fps * self.max_buffer_seconds

    def add_frame(self, frame):
        """Agregar frame al buffer circular"""
        with self.buffer_lock:
            self.frames_buffer.append(frame.copy())
            # Mantener solo los últimos X segundos
            if len(self.frames_buffer) > self.max_frames:
                self.frames_buffer.pop(0)

    def record_motion_video(self, duration=5):
        """Grabar video de X segundos y retornar la ruta"""
        try:
            print(f"🎥 Iniciando grabación de {duration} segundos...")

            # Crear nombre de archivo único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/tmp/motion_{timestamp}.mp4"

            # Obtener frames del buffer (los últimos X segundos)
            with self.buffer_lock:
                if len(self.frames_buffer) == 0:
                    print("⚠️ No hay frames en el buffer")
                    return None

                # Tomar frames para el video
                frames_to_save = self.frames_buffer[-int(self.fps * duration):]

                if len(frames_to_save) < self.fps * 2:  # Al menos 2 segundos
                    print("⚠️ No hay suficientes frames para grabar")
                    return None

                # Obtener dimensiones del primer frame
                height, width = frames_to_save[0].shape[:2]

            # Configurar el writer de video con H.264 (mejor compresión)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec MP4
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))

            if not out.isOpened():
                print("❌ Error al crear archivo de video")
                return None

            # Escribir frames al video
            frames_written = 0
            for frame in frames_to_save:
                out.write(frame)
                frames_written += 1

            out.release()

            # Verificar que el archivo se creó
            if os.path.exists(output_path):
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"✅ Video grabado: {output_path}")
                print(f"📹 Frames: {frames_written} | Tamaño: {file_size_mb:.2f} MB")

                # Si es muy grande, intentar reducir calidad
                if file_size_mb > 50:
                    print("⚠️ Video muy grande, comprimiendo...")
                    compressed_path = self._compress_video(output_path)
                    if compressed_path:
                        os.remove(output_path)
                        return compressed_path

                return output_path
            else:
                print("❌ El archivo de video no se creó correctamente")
                return None

        except Exception as e:
            print(f"❌ Error grabando video: {e}")
            return None

    def _compress_video(self, input_path):
        """Comprimir video si es muy grande"""
        try:
            output_path = input_path.replace(".mp4", "_compressed.mp4")

            cap = cv2.VideoCapture(input_path)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            # Reducir resolución a 640x480
            out = cv2.VideoWriter(output_path, fourcc, self.fps, (640, 480))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                # Reducir resolución
                frame_resized = cv2.resize(frame, (640, 480))
                out.write(frame_resized)

            cap.release()
            out.release()

            if os.path.exists(output_path):
                new_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"✅ Video comprimido: {new_size_mb:.2f} MB")
                return output_path

            return None

        except Exception as e:
            print(f"❌ Error comprimiendo video: {e}")
            return None