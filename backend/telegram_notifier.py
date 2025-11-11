import requests
from datetime import datetime


def send_motion_alert(telegram_config):
    """Envía notificación de movimiento detectado a Telegram"""
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
                print(f"✅ Notificación enviada a chat_id {chat_id}")
                success_count += 1
            else:
                print(f"❌ Error enviando a {chat_id}: {response.status_code} - {response.text}")

        print(f"📬 Enviadas correctamente {success_count}/{len(chat_ids)} notificaciones")
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
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200

    except Exception as e:
        print(f"❌ Error en Telegram: {e}")
        return False