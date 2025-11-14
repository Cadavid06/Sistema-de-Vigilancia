import os, yaml

def _is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except:
        return False


def load_config():
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ No se pudo cargar config.yaml: {e}")
        return {}


config = load_config()
hardware_cfg = config.get("hardware", {})

LED_VERDE_PIN = hardware_cfg.get("led_green_pin", 23)
LED_ROJO_PIN = hardware_cfg.get("led_red_pin", 24)
BUZZER_PIN = hardware_cfg.get("buzzer_pin", 22)

SIMULATE_MODE = not _is_raspberry_pi()


if SIMULATE_MODE:
    print(" Modo simulado: Raspberry Apagada.")

    def encender_verde(): print(f"[SIM] LED verde ON (pin {LED_VERDE_PIN})")
    def apagar_verde(): print(f"[SIM] LED verde OFF (pin {LED_VERDE_PIN})")
    def encender_rojo(): print(f"[SIM] LED rojo ON (pin {LED_ROJO_PIN})")
    def apagar_rojo(): print(f"[SIM] LED rojo OFF (pin {LED_ROJO_PIN})")
    def encender_buzzer(): print(f"[SIM] 🔊 Buzzer ON (pin {BUZZER_PIN})")
    def apagar_buzzer(): print(f"[SIM] 🔊 Buzzer OFF (pin {BUZZER_PIN})")
    def limpiar(): print("[SIM] 🧹 GPIO cleanup")

    encender_verde()

else:
    try:
        import RPi.GPIO as GPIO
        print(" Modo Raspberry Pi: GPIO real activado.")

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(LED_VERDE_PIN, GPIO.OUT)
        GPIO.setup(LED_ROJO_PIN, GPIO.OUT)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)

        def encender_verde(): GPIO.output(LED_VERDE_PIN, GPIO.HIGH)
        def apagar_verde(): GPIO.output(LED_VERDE_PIN, GPIO.LOW)
        def encender_rojo(): GPIO.output(LED_ROJO_PIN, GPIO.HIGH)
        def apagar_rojo(): GPIO.output(LED_ROJO_PIN, GPIO.LOW)
        def encender_buzzer(): GPIO.output(BUZZER_PIN, GPIO.HIGH)
        def apagar_buzzer(): GPIO.output(BUZZER_PIN, GPIO.LOW)
        def limpiar(): GPIO.cleanup()

        encender_verde()
        apagar_rojo()
        apagar_buzzer()

    except Exception as e:
        print(f"⚠️ Error con RPi.GPIO: {e}. Modo simulado forzado.")
        SIMULATE_MODE = True
        def encender_verde(): print(f"[SIM]  LED verde ON (pin {LED_VERDE_PIN})")
        def apagar_verde(): print(f"[SIM]  LED verde OFF (pin {LED_VERDE_PIN})")
        def encender_rojo(): print(f"[SIM]   LED rojo ON (pin {LED_ROJO_PIN})")
        def apagar_rojo(): print(f"[SIM]   LED rojo OFF (pin {LED_ROJO_PIN})")
        def encender_buzzer(): print(f"[SIM] 🔊 Buzzer ON (pin {BUZZER_PIN})")
        def apagar_buzzer(): print(f"[SIM] 🔊 Buzzer OFF (pin {BUZZER_PIN})")
        def limpiar(): print("[SIM] 🧹 GPIO cleanup")
        encender_verde()
