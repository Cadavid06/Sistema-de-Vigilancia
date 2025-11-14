import requests
from datetime import datetime
import os
import cv2
import tempfile
import time


def send_motion_alert(telegram_config, video_path=None):
    """Envía notificación Completa"""
    try:
        token = telegram_config.get("token")
        chat_id = telegram_config.get("chat_id", [])

        if not token or not chat_id:
            print("⚠️ Token o Chat ID de Telegram no configurados")
            return False

        # Mensaje de alerta
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"🚨 *ALARMA ACTIVADA*\n\n"
        message += f"⏰ Hora: {timestamp}\n"
        message += f"📹 Movimiento detectado en la cámara\n"
        message += f"🎥 Enviando video...\n"
        message += f"🏠 Sistema de Vigilancia"

        # Enviar mensaje
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        success_count = 0

        for chat_ids in chat_id:
            data = {
                "chat_id": chat_ids,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                print(f"✅ Notificación enviada a chat_id {chat_ids}")
                success_count += 1
            else:
                print(f"❌ Error enviando a {chat_ids}: {response.status_code} - {response.text}")

            if video_path and os.path.exists(video_path):
                try:
                    video_size_mb = os.path.getsize(video_path) / (1024 * 1024)

                    if video_size_mb > 50:
                        print("⚠️ Video muy grande (>50MB), Telegram no lo aceptará")
                        return False

                    url_video = f"https://api.telegram.org/bot{token}/sendVideo"
                    with open(video_path, 'rb') as video_file:
                        files = {'video': video_file}
                        data_video = {
                            'chat_id': chat_ids,
                            'caption': f' Grabación: {timestamp}\n Duración 5s',
                            'supports_streaming': True
                        }
                        response_video = requests.post(url_video, data=data_video, files=files, timeout=120)

                    if response_video.status_code == 200:
                        print(" Video Enviado")
                    else:
                        print(f" Error al enviar video: {response_video.status_code}")

                except Exception as e:
                    print(f"❌ Error enviando video: {e}")


        print(f"📬 Enviadas correctamente {success_count}/{len(chat_id)} notificaciones")
        return success_count > 0

    except Exception as e:
        print(f"❌ Error en Telegram: {e}")
        return False


def send_custom_message(telegram_config, message):
    """Envía un mensaje personalizado a Telegram"""
    try:
        token = telegram_config.get("token")
        chat_id = telegram_config.get("chat_id")

        if not token or not chat_id:
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        success = True

        for chat in chat_id:
            data = {
                "chat_id": chat,
                "text": message,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                print(f"✅ Mensaje enviado a {chat}")
            else:
                print(f"❌ Error enviando a {chat}: {response.status_code} - {response.text}")
                success = False

        return success

    except Exception as e:
        print(f"❌ Error en Telegram: {e}")
        return False