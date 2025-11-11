import os

def _is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return 'Raspberry Pi' in f.read()
    except:
        return False

SIMULATE_MODE = os.getenv("SVP_SIMULATE", "0") == "1" or not _is_raspberry_pi()

if SIMULATE_MODE:
    print("🟢 Modo simulado: GPIO emulado (Manjaro).")

    def encender_verde(): print("[SIM] 💚 LED verde ON")
    def apagar_verde(): print("[SIM] 💚 LED verde OFF")
    def encender_rojo(): print("[SIM] ❤️  LED rojo ON")
    def apagar_rojo(): print("[SIM] ❤️  LED rojo OFF")
    def encender_buzzer(): print("[SIM] 🔊 Buzzer ON")
    def apagar_buzzer(): print("[SIM] 🔊 Buzzer OFF")
    def limpiar(): print("[SIM] 🧹 GPIO cleanup")

    # Encender verde al importar (simulado)
    encender_verde()

else:
    try:
        import RPi.GPIO as GPIO
        print("🟢 Modo Raspberry Pi: GPIO real activado.")

        # Pines (los leeremos de config más adelante, pero por ahora hardcode)
        LED_VERDE_PIN = 23
        LED_ROJO_PIN = 24
        BUZZER_PIN = 22

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

        # ✅ Encender LED verde al iniciar (sistema en operación)
        encender_verde()
        apagar_rojo()
        apagar_buzzer()

    except Exception as e:
        print(f"⚠️ Error con RPi.GPIO: {e}. Modo simulado forzado.")
        SIMULATE_MODE = True
        # Repetir funciones simuladas + encender verde
        def encender_verde(): print("[SIM] 💚 LED verde ON")
        def apagar_verde(): print("[SIM] 💚 LED verde OFF")
        def encender_rojo(): print("[SIM] ❤️  LED rojo ON")
        def apagar_rojo(): print("[SIM] ❤️  LED rojo OFF")
        def encender_buzzer(): print("[SIM] 🔊 Buzzer ON")
        def apagar_buzzer(): print("[SIM] 🔊 Buzzer OFF")
        def limpiar(): print("[SIM] 🧹 GPIO cleanup")
        encender_verde()